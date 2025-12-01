#!/bin/bash
# Real-world connection test runner
# Uploads and executes the Python test on the server

SERVER="ubuntu@43.205.90.213"
KEY="/home/guest/tzdump/vpn-bot/keys/myanmar-vpn-key.pem"
# Use relative path from script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_SCRIPT="$PROJECT_ROOT/tests/test_real_connections.py"

echo "=========================================="
echo "🔬 Real-World VPN Connection Test"
echo "=========================================="
echo ""

# Upload test script
echo "[1/2] Uploading test script to server..."
scp -o StrictHostKeyChecking=no -i "$KEY" "$TEST_SCRIPT" "$SERVER:/tmp/test_real_connections.py" 2>&1 | grep -v "Warning"

if [ $? -ne 0 ]; then
    echo "✗ Failed to upload test script"
    exit 1
fi
echo "✓ Test script uploaded"
echo ""

# Run the test
echo "[2/2] Running real connection tests..."
echo ""
ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" 'cd /home/ubuntu/vpn-bot && python3 /tmp/test_real_connections.py'

TEST_RESULT=$?

# Cleanup
ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" 'rm -f /tmp/test_real_connections.py' 2>/dev/null

exit $TEST_RESULT
