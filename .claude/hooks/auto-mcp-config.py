#!/usr/bin/env python3
"""
Auto-MCP Config Hook - Updates MCP configuration when new repos are added.

Triggered by post-integration-analyze.py when it detects MCP-compatible repos.
Can also be run manually to scan and update.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Paths
ATLAS_ROOT = Path(os.environ.get("ATLAS_ROOT", "C:/Users/New Employee/Downloads/Atlas-OS-main"))
MCP_CONFIG_PATH = ATLAS_ROOT / "Claude n8n" / ".mcp.json"
INTEGRATION_INDEX = ATLAS_ROOT / "Claude n8n" / "daemon" / "integrations" / "integration_index.json"

# MCP detection patterns
MCP_INDICATORS = [
    "mcp.json",
    ".mcp.json",
    "mcp_server.py",
    "mcp-server.js",
    "mcp-server.ts",
    "tooluniverse",
    "mcp_integration",
    "MCPServer",
]

# Template configs for known repo types
MCP_TEMPLATES = {
    "tooluniverse": {
        "command": "python",
        "args": ["-m", "tooluniverse.mcp_server"],
        "env": {
            "TOOLUNIVERSE_CACHE": "C:/Users/New Employee/.claude/cache/tooluniverse"
        },
        "description": "700+ scientific tools"
    },
    "dify": {
        "type": "http",
        "url": "http://localhost:3000/api/mcp",
        "description": "Dify workflow automation platform"
    },
    "cortexon": {
        "command": "python",
        "args": ["-m", "cortexon.mcp_server"],
        "description": "CortexON task automation"
    }
}


def load_mcp_config() -> Dict[str, Any]:
    """Load existing MCP configuration."""
    if MCP_CONFIG_PATH.exists():
        with open(MCP_CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {"mcpServers": {}}


def save_mcp_config(config: Dict[str, Any]):
    """Save MCP configuration."""
    with open(MCP_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


def detect_mcp_support(repo_path: Path) -> Optional[Dict[str, Any]]:
    """Detect if a repo has MCP support and return config template."""
    repo_name = repo_path.name.lower()

    # Check known templates first
    for template_name, template_config in MCP_TEMPLATES.items():
        if template_name in repo_name:
            config = template_config.copy()
            config["_source_repo"] = str(repo_path)
            return {template_name: config}

    # Scan for MCP indicators
    for indicator in MCP_INDICATORS:
        matches = list(repo_path.glob(f"**/{indicator}"))
        if matches:
            # Found MCP support - create basic config
            server_name = repo_name.replace("-", "_").replace(" ", "_")

            # Determine command type
            if any(m.suffix == '.py' for m in matches):
                return {
                    server_name: {
                        "command": "python",
                        "args": [str(matches[0])],
                        "description": f"MCP server from {repo_name}",
                        "_source_repo": str(repo_path)
                    }
                }
            elif any(m.suffix in ['.js', '.ts'] for m in matches):
                return {
                    server_name: {
                        "command": "npx",
                        "args": ["-y", str(matches[0])],
                        "description": f"MCP server from {repo_name}",
                        "_source_repo": str(repo_path)
                    }
                }

    return None


def scan_integrations_for_mcp() -> Dict[str, Any]:
    """Scan integration index for repos with MCP support."""
    new_servers = {}

    if not INTEGRATION_INDEX.exists():
        return new_servers

    with open(INTEGRATION_INDEX, 'r') as f:
        index = json.load(f)

    for repo_name, repo_info in index.get("repos", {}).items():
        repo_path = Path(repo_info.get("path", ""))
        if not repo_path.exists():
            continue

        mcp_config = detect_mcp_support(repo_path)
        if mcp_config:
            new_servers.update(mcp_config)

    return new_servers


def update_mcp_config_from_integrations():
    """Main function - update MCP config with newly integrated repos."""
    config = load_mcp_config()
    existing_servers = set(config.get("mcpServers", {}).keys())

    # Scan for new MCP-capable repos
    new_servers = scan_integrations_for_mcp()

    added = []
    for server_name, server_config in new_servers.items():
        if server_name not in existing_servers:
            config.setdefault("mcpServers", {})[server_name] = server_config
            added.append(server_name)

    if added:
        save_mcp_config(config)
        print(json.dumps({
            "action": "mcp_config_updated",
            "added_servers": added,
            "total_servers": len(config.get("mcpServers", {}))
        }))
    else:
        print(json.dumps({"action": "no_changes", "existing_servers": len(existing_servers)}))


def add_repo_mcp(repo_path: str, server_name: str = None):
    """Manually add a repo's MCP server to config."""
    path = Path(repo_path)
    if not path.exists():
        print(json.dumps({"error": f"Repo path not found: {repo_path}"}))
        return

    mcp_config = detect_mcp_support(path)
    if not mcp_config:
        print(json.dumps({"error": "No MCP support detected in repo"}))
        return

    config = load_mcp_config()

    # Use provided server name or detected name
    if server_name:
        detected_name = list(mcp_config.keys())[0]
        mcp_config[server_name] = mcp_config.pop(detected_name)

    config.setdefault("mcpServers", {}).update(mcp_config)
    save_mcp_config(config)

    print(json.dumps({
        "action": "server_added",
        "servers": list(mcp_config.keys())
    }))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "scan":
            update_mcp_config_from_integrations()
        elif sys.argv[1] == "add" and len(sys.argv) > 2:
            server_name = sys.argv[3] if len(sys.argv) > 3 else None
            add_repo_mcp(sys.argv[2], server_name)
        else:
            print("Usage: auto-mcp-config.py [scan|add <repo_path> [server_name]]")
    else:
        update_mcp_config_from_integrations()
