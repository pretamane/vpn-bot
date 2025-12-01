import sys
import os
import sqlite3
import json
import subprocess

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

from db.database import DB_PATH, get_db_connection
from bot.config import SINGBOX_CONFIG_PATH
from bot.config_manager import save_config, reload_service

def reset_database():
    print("Resetting database (Soft Reset)...")
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Delete all data from tables
        c.execute("DELETE FROM usage_logs")
        c.execute("DELETE FROM payment_transactions")
        c.execute("DELETE FROM users")
        conn.commit()
        print("✅ Database cleared (users, transactions, logs).")
        print("ℹ️  VPN Keys in config.json were NOT touched (User request).")
    except Exception as e:
        print(f"❌ Error clearing database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("⚠️  WARNING: This will DELETE ALL USERS and TRANSACTIONS from the Bot DB! ⚠️")
    print("Existing VPN keys will REMAIN ACTIVE on the server, but the bot will forget them.")
    confirm = input("Type 'yes' to confirm: ")
    
    if confirm.lower() == 'yes':
        reset_database()
        # reset_vpn_config() # Disabled per user request
        print("\n✨ Soft reset complete. You can now restart testing as a 'new' user.")
    else:
        print("Operation cancelled.")
