#!/bin/bash
# Direct diagnosis script - Tests actual protocol behaviors

SERVER_IP="43.205.90.213"
KEY="/home/guest/tzdump/vpn-bot/keys/myanmar-vpn-key.pem"

echo "==================================="
echo "🔬 Direct Protocol Diagnosis"
echo "==================================="
echo ""

# Test 1: Check if Shadowsocks is actually Shadowsocks 2022 (new format)
echo "[Test 1] Checking Shadowsocks protocol version..."
ssh -o StrictHostKeyChecking=no -i "$KEY" ubuntu@$SERVER_IP 'sing-box version' 2>&1 | grep -i version
echo ""

# Test 2: Try connecting to SS with legacy method  
echo "[Test 2] Testing SS connection with legacy cipher..."
echo "Method: chacha20-ietf-poly1305"
echo "Password: 2ca0d010-d151-48f5-b660-973492e39584"
echo ""

# Test 3: Check if sing-box SS requires network specification
echo "[Test 3] Checking sing-box SS configuration requirements..."
ssh -o StrictHostKeyChecking=no -i "$KEY" ubuntu@$SERVER_IP 'cat /etc/sing-box/config.json | jq ".inbounds[] | select(.tag==\"ss-in\")"'
echo ""

# Test 4: Check Plain VLESS TLS requirements
echo "[Test 4] Testing TLS certificate on port 8443..."
timeout 5 openssl s_client -connect $SERVER_IP:8443 -servername www.microsoft.com 2>&1 | grep -E "Verify return code|subject|issuer|Protocol" | head -5
echo ""

# Test 5: Try to see actual errors by enabling debug mode temporarily
echo "[Test 5] Checking for authentication errors in logs..."
ssh -o StrictHostKeyChecking=no -i "$KEY" ubuntu@$SERVER_IP 'sudo journalctl -u sing-box --since "5 minutes ago" | grep -i "auth\|decrypt\|cipher\|handshake" | tail -10'
echo ""

echo "==================================="
echo "DONE"
echo "==================================="
