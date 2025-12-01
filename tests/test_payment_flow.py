#!/usr/bin/env python3
"""
Test script for KBZ Pay slip validation flow
- Uploads a payment slip to the bot
- Verifies payment validation works
- Cleans up transaction to allow reuse
"""

import os
import sys
import time
import sqlite3
from pathlib import Path

# Add project root to path
# Add project root and src to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from services.ocr_service import ocr_service
from services.payment_validator import payment_validator, InvalidReceiptError
from db.database import is_transaction_used, add_transaction, DB_PATH

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.YELLOW}→ {text}{Colors.RESET}")

def cleanup_transaction(transaction_id):
    """Remove transaction from database to allow reuse"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM payment_transactions WHERE transaction_id = ?", (transaction_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted_count > 0
    except Exception as e:
        print_error(f"Failed to cleanup transaction: {e}")
        return False

def test_payment_slip(image_path):
    """Test the complete payment validation flow"""
    
    print_header("🧪 KBZ Pay Slip Validation Test")
    
    # Step 1: Verify image exists
    print_info(f"Checking image: {image_path}")
    if not os.path.exists(image_path):
        print_error(f"Image not found: {image_path}")
        return False
    print_success(f"Image found: {os.path.basename(image_path)}")
    
    # Step 2: OCR Extraction
    print_info("Extracting text from image...")
    try:
        text_lines = ocr_service.extract_text(image_path)
        if not text_lines:
            print_error("No text extracted from image")
            return False
        print_success(f"Extracted {len(text_lines)} text lines")
        print(f"\n{Colors.BOLD}Extracted Text:{Colors.RESET}")
        for i, line in enumerate(text_lines[:10], 1):  # Show first 10 lines
            print(f"  {i}. {line}")
        if len(text_lines) > 10:
            print(f"  ... and {len(text_lines) - 10} more lines")
    except Exception as e:
        print_error(f"OCR extraction failed: {e}")
        return False
    
    # Step 3: Payment Validation
    print_info("\nValidating payment receipt...")
    try:
        data = payment_validator.validate_receipt(text_lines)
        print_success("Payment validation successful!")
        print(f"\n{Colors.BOLD}Payment Details:{Colors.RESET}")
        print(f"  Provider: {data['provider']}")
        print(f"  Transaction ID: {data['transaction_id']}")
        print(f"  Amount: {data['amount']} MMK")
    except InvalidReceiptError as e:
        print_error(f"Invalid receipt: {e}")
        return False
    except Exception as e:
        print_error(f"Validation error: {e}")
        return False
    
    # Step 4: Check for duplicates
    print_info("\nChecking for duplicate transactions...")
    transaction_id = data['transaction_id']
    is_duplicate = is_transaction_used(transaction_id)
    
    if is_duplicate:
        print_error(f"Transaction {transaction_id} already exists in database")
        print_info("Cleaning up existing transaction for reuse...")
        if cleanup_transaction(transaction_id):
            print_success("Transaction cleaned up successfully")
        else:
            print_error("Failed to cleanup transaction")
            return False
    else:
        print_success("Transaction ID is unique")
    
    # Step 5: Test adding transaction
    print_info("\nTesting transaction registration...")
    try:
        test_user_id = 999999999  # Test user ID
        add_transaction(test_user_id, data['provider'], data['transaction_id'], data['amount'])
        print_success(f"Transaction registered for test user {test_user_id}")
    except Exception as e:
        print_error(f"Failed to register transaction: {e}")
        return False
    
    # Step 6: Verify it was added
    print_info("Verifying transaction was added...")
    if is_transaction_used(transaction_id):
        print_success("Transaction successfully recorded in database")
    else:
        print_error("Transaction not found in database after adding")
        return False
    
    # Step 7: Cleanup for reuse
    print_info("\nCleaning up transaction for future reuse...")
    if cleanup_transaction(transaction_id):
        print_success("Transaction cleaned up - slip can be reused")
    else:
        print_error("Failed to cleanup transaction")
        return False
    
    # Step 8: Final verification
    print_info("Verifying cleanup...")
    if not is_transaction_used(transaction_id):
        print_success("Transaction successfully removed from database")
    else:
        print_error("Transaction still exists after cleanup")
        return False
    
    return True

def main():
    # Default test image path
    default_image = "/home/guest/tzdump/vpn-bot/tests/KBZ-Pay-Slip-Sample.jpeg"
    
    # Allow custom image path via command line
    image_path = sys.argv[1] if len(sys.argv) > 1 else default_image
    
    # Run the test
    start_time = time.time()
    success = test_payment_slip(image_path)
    duration = time.time() - start_time
    
    # Print summary
    print_header("📊 Test Summary")
    
    if success:
        print_success(f"ALL TESTS PASSED in {duration:.2f}s")
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ Payment validation is working correctly!{Colors.RESET}")
        print(f"{Colors.GREEN}   The KBZ Pay slip can now be reused for testing.{Colors.RESET}\n")
        return 0
    else:
        print_error(f"TESTS FAILED after {duration:.2f}s")
        print(f"\n{Colors.RED}{Colors.BOLD}❌ Payment validation has issues!{Colors.RESET}")
        print(f"{Colors.RED}   Please check the errors above.{Colors.RESET}\n")
        return 1

if __name__ == "__main__":
    exit(main())
