#!/usr/bin/env python3
"""
Quick Start Script for Multi-Account TRM Training
Run this in a fresh Colab/Kaggle instance to get started in 60 seconds
"""

import os
import sys
import subprocess
from pathlib import Path

def print_banner():
    print("="*70)
    print("  🚀 TRM Multi-Account Training Quick Start")
    print("="*70)
    print()

def get_account_info():
    """Get account ID from user"""
    print("📋 Account Setup")
    print("-" * 70)

    default_id = os.environ.get("ACCOUNT_ID", "account_1")

    # Try to get from environment
    account_id = os.getenv("ACCOUNT_ID", "")

    if not account_id:
        account_id = input(f"Enter account ID (e.g., account_1) [{default_id}]: ").strip()
        if not account_id:
            account_id = default_id

    print(f"✓ Account ID: {account_id}")
    print()

    return account_id

def detect_platform():
    """Detect if we're in Colab, Kaggle, or other"""
    if 'google.colab' in sys.modules:
        return 'colab'
    elif os.path.exists('/kaggle'):
        return 'kaggle'
    else:
        return 'other'

def setup_cloud_storage(platform):
    """Setup cloud storage based on platform"""
    print("☁️  Cloud Storage Setup")
    print("-" * 70)

    if platform == 'colab':
        print("Detected: Google Colab")
        print("Setting up Google Drive...")

        try:
            from google.colab import drive
            drive.mount('/content/drive', force_remount=True)
            sync_dir = "/content/drive/MyDrive/trm_checkpoints"
            print(f"✓ Google Drive mounted at: {sync_dir}")
        except ImportError:
            print("⚠️  google.colab not available, will use local storage")
            sync_dir = "./sync"

    elif platform == 'kaggle':
        print("Detected: Kaggle")
        print("Using Kaggle's persistent storage...")

        # Create directory in Kaggle working directory
        sync_dir = "/kaggle/working/trm_checkpoints"
        print(f"✓ Using Kaggle working directory: {sync_dir}")

    else:
        print("Detected: Other platform")
        sync_dir = "./sync"
        print(f"✓ Using local sync directory: {sync_dir}")

    # Create sync directory
    os.makedirs(sync_dir, exist_ok=True)
    os.environ['SYNC_DIR'] = sync_dir

    print()
    return sync_dir

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing Dependencies")
    print("-" * 70)

    commands = [
        ["pip", "install", "--upgrade", "pip", "wheel", "setuptools"],
        ["pip", "install", "--pre", "--upgrade", "torch", "torchvision", "torchaudio",
         "--index-url", "https://download.pytorch.org/whl/nightly/cu126"],
        ["pip", "install", "-r", "requirements.txt"],
        ["pip", "install", "--no-cache-dir", "--no-build-isolation", "adam-atan2"]
    ]

    for cmd in commands:
        print(f"Running: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning: Command failed (may already be installed): {e}")

    print("✓ Dependencies installed")
    print()

def check_dataset():
    """Check if dataset exists"""
    print("📊 Dataset Check")
    print("-" * 70)

    dataset_path = "data/sudoku-extreme-1k-aug-1000"

    if os.path.exists(dataset_path):
        print(f"✓ Dataset found at: {dataset_path}")
        print()
        return

    print("Dataset not found. Building dataset...")
    print("This will take ~5-10 minutes...")

    try:
        # Create data directory
        os.makedirs("data", exist_ok=True)

        # Build dataset
        cmd = [
            "python", "dataset/build_sudoku_dataset.py",
            "--output-dir", dataset_path,
            "--subsample-size", "1000",
            "--num-aug", "1000"
        ]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✓ Dataset built successfully")
        else:
            print(f"⚠️  Dataset build had issues, but continuing anyway")
            print(f"Error: {result.stderr[:200]}")

    except Exception as e:
        print(f"⚠️  Could not build dataset: {e}")
        print("Will try to continue anyway...")

    print()

def find_latest_checkpoint(sync_dir):
    """Find the latest checkpoint in sync directory"""
    print("💾 Checkpoint Management")
    print("-" * 70)

    checkpoint_path = "checkpoints/sudoku_pretrain_multiaccount/rotating_accounts_v1"

    # Look in sync directory
    if os.path.exists(sync_dir):
        checkpoints = list(Path(sync_dir).glob("step_*"))
        if checkpoints:
            latest = max(checkpoints, key=lambda x: int(x.stem.split("_")[1]))
            print(f"✓ Found latest checkpoint: {latest.name}")

            # Copy to local checkpoint directory
            os.makedirs(checkpoint_path, exist_ok=True)
            import shutil
            shutil.copy(latest, f"{checkpoint_path}/{latest.name}")

            # Extract step number
            step_num = int(latest.stem.split("_")[1])
            print(f"✓ Will resume from step: {step_num}")
            return step_num

    print("✓ No checkpoint found, starting from step 0")
    print()
    return 0

def show_training_command(account_id, start_step):
    """Show the training command"""
    print("🎯 Training Command")
    print("-" * 70)

    print("Run this command to start training:")
    print()
    print("```bash")
    print("python pretrain.py \\")
    print("  --config-path='config' \\")
    print("  --config-name='cfg_pretrain' \\")
    print("  data_paths='[data/sudoku-extreme-1k-aug-1000]' \\")
    print("  evaluators='[]' \\")
    print("  epochs=50000 \\")
    print("  eval_interval=500 \\")
    print("  checkpoint_every_eval=True \\")
    print("  lr=1e-4 \\")
    print("  puzzle_emb_lr=1e-4 \\")
    print("  weight_decay=1.0 \\")
    print("  puzzle_emb_weight_decay=1.0 \\")
    print("  arch.mlp_t=True \\")
    print("  arch.pos_encodings=none \\")
    print("  arch.L_layers=2 \\")
    print("  arch.H_cycles=3 \\")
    print("  arch.L_cycles=6 \\")
    print("  ema=True \\")
    print("  project_name='sudoku_pretrain_multiaccount' \\")
    print("  +run_name='rotating_accounts_v1' \\")
    if start_step > 0:
        print(f"  load_checkpoint='{checkpoint_path}/step_{start_step}' \\")
    print("```")
    print()

    print("⏱️  This will run for ~45-60 minutes before timeout")
    print("💾 Checkpoints will be saved every 500 steps (~15-20 minutes)")
    print("☁️  Checkpoints will be synced to cloud storage")
    print()

def main():
    print_banner()

    # Get account info
    account_id = get_account_info()
    os.environ['ACCOUNT_ID'] = account_id

    # Detect platform
    platform = detect_platform()
    print(f"🖥️  Platform detected: {platform.upper()}")
    print()

    # Setup cloud storage
    sync_dir = setup_cloud_storage(platform)

    # Install dependencies
    install_dependencies()

    # Check dataset
    check_dataset()

    # Find checkpoint
    start_step = find_latest_checkpoint(sync_dir)

    # Show training command
    show_training_command(account_id, start_step)

    print("="*70)
    print("  ✅ Setup complete! Ready to train.")
    print("="*70)
    print()
    print("Next steps:")
    print("1. Copy and paste the training command above")
    print("2. Wait for training to complete (or timeout)")
    print("3. Checkpoints will auto-sync to cloud storage")
    print("4. Next account can pick up where you left off")
    print()
    print("💡 Pro tip: Keep this browser tab open to check progress")
    print()

if __name__ == "__main__":
    main()
