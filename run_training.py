#!/usr/bin/env python3
"""
ONE-FILE DEPLOYMENT - TRM Training
Run this on any cloud instance. That's it.

Usage:
    python run_training.py

Everything else is automatic.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# ============================================================================
# CONFIGURATION (Change these to customize)
# ============================================================================

ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "account_1")
RUN_NAME = os.environ.get("RUN_NAME", "sudoku_rotation")

# Your Dropbox API (pre-configured)
# Note: For Jupyter notebooks, use local storage (no interactive input)
# To enable Dropbox: Set DROPBOX_ACCESS_TOKEN env var before running
DROPBOX_APP_KEY = "bup4b0722jw3ygh"
DROPBOX_APP_SECRET = "dkee7wj9z8ednhr"
DROPBOX_FOLDER = f"/trm_checkpoints/{RUN_NAME}"

# For Jupyter notebooks: Set this to a real access token to enable Dropbox
# Get token at: https://www.dropbox.com/developers/apps
DROPBOX_ACCESS_TOKEN_HARDCODE = None  # e.g., "sl.BCxxxxxxxxx" (starts with "sl.")
                                     # Leave as None to use local storage

# Training config
TRAINING_STEPS = 50000
CHECKPOINT_INTERVAL = 250  # Save every ~10 minutes (was 500 = ~20 min)
BATCH_SIZE = 768
LEARNING_RATE = 1e-4

# ============================================================================
# AUTO-INSTALL DEPENDENCIES
# ============================================================================

def install(package):
    """Install a package"""
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", package, "-q"],
                      check=True, capture_output=True)
    except:
        pass

# Install all dependencies automatically
print("📦 Installing dependencies...")
install("--upgrade pip wheel setuptools")
install("--pre --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu126")

# Core dependencies
for pkg in ["-r", "requirements.txt"]:
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"],
                      check=True, capture_output=True)
    except:
        pass

# Additional packages
install("--no-cache-dir --no-build-isolation adam-atan2")
install("dropbox")

print("✅ All dependencies installed")
print()

# ============================================================================
# PLATFORM DETECTION
# ============================================================================

PLATFORM = "unknown"
if "google.colab" in sys.modules:
    PLATFORM = "colab"
    from google.colab import drive
    drive.mount('/content/drive', force_remount=True)
    SYNC_DIR = "/content/drive/MyDrive/trm_checkpoints"
    print("🖥️  Platform: Google Colab")
elif os.path.exists('/kaggle'):
    PLATFORM = "kaggle"
    SYNC_DIR = "/kaggle/working/trm_checkpoints"
    print("🖥️  Platform: Kaggle")
else:
    SYNC_DIR = "./sync"
    print("🖥️  Platform: Cloud Instance")

os.makedirs(SYNC_DIR, exist_ok=True)
print()

# ============================================================================
# DROPBOX SYNC (Minimal Implementation)
# ============================================================================

class DropboxSync:
    """Minimal Dropbox client"""
    def __init__(self):
        self.token_cache = "/tmp/.trm_dropbox_cache"
        self.app_key = DROPBOX_APP_KEY
        self.app_secret = DROPBOX_APP_SECRET
        self.token = None

    def get_or_create_token(self):
        """Get or create Dropbox access token"""
        # Check hardcoded token first (for Jupyter notebooks)
        if DROPBOX_ACCESS_TOKEN_HARDCODE:
            if self._test_token(DROPBOX_ACCESS_TOKEN_HARDCODE):
                return DROPBOX_ACCESS_TOKEN_HARDCODE

        # Check cache first
        cache_file = Path(self.token_cache)
        if cache_file.exists():
            try:
                token = cache_file.read_text().strip()
                # Verify token works
                if self._test_token(token):
                    return token
            except:
                pass

        # Try to get token from environment (for automation)
        token = os.environ.get('DROPBOX_ACCESS_TOKEN')
        if token and self._test_token(token):
            # Save for future use
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(token)
            return token

        # No valid token found
        return None

    def _test_token(self, token):
        """Test if a token works"""
        try:
            import dropbox
            dbx = dropbox.Dropbox(token)
            dbx.users_get_current_account()
            return True
        except:
            return False

    def setup_token_interactive(self):
        """Interactive token setup"""
        print()
        print("╔" + "═" * 76 + "╗")
        print("║" + " " * 10 + "🔑 DROPBOX TOKEN SETUP REQUIRED" + " " * 37 + "║")
        print("╚" + "═" * 76 + "╝")
        print()
        print("To enable Dropbox sync, you need an access token.")
        print()
        print("Option 1: Quick Token (Recommended)")
        print("1. Go to: https://www.dropbox.com/developers/apps")
        print("2. Create an app or use existing one")
        print("3. Generate an access token")
        print("4. Copy the token")
        print()
        token = input("Paste your access token here (or press Enter to skip): ").strip()
        print()

        if token and self._test_token(token):
            # Save token
            cache_file = Path(self.token_cache)
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(token)
            print("✅ Token saved! Dropbox sync enabled")
            return token
        else:
            print("⚠️  Invalid token. Using local storage only")
            return None

    def get_token(self):
        """Get access token (try to get/create, fallback to interactive)"""
        if self.token:
            return self.token

        token = self.get_or_create_token()
        if not token:
            # If we're in a notebook or CI environment, don't prompt
            if sys.stdin.isatty() and not os.environ.get('CI'):
                token = self.setup_token_interactive()
            else:
                print("💡 To enable Dropbox sync, set environment variable:")
                print("   export DROPBOX_ACCESS_TOKEN='your_token_here'")
                print("   or run: python run_training.py")
                return None

        self.token = token
        return token

    def list_checkpoints(self, folder):
        """List checkpoints in Dropbox folder"""
        try:
            import dropbox
            token = self.get_token()
            if not token:
                return []

            dbx = dropbox.Dropbox(token)
            result = dbx.files_list_folder(folder)
            checkpoints = [e.name for e in result.entries if e.name.startswith('step_')]
            return sorted(checkpoints)
        except:
            return []

    def download(self, remote_path, local_path):
        """Download checkpoint from Dropbox"""
        try:
            import dropbox
            token = self.get_token()
            if not token:
                return False

            dbx = dropbox.Dropbox(token)
            dbx.files_download_to_file(local_path, remote_path)
            return True
        except:
            return False

    def upload(self, local_path, remote_path):
        """Upload checkpoint to Dropbox"""
        try:
            import dropbox
            token = self.get_token()
            if not token:
                return False

            dbx = dropbox.Dropbox(token)
            with open(local_path, 'rb') as f:
                dbx.files_upload(f.read(), remote_path,
                                mode=dropbox.files.WriteMode('overwrite'))
            return True
        except:
            return False

# Initialize Dropbox sync
print("☁️  Initializing Dropbox sync...")
dropbox = DropboxSync()
token = dropbox.get_token()
dropbox_ok = token is not None

if dropbox_ok:
    print("✅ Dropbox configured and ready")
    print("   Folder: " + DROPBOX_FOLDER)
else:
    print("⚠️  Dropbox not configured, using local storage only")
    print("   Checkpoints will be stored locally only")
    print("💡 To enable Dropbox sync:")
    print("   1. Get a token at: https://www.dropbox.com/developers/apps")
    print("   2. Run: export DROPBOX_ACCESS_TOKEN='your_token'")
    print("   3. Re-run this script")
    print()

# ============================================================================
# DATASET SETUP
# ============================================================================

dataset_path = "data/sudoku-extreme-1k-aug-1000"

print("📊 Checking dataset...")
if not os.path.exists(dataset_path):
    print("Building dataset (this takes ~5-10 minutes)...")

    # Create data directory
    os.makedirs("data", exist_ok=True)

    # Build dataset
    from dataset.build_sudoku_dataset import build_sudoku_dataset
    build_sudoku_dataset(
        output_dir=dataset_path,
        subsample_size=1000,
        num_aug=1000
    )
    print("✅ Dataset built")
else:
    print("✅ Dataset found")
print()

# ============================================================================
# CHECKPOINT MANAGEMENT
# ============================================================================

checkpoint_dir = f"checkpoints/sudoku_pretrain_multiaccount/{RUN_NAME}"
os.makedirs(checkpoint_dir, exist_ok=True)

print("💾 Finding latest checkpoint...")
start_step = 0
latest_checkpoint = None

# Try Dropbox first
if dropbox_ok:
    checkpoints = dropbox.list_checkpoints(DROPBOX_FOLDER)
    if checkpoints:
        latest = checkpoints[-1]
        local_path = f"{checkpoint_dir}/{latest}"
        remote_path = f"{DROPBOX_FOLDER}/{latest}"

        print(f"   Found in Dropbox: {latest}")
        if dropbox.download(remote_path, local_path):
            start_step = int(latest.replace("step_", "").replace(".pt", ""))
            latest_checkpoint = local_path
            print(f"✅ Resuming from step: {start_step}")
        else:
            print("⚠️  Download failed, starting from step 0")
    else:
        print("   No checkpoints in Dropbox")
else:
    # Check local sync directory
    sync_checkpoints = list(Path(SYNC_DIR).glob("step_*"))
    if sync_checkpoints:
        latest = max(sync_checkpoints, key=lambda x: int(x.stem.split("_")[1]))
        local_path = f"{checkpoint_dir}/{latest.name}"
        import shutil
        shutil.copy(latest, local_path)
        start_step = int(latest.stem.split("_")[1])
        latest_checkpoint = local_path
        print(f"✅ Resuming from local checkpoint: {start_step}")
    else:
        print("   No local checkpoints found")

if not latest_checkpoint:
    print("✅ Starting from step 0")
print()

# ============================================================================
# BUILD TRAINING COMMAND
# ============================================================================

cmd = [
    sys.executable, "pretrain.py",
    "--config-path=config",
    "--config-name=cfg_pretrain",
    f"data_paths=['{dataset_path}']",
    "evaluators='[]'",
    f"epochs={TRAINING_STEPS}",
    f"eval_interval={CHECKPOINT_INTERVAL}",
    "checkpoint_every_eval=True",
    f"lr={LEARNING_RATE}",
    f"puzzle_emb_lr={LEARNING_RATE}",
    "weight_decay=1.0",
    "puzzle_emb_weight_decay=1.0",
    "arch.mlp_t=True",
    "arch.pos_encodings=none",
    "arch.L_layers=2",
    "arch.H_cycles=3",
    "arch.L_cycles=6",
    "ema=True",
    f"project_name='sudoku_pretrain_multiaccount'",
    f"+run_name='{RUN_NAME}'"
]

if start_step > 0:
    cmd.append(f"load_checkpoint='{checkpoint_dir}/step_{start_step}'")

# ============================================================================
# START TRAINING
# ============================================================================

print("╔" + "═" * 76 + "╗")
print("║" + " " * 20 + "🚀 STARTING TRAINING NOW" + " " * 35 + "║")
print("╚" + "═" * 76 + "╝")
print()
print(f"Account:      {ACCOUNT_ID}")
print(f"Run Name:     {RUN_NAME}")
print(f"Platform:     {PLATFORM}")
print(f"Starting:     Step {start_step}")
print(f"Target:       {TRAINING_STEPS} steps")
print(f"Checkpoint:   Every {CHECKPOINT_INTERVAL} steps (~10 min)")
print(f"Cloud Sync:   {'Dropbox' if dropbox_ok else 'Local only'}")
print()
print("⏱️  This will run for 45-60 minutes (or until timeout)")
print("💾 Checkpoints auto-save and sync")
print()
print("Press Ctrl+C to stop early (checkpoint will be saved)")
print("─" * 78)
print()

# Start training
try:
    result = subprocess.run(cmd)
except KeyboardInterrupt:
    print("\n\n🛑 Training interrupted by user")
    print("Saving final checkpoint...")

# ============================================================================
# SYNC FINAL CHECKPOINT
# ============================================================================

print()
print("Syncing final checkpoint...")
latest = list(Path(checkpoint_dir).glob("step_*"))
if latest:
    latest = max(latest, key=lambda x: int(x.stem.split("_")[1]))
    final_step = int(latest.stem.split("_")[1])

    if dropbox_ok:
        remote_path = f"{DROPBOX_FOLDER}/{latest.name}"
        if dropbox.upload(str(latest), remote_path):
            print(f"✅ Final checkpoint synced to Dropbox: step_{final_step}")
        else:
            print(f"⚠️  Failed to sync to Dropbox")
    else:
        import shutil
        local_sync = f"{SYNC_DIR}/{latest.name}"
        shutil.copy(latest, local_sync)
        print(f"✅ Final checkpoint saved locally: step_{final_step}")

    print()
    print("╔" + "═" * 76 + "╗")
    print("║" + " " * 28 + "✅ TRAINING COMPLETE" + " " * 31 + "║")
    print("╠" + "═" * 76 + "╣")
    print("║" + " " * 76 + "║")
    print(f"║  Final Step:     {final_step:>5}  / {TRAINING_STEPS}                   ║")
    print(f"║  Progress:       {(final_step/TRAINING_STEPS)*100:>5.1f}%                       ║")
    print("║" + " " * 76 + "║")
    print("║  To continue training on another account:                         ║")
    print("║                                                                      ║")
    print(f"║    ACCOUNT_ID=account_2 RUN_NAME={RUN_NAME} python run_training.py ║")
    print("║" + " " * 76 + "║")
    print("╚" + "═" * 76 + "╝")
else:
    print("⚠️  No checkpoint found")

print()
