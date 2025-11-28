import unittest
import sys
import os

# Add src to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

from services.payment_validator import payment_validator, InvalidReceiptError

class TestPaymentValidator(unittest.TestCase):
    def test_kbz_valid(self):
        # Simulated OCR output for KBZ
        lines = [
            "KBZ Pay",
            "Transfer Successful",
            "Transaction ID: 0123456789",
            "Amount",
            "3,000 MMK"
        ]
        result = payment_validator.validate_receipt(lines)
        self.assertEqual(result['provider'], "KBZ Pay")
        self.assertEqual(result['transaction_id'], "0123456789")
        self.assertEqual(result['amount'], 3000.0)

    def test_wave_valid(self):
        # Simulated OCR output for Wave
        lines = [
            "Wave Money",
            "Transferred",
            "TID: 9876543210",
            "Amount: 3000 Ks"
        ]
        result = payment_validator.validate_receipt(lines)
        self.assertEqual(result['provider'], "Wave Pay")
        self.assertEqual(result['transaction_id'], "9876543210")
        self.assertEqual(result['amount'], 3000.0)

    def test_invalid_provider(self):
        lines = ["Random Text", "No provider here"]
        with self.assertRaisesRegex(InvalidReceiptError, "Could not identify payment provider"):
            payment_validator.validate_receipt(lines)

    def test_missing_tid(self):
        lines = ["KBZ Pay", "Amount: 3000 MMK"]
        with self.assertRaisesRegex(InvalidReceiptError, "Could not find Transaction ID"):
            payment_validator.validate_receipt(lines)

    def test_missing_amount(self):
        lines = ["KBZ Pay", "Transaction ID: 1234567890"]
        # Should fail or fallback if we didn't implement fallback for missing MMK
        # In my implementation I added a fallback for "3000" but let's test failure first
        with self.assertRaisesRegex(InvalidReceiptError, "Could not find valid amount"):
            payment_validator.validate_receipt(lines)

    def test_amount_fallback(self):
        # Test the fallback logic for just "3000" without MMK
        lines = ["KBZ Pay", "Transaction ID: 1234567890", "Total: 3000"]
        result = payment_validator.validate_receipt(lines)
        self.assertEqual(result['amount'], 3000.0)

if __name__ == '__main__':
    unittest.main()
