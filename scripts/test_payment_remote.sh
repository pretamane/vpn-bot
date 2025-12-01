#!/bin/bash
# Remote payment validation test
# Runs the payment test on the server where all modules are available

SERVER="ubuntu@43.205.90.213"
KEY="/home/guest/tzdump/vpn-bot/keys/myanmar-vpn-key.pem"
TEST_IMAGE="/home/guest/tzdump/vpn-bot/tests/KBZ-Pay-Slip-Sample.jpeg"

echo "=========================================="
echo "🧪 Testing Payment Validation on Server"
echo "=========================================="
echo ""

# Upload test image to server
echo "[1/3] Uploading test image to server..."
scp -o StrictHostKeyChecking=no -i "$KEY" "$TEST_IMAGE" "$SERVER:/tmp/test_payment_slip.jpg" 2>&1 | grep -v "Warning"
if [ $? -eq 0 ]; then
    echo "✓ Image uploaded"
else
    echo "✗ Failed to upload image"
    exit 1
fi
echo ""

# Run the test on server
echo "[2/3] Running payment validation test..."
ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" 'cd /home/ubuntu/vpn-bot && python3 << EOF
import sys
import sqlite3
from services.ocr_service import ocr_service
from services.payment_validator import payment_validator, InvalidReceiptError
from db.database import is_transaction_used, add_transaction, get_db_path

print("\n→ Extracting text from payment slip...")
try:
    text_lines = ocr_service.extract_text("/tmp/test_payment_slip.jpg")
    if not text_lines:
        print("✗ No text extracted")
        sys.exit(1)
    print(f"✓ Extracted {len(text_lines)} text lines")
except Exception as e:
    print(f"✗ OCR failed: {e}")
    sys.exit(1)

print("\n→ Validating payment receipt...")
try:
    data = payment_validator.validate_receipt(text_lines)
    print("✓ Payment validation successful!")
    print(f"  Provider: {data['"'"'provider'"'"']}")
    print(f"  Transaction ID: {data['"'"'transaction_id'"'"']}")
    print(f"  Amount: {data['"'"'amount'"'"']} MMK")
    transaction_id = data['"'"'transaction_id'"'"']
except InvalidReceiptError as e:
    print(f"✗ Invalid receipt: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Validation error: {e}")
    sys.exit(1)

print("\n→ Testing transaction registration...")
# Clean up if exists
if is_transaction_used(transaction_id):
    print("  Transaction already exists, cleaning up...")
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM payment_transactions WHERE transaction_id = ?", (transaction_id,))
    conn.commit()
    conn.close()

# Add test transaction
try:
    add_transaction(999999999, data['"'"'provider'"'"'], transaction_id, data['"'"'amount'"'"'])
    print("✓ Transaction registered")
except Exception as e:
    print(f"✗ Failed to register: {e}")
    sys.exit(1)

print("\n→ Cleaning up for reuse...")
db_path = get_db_path()
conn = sqlite3.connect(db_path)
cursor = conn.execute("DELETE FROM payment_transactions WHERE transaction_id = ?", (transaction_id,))
deleted = cursor.rowcount
conn.commit()
conn.close()

if deleted > 0:
    print("✓ Transaction cleaned up - slip can be reused")
else:
    print("✗ Cleanup failed")
    sys.exit(1)

print("\n✅ ALL PAYMENT TESTS PASSED")
EOF
'

TEST_RESULT=$?
echo ""

# Cleanup
echo "[3/3] Cleaning up..."
ssh -o StrictHostKeyChecking=no -i "$KEY" "$SERVER" 'rm -f /tmp/test_payment_slip.jpg' 2>/dev/null
echo "✓ Cleanup complete"
echo ""

echo "=========================================="
if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ Payment validation is working correctly!"
else
    echo "❌ Payment validation test failed!"
fi
echo "=========================================="

exit $TEST_RESULT
