#!/bin/bash
# Safe Start Script for SingBox VPN
# Automatically rolls back if connection fails

SERVICE_NAME="sing-box"
CHECK_URL="https://www.google.com"
CHECK_TIMEOUT=5

echo "🛡️  Safe-Starting SingBox VPN..."

# 1. Start Service
echo "🚀 Starting service..."
systemctl --user start $SERVICE_NAME

# 2. Wait for initialization
echo "⏳ Waiting 5 seconds for tunnel..."
sleep 5

# 3. Verify Connectivity
echo "🔍 Verifying connectivity..."
if curl -s -m $CHECK_TIMEOUT --head $CHECK_URL > /dev/null; then
    echo "✅ VPN IS STABLE!"
    echo "   - IP: $(curl -s -m 3 ipinfo.io | jq -r .ip)"
    echo "   - DNS: Working"
    exit 0
else
    echo "❌ CONNECTION FAILED (DNS/Network Error)"
    echo "⚠️  Rolling back immediately to restore internet..."
    systemctl --user stop $SERVICE_NAME
    echo "✓ Rollback complete. You have internet again."
    echo ""
    echo "Diagnosis:"
    echo " - Service started but could not reach internet."
    echo " - Possible causes: DNS hijacking failure, server block, or time sync."
    exit 1
fi
