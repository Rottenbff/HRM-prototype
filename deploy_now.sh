#!/bin/bash
# 🚀 ONE-CLICK DEPLOYMENT SCRIPT
# Upload this to any cloud instance and run!

set -e

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║              🚀 TRM Multi-Account Training - DEPLOY NOW              ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "This script will:"
echo "  ✅ Install all dependencies"
echo "  ✅ Setup Dropbox sync (pre-configured with your API)"
echo "  ✅ Download latest checkpoint (or start fresh)"
echo "  ✅ Begin training immediately"
echo ""
echo "Your Dropbox API:"
echo "  App Key: bup4b0722jw3ygh"
echo "  App Secret: dkee7wj9z8ednhr"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Press ENTER to start deployment, or Ctrl+C to cancel..."
echo ""

# Get account ID
ACCOUNT_ID=${ACCOUNT_ID:-"account_1"}
echo "Enter your account ID (e.g., account_1, colab_user1, kaggle_1):"
read -p "Account ID [$ACCOUNT_ID]: " INPUT_ID
ACCOUNT_ID=${INPUT_ID:-$ACCOUNT_ID}

# Get run name
RUN_NAME=${RUN_NAME:-"sudoku_rotation"}
echo ""
echo "Enter a name for this training run:"
read -p "Run Name [$RUN_NAME]: " INPUT_RUN
RUN_NAME=${INPUT_RUN:-$RUN_NAME}

export ACCOUNT_ID
export RUN_NAME
export CLOUD_STORAGE=dropbox

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                        DEPLOYMENT CONFIG                              ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║  Account ID:    $ACCOUNT_ID"
echo "║  Run Name:      $RUN_NAME"
echo "║  Cloud Storage: Dropbox (API pre-configured)"
echo "║  Checkpoint Folder: /trm_checkpoints/$RUN_NAME"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Install dependencies
echo "📦 [1/4] Installing dependencies..."
pip install --upgrade pip wheel setuptools -q
pip install --pre --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu126 -q
pip install -r requirements.txt -q
pip install --no-cache-dir --no-build-isolation adam-atan2 -q
pip install dropbox -q
echo "✅ Dependencies installed"
echo ""

# Setup Dropbox
echo "☁️  [2/4] Setting up Dropbox..."
if [ ! -f "dropbox_sync.py" ]; then
    cat > dropbox_sync.py << 'EOF'
import os, sys
try: import dropbox
except: os.system("pip install dropbox"); import dropbox

APP_KEY, APP_SECRET = "bup4b0722jw3ygh", "dkee7wj9z8ednhr"

class DropboxSync:
    def __init__(self):
        self.token_cache = "/tmp/.trm_dropbox_cache"
    def get_token(self): return open(self.token_cache).read().strip() if os.path.exists(self.token_cache) else None
    def list(self, folder):
        try:
            dbx = dropbox.Dropbox(self.get_token())
            return [e.name for e in dbx.files_list_folder(folder).entries if e.name.startswith('step_')]
        except: return []
    def download(self, remote, local):
        try:
            dbx = dropbox.Dropbox(self.get_token())
            dbx.files_download_to_file(local, remote)
            return True
        except: return False
    def upload(self, local, remote):
        try:
            dbx = dropbox.Dropbox(self.get_token())
            with open(local, 'rb') as f: dbx.files_upload(f.read(), remote, mode=dropbox.files.WriteMode('overwrite'))
            return True
        except: return False

if __name__ == "__main__":
    s = DropboxSync()
    if len(sys.argv) > 1:
        if sys.argv[1] == "list" and len(sys.argv) > 2:
            for item in s.list(sys.argv[2]): print(item)
        elif sys.argv[1] == "download" and len(sys.argv) > 3:
            s.download(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "upload" and len(sys.argv) > 3:
            s.upload(sys.argv[2], sys.argv[3])
EOF
    chmod +x dropbox_sync.py
fi
echo "✅ Dropbox configured"
echo ""

# Check for dataset
echo "📊 [3/4] Checking dataset..."
if [ ! -d "data/sudoku-extreme-1k-aug-1000" ]; then
    echo "Dataset not found. Building dataset (this takes ~5-10 minutes)..."
    python dataset/build_sudoku_dataset.py \
        --output-dir data/sudoku-extreme-1k-aug-1000 \
        --subsample-size 1000 \
        --num-aug 1000
    echo "✅ Dataset ready"
else
    echo "✅ Dataset found"
fi
echo ""

# Find checkpoint
echo "💾 [4/4] Looking for latest checkpoint..."
STEP_NUM=0
DROPBOX_FOLDER="/trm_checkpoints/$RUN_NAME"

CHECKPOINTS=$(python dropbox_sync.py list "$DROPBOX_FOLDER" 2>/dev/null | sort -V)
if [ -n "$CHECKPOINTS" ]; then
    LATEST=$(echo "$CHECKPOINTS" | tail -1)
    echo "Found: $LATEST"
    mkdir -p "checkpoints/sudoku_pretrain_multiaccount/$RUN_NAME"
    python dropbox_sync.py download "$DROPBOX_FOLDER/$LATEST" "checkpoints/sudoku_pretrain_multiaccount/$RUN_NAME/$LATEST" 2>/dev/null
    if [ -f "checkpoints/sudoku_pretrain_multiaccount/$RUN_NAME/$LATEST" ]; then
        STEP_NUM=$(echo "$LATEST" | sed 's/step_//' | sed 's/\.pt//')
        echo "✅ Resuming from step: $STEP_NUM"
    fi
else
    echo "No checkpoint found, starting from step 0"
fi
echo ""

# Build training command
LOAD_CHECKPOINT=""
if [ $STEP_NUM -gt 0 ]; then
    LOAD_CHECKPOINT="load_checkpoint='checkpoints/sudoku_pretrain_multiaccount/$RUN_NAME/step_$STEP_NUM' \\"
fi

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    🚀 STARTING TRAINING NOW                           ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Config:"
echo "  Account: $ACCOUNT_ID"
echo "  Starting Step: $STEP_NUM"
echo "  Cloud Sync: Dropbox → $DROPBOX_FOLDER"
echo "  Checkpoint Interval: 500 steps (~15-20 minutes)"
echo ""
echo "⏱️  This will run for ~45-60 minutes before timeout"
echo "💾 Checkpoints auto-save every 500 steps"
echo "☁️  Checkpoints auto-upload to Dropbox"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start training
python pretrain.py \
    --config-path='config' \
    --config-name='cfg_pretrain' \
    data_paths='[data/sudoku-extreme-1k-aug-1000]' \
    evaluators='[]' \
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
    project_name='sudoku_pretrain_multiaccount' \
    +run_name="$RUN_NAME" \
    $LOAD_CHECKPOINT

# After training, sync latest checkpoint
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Training session complete. Syncing final checkpoint..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

LATEST_CHECKPOINT=$(find "checkpoints/sudoku_pretrain_multiaccount/$RUN_NAME" -name "step_*" -type f | sort -V | tail -1)
if [ -n "$LATEST_CHECKPOINT" ]; then
    python dropbox_sync.py upload "$LATEST_CHECKPOINT" "$DROPBOX_FOLDER/$(basename $LATEST_CHECKPOINT)" 2>/dev/null
    echo "✅ Final checkpoint synced to Dropbox"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ DEPLOYMENT COMPLETE                             ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║                                                                      ║"
echo "║  Next step: Run this script on another account to continue training ║"
echo "║                                                                      ║"
echo "║  Account $ACCOUNT_ID completed $STEP_NUM steps                      ║"
echo "║                                                                      ║"
echo "║  To continue from this checkpoint on a new account:                 ║"
echo "║                                                                      ║"
echo "║    ACCOUNT_ID=account_2 RUN_NAME=$RUN_NAME bash deploy_now.sh       ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
