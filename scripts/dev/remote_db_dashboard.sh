#!/bin/bash
KEY_PATH="/home/guest/tzdump/vpn-bot/keys/myanmar-vpn-key.pem"
REMOTE_HOST="ubuntu@43.205.90.213"

echo "🔗 Connecting to $REMOTE_HOST..."
echo ""
echo "✅ Once connected, you can access:"
echo "   📊 Database Dashboard: http://localhost:8081"
echo "   🔐 Key Viewer:         http://localhost:8000/viewer"
echo "   📚 API Docs:           http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to disconnect."
echo ""

# Tunnel both ports: 8081 (database) and 8000 (API/key viewer)
ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" -N \
    -L 8081:127.0.0.1:8081 \
    -L 8000:127.0.0.1:8000 \
    "$REMOTE_HOST"
