#!/usr/bin/env python3
"""SQLite-backed approval queue for actions requiring human sign-off.

Use this when Claude encounters actions that need user approval before execution.
The user can review and approve/reject items when they return.

Example usage:
    queue = ApprovalQueue()
    approval_id = queue.request_approval(
        action="Install openmemory SDK",
        approval_type=ApprovalType.INSTALL_PACKAGE,
        details={"package": "openmemory-sdk", "version": "1.0.0"}
    )
"""

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict


class ApprovalType(str, Enum):
    INSTALL_PACKAGE = "install_package"
    DELETE_FILES = "delete_files"
    GIT_COMMIT = "git_commit"
    API_CALL = "api_call"
    OTHER = "other"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"  # Approved and action was performed
    EXPIRED = "expired"    # Timed out without decision


@dataclass
class Approval:
    id: str
    action: str
    approval_type: ApprovalType
    status: ApprovalStatus
    details: Optional[Dict[str, Any]]
    requested_at: str
    decided_at: Optional[str] = None
    executed_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    requested_by: Optional[str] = None  # Session or agent that requested

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['approval_type'] = self.approval_type.value
        d['status'] = self.status.value
        return d

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'Approval':
        return cls(
            id=row['id'],
            action=row['action'],
            approval_type=ApprovalType(row['approval_type']),
            status=ApprovalStatus(row['status']),
            details=json.loads(row['details']) if row['details'] else None,
            requested_at=row['requested_at'],
            decided_at=row['decided_at'],
            executed_at=row['executed_at'],
            rejection_reason=row['rejection_reason'],
            requested_by=row['requested_by']
        )

    def summary(self) -> str:
        """One-line summary for display."""
        type_emoji = {
            ApprovalType.INSTALL_PACKAGE: "[PKG]",
            ApprovalType.DELETE_FILES: "[DEL]",
            ApprovalType.GIT_COMMIT: "[GIT]",
            ApprovalType.API_CALL: "[API]",
            ApprovalType.OTHER: "[???]"
        }
        prefix = type_emoji.get(self.approval_type, "[???]")
        return f"{prefix} {self.action[:60]}"


class ApprovalQueue:
    """SQLite-backed approval queue for human sign-off."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent / "approvals.db"

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        conn.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                approval_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                details TEXT,
                requested_at TEXT NOT NULL,
                decided_at TEXT,
                executed_at TEXT,
                rejection_reason TEXT,
                requested_by TEXT
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_approvals_status
            ON approvals(status)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_approvals_type
            ON approvals(approval_type)
        """)

        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def request_approval(
        self,
        action: str,
        approval_type: ApprovalType,
        details: Optional[Dict[str, Any]] = None,
        requested_by: Optional[str] = None
    ) -> str:
        """
        Request approval for an action.

        Args:
            action: Human-readable description of what needs approval
            approval_type: Category of the action
            details: Additional context (files, packages, etc.)
            requested_by: Session/agent identifier

        Returns:
            The approval ID
        """
        approval = Approval(
            id=str(uuid.uuid4()),
            action=action,
            approval_type=approval_type,
            status=ApprovalStatus.PENDING,
            details=details,
            requested_at=datetime.now().isoformat(),
            requested_by=requested_by
        )

        conn = self._get_conn()
        conn.execute("""
            INSERT INTO approvals
            (id, action, approval_type, status, details, requested_at, requested_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            approval.id,
            approval.action,
            approval.approval_type.value,
            approval.status.value,
            json.dumps(approval.details) if approval.details else None,
            approval.requested_at,
            approval.requested_by
        ))
        conn.commit()
        conn.close()

        return approval.id

    def list_pending(self) -> List[Approval]:
        """Get all pending approvals awaiting human decision."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM approvals
            WHERE status = 'pending'
            ORDER BY requested_at ASC
        """).fetchall()
        conn.close()

        return [Approval.from_row(row) for row in rows]

    def approve(self, approval_id: str) -> bool:
        """
        Mark an approval as approved.

        Returns True if successful, False if not found or not pending.
        """
        conn = self._get_conn()
        cursor = conn.execute("""
            UPDATE approvals
            SET status = 'approved', decided_at = ?
            WHERE id = ? AND status = 'pending'
        """, (datetime.now().isoformat(), approval_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    def reject(self, approval_id: str, reason: Optional[str] = None) -> bool:
        """
        Mark an approval as rejected.

        Args:
            approval_id: The approval to reject
            reason: Why it was rejected

        Returns True if successful, False if not found or not pending.
        """
        conn = self._get_conn()
        cursor = conn.execute("""
            UPDATE approvals
            SET status = 'rejected', decided_at = ?, rejection_reason = ?
            WHERE id = ? AND status = 'pending'
        """, (datetime.now().isoformat(), reason, approval_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    def get_approved(self) -> List[Approval]:
        """Get approvals that are approved but not yet executed."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM approvals
            WHERE status = 'approved'
            ORDER BY decided_at ASC
        """).fetchall()
        conn.close()

        return [Approval.from_row(row) for row in rows]

    def mark_executed(self, approval_id: str) -> bool:
        """Mark an approved action as executed."""
        conn = self._get_conn()
        cursor = conn.execute("""
            UPDATE approvals
            SET status = 'executed', executed_at = ?
            WHERE id = ? AND status = 'approved'
        """, (datetime.now().isoformat(), approval_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    def get_approval(self, approval_id: str) -> Optional[Approval]:
        """Get a specific approval by ID (supports partial ID match)."""
        conn = self._get_conn()

        # Try exact match first
        row = conn.execute(
            "SELECT * FROM approvals WHERE id = ?",
            (approval_id,)
        ).fetchone()

        # If not found, try prefix match
        if not row:
            row = conn.execute(
                "SELECT * FROM approvals WHERE id LIKE ? LIMIT 1",
                (f"{approval_id}%",)
            ).fetchone()

        conn.close()
        return Approval.from_row(row) if row else None

    def get_recent(self, limit: int = 20) -> List[Approval]:
        """Get recent approvals regardless of status."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM approvals
            ORDER BY requested_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()

        return [Approval.from_row(row) for row in rows]

    def get_by_type(self, approval_type: ApprovalType, status: Optional[ApprovalStatus] = None) -> List[Approval]:
        """Get approvals filtered by type and optionally status."""
        conn = self._get_conn()

        if status:
            rows = conn.execute("""
                SELECT * FROM approvals
                WHERE approval_type = ? AND status = ?
                ORDER BY requested_at DESC
            """, (approval_type.value, status.value)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM approvals
                WHERE approval_type = ?
                ORDER BY requested_at DESC
            """, (approval_type.value,)).fetchall()

        conn.close()
        return [Approval.from_row(row) for row in rows]

    def cleanup_old(self, days: int = 30) -> int:
        """Remove executed/rejected approvals older than N days."""
        conn = self._get_conn()
        cursor = conn.execute("""
            DELETE FROM approvals
            WHERE status IN ('executed', 'rejected', 'expired')
            AND datetime(decided_at) < datetime('now', ? || ' days')
        """, (f"-{days}",))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected

    def pending_count(self) -> int:
        """Quick count of pending approvals."""
        conn = self._get_conn()
        count = conn.execute(
            "SELECT COUNT(*) FROM approvals WHERE status = 'pending'"
        ).fetchone()[0]
        conn.close()
        return count


def format_approval_display(approval: Approval, verbose: bool = False) -> str:
    """Format an approval for CLI display."""
    status_colors = {
        ApprovalStatus.PENDING: "\033[33m",   # Yellow
        ApprovalStatus.APPROVED: "\033[32m",  # Green
        ApprovalStatus.REJECTED: "\033[31m",  # Red
        ApprovalStatus.EXECUTED: "\033[34m",  # Blue
        ApprovalStatus.EXPIRED: "\033[90m"    # Gray
    }
    reset = "\033[0m"

    color = status_colors.get(approval.status, "")
    short_id = approval.id[:8]

    line = f"{color}[{approval.status.value:8}]{reset} {short_id}... | [{approval.approval_type.value:15}] {approval.action[:50]}"

    if verbose and approval.details:
        line += f"\n           Details: {json.dumps(approval.details)}"
    if verbose and approval.rejection_reason:
        line += f"\n           Reason: {approval.rejection_reason}"

    return line


# CLI interface
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Approval Queue CLI - Manage actions requiring human sign-off"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List approvals
    list_parser = subparsers.add_parser("list", help="List pending approvals")
    list_parser.add_argument("--all", action="store_true", help="Show all approvals, not just pending")
    list_parser.add_argument("--type", choices=[t.value for t in ApprovalType], help="Filter by type")
    list_parser.add_argument("--verbose", "-v", action="store_true", help="Show details")

    # Approve
    approve_parser = subparsers.add_parser("approve", help="Approve an action")
    approve_parser.add_argument("id", help="Approval ID (can be partial)")

    # Reject
    reject_parser = subparsers.add_parser("reject", help="Reject an action")
    reject_parser.add_argument("id", help="Approval ID (can be partial)")
    reject_parser.add_argument("reason", nargs="?", default=None, help="Rejection reason")

    # Request (for testing/manual use)
    request_parser = subparsers.add_parser("request", help="Request a new approval")
    request_parser.add_argument("action", help="Description of the action")
    request_parser.add_argument("--type", choices=[t.value for t in ApprovalType],
                                default="other", help="Approval type")
    request_parser.add_argument("--details", help="JSON details")

    # Get details
    get_parser = subparsers.add_parser("get", help="Get approval details")
    get_parser.add_argument("id", help="Approval ID (can be partial)")

    # Approved (ready to execute)
    subparsers.add_parser("approved", help="List approved actions ready to execute")

    # Count
    subparsers.add_parser("count", help="Count pending approvals")

    args = parser.parse_args()
    queue = ApprovalQueue()

    if args.command == "list":
        if args.all:
            approvals = queue.get_recent(50)
        else:
            approvals = queue.list_pending()

        if args.type:
            approvals = [a for a in approvals if a.approval_type.value == args.type]

        if not approvals:
            print("No approvals found.")
        else:
            for approval in approvals:
                print(format_approval_display(approval, verbose=getattr(args, 'verbose', False)))

    elif args.command == "approve":
        approval = queue.get_approval(args.id)
        if not approval:
            print(f"Approval not found: {args.id}")
            sys.exit(1)

        if approval.status != ApprovalStatus.PENDING:
            print(f"Cannot approve - status is {approval.status.value}")
            sys.exit(1)

        if queue.approve(approval.id):
            print(f"APPROVED: {approval.action}")
            print(f"ID: {approval.id}")
        else:
            print(f"Failed to approve: {args.id}")
            sys.exit(1)

    elif args.command == "reject":
        approval = queue.get_approval(args.id)
        if not approval:
            print(f"Approval not found: {args.id}")
            sys.exit(1)

        if approval.status != ApprovalStatus.PENDING:
            print(f"Cannot reject - status is {approval.status.value}")
            sys.exit(1)

        if queue.reject(approval.id, args.reason):
            print(f"REJECTED: {approval.action}")
            if args.reason:
                print(f"Reason: {args.reason}")
        else:
            print(f"Failed to reject: {args.id}")
            sys.exit(1)

    elif args.command == "request":
        type_map = {t.value: t for t in ApprovalType}
        approval_type = type_map[args.type]

        details = None
        if args.details:
            try:
                details = json.loads(args.details)
            except json.JSONDecodeError:
                print(f"Invalid JSON in --details: {args.details}")
                sys.exit(1)

        approval_id = queue.request_approval(
            action=args.action,
            approval_type=approval_type,
            details=details
        )
        print(f"Requested approval: {approval_id}")
        print(f"Action: {args.action}")
        print(f"Type: {approval_type.value}")

    elif args.command == "get":
        approval = queue.get_approval(args.id)
        if approval:
            print(json.dumps(approval.to_dict(), indent=2))
        else:
            print(f"Approval not found: {args.id}")
            sys.exit(1)

    elif args.command == "approved":
        approved = queue.get_approved()
        if not approved:
            print("No approved actions waiting for execution.")
        else:
            print(f"Actions approved and ready to execute ({len(approved)}):\n")
            for approval in approved:
                print(format_approval_display(approval, verbose=True))

    elif args.command == "count":
        count = queue.pending_count()
        print(f"Pending approvals: {count}")

    else:
        # No command - show summary
        pending = queue.list_pending()
        approved = queue.get_approved()

        print("=== Approval Queue Summary ===\n")
        print(f"Pending:  {len(pending)}")
        print(f"Approved: {len(approved)} (ready to execute)")

        if pending:
            print(f"\n--- Pending Approvals ---")
            for approval in pending[:5]:
                print(format_approval_display(approval))
            if len(pending) > 5:
                print(f"  ... and {len(pending) - 5} more")

        if approved:
            print(f"\n--- Ready to Execute ---")
            for approval in approved:
                print(format_approval_display(approval))

        print("\nUse 'python approvals.py --help' for commands")
