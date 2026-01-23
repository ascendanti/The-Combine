#!/usr/bin/env python3
"""Email Trigger - Submit tasks via email.

Polls IMAP inbox for emails with specific subject prefix.
Converts to daemon tasks.

Usage:
    python email_trigger.py --poll-interval 60

Environment:
    IMAP_SERVER: Mail server (e.g., imap.gmail.com)
    IMAP_USER: Email address
    IMAP_PASSWORD: App password
    EMAIL_PREFIX: Subject prefix to match (default: [CLAUDE])
"""

import imaplib
import email
from email.header import decode_header
import os
import time
import sys
from pathlib import Path
from typing import Optional, List, Tuple

sys.path.insert(0, str(Path(__file__).parent))
from queue import TaskQueue, TaskPriority


class EmailTrigger:
    def __init__(self):
        self.server = os.getenv("IMAP_SERVER", "imap.gmail.com")
        self.user = os.getenv("IMAP_USER", "")
        self.password = os.getenv("IMAP_PASSWORD", "")
        self.prefix = os.getenv("EMAIL_PREFIX", "[CLAUDE]")
        self.queue = TaskQueue()
        self._mail: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> bool:
        if not self.user or not self.password:
            print("IMAP_USER and IMAP_PASSWORD required")
            return False
        try:
            self._mail = imaplib.IMAP4_SSL(self.server)
            self._mail.login(self.user, self.password)
            return True
        except Exception as e:
            print(f"IMAP connection failed: {e}")
            return False

    def disconnect(self):
        if self._mail:
            try:
                self._mail.logout()
            except:
                pass
            self._mail = None

    def poll(self) -> List[Tuple[str, str]]:
        """Poll inbox for matching emails. Returns list of (subject, body)."""
        if not self._mail:
            return []

        tasks = []
        try:
            self._mail.select("INBOX")
            _, messages = self._mail.search(None, "UNSEEN")

            for num in messages[0].split():
                _, msg_data = self._mail.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])

                subject = self._decode_header(msg["Subject"])
                if not subject.upper().startswith(self.prefix.upper()):
                    continue

                body = self._get_body(msg)
                task_title = subject[len(self.prefix):].strip()
                tasks.append((task_title, body))

                # Mark as seen
                self._mail.store(num, "+FLAGS", "\\Seen")

        except Exception as e:
            print(f"Poll error: {e}")

        return tasks

    def _decode_header(self, header: str) -> str:
        if not header:
            return ""
        decoded = decode_header(header)
        parts = []
        for content, encoding in decoded:
            if isinstance(content, bytes):
                parts.append(content.decode(encoding or "utf-8", errors="replace"))
            else:
                parts.append(content)
        return "".join(parts)

    def _get_body(self, msg) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    return payload.decode("utf-8", errors="replace")[:1000]
        else:
            payload = msg.get_payload(decode=True)
            return payload.decode("utf-8", errors="replace")[:1000]
        return ""

    def process_tasks(self, tasks: List[Tuple[str, str]]):
        """Convert emails to daemon tasks."""
        for title, body in tasks:
            # Determine priority from keywords
            priority = TaskPriority.NORMAL
            lower_title = title.lower()
            if "urgent" in lower_title or "asap" in lower_title:
                priority = TaskPriority.URGENT
            elif "high" in lower_title or "important" in lower_title:
                priority = TaskPriority.HIGH

            prompt = f"""Email Task: {title}

{body}

Process this request appropriately."""

            task = self.queue.add_task(prompt, priority, metadata={
                "source": "email",
                "subject": title
            })
            print(f"Created task {task.id[:8]}... from email: {title}")

    def run(self, poll_interval: int = 60):
        """Run continuous polling loop."""
        if not self.connect():
            return

        print(f"Email trigger started. Polling every {poll_interval}s")
        print(f"Watching for: {self.prefix}* subjects")

        try:
            while True:
                tasks = self.poll()
                if tasks:
                    self.process_tasks(tasks)
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.disconnect()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Email trigger for daemon")
    parser.add_argument("--poll-interval", type=int, default=60,
                        help="Seconds between polls")
    parser.add_argument("--test", action="store_true",
                        help="Test connection and exit")

    args = parser.parse_args()

    trigger = EmailTrigger()

    if args.test:
        if trigger.connect():
            print("Connection successful!")
            tasks = trigger.poll()
            print(f"Found {len(tasks)} matching emails")
            trigger.disconnect()
        else:
            print("Connection failed")
            sys.exit(1)
    else:
        trigger.run(args.poll_interval)
