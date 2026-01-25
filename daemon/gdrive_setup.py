#!/usr/bin/env python3
"""
Google Drive OAuth Setup

Run this once to authenticate with Google Drive.
After running, you'll have credentials stored for automated access.

Steps:
1. Go to https://console.cloud.google.com/
2. Create a new project (or select existing)
3. Enable "Google Drive API"
4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID
5. Application type: Desktop app
6. Download JSON → save as ~/.atlas/gdrive_credentials/credentials.json
7. Run this script: python gdrive_setup.py
"""

import sys
from pathlib import Path

# Credentials location
CREDS_DIR = Path.home() / ".atlas" / "gdrive_credentials"
CREDS_FILE = CREDS_DIR / "credentials.json"
TOKEN_FILE = CREDS_DIR / "token.json"

def check_pydrive():
    """Check if PyDrive2 is installed."""
    try:
        from pydrive2.auth import GoogleAuth
        from pydrive2.drive import GoogleDrive
        return True
    except ImportError:
        print("PyDrive2 not installed. Run: pip install PyDrive2")
        return False

def setup_credentials_dir():
    """Create credentials directory."""
    CREDS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Credentials directory: {CREDS_DIR}")

def check_credentials_file():
    """Check if credentials.json exists."""
    if not CREDS_FILE.exists():
        print(f"""
ERROR: credentials.json not found at {CREDS_FILE}

To get credentials:
1. Go to https://console.cloud.google.com/
2. Create project → Enable "Google Drive API"
3. Credentials → Create OAuth 2.0 Client ID → Desktop app
4. Download JSON → save as: {CREDS_FILE}

Then run this script again.
""")
        return False
    return True

def authenticate():
    """Run OAuth flow and save token."""
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive

    # Create settings.yaml for PyDrive
    settings_file = CREDS_DIR / "settings.yaml"
    settings_content = f"""
client_config_file: {CREDS_FILE}
save_credentials: True
save_credentials_backend: file
save_credentials_file: {TOKEN_FILE}
get_refresh_token: True
oauth_scope:
  - https://www.googleapis.com/auth/drive
"""
    settings_file.write_text(settings_content)

    # Authenticate
    gauth = GoogleAuth(settings_file=str(settings_file))

    # Try to load saved credentials
    gauth.LoadCredentialsFile(str(TOKEN_FILE))

    if gauth.credentials is None:
        # No credentials - run OAuth flow
        print("\nOpening browser for Google authentication...")
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        # Refresh expired token
        print("Refreshing expired token...")
        gauth.Refresh()
    else:
        # Credentials valid
        print("Using existing valid credentials")

    # Save credentials
    gauth.SaveCredentialsFile(str(TOKEN_FILE))

    # Test connection
    drive = GoogleDrive(gauth)

    # List root folder
    file_list = drive.ListFile({'q': "'root' in parents and trashed=false", 'maxResults': 5}).GetList()

    print(f"\n✓ Connected to Google Drive!")
    print(f"  Files in root: {len(file_list)}")
    for f in file_list[:3]:
        print(f"    - {f['title']}")

    return True

def main():
    print("=" * 50)
    print("GOOGLE DRIVE OAUTH SETUP")
    print("=" * 50)

    if not check_pydrive():
        return 1

    setup_credentials_dir()

    if not check_credentials_file():
        return 1

    try:
        if authenticate():
            print(f"\n✓ Setup complete!")
            print(f"  Token saved: {TOKEN_FILE}")
            print(f"\nYou can now use Google Drive integration.")
            return 0
    except Exception as e:
        print(f"\nError during authentication: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
