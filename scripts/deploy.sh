#!/bin/bash
# Deploy script to sync local code to production server and prevent drift

SERVER="ubuntu@43.205.90.213"
KEY="/home/guest/tzdump/vpn-bot/keys/myanmar-vpn-key.pem"
PROJECT_DIR="/home/guest/tzdump/vpn-bot"

echo "=========================================="
echo "🚀 VPN Bot Deployment Script"
echo "=========================================="

# Step 1: Sync src/ to root (handle dual directory structure)
echo "[1/5] Syncing src/ to root directories locally..."
cp -r "${PROJECT_DIR}/src/bot/"* "${PROJECT_DIR}/bot/" 2>/dev/null || true
cp -r "${PROJECT_DIR}/src/db/"* "${PROJECT_DIR}/db/" 2>/dev/null || true
cp -r "${PROJECT_DIR}/src/services/"* "${PROJECT_DIR}/services/" 2>/dev/null || true
cp -r "${PROJECT_DIR}/src/api/"* "${PROJECT_DIR}/api/" 2>/dev/null || true
echo "   ✅ Local sync complete"

# Step 2: Deploy code to server (both src/ and root/)
echo "[2/5] Deploying code to server..."
rsync -avz --delete -e "ssh -i ${KEY} -o StrictHostKeyChecking=no" \
    "${PROJECT_DIR}/src/" "${SERVER}:/home/ubuntu/vpn-bot/src/"
rsync -avz --delete -e "ssh -i ${KEY} -o StrictHostKeyChecking=no" \
    "${PROJECT_DIR}/bot/" "${SERVER}:/home/ubuntu/vpn-bot/bot/"
rsync -avz --delete -e "ssh -i ${KEY} -o StrictHostKeyChecking=no" \
    "${PROJECT_DIR}/scripts/" "${SERVER}:/home/ubuntu/vpn-bot/scripts/"
echo "   ✅ Code deployed"

# Step 3: Deploy service files
echo "[3/5] Deploying service files..."
scp -i "${KEY}" -o StrictHostKeyChecking=no \
    "${PROJECT_DIR}/scripts/deployment/vpn-bot.service" \
    "${SERVER}:/tmp/vpn-bot.service"
ssh -i "${KEY}" -o StrictHostKeyChecking=no ${SERVER} \
    'sudo cp /tmp/vpn-bot.service /etc/systemd/system/vpn-bot.service && sudo systemctl daemon-reload'
echo "   ✅ Service files updated"

# Step 4: Restart service
echo "[4/5] Restarting vpn-bot service..."
ssh -i "${KEY}" -o StrictHostKeyChecking=no ${SERVER} \
    'sudo systemctl restart vpn-bot'
sleep 2
echo "   ✅ Service restarted"

# Step 5: Verify status
echo "[5/5] Verifying deployment..."
ssh -i "${KEY}" -o StrictHostKeyChecking=no ${SERVER} \
    'sudo systemctl status vpn-bot --no-pager | head -15'

echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Services running:"
echo "  - VPN Bot: http://localhost:8000 (via tunnel)"
echo "To view logs: ssh ... 'sudo journalctl -u vpn-bot -f'"
