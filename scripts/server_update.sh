#!/bin/bash
# Script to update the server code from Git and restart services
# This script is intended to run ON THE SERVER

set -e  # Exit on error

PROJECT_DIR="/home/ubuntu/vpn-bot"
SERVICE_NAME="vpn-bot"

echo "=========================================="
echo "🔄 VPN Bot Server Update"
echo "=========================================="
date

# 1. Navigate to project directory
echo "[1/4] Navigating to project directory..."
cd "$PROJECT_DIR" || { echo "❌ Project directory not found!"; exit 1; }

# 2. Pull latest changes
echo "[2/4] Pulling latest changes from Git..."
git fetch origin
git reset --hard origin/master # Force sync to match remote (WARNING: discards local changes)
# git pull origin master

# 3. Update dependencies (if any)
echo "[3/4] Updating dependencies..."
if [ -f "requirements.txt" ]; then
    # Assuming virtualenv is active or using system python if that's how it's set up
    # Adjust python command as needed (e.g., /home/ubuntu/vpn-bot/venv/bin/pip)
    pip3 install -r requirements.txt
fi

# 4. Restart Service
echo "[4/4] Restarting service..."
sudo systemctl restart "$SERVICE_NAME"

# 5. Verify
echo "✅ Update Complete!"
sudo systemctl status "$SERVICE_NAME" --no-pager | head -n 10
