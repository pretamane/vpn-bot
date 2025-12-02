#!/bin/bash
# 🚀 Local-First Deployment Script (Rsync + Git)
# Usage: ./scripts/deploy_rsync.sh

SERVER="ubuntu@43.205.90.213"
KEY="keys/myanmar-vpn-key.pem"
REMOTE_DIR="/home/ubuntu/vpn-bot/"

# Ensure key permissions
chmod 600 "$KEY" 2>/dev/null

echo "=========================================="
echo "🚀 Starting Local-First Deployment"
echo "=========================================="

# 1. Git Safety Check & Push
echo "[1/3] Checking Git Status..."
if [[ -n $(git status -s) ]]; then
    echo "⚠️  You have uncommitted changes!"
    git status -s
    echo "------------------------------------------"
    read -p "Do you want to commit and push these changes first? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter commit message: " msg
        git add .
        git commit -m "$msg"
        git push origin master
    else
        echo "❌ Deployment aborted. Please commit or stash your changes to ensure history is saved."
        exit 1
    fi
else
    echo "✅ Working directory clean."
    # Always ask to push to ensure remote origin is up to date
    read -p "Do you want to push to GitHub before deploying? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin master
    fi
fi

# 2. Rsync Deployment
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
    -e "ssh -i $KEY -o StrictHostKeyChecking=no" \
    ./ "$SERVER:$REMOTE_DIR"

# 3. Remote Restart
echo "------------------------------------------"
echo "[3/3] 🔄 Restarting remote services..."
ssh -i "$KEY" -o StrictHostKeyChecking=no "$SERVER" "sudo systemctl restart vpn-bot && echo '✅ vpn-bot restarted' && sudo systemctl status vpn-bot --no-pager | head -n 5"

echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
