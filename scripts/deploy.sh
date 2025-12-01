#!/bin/bash
# 🚀 Standard Deployment Script
# Usage: ./scripts/deploy.sh
#
# This script:
# 1. Pushes your local changes to GitHub
# 2. Triggers the server to pull the changes and restart

SERVER="ubuntu@43.205.90.213"
KEY="/home/guest/tzdump/vpn-bot/keys/myanmar-vpn-key.pem"
REMOTE_SCRIPT="/home/ubuntu/vpn-bot/scripts/server_update.sh"

echo "=========================================="
echo "🚀 Starting Git Deployment"
echo "=========================================="

# 1. Ensure local changes are pushed
echo "[1/3] Checking git status..."
if [[ -n $(git status -s) ]]; then
    echo "⚠️  You have uncommitted changes!"
    git status -s
    read -p "Do you want to commit and push these changes first? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter commit message: " msg
        git add .
        git commit -m "$msg"
        git push origin master
    else
        echo "⚠️  Proceeding without pushing local changes (Server will pull what is on remote)"
    fi
else
    echo "✅ Clean working directory"
    # Check if we need to push
    # (Simplified check)
    git push origin master
fi

# 2. Copy the update script to server (in case it changed)
echo "[2/3] Updating server-side script..."
scp -i "$KEY" -o StrictHostKeyChecking=no \
    "scripts/server_update.sh" \
    "${SERVER}:${REMOTE_SCRIPT}"
# Ensure it's executable
ssh -i "$KEY" -o StrictHostKeyChecking=no "$SERVER" "chmod +x ${REMOTE_SCRIPT}"

# 3. Execute update on server
echo "[3/3] Executing update on server..."
ssh -i "$KEY" -o StrictHostKeyChecking=no "$SERVER" "${REMOTE_SCRIPT}"

echo "=========================================="
echo "✅ Deployment Triggered"
echo "=========================================="
