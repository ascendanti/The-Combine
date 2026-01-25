#!/usr/bin/env python3
"""GitHub Webhook Handler - Converts GitHub events to daemon tasks.

Run with: python github_webhook.py --port 8080
Configure GitHub webhook to point to: http://your-ip:8080/webhook
"""

import json
import hmac
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import os
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from task_queue import TaskQueue, TaskPriority


class WebhookHandler(BaseHTTPRequestHandler):
    queue = TaskQueue()
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")

    def do_POST(self):
        if self.path != "/webhook":
            self.send_error(404)
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        # Verify signature if secret configured
        if self.secret:
            signature = self.headers.get('X-Hub-Signature-256', '')
            if not self._verify_signature(body, signature):
                self.send_error(401, "Invalid signature")
                return

        try:
            payload = json.loads(body.decode('utf-8'))
            event_type = self.headers.get('X-GitHub-Event', 'unknown')
            task = self._process_event(event_type, payload)

            if task:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "queued",
                    "task_id": task.id
                }).encode())
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"status": "ignored"}')

        except Exception as e:
            self.send_error(500, str(e))

    def _verify_signature(self, payload: bytes, signature: str) -> bool:
        if not signature.startswith('sha256='):
            return False
        expected = 'sha256=' + hmac.new(
            self.secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    def _process_event(self, event_type: str, payload: dict):
        """Convert GitHub event to task."""

        # Issue opened/labeled
        if event_type == "issues":
            action = payload.get("action")
            issue = payload.get("issue", {})

            if action == "opened":
                return self._create_issue_task(issue, TaskPriority.NORMAL)

            if action == "labeled":
                label = payload.get("label", {}).get("name", "")
                if label in ("urgent", "priority", "claude"):
                    return self._create_issue_task(issue, TaskPriority.HIGH)

        # Issue comment with @claude mention
        if event_type == "issue_comment":
            comment = payload.get("comment", {})
            body = comment.get("body", "")
            if "@claude" in body.lower():
                issue = payload.get("issue", {})
                return self._create_comment_task(issue, comment)

        # PR opened
        if event_type == "pull_request":
            action = payload.get("action")
            pr = payload.get("pull_request", {})

            if action == "opened":
                return self._create_pr_review_task(pr)

        # PR review requested
        if event_type == "pull_request_review":
            if payload.get("action") == "submitted":
                pr = payload.get("pull_request", {})
                review = payload.get("review", {})
                if review.get("state") == "changes_requested":
                    return self._create_pr_fix_task(pr, review)

        return None

    def _create_issue_task(self, issue: dict, priority: TaskPriority):
        title = issue.get("title", "Unknown issue")
        body = issue.get("body", "")[:500]  # Truncate for token efficiency
        number = issue.get("number")
        url = issue.get("html_url", "")

        prompt = f"""GitHub Issue #{number}: {title}

{body}

URL: {url}

Analyze this issue and:
1. Understand the request/bug
2. Create implementation plan
3. Implement fix/feature
4. Create PR with changes"""

        return self.queue.add_task(prompt, priority, metadata={
            "source": "github",
            "type": "issue",
            "number": number,
            "url": url
        })

    def _create_comment_task(self, issue: dict, comment: dict):
        title = issue.get("title", "")
        number = issue.get("number")
        comment_body = comment.get("body", "")[:300]
        url = comment.get("html_url", "")

        prompt = f"""GitHub Comment on Issue #{number}: {title}

Comment: {comment_body}

Respond to this @claude mention appropriately."""

        return self.queue.add_task(prompt, TaskPriority.HIGH, metadata={
            "source": "github",
            "type": "comment",
            "issue_number": number,
            "url": url
        })

    def _create_pr_review_task(self, pr: dict):
        title = pr.get("title", "")
        number = pr.get("number")
        body = pr.get("body", "")[:300]
        url = pr.get("html_url", "")

        prompt = f"""Review PR #{number}: {title}

{body}

URL: {url}

Review this PR and provide feedback."""

        return self.queue.add_task(prompt, TaskPriority.NORMAL, metadata={
            "source": "github",
            "type": "pr_review",
            "number": number,
            "url": url
        })

    def _create_pr_fix_task(self, pr: dict, review: dict):
        title = pr.get("title", "")
        number = pr.get("number")
        review_body = review.get("body", "")[:300]

        prompt = f"""Fix PR #{number}: {title}

Review feedback: {review_body}

Address the requested changes."""

        return self.queue.add_task(prompt, TaskPriority.HIGH, metadata={
            "source": "github",
            "type": "pr_fix",
            "number": number
        })

    def log_message(self, format, *args):
        # Suppress default logging
        pass


def run_server(port: int = 8080):
    server = HTTPServer(('0.0.0.0', port), WebhookHandler)
    print(f"GitHub webhook server running on port {port}")
    print(f"Configure webhook URL: http://YOUR_IP:{port}/webhook")
    server.serve_forever()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    run_server(args.port)
