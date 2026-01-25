#!/usr/bin/env python3
"""Simple Google Drive OAuth using google-auth-oauthlib."""

import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']
CREDS_DIR = Path.home() / '.atlas' / 'gdrive_credentials'
CREDS_FILE = CREDS_DIR / 'credentials.json'
TOKEN_FILE = CREDS_DIR / 'token.json'

def main():
    print("=" * 50)
    print("GOOGLE DRIVE OAUTH (Simple)")
    print("=" * 50)

    if not CREDS_FILE.exists():
        print(f"ERROR: {CREDS_FILE} not found")
        return 1

    print(f"Credentials: {CREDS_FILE}")
    print(f"Token will be saved to: {TOKEN_FILE}")
    print()
    print("Opening browser for authentication...")
    print("(If browser doesn't open, copy the URL from below)")
    print()

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDS_FILE),
            SCOPES
        )

        # Run local server for OAuth callback
        creds = flow.run_local_server(
            port=8090,
            prompt='consent',
            success_message='Authentication successful! You can close this window.'
        )

        # Save token
        TOKEN_FILE.write_text(creds.to_json())
        print()
        print(f"[OK] Token saved to: {TOKEN_FILE}")

        # Test connection
        service = build('drive', 'v3', credentials=creds)
        about = service.about().get(fields='user').execute()
        user = about.get('user', {})
        print(f"[OK] Connected as: {user.get('displayName', '?')} ({user.get('emailAddress', '?')})")

        # List some files
        results = service.files().list(pageSize=5, fields="files(id, name)").execute()
        files = results.get('files', [])
        print(f"[OK] Found {len(files)} files in Drive")
        for f in files[:3]:
            print(f"     - {f['name']}")

        print()
        print("=" * 50)
        print("OAUTH COMPLETE - Google Drive ready!")
        print("=" * 50)
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1

if __name__ == '__main__':
    exit(main())
