#!/bin/bash
# 🚀 Local-First Deployment Script (Rsync + Optional Git)
# Usage: ./scripts/deploy_rsync.sh

SERVER="ubuntu@43.205.90.213"
KEY="keys/myanmar-vpn-key.pem"
REMOTE_DIR="/home/ubuntu/vpn-bot/"

# Ensure key permissions
chmod 600 "$KEY" 2>/dev/null

echo "=========================================="
echo "🚀 Starting Local-First Deployment"
echo "=========================================="

# 1. Git Status Check (Informational)
echo "[1/3] Checking Git Status..."
if [[ -n $(git status -s) ]]; then
    echo "⚠️  Uncommitted changes detected:"
    git status -s
    echo "------------------------------------------"
    echo "NOTE: These changes will be synced to the server immediately."
    echo "You can commit/push them to GitHub later."
    echo "------------------------------------------"
    read -p "Proceed with Sync? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Deployment aborted."
        exit 1
    fi
else
    echo "✅ Working directory clean."
fi

# 2. Rsync Deployment (The "Instant Sync")
echo "------------------------------------------"
echo "[2/3] 📦 Syncing files to remote server..."
# Using rsync to mirror local state. 
# --delete: Removes files on remote that are not present locally (Strict Sync)
rsync -av --delete \
    --exclude '.git/' \
    --exclude '.env' \
    --exclude 'venv/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '*.log' \
    --exclude '*.db' \
    --exclude '.DS_Store' \
    --exclude 'keys/' \
    --exclude 'archive/' \
    --exclude 'remote_diff.txt' \
    --exclude 'ssm_output.txt' \
    --exclude 'ssm-trust-policy.json' \
    -e "ssh -i $KEY -o StrictHostKeyChecking=no" \
    ./ "$SERVER:$REMOTE_DIR"

# 3. Remote Restart
echo "------------------------------------------"
echo "[3/3] 🔄 Restarting remote services..."
ssh -i "$KEY" -o StrictHostKeyChecking=no "$SERVER" "sudo systemctl restart vpn-bot && echo '✅ vpn-bot restarted' && sudo systemctl status vpn-bot --no-pager | head -n 5"

echo "=========================================="
echo "✅ Sync Complete!"
echo "=========================================="

# 4. Optional Git Push
if [[ -n $(git status -s) ]]; then
    echo "💡 You have uncommitted changes."
    read -p "Do you want to Commit and Push to GitHub now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter commit message: " msg
        git add .
        git commit -m "$msg"
        git push origin master
        echo "✅ Changes pushed to GitHub."
    else
        echo "👌 Changes kept local only."
    fi
else
    # Clean, but maybe check if we are ahead of origin
    read -p "Do you want to Push to GitHub? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin master
    fi
fi
