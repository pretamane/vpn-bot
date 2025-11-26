#!/bin/bash
# v2rayNG / v2rayN Share Link Generator for Mumbai REALITY Server

# Connection parameters
UUID="e6a273ae-3adb-4a6e-af35-08320c3a06cd"
SERVER="43.205.90.213"
PORT="443"
SNI="www.microsoft.com"
PUBLIC_KEY="ebn5poHxOL6U1lLVXiZmLxDIlF4I6ChnqZ7KtM00DlM"
SHORT_ID="32155302"
NAME="Mumbai-India-AWS-Reality"

# Generate VLESS share link
SHARE_LINK="vless://${UUID}@${SERVER}:${PORT}?encryption=none&flow=xtls-rprx-vision&security=reality&sni=${SNI}&fp=chrome&pbk=${PUBLIC_KEY}&sid=${SHORT_ID}&type=tcp&headerType=none#${NAME}"

echo "=================================="
echo "VLESS + REALITY Share Link"
echo "=================================="
echo ""
echo "Share Link (Copy this to v2rayNG):"
echo ""
echo "$SHARE_LINK"
echo ""
echo "=================================="
echo "Manual Configuration (Alternative)"
echo "=================================="
echo ""
echo "Server: $SERVER"
echo "Port: $PORT"
echo "UUID: $UUID"
echo "Protocol: VLESS"
echo "Flow: xtls-rprx-vision"
echo "Security: reality"
echo "SNI: $SNI"
echo "Fingerprint: chrome"
echo "Public Key: $PUBLIC_KEY"
echo "Short ID: $SHORT_ID"
echo "Network: tcp"
echo ""
echo "=================================="

# Save to file
echo "$SHARE_LINK" > /home/guest/.gemini/antigravity/scratch/mumbai-vless-link.txt
echo ""
echo "✅ Share link saved to:"
echo "   /home/guest/.gemini/antigravity/scratch/mumbai-vless-link.txt"
