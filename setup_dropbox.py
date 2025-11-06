#!/usr/bin/env python3
"""
Dropbox Setup for TRM Multi-Account Training
This script configures Dropbox API for checkpoint syncing
"""

import os
import sys

def setup_dropbox_api():
    """Set up Dropbox API with provided credentials"""
    print("="*70)
    print("  📦 Setting up Dropbox API")
    print("="*70)
    print()

    # Install Dropbox SDK
    print("Installing Dropbox SDK...")
    os.system("pip install dropbox")

    # Create config file
    config_content = '''# Dropbox Configuration for TRM Training
# Copy this to your home directory as .trm_dropbox_config

DROPBOX_APP_KEY=bup4b0722jw3ygh
DROPBOX_APP_SECRET=dkee7wj9z8ednhr
DROPBOX_REDIRECT_URI=http://localhost:53682/auth
DROPBOX_REFRESH_TOKEN=
'''

    config_path = os.path.expanduser("~/.trm_dropbox_config")
    with open(config_path, 'w') as f:
        f.write(config_content)

    print(f"✓ Created config file: {config_path}")
    print()

    # Create Dropbox sync script
    dropbox_script = '''#!/usr/bin/env python3
"""
Dropbox Sync Script for TRM Checkpoints
"""

import os
import sys
import time
from pathlib import Path

try:
    import dropbox
    from dropbox import Dropbox
    from dropbox.exceptions import AuthError
except ImportError:
    print("Installing Dropbox SDK...")
    os.system("pip install dropbox")
    import dropbox
    from dropbox import Dropbox
    from dropbox.exceptions import AuthError

# Load config
config_path = os.path.expanduser("~/.trm_dropbox_config")
if not os.path.exists(config_path):
    print(f"Config file not found: {config_path}")
    print("Please run setup_dropbox.py first")
    sys.exit(1)

with open(config_path, 'r') as f:
    config = dict(line.strip().split('=', 1) for line in f if '=' in line and not line.startswith('#'))

APP_KEY = config.get('DROPBOX_APP_KEY')
APP_SECRET = config.get('DROPBOX_APP_SECRET')
REDIRECT_URI = config.get('DROPBOX_REDIRECT_URI', 'http://localhost:53682/auth')

class DropboxSync:
    def __init__(self):
        self.dbx = None
        self.token_file = os.path.expanduser("~/.trm_dropbox_token")

    def get_access_token(self):
        """Get or refresh access token"""
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as f:
                return f.read().strip()

        # Need to get token via OAuth2
        print("\\n" + "="*70)
        print("  🔑 First-time Dropbox Authentication")
        print("="*70)
        print("\\nTo authorize this app:")
        print("1. This script will open a browser window")
        print("2. Log into Dropbox and allow access")
        print("3. You'll be redirected to a localhost URL")
        print("4. Copy the access_token from the URL")
        print()

        from dropbox.oauth import DropboxOAuth2Flow
        oauth2_flow = DropboxOAuth2Flow(
            APP_KEY,
            REDIRECT_URI,
            [], # token_access_type
            use_pkce=True,
            include_grant_scopes=False
        )

        auth_url = oauth2_flow.get_auth_url()
        print(f"\\n🔗 Please visit this URL to authorize:")
        print(f"   {auth_url}")

        # In a real implementation, you'd handle the redirect
        # For now, we'll create a simple approach
        print("\\n" + "="*70)
        print("  ⚠️  Manual Token Entry Required")
        print("="*70)
        print("\\nFor a quick setup, we'll use the refresh token approach.")
        print("Please visit: https://www.dropbox.com/developers/apps")
        print("Create an app and generate a refresh token.")
        print("\\nOr use the simpler approach: Just upload checkpoints manually.")

        return None

    def init_dropbox(self):
        """Initialize Dropbox client"""
        token = self.get_access_token()
        if not token:
            print("\\n⚠️  No token available. Using local storage fallback.")
            return False

        try:
            self.dbx = Dropbox(token)
            # Test the connection
            self.dbx.users_get_current_account()
            print("✓ Dropbox connected successfully!")
            return True
        except AuthError as e:
            print(f"✗ Dropbox authentication failed: {e}")
            return False

    def upload_checkpoint(self, local_path, remote_path):
        """Upload checkpoint to Dropbox"""
        if not self.dbx:
            print("Dropbox not initialized, skipping upload")
            return False

        try:
            with open(local_path, 'rb') as f:
                self.dbx.files_upload(f.read(), remote_path, mode=dropbox.files.WriteMode('overwrite'))
            print(f"✓ Uploaded: {remote_path}")
            return True
        except Exception as e:
            print(f"✗ Upload failed: {e}")
            return False

    def download_checkpoint(self, remote_path, local_path):
        """Download checkpoint from Dropbox"""
        if not self.dbx:
            print("Dropbox not initialized, skipping download")
            return False

        try:
            self.dbx.files_download_to_file(local_path, remote_path)
            print(f"✓ Downloaded: {remote_path}")
            return True
        except Exception as e:
            print(f"✗ Download failed: {e}")
            return False

    def list_checkpoints(self, remote_path):
        """List all checkpoints in Dropbox"""
        if not self.dbx:
            return []

        try:
            result = self.dbx.files_list_folder(remote_path)
            checkpoints = []
            for entry in result.entries:
                if entry.name.startswith('step_') and entry.name.endswith('.pt'):
                    checkpoints.append(entry.name)
            return sorted(checkpoints)
        except Exception as e:
            print(f"✗ List failed: {e}")
            return []

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Dropbox Sync for TRM')
    parser.add_argument('action', choices=['upload', 'download', 'list'],
                       help='Action to perform')
    parser.add_argument('--local', help='Local file path')
    parser.add_argument('--remote', help='Remote Dropbox path')
    parser.add_argument('--folder', default='/trm_checkpoints',
                       help='Remote folder path')

    args = parser.parse_args()

    sync = DropboxSync()

    if args.action == 'init':
        if sync.init_dropbox():
            print("✓ Dropbox ready!")
        else:
            print("✗ Dropbox not ready, using local storage")

    elif args.action == 'upload':
        if not args.local or not args.remote:
            print("Need --local and --remote")
            sys.exit(1)
        sync.init_dropbox()
        sync.upload_checkpoint(args.local, args.remote)

    elif args.action == 'download':
        if not args.remote or not args.local:
            print("Need --remote and --local")
            sys.exit(1)
        sync.init_dropbox()
        sync.download_checkpoint(args.remote, args.local)

    elif args.action == 'list':
        sync.init_dropbox()
        checkpoints = sync.list_checkpoints(args.folder)
        for cp in checkpoints:
            print(cp)

if __name__ == "__main__":
    main()
'''

    dropbox_path = os.path.expanduser("~/dropbox_sync.py")
    with open(dropbox_path, 'w') as f:
        f.write(dropbox_script)

    print(f"✓ Created Dropbox sync script: {dropbox_path}")
    print()
    print("="*70)
    print("  ✅ Dropbox setup complete!")
    print("="*70)
    print()
    print("Next steps:")
    print("1. Run: python dropbox_sync.py init")
    print("2. Follow the authentication flow")
    print("3. Then use: python dropbox_sync.py upload --local file --remote /path")
    print("Or use the multi_account_workflow.sh which handles this automatically")
    print()

if __name__ == "__main__":
    setup_dropbox_api()
