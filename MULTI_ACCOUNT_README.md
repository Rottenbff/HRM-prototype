# Multi-Account TRM Training Guide

## Overview

This guide explains how to train TRM on **free H100 instances** by rotating through **multiple accounts** (Google Colab, Kaggle, etc.). Each account provides **1 hour per week**, so by using **8-10 accounts**, you can achieve **8-10 hours per week** of training time and finish in **3-4 weeks** instead of 20+ weeks!

## Strategy

### Time Breakdown
- **1 H100 hour** = ~1000-1500 training steps
- **Target**: 50,000 steps total
- **With 1 account**: 50 hours → 50 weeks
- **With 10 accounts**: 5 hours/account → 5 weeks

### Checkpointing
- **Frequency**: Every 500 steps (~15-20 minutes on H100)
- **Storage**: Cloud storage (Google Drive, S3, Dropbox)
- **Seamless resume**: Each account loads latest checkpoint, trains for ~50 minutes, saves, hands off

## Setup Instructions

### Step 1: Prepare Cloud Storage (Choose One)

#### Option A: Google Drive (Easiest)
```bash
# Works great with Google Colab
# Mounts automatically in Colab
# Free: 15GB storage
```

#### Option B: AWS S3 (Most Reliable)
```bash
# Create S3 bucket
aws s3 mb s3://your-trm-checkpoints

# Configure credentials
aws configure
```

#### Option C: Dropbox
```bash
# Install Dropbox client
pip install dropbox
```

### Step 2: Register Your Accounts

Create a tracking file that all accounts will use:

```bash
# On your local machine or shared location
python rotate_accounts.py register account_1 "John's Colab"
python rotate_accounts.py register account_2 "Jane's Colab"
python rotate_accounts.py register account_3 "Kaggle - Project 1"
# ... continue for all accounts
```

### Step 3: Per-Account Training Script

Each account will run the same script with a unique `ACCOUNT_ID`:

```bash
# For Account 1
ACCOUNT_ID=account_1 RUN_NAME=sudoku_rotation bash multi_account_workflow.sh

# For Account 2
ACCOUNT_ID=account_2 RUN_NAME=sudoku_rotation bash multi_account_workflow.sh

# etc.
```

## Account Rotation Workflow

### For Each Account Session (~1 hour)

1. **Login** to your cloud account (Colab/Kaggle)

2. **Upload** the training files:
   - `multi_account_workflow.sh`
   - `rotate_accounts.py`
   - `config_multi_account.yaml`
   - Source code

3. **Run the workflow**:
   ```bash
   export ACCOUNT_ID=account_X
   export RUN_NAME=sudoku_rotation
   bash multi_account_workflow.sh
   ```

4. **Wait 45-50 minutes** (until time limit or checkpoint saved)

5. **Stop the session** (either manually or when time limit reached)

6. **Next account picks up** from the latest checkpoint

## Training Schedule Example

### Week 1 (10 hours total)
- **Monday**: Account 1 → Step 0 → 1500
- **Tuesday**: Account 2 → 1500 → 3000
- **Wednesday**: Account 3 → 3000 → 4500
- **Thursday**: Account 4 → 4500 → 6000
- **Friday**: Account 5 → 6000 → 7500
- **Saturday**: Account 6 → 7500 → 9000
- **Sunday**: Account 7 → 9000 → 10500

### Continue for 5 weeks...

**Total Time**: 5 weeks × 10 hours/week = 50 hours

**Completion**: ~50,000 steps trained

## Monitoring Progress

### Check Current Status
```bash
python rotate_accounts.py report
```

**Output Example**:
```
╔════════════════════════════════════════════════════════════╗
║           MULTI-ACCOUNT TRAINING PROGRESS REPORT           ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  Total Progress:   23.5% (11,750/50,000 steps)            ║
║                                                            ║
║  Last Update: 2025-01-15T14:30:00                         ║
║                                                            ║
║  Accounts Status:                                         ║
║  ───────────────────────────────────────────────────────── ║
║  account_1     | Steps:   3,000 | Sessions:   2 | ready   ║
║  account_2     | Steps:   2,500 | Sessions:   2 | active  ║
║  Kaggle-1      | Steps:   4,250 | Sessions:   3 | ready   ║
╚════════════════════════════════════════════════════════════╝
```

### Track Specific Account
```bash
python rotate_accounts.py status
```

## Technical Details

### Checkpoint Location
```
checkpoints/
  └─ sudoku_pretrain_multiaccount/
      └─ sudoku_rotation/
          └─ step_500
          └─ step_1000
          └─ step_1500
          └─ ...
```

### What's Saved
- **Model weights**: State dict at each checkpoint
- **Step number**: In filename (`step_XXXX`)
- **EMA weights**: If enabled

### Resume Training
```bash
# Automatic: The script finds the latest checkpoint and resumes
python pretrain.py \
  load_checkpoint=checkpoints/sudoku_pretrain_multiaccount/sudoku_rotation/step_5000 \
  ...
```

## Best Practices

### 1. **Frequent Checkpointing**
   - `eval_interval=500` = checkpoint every 15-20 min
   - Never lose more than 20 minutes of work

### 2. **Account Management**
   - Keep a spreadsheet with account login credentials
   - Rotate accounts evenly to avoid one doing all the work
   - Mark accounts as "active" in tracker

### 3. **Cloud Storage**
   - Use the same cloud storage location for ALL accounts
   - Ensure automatic sync if using Google Drive
   - Keep local backup of checkpoints

### 4. **Training Stability**
   - EMA enabled for smoother training
   - Resume from exact checkpoint (not approximate)
   - Check W&B logs to verify continuity

### 5. **Time Management**
   - Start training 45 minutes before time limit
   - Give 5 minutes for checkpoint sync
   - Don't wait for the very last second

## Expected Costs

### Free Tier Costs
- **Google Colab Pro**: $10/month (unlimited accounts)
- **Kaggle**: Free (30 hours GPU/week per account)
- **Total**: $30-50 for 5 weeks

### What You Get
- **7M parameter model** trained on 1000 Sudoku puzzles
- **Recursive reasoning** with 2-level cycles
- **Full training run** in 5 weeks instead of 25
- **W&B logs** showing training curve

## Troubleshooting

### Issue: Checkpoint not found
```bash
# Check sync directory
ls -la sync/

# Re-download latest checkpoint
find . -name "step_*" -type f | sort -V | tail -5
```

### Issue: Resume failed
```bash
# Check checkpoint integrity
python -c "import torch; state = torch.load('checkpoint.pt'); print(state.keys())"
```

### Issue: Account quota exceeded
```bash
# Skip to next account
# Update tracker to mark account as "quota_exceeded"
python rotate_accounts.py register account_11 "Backup Account"
```

## Alternative: Use Your Own H100

If you have access to an H100 for a few hours:

```bash
# Train continuously for maximum efficiency
python pretrain.py \
  arch=trm \
  data_paths="[data/sudoku-extreme-1k-aug-1000]" \
  epochs=50000 \
  eval_interval=1000 \
  checkpoint_every_eval=True \
  # ... rest of config
```

**Time on H100**: 20-30 hours (continuous)

## Summary

**Multi-account training** lets you:
- ✓ Use free H100 hours efficiently
- ✓ Complete 5 weeks of training in 5 weeks (not 25)
- ✓ No single point of failure
- ✓ Distribute cost across multiple accounts
- ✓ Learn distributed training workflows

**The key**: Frequent checkpointing (every 500 steps) + cloud storage sync = seamless account rotation!

Good luck! 🚀
