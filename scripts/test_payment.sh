#!/bin/bash
# Wrapper script to test KBZ Pay slip validation
# Usage: ./test_payment.sh [path/to/image.jpg]

cd "$(dirname "$0")/.."

# Default to sample image if no argument provided
IMAGE="${1:-/home/guest/tzdump/vpn-bot/tests/KBZ-Pay-Slip-Sample.jpeg}"

echo "Testing payment validation with: $(basename "$IMAGE")"
echo ""

python3 tests/test_payment_flow.py "$IMAGE"
