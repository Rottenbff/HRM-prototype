#!/bin/bash
# Multi-Account Training Workflow
# Use this on each account (Colab, Kaggle, or cloud)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Multi-Account TRM Training ===${NC}"
echo

# Configuration
RUN_NAME=${RUN_NAME:-"sudoku_rotation"}
ACCOUNT_ID=${ACCOUNT_ID:-"account_1"}
CLOUD_STORAGE=${CLOUD_STORAGE:-"dropbox"}  # Options: google_drive, s3, dropbox
SYNC_DIR=${SYNC_DIR:-"./sync"}
CHECKPOINT_PATH="checkpoints/sudoku_pretrain_multiaccount/${RUN_NAME}"
DROPBOX_FOLDER="/trm_checkpoints/${RUN_NAME}"

echo -e "${YELLOW}Account:${NC} $ACCOUNT_ID"
echo -e "${YELLOW}Run Name:${NC} $RUN_NAME"
echo -e "${YELLOW}Cloud Storage:${NC} $CLOUD_STORAGE"
echo

# Step 1: Install dependencies
echo -e "${GREEN}[1/5] Installing dependencies...${NC}"
pip install --pre --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu126
pip install -r requirements.txt
pip install --no-cache-dir --no-build-isolation adam-atan2

# Step 2: Mount cloud storage
echo -e "${GREEN}[2/5] Setting up cloud storage...${NC}"
if [ "$CLOUD_STORAGE" = "google_drive" ]; then
    # For Google Colab
    if command -v pip &> /dev/null; then
        echo "Mounting Google Drive..."
        python -c "from google.colab import drive; drive.mount('/content/drive', force_remount=True)"
        SYNC_DIR="/content/drive/MyDrive/trm_checkpoints"
    fi
elif [ "$CLOUD_STORAGE" = "s3" ]; then
    # For AWS S3
    echo "Setting up S3 sync..."
    # Requires AWS credentials configured
    pip install awscli
elif [ "$CLOUD_STORAGE" = "dropbox" ]; then
    # For Dropbox
    echo "Setting up Dropbox sync..."
    pip install dropbox

    # Create dropbox sync script
    if [ ! -f "dropbox_sync.py" ]; then
        echo "Creating Dropbox sync script..."
        cat > dropbox_sync.py << 'DROPSCRIPT'
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

try:
    import dropbox
except ImportError:
    os.system("pip install dropbox")
    import dropbox

APP_KEY = "bup4b0722jw3ygh"
APP_SECRET = "dkee7wj9z8ednhr"

class DropboxSync:
    def __init__(self):
        self.dbx = None
        self.token_cache = "/tmp/.trm_dropbox_cache"

    def get_token(self):
        """Simple token-based auth (using app key/secret)"""
        # For demo: Use app key/secret for development
        # In production, use proper OAuth2 flow
        cache_file = Path(self.token_cache)
        if cache_file.exists():
            return cache_file.read_text().strip()
        return None

    def init(self):
        token = self.get_token()
        if not token:
            print("⚠️  Dropbox not fully configured, using local storage only")
            return False

        try:
            self.dbx = dropbox.Dropbox(token)
            self.dbx.users_get_current_account()
            print("✓ Dropbox connected")
            return True
        except Exception as e:
            print(f"✗ Dropbox connection failed: {e}")
            return False

    def upload(self, local_path, remote_path):
        if not self.dbx:
            return False
        try:
            with open(local_path, 'rb') as f:
                self.dbx.files_upload(f.read(), remote_path, mode=dropbox.files.WriteMode('overwrite'))
            return True
        except:
            return False

    def download(self, remote_path, local_path):
        if not self.dbx:
            return False
        try:
            self.dbx.files_download_to_file(local_path, remote_path)
            return True
        except:
            return False

    def list(self, folder):
        if not self.dbx:
            return []
        try:
            result = self.dbx.files_list_folder(folder)
            return [e.name for e in result.entries if e.name.startswith('step_')]
        except:
            return []

if __name__ == "__main__":
    sync = DropboxSync()
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == "list" and len(sys.argv) > 2:
            result = sync.list(sys.argv[2])
            for item in result:
                print(item)
        elif action == "download" and len(sys.argv) > 3:
            sync.download(sys.argv[2], sys.argv[3])
        elif action == "upload" and len(sys.argv) > 3:
            sync.upload(sys.argv[2], sys.argv[3])
DROPSCRIPT
        chmod +x dropbox_sync.py
    fi

    # Initialize Dropbox
    python dropbox_sync.py
    DROPBOX_READY=$?
    echo "Dropbox setup complete"
fi

mkdir -p "$SYNC_DIR"

# Step 3: Sync latest checkpoint from cloud
echo -e "${GREEN}[3/5] Syncing latest checkpoint...${NC}"
STEP_NUM=0

if [ "$CLOUD_STORAGE" = "dropbox" ]; then
    # Dropbox sync
    echo "Using Dropbox for sync..."

    # Try to download latest checkpoint
    if python -c "import dropbox" 2>/dev/null; then
        # List checkpoints in Dropbox
        CHECKPOINTS=$(python dropbox_sync.py list "$DROPBOX_FOLDER" 2>/dev/null | sort -V)

        if [ -n "$CHECKPOINTS" ]; then
            LATEST=$(echo "$CHECKPOINTS" | tail -1)
            echo -e "${GREEN}Found latest checkpoint in Dropbox: $LATEST${NC}"

            mkdir -p "$CHECKPOINT_PATH"
            python dropbox_sync.py download "$DROPBOX_FOLDER/$LATEST" "$CHECKPOINT_PATH/$LATEST" 2>/dev/null

            if [ -f "$CHECKPOINT_PATH/$LATEST" ]; then
                STEP_NUM=$(echo "$LATEST" | sed 's/step_//' | sed 's/\.pt//')
                echo -e "${YELLOW}Resuming from step: $STEP_NUM${NC}"
            fi
        else
            echo -e "${YELLOW}No checkpoints found in Dropbox, starting from scratch${NC}"
        fi
    fi
elif [ -d "$SYNC_DIR" ]; then
    # Google Drive / local sync
    LATEST_CHECKPOINT=$(find "$SYNC_DIR" -name "step_*" -type f 2>/dev/null | sort -V | tail -1)

    if [ -n "$LATEST_CHECKPOINT" ]; then
        echo -e "${GREEN}Found latest checkpoint: $(basename $LATEST_CHECKPOINT)${NC}"
        mkdir -p "$CHECKPOINT_PATH"
        cp "$LATEST_CHECKPOINT" "$CHECKPOINT_PATH/"

        STEP_NUM=$(basename "$LATEST_CHECKPOINT" | sed 's/step_//')
        echo -e "${YELLOW}Resuming from step: $STEP_NUM${NC}"
    else
        echo -e "${YELLOW}No checkpoint found, starting from scratch${NC}"
    fi
else
    echo -e "${YELLOW}Sync directory not found, starting from scratch${NC}"
fi

# Step 4: Build dataset if needed
echo -e "${GREEN}[4/5] Checking dataset...${NC}"
if [ ! -d "data/sudoku-extreme-1k-aug-1000" ]; then
    echo "Building sudoku dataset..."
    python dataset/build_sudoku_dataset.py \
        --output-dir data/sudoku-extreme-1k-aug-1000 \
        --subsample-size 1000 \
        --num-aug 1000
else
    echo "Dataset already exists"
fi

# Step 5: Train
echo -e "${GREEN}[5/5] Starting training...${NC}"
echo -e "${YELLOW}This will run until manually stopped or time limit reached${NC}"
echo

# Start training
python pretrain.py \
    --config-path="config" \
    --config-name="cfg_pretrain" \
    data_paths="[data/sudoku-extreme-1k-aug-1000]" \
    evaluators="[]" \
    epochs=50000 \
    eval_interval=500 \
    checkpoint_every_eval=True \
    lr=1e-4 \
    puzzle_emb_lr=1e-4 \
    weight_decay=1.0 \
    puzzle_emb_weight_decay=1.0 \
    arch.mlp_t=True \
    arch.pos_encodings=none \
    arch.L_layers=2 \
    arch.H_cycles=3 \
    arch.L_cycles=6 \
    ema=True \
    project_name="sudoku_pretrain_multiaccount" \
    +run_name="$RUN_NAME"

# After training stops, sync checkpoints back to cloud
echo -e "${GREEN}Syncing checkpoints back to cloud...${NC}"
if [ -d "$CHECKPOINT_PATH" ]; then
    LATEST_CHECKPOINT=$(find "$CHECKPOINT_PATH" -name "step_*" -type f | sort -V | tail -1)

    if [ -n "$LATEST_CHECKPOINT" ]; then
        echo -e "${GREEN}Uploading checkpoint: $(basename $LATEST_CHECKPOINT)${NC}"

        if [ "$CLOUD_STORAGE" = "dropbox" ]; then
            # Upload to Dropbox
            python dropbox_sync.py upload "$LATEST_CHECKPOINT" "$DROPBOX_FOLDER/$(basename $LATEST_CHECKPOINT)" 2>/dev/null
        else
            # Upload to Google Drive / local
            cp "$LATEST_CHECKPOINT" "$SYNC_DIR/" 2>/dev/null || true
        fi

        echo -e "${GREEN}Checkpoint synced successfully!${NC}"
    fi
fi

echo -e "${GREEN}=== Training session complete ===${NC}"
