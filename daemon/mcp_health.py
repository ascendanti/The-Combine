#!/usr/bin/env python3
"""
MCP Health Monitor - Ensure MCP servers are stable and responsive.

Addresses cold-start issues and provides health checks for MCP servers.

Usage:
    python daemon/mcp_health.py check         # Check all servers
    python daemon/mcp_health.py warmup        # Pre-warm servers
    python daemon/mcp_health.py status        # Show status dashboard
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import sqlite3

DAEMON_DIR = Path(__file__).parent
PROJECT_DIR = DAEMON_DIR.parent
MCP_CONFIG = PROJECT_DIR / ".mcp.json"
HEALTH_DB = DAEMON_DIR / "mcp_health.db"


@dataclass
class ServerHealth:
    name: str
    status: str  # "healthy", "degraded", "unhealthy", "unknown"
    last_check: str
    response_time_ms: int
    error: Optional[str] = None
    consecutive_failures: int = 0


def init_db():
    """Initialize health tracking database."""
    conn = sqlite3.connect(HEALTH_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS health_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_name TEXT,
            status TEXT,
            response_time_ms INTEGER,
            error TEXT,
            checked_at TEXT
        );

        CREATE TABLE IF NOT EXISTS server_state (
            server_name TEXT PRIMARY KEY,
            status TEXT,
            consecutive_failures INTEGER DEFAULT 0,
            last_healthy TEXT,
            last_check TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_health_server ON health_checks(server_name);
        CREATE INDEX IF NOT EXISTS idx_health_time ON health_checks(checked_at);
    """)
    conn.commit()
    conn.close()


def get_mcp_servers() -> Dict[str, dict]:
    """Load MCP server configurations."""
    if not MCP_CONFIG.exists():
        return {}

    try:
        config = json.loads(MCP_CONFIG.read_text(encoding='utf-8'))
        return config.get("mcpServers", {})
    except Exception as e:
        print(f"[mcp_health] Error loading config: {e}")
        return {}


def check_server(name: str, config: dict) -> ServerHealth:
    """Check health of a single MCP server."""
    start_time = time.time()

    try:
        command = config.get("command", "")
        args = config.get("args", [])

        if not command:
            return ServerHealth(
                name=name,
                status="unknown",
                last_check=datetime.now().isoformat(),
                response_time_ms=0,
                error="No command configured"
            )

        # For stdio-based servers, we check if the command exists
        # and can start without immediate error
        if command in ("node", "python", "npx", "uvx"):
            # Check if base command exists
            result = subprocess.run(
                ["where" if Path(command).suffix == "" else "which", command],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                return ServerHealth(
                    name=name,
                    status="unhealthy",
                    last_check=datetime.now().isoformat(),
                    response_time_ms=int((time.time() - start_time) * 1000),
                    error=f"Command not found: {command}"
                )

        # For HTTP-based servers, try a health endpoint
        if "url" in config:
            import urllib.request
            try:
                url = config["url"].rstrip("/") + "/health"
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        return ServerHealth(
                            name=name,
                            status="healthy",
                            last_check=datetime.now().isoformat(),
                            response_time_ms=int((time.time() - start_time) * 1000)
                        )
            except Exception as e:
                return ServerHealth(
                    name=name,
                    status="degraded",
                    last_check=datetime.now().isoformat(),
                    response_time_ms=int((time.time() - start_time) * 1000),
                    error=str(e)
                )

        # Default: assume healthy if no errors so far
        return ServerHealth(
            name=name,
            status="healthy",
            last_check=datetime.now().isoformat(),
            response_time_ms=int((time.time() - start_time) * 1000)
        )

    except subprocess.TimeoutExpired:
        return ServerHealth(
            name=name,
            status="degraded",
            last_check=datetime.now().isoformat(),
            response_time_ms=5000,
            error="Health check timed out"
        )
    except Exception as e:
        return ServerHealth(
            name=name,
            status="unhealthy",
            last_check=datetime.now().isoformat(),
            response_time_ms=int((time.time() - start_time) * 1000),
            error=str(e)
        )


def record_health(health: ServerHealth):
    """Record health check result."""
    init_db()
    conn = sqlite3.connect(HEALTH_DB)

    # Record check
    conn.execute("""
        INSERT INTO health_checks (server_name, status, response_time_ms, error, checked_at)
        VALUES (?, ?, ?, ?, ?)
    """, (health.name, health.status, health.response_time_ms, health.error, health.last_check))

    # Update state
    if health.status == "healthy":
        conn.execute("""
            INSERT INTO server_state (server_name, status, consecutive_failures, last_healthy, last_check)
            VALUES (?, ?, 0, ?, ?)
            ON CONFLICT(server_name) DO UPDATE SET
                status = excluded.status,
                consecutive_failures = 0,
                last_healthy = excluded.last_healthy,
                last_check = excluded.last_check
        """, (health.name, health.status, health.last_check, health.last_check))
    else:
        conn.execute("""
            INSERT INTO server_state (server_name, status, consecutive_failures, last_check)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(server_name) DO UPDATE SET
                status = excluded.status,
                consecutive_failures = consecutive_failures + 1,
                last_check = excluded.last_check
        """, (health.name, health.status, health.last_check))

    conn.commit()
    conn.close()


def check_all_servers() -> List[ServerHealth]:
    """Check health of all configured MCP servers."""
    servers = get_mcp_servers()
    results = []

    for name, config in servers.items():
        health = check_server(name, config)
        record_health(health)
        results.append(health)

    return results


def warmup_servers():
    """Pre-warm MCP servers to avoid cold-start issues."""
    servers = get_mcp_servers()
    print(f"[mcp_health] Warming up {len(servers)} servers...")

    for name, config in servers.items():
        command = config.get("command", "")
        args = config.get("args", [])

        if command == "npx":
            # Pre-install npx packages
            pkg = args[0] if args else ""
            if pkg:
                print(f"  Pre-warming {name} ({pkg})...")
                try:
                    subprocess.run(
                        ["npm", "list", pkg],
                        capture_output=True,
                        timeout=30
                    )
                except Exception as e:
                    print(f"    Warning: {e}")

        elif command == "uvx":
            # Pre-install uvx packages
            pkg = args[0] if args else ""
            if pkg:
                print(f"  Pre-warming {name} ({pkg})...")
                try:
                    subprocess.run(
                        ["uv", "tool", "install", pkg],
                        capture_output=True,
                        timeout=60
                    )
                except Exception as e:
                    print(f"    Warning: {e}")

    print("[mcp_health] Warmup complete")


def get_status() -> dict:
    """Get current health status of all servers."""
    init_db()
    conn = sqlite3.connect(HEALTH_DB)

    # Get current state
    cursor = conn.execute("""
        SELECT server_name, status, consecutive_failures, last_healthy, last_check
        FROM server_state
    """)
    states = {
        row[0]: {
            "status": row[1],
            "consecutive_failures": row[2],
            "last_healthy": row[3],
            "last_check": row[4]
        }
        for row in cursor.fetchall()
    }

    # Get recent history
    cursor = conn.execute("""
        SELECT server_name, AVG(response_time_ms), COUNT(*)
        FROM health_checks
        WHERE checked_at > datetime('now', '-1 hour')
        GROUP BY server_name
    """)
    history = {
        row[0]: {"avg_response_ms": int(row[1]), "checks_last_hour": row[2]}
        for row in cursor.fetchall()
    }

    conn.close()

    # Combine with config
    servers = get_mcp_servers()
    result = {}

    for name in servers:
        result[name] = {
            "configured": True,
            **states.get(name, {"status": "unknown", "consecutive_failures": 0}),
            **history.get(name, {"avg_response_ms": 0, "checks_last_hour": 0})
        }

    return result


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python mcp_health.py [check|warmup|status]")
        return

    cmd = sys.argv[1]

    if cmd == "check":
        results = check_all_servers()
        for h in results:
            icon = {"healthy": "[OK]", "degraded": "[!]", "unhealthy": "[X]"}.get(h.status, "[?]")
            print(f"{icon} {h.name}: {h.status} ({h.response_time_ms}ms)")
            if h.error:
                print(f"    Error: {h.error}")

    elif cmd == "warmup":
        warmup_servers()

    elif cmd == "status":
        status = get_status()
        print(json.dumps(status, indent=2))

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
