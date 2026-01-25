#!/usr/bin/env python3
"""Unified REST API - Single endpoint for all daemon services.

Exposes:
- Task queue management
- Goal/coherence operations
- Decision engine
- Memory operations
- Meta-cognition queries

Usage:
    python api.py --port 5000

Endpoints:
    POST /tasks          - Submit task
    GET  /tasks          - List tasks
    POST /goals          - Add goal
    GET  /goals          - List goals
    POST /decisions      - Evaluate decision
    GET  /calibration    - Get confidence calibration
    GET  /capabilities   - List capabilities
    GET  /health         - Health check
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from task_queue import TaskQueue, TaskPriority
from coherence import GoalCoherenceLayer, GoalTimeframe
from registry import create_default_registry
from decisions import DecisionEngine, Criterion
from metacognition import MetaCognitionEngine, CapabilityLevel
from memory import Memory


class APIHandler(BaseHTTPRequestHandler):
    """Unified API request handler."""

    # Shared instances
    queue = TaskQueue()
    coherence = GoalCoherenceLayer()
    registry = create_default_registry()
    decisions = DecisionEngine()
    metacog = MetaCognitionEngine()
    memory = Memory()

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _read_body(self) -> dict:
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length:
            body = self.rfile.read(content_length)
            return json.loads(body.decode('utf-8'))
        return {}

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        try:
            if path == '/health':
                self._send_json({"status": "ok", "services": [
                    "tasks", "goals", "decisions", "memory", "metacognition"
                ]})

            elif path == '/tasks':
                status = query.get('status', [None])[0]
                limit = int(query.get('limit', [50])[0])
                tasks = self.queue.get_tasks(limit=limit)
                if status:
                    tasks = [t for t in tasks if t.status.value == status]
                self._send_json({
                    "tasks": [t.to_dict() for t in tasks],
                    "count": len(tasks)
                })

            elif path == '/goals':
                goals = self.coherence.get_goal_hierarchy()
                self._send_json({
                    "goals": [g.to_dict() for g in goals],
                    "count": len(goals)
                })

            elif path == '/context':
                context = self.registry.get_unified_context()
                self._send_json(context)

            elif path == '/calibration':
                domain = query.get('domain', [None])[0]
                result = self.metacog.get_calibration(domain)
                self._send_json(result)

            elif path == '/capabilities':
                caps = self.metacog.get_capabilities()
                self._send_json({
                    "capabilities": [{
                        "name": c.capability,
                        "level": c.level.value,
                        "limitations": c.limitations
                    } for c in caps]
                })

            elif path == '/gaps':
                domain = query.get('domain', [None])[0]
                gaps = self.metacog.get_gaps(domain)
                self._send_json({
                    "gaps": [{
                        "id": g.id,
                        "domain": g.domain,
                        "topic": g.topic,
                        "importance": g.importance
                    } for g in gaps]
                })

            elif path == '/performance':
                period = int(query.get('period', [30])[0])
                result = self.metacog.get_performance(period)
                self._send_json(result)

            elif path == '/memory/search':
                q = query.get('q', [''])[0]
                k = int(query.get('k', [5])[0])
                results = self.memory.search(q, k=k)
                self._send_json({
                    "query": q,
                    "results": results
                })

            # Phase 12.4: State Abstractions (Bisimulation)
            elif path == '/abstractions':
                try:
                    from bisimulation import BisimulationEngine
                    engine = BisimulationEngine()
                    abstractions = engine.get_state_abstractions(limit=20)
                    self._send_json({
                        "abstractions": abstractions,
                        "total": len(abstractions)
                    })
                except Exception as e:
                    self._send_json({"abstractions": [], "error": str(e)})

            # Phase 12.4: Policy Transfers
            elif path == '/transfers':
                try:
                    from bisimulation import BisimulationEngine
                    engine = BisimulationEngine()
                    transfers = engine.get_recent_transfers(limit=10)
                    self._send_json({
                        "transfers": transfers,
                        "total": len(transfers)
                    })
                except Exception as e:
                    self._send_json({"transfers": [], "error": str(e)})

            # Phase 12.4: Claim Clusters
            elif path == '/claims/clusters':
                clusters = self.memory.get_claim_clusters(limit=15)
                self._send_json({
                    "clusters": clusters,
                    "total": len(clusters)
                })

            # Phase 12.4: Cross-paper Insights
            elif path == '/claims/cross-paper':
                topic = query.get('topic', [None])[0]
                insights = self.memory.get_cross_paper_insights(topic=topic, min_papers=2)
                self._send_json({
                    "insights": insights[:15],
                    "total": len(insights)
                })

            # Phase 12.4: Similar Claims
            elif path == '/claims/search':
                q = query.get('q', [''])[0]
                k = int(query.get('k', [10])[0])
                claims = self.memory.recall_similar_claims(q, k=k)
                self._send_json({
                    "query": q,
                    "claims": claims,
                    "total": len(claims)
                })

            else:
                self._send_json({"error": "Not found"}, 404)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        try:
            if path == '/tasks':
                prompt = body.get('prompt', '')
                priority_str = body.get('priority', 'normal')
                priority_map = {
                    'low': TaskPriority.LOW,
                    'normal': TaskPriority.NORMAL,
                    'high': TaskPriority.HIGH,
                    'urgent': TaskPriority.URGENT
                }
                priority = priority_map.get(priority_str, TaskPriority.NORMAL)
                metadata = body.get('metadata', {})

                task = self.queue.add_task(prompt, priority, metadata)
                self._send_json({
                    "task_id": task.id,
                    "status": "queued"
                })

            elif path == '/goals':
                title = body.get('title', '')
                description = body.get('description', '')
                timeframe_str = body.get('timeframe', 'medium')
                timeframe = GoalTimeframe(timeframe_str)
                domains = body.get('domains', [])
                parent_id = body.get('parent_id')

                goal = self.coherence.add_goal(
                    title=title,
                    description=description,
                    timeframe=timeframe,
                    domains=domains,
                    parent_id=parent_id
                )
                self._send_json({
                    "goal_id": goal.id,
                    "status": "created"
                })

            elif path == '/decisions':
                title = body.get('title', '')
                criteria_data = body.get('criteria', [])
                context = body.get('context', '')
                risk = body.get('risk_aversion', 0.5)

                criteria = [
                    Criterion(
                        name=c['name'],
                        weight=c['weight'],
                        score=c['score'],
                        confidence=c.get('confidence', 0.7)
                    ) for c in criteria_data
                ]

                decision = self.decisions.evaluate(title, criteria, context, risk)
                self._send_json({
                    "decision_id": decision.id,
                    "expected_value": decision.expected_value,
                    "risk_adjusted": decision.risk_adjusted_value,
                    "confidence": decision.confidence_level.value,
                    "recommendation": decision.recommendation
                })

            elif path == '/coherence/check':
                domain = body.get('domain', '')
                action = body.get('action', {})

                valid, issues = self.registry.check_action(domain, action)
                self._send_json({
                    "valid": valid,
                    "issues": issues
                })

            elif path == '/capabilities':
                capability = body.get('capability', '')
                level_str = body.get('level', 'basic')
                evidence = body.get('evidence', '')
                limitations = body.get('limitations', [])

                self.metacog.assess_capability(
                    capability,
                    CapabilityLevel(level_str),
                    evidence,
                    limitations
                )
                self._send_json({"status": "assessed"})

            elif path == '/gaps':
                domain = body.get('domain', 'general')
                topic = body.get('topic', '')
                description = body.get('description', '')
                importance = body.get('importance', 0.5)

                gap_id = self.metacog.identify_gap(domain, topic, description, importance)
                self._send_json({"gap_id": gap_id})

            elif path == '/memory/add':
                content = body.get('content', '')
                metadata = body.get('metadata', {})
                # Use correct Memory API: store_learning(content, context, tags, confidence)
                learning = self.memory.store_learning(
                    content=content,
                    context=metadata.get('context', ''),
                    tags=metadata.get('tags', []),
                    confidence=metadata.get('confidence', 'medium')
                )
                self._send_json({"status": "stored", "id": learning.id})

            else:
                self._send_json({"error": "Not found"}, 404)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def log_message(self, format, *args):
        # Custom logging
        print(f"[API] {args[0]}")


def run_api(port: int = 5000):
    server = HTTPServer(('0.0.0.0', port), APIHandler)
    print(f"API server running on port {port}")
    print("Endpoints:")
    print("  GET  /health         - Health check")
    print("  GET  /tasks          - List tasks")
    print("  POST /tasks          - Submit task")
    print("  GET  /goals          - List goals")
    print("  POST /goals          - Add goal")
    print("  GET  /context        - Unified context")
    print("  POST /decisions      - Evaluate decision")
    print("  POST /coherence/check - Check action coherence")
    print("  GET  /calibration    - Confidence calibration")
    print("  GET  /capabilities   - List capabilities")
    print("  GET  /gaps           - Knowledge gaps")
    print("  GET  /performance    - Performance metrics")
    print("  GET  /memory/search  - Search memory")
    print("  POST /memory/add     - Add to memory")
    server.serve_forever()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    run_api(args.port)
