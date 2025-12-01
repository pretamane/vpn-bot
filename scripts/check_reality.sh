#!/bin/bash
# VLESS REALITY Pre-Flight Check
# Run this to verify server readiness for VLESS connections

echo "========================================"
echo "🛡️  VLESS REALITY HEALTH CHECK"
echo "========================================"

# 1. Time Synchronization Check
# REALITY requires time to be within ±90s of actual time
echo -n "[1] Time Sync Check: "
SERVER_TIME=$(date +%s)
# Fetch time from google (reliable source)
REAL_TIME=$(curl -sI "https://www.google.com" | grep -i "Date:" | sed 's/Date: //g' | tr -d '\r' | date -f - +%s)

if [ -z "$REAL_TIME" ]; then
    echo "⚠️  Could not fetch real time from Google."
else
    DIFF=$((SERVER_TIME - REAL_TIME))
    # Absolute value
    [ $DIFF -lt 0 ] && DIFF=$((-DIFF))
    
    if [ $DIFF -lt 90 ]; then
        echo "✅ OK (Diff: ${DIFF}s)"
    else
        echo "❌ FAIL (Diff: ${DIFF}s) - CRITICAL: TLS Handshake will fail!"
        echo "    Fix: sudo apt install chrony -y && sudo systemctl restart chrony"
    fi
fi

# 2. SNI Accessibility Check
# Server must be able to reach the camouflage domain
SNI_DOMAIN="www.google.com"
echo -n "[2] SNI Reachability ($SNI_DOMAIN): "
HTTP_CODE=$(curl -o /dev/null -s -w "%{http_code}\n" --max-time 5 "https://$SNI_DOMAIN")

if [[ "$HTTP_CODE" =~ ^(200|301|302)$ ]]; then
    echo "✅ OK (HTTP $HTTP_CODE)"
else
    echo "❌ FAIL (HTTP $HTTP_CODE) - CRITICAL: REALITY cannot handshake!"
    echo "    Fix: Change 'server_name' in config.json to an accessible site."
fi

# 3. Port 443 Check
echo -n "[3] Port 443 Listener: "
PORT_PID=$(sudo lsof -t -i:443 -sTCP:LISTEN)
if [ -z "$PORT_PID" ]; then
    echo "❌ FAIL (Not Listening)"
elif ps -p $PORT_PID -o comm= | grep -q "sing-box"; then
    echo "✅ OK (sing-box is listening)"
else
    PROC_NAME=$(ps -p $PORT_PID -o comm=)
    echo "❌ FAIL (Conflict: $PROC_NAME is listening, not sing-box)"
fi

# 4. Config Validation
echo -n "[4] Config Syntax: "
if sudo sing-box check -c /etc/sing-box/config.json > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAIL (Invalid Config)"
fi

echo "========================================"
echo "Health Check Complete"
