"""
Supervisor API for Clawdbot Integration
Draft: 2026-01-29

This module adds HTTP endpoints so Clawdbot can query and control the daemon.
Intended location: daemon/supervisor_api.py

Endpoints:
  GET  /supervisor/status     - System health and metrics
  GET  /supervisor/tasks      - Query task queue
  POST /supervisor/tasks      - Submit new task
  GET  /supervisor/strategies - List active strategies
  POST /supervisor/notify     - Receive notifications from Clawdbot
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import sqlite3
from pathlib import Path

# Would integrate with existing daemon modules
# from task_queue import TaskQueue
# from strategy_evolution import StrategyEvolution
# from unified_spine import UnifiedSpine

app = FastAPI(title="Atlas Supervisor API", version="1.0.0")

DAEMON_DIR = Path(__file__).parent


# === Models ===

class TaskSubmit(BaseModel):
    prompt: str
    source: str = "clawdbot"
    priority: int = 5
    context: Optional[dict] = None


class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    source: str
    priority: int
    prompt: str
    result: Optional[str] = None


class StatusResponse(BaseModel):
    healthy: bool
    uptime_seconds: float
    tasks_pending: int
    tasks_running: int
    tasks_completed_24h: int
    strategies_active: int
    localai_available: bool
    clawdbot_connected: bool
    last_task_at: Optional[str] = None


class StrategyResponse(BaseModel):
    strategy_id: str
    name: str
    fitness: float
    generation: int
    active: bool


class NotifyRequest(BaseModel):
    event: str  # "task_assigned", "heartbeat", "intervention"
    payload: dict


# === Endpoints ===

@app.get("/supervisor/status", response_model=StatusResponse)
async def get_status():
    """System health and metrics for Clawdbot oversight."""
    # TODO: Wire to actual daemon modules
    conn = sqlite3.connect(DAEMON_DIR / "tasks.db")
    cursor = conn.cursor()
    
    # Count tasks by status
    cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
    task_counts = dict(cursor.fetchall())
    
    # Count recent completions
    cursor.execute("""
        SELECT COUNT(*) FROM tasks 
        WHERE status = 'completed' 
        AND completed_at > datetime('now', '-24 hours')
    """)
    completed_24h = cursor.fetchone()[0]
    
    # Last task timestamp
    cursor.execute("SELECT MAX(created_at) FROM tasks")
    last_task = cursor.fetchone()[0]
    
    conn.close()
    
    # Strategy count (from strategies.db)
    try:
        sconn = sqlite3.connect(DAEMON_DIR / "strategies.db")
        scursor = sconn.cursor()
        scursor.execute("SELECT COUNT(*) FROM strategies WHERE active = 1")
        strategies_active = scursor.fetchone()[0]
        sconn.close()
    except:
        strategies_active = 0
    
    return StatusResponse(
        healthy=True,
        uptime_seconds=0,  # TODO: track actual uptime
        tasks_pending=task_counts.get("pending", 0),
        tasks_running=task_counts.get("in_progress", 0),
        tasks_completed_24h=completed_24h,
        strategies_active=strategies_active,
        localai_available=True,  # TODO: actual health check
        clawdbot_connected=True,
        last_task_at=last_task
    )


@app.get("/supervisor/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, le=100),
    source: Optional[str] = Query(None, description="Filter by source")
):
    """Query task queue."""
    conn = sqlite3.connect(DAEMON_DIR / "tasks.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
    if source:
        query += " AND source = ?"
        params.append(source)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [
        TaskResponse(
            task_id=row["id"],
            status=row["status"],
            created_at=row["created_at"],
            source=row["source"],
            priority=row["priority"],
            prompt=row["prompt"],
            result=row.get("result")
        )
        for row in rows
    ]


@app.post("/supervisor/tasks", response_model=TaskResponse)
async def submit_task(task: TaskSubmit):
    """Submit a new task from Clawdbot."""
    import uuid
    
    task_id = str(uuid.uuid4())[:8]
    created_at = datetime.utcnow().isoformat()
    
    conn = sqlite3.connect(DAEMON_DIR / "tasks.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO tasks (id, prompt, source, priority, status, created_at, context)
        VALUES (?, ?, ?, ?, 'pending', ?, ?)
    """, (task_id, task.prompt, task.source, task.priority, created_at, 
          str(task.context) if task.context else None))
    
    conn.commit()
    conn.close()
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        created_at=created_at,
        source=task.source,
        priority=task.priority,
        prompt=task.prompt
    )


@app.get("/supervisor/strategies", response_model=List[StrategyResponse])
async def list_strategies(active_only: bool = Query(True)):
    """List strategies for Clawdbot oversight."""
    conn = sqlite3.connect(DAEMON_DIR / "strategies.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if active_only:
        cursor.execute("SELECT * FROM strategies WHERE active = 1 ORDER BY fitness DESC")
    else:
        cursor.execute("SELECT * FROM strategies ORDER BY fitness DESC")
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        StrategyResponse(
            strategy_id=row["id"],
            name=row["name"],
            fitness=row["fitness"],
            generation=row["generation"],
            active=bool(row["active"])
        )
        for row in rows
    ]


@app.post("/supervisor/notify")
async def receive_notification(notify: NotifyRequest):
    """Receive notifications from Clawdbot (heartbeat, intervention, etc.)."""
    # Log the notification
    print(f"[Supervisor] Received {notify.event}: {notify.payload}")
    
    # Handle specific events
    if notify.event == "heartbeat":
        return {"ack": True, "status": "healthy"}
    
    elif notify.event == "intervention":
        # Clawdbot is intervening - pause autonomous execution
        # TODO: Wire to continuous_executor
        return {"ack": True, "action": "paused"}
    
    elif notify.event == "task_assigned":
        # Clawdbot assigned us a task directly
        task_id = notify.payload.get("task_id")
        return {"ack": True, "task_id": task_id}
    
    return {"ack": True}


# === Startup ===

def start_supervisor_api(host: str = "0.0.0.0", port: int = 8765):
    """Start the supervisor API server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_supervisor_api()
