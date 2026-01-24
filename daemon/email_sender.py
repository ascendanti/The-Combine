#!/usr/bin/env python3
"""
Email Sender - Send files and messages via SMTP

Usage:
    python email_sender.py --to adam@example.com --subject "Test" --body "Hello"
    python email_sender.py --to adam@example.com --file /path/to/file.md
    python email_sender.py --to adam@example.com --folder /path/to/folder --pattern "*.md"

Environment Variables:
    SMTP_HOST - SMTP server (default: smtp.gmail.com)
    SMTP_PORT - SMTP port (default: 587)
    SMTP_USER - Email address to send from
    SMTP_PASS - Email password or app password
"""

import os
import sys
import argparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

# Configuration
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")


def send_email(
    to: str,
    subject: str,
    body: str,
    attachments: Optional[List[Path]] = None,
    html: bool = False
) -> bool:
    """
    Send an email with optional attachments.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text or HTML)
        attachments: List of file paths to attach
        html: If True, treat body as HTML

    Returns:
        True if sent successfully, False otherwise
    """
    if not SMTP_USER or not SMTP_PASS:
        print("[ERROR] SMTP_USER and SMTP_PASS environment variables required")
        print("  Set in .env file or environment:")
        print("    SMTP_USER=your-email@gmail.com")
        print("    SMTP_PASS=your-app-password")
        return False

    # Create message
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject

    # Add body
    if html:
        msg.attach(MIMEText(body, "html"))
    else:
        msg.attach(MIMEText(body, "plain"))

    # Add attachments
    if attachments:
        for file_path in attachments:
            if not file_path.exists():
                print(f"[WARN] Attachment not found: {file_path}")
                continue

            with open(file_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={file_path.name}"
                )
                msg.attach(part)

    # Send
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"[OK] Email sent to {to}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False


def send_file(to: str, file_path: Path, subject: Optional[str] = None) -> bool:
    """Send a single file as attachment."""
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return False

    subject = subject or f"File: {file_path.name}"
    body = f"Attached: {file_path.name}\n\nSent from Claude autonomous system."

    return send_email(to, subject, body, attachments=[file_path])


def send_folder(
    to: str,
    folder_path: Path,
    pattern: str = "*",
    subject: Optional[str] = None
) -> bool:
    """Send all files matching pattern in a folder."""
    if not folder_path.exists():
        print(f"[ERROR] Folder not found: {folder_path}")
        return False

    files = list(folder_path.glob(pattern))
    if not files:
        print(f"[WARN] No files matching '{pattern}' in {folder_path}")
        return False

    subject = subject or f"Files from {folder_path.name} ({len(files)} files)"
    body = f"Attached {len(files)} file(s):\n"
    body += "\n".join(f"  - {f.name}" for f in files)
    body += "\n\nSent from Claude autonomous system."

    return send_email(to, subject, body, attachments=files)


def main():
    parser = argparse.ArgumentParser(description="Send emails with attachments")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--subject", help="Email subject")
    parser.add_argument("--body", help="Email body text")
    parser.add_argument("--file", help="Single file to attach")
    parser.add_argument("--folder", help="Folder to attach files from")
    parser.add_argument("--pattern", default="*", help="Glob pattern for folder (default: *)")
    parser.add_argument("--html", action="store_true", help="Treat body as HTML")

    args = parser.parse_args()

    if args.file:
        success = send_file(args.to, Path(args.file), args.subject)
    elif args.folder:
        success = send_folder(args.to, Path(args.folder), args.pattern, args.subject)
    elif args.body:
        success = send_email(args.to, args.subject or "Message from Claude", args.body, html=args.html)
    else:
        print("[ERROR] Provide --file, --folder, or --body")
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
