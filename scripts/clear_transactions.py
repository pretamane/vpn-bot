import sqlite3
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from db.database import DB_PATH

def clear_transactions():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("⚠️  WARNING: This will delete ALL payment transaction records!")
    print("   This allows reusing KBZ Pay slips for testing.")
    
    confirm = input("Are you sure you want to proceed? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return

    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payment_transactions'")
        if not cursor.fetchone():
            print("Table 'payment_transactions' does not exist.")
            return

        # Count before
        cursor.execute("SELECT COUNT(*) FROM payment_transactions")
        count_before = cursor.fetchone()[0]
        print(f"Found {count_before} transactions.")

        # Delete
        cursor.execute("DELETE FROM payment_transactions")
        conn.commit()
        
        print(f"✅ Successfully deleted {count_before} transactions.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    clear_transactions()
