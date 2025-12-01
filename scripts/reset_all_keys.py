#!/usr/bin/env python3
"""
Reset all VPN keys - Clean slate for database and sing-box config.

This script:
1. Deletes all users from database
2. Clears all users from sing-box config (keeps structure)
3. Restarts sing-box
4. Users will need to re-purchase keys

WARNING: This is destructive! All existing keys will stop working.
"""

import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.database import get_db_connection
from bot.config import SINGBOX_CONFIG_PATH

def confirm_reset():
    """Ask for confirmation before proceeding."""
    print("=" * 60)
    print("⚠️  WARNING: KEY RESET TOOL")
    print("=" * 60)
    print()
    print("This will:")
    print("  1. DELETE all users from database")
    print("  2. CLEAR all users from sing-box config")
    print("  3. RESTART sing-box service")
    print()
    print("ALL EXISTING KEYS WILL STOP WORKING!")
    print("Users will need to re-purchase keys.")
    print()
    response = input("Type 'RESET' to confirm: ")
    return response == "RESET"

def reset_database():
    """Delete all users from database."""
    print("\n🗑️  Deleting all users from database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Count users before deletion
    count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    print(f"   Found {count} users")
    
    # Delete all users
    cursor.execute("DELETE FROM users")
    
    # Delete all transactions
    cursor.execute("DELETE FROM payment_transactions")
    
    conn.commit()
    conn.close()
    
    print(f"   ✅ Deleted {count} users from database")
    print(f"   ✅ Cleared all payment transactions\n")
    return count

def reset_singbox_config():
    """Clear all users from sing-box config."""
    print("🔧 Clearing users from sing-box config...")
    
    try:
        with open(SINGBOX_CONFIG_PATH, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"   ❌ Config file not found at {SINGBOX_CONFIG_PATH}")
        return False
    
    # Find and clear user arrays
    vless_count = 0
    ss_count = 0
    
    for inbound in config.get('inbounds', []):
        if inbound.get('type') == 'vless':
            vless_count = len(inbound.get('users', []))
            inbound['users'] = []
        elif inbound.get('type') == 'shadowsocks':
            ss_count = len(inbound.get('users', []))
            inbound['users'] = []
    
    # Clear v2ray_api stats users
    if 'experimental' in config and 'v2ray_api' in config['experimental']:
        if 'stats' in config['experimental']['v2ray_api']:
            config['experimental']['v2ray_api']['stats']['users'] = []
    
    # Save config
    temp_path = "/tmp/singbox_config_reset.json"
    try:
        with open(temp_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        import subprocess
        subprocess.run(["sudo", "cp", temp_path, SINGBOX_CONFIG_PATH], check=True)
        subprocess.run(["rm", temp_path], check=True)
        
        print(f"   ✅ Cleared {vless_count} VLESS users")
        print(f"   ✅ Cleared {ss_count} SS users\n")
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to save config: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False

def restart_singbox():
    """Restart sing-box service."""
    print("🔄 Restarting sing-box...")
    import subprocess
    
    try:
        subprocess.run(["sudo", "systemctl", "restart", "sing-box"], check=True, timeout=10)
        print("   ✅ Sing-box restarted\n")
        return True
    except Exception as e:
        print(f"   ❌ Failed to restart sing-box: {e}\n")
        return False

def main():
    # Confirm before proceeding
    if not confirm_reset():
        print("\n❌ Reset cancelled.")
        return 1
    
    print("\n" + "=" * 60)
    print("PROCEEDING WITH RESET...")
    print("=" * 60)
    
    # Step 1: Reset database
    db_count = reset_database()
    
    # Step 2: Reset config
    if not reset_singbox_config():
        print("❌ Failed to reset config. Database was cleared but config unchanged.")
        return 1
    
    # Step 3: Restart service
    if not restart_singbox():
        print("⚠️  Service restart failed. Manual restart may be needed.")
        return 1
    
    print("=" * 60)
    print("✅ RESET COMPLETE!")
    print("=" * 60)
    print()
    print(f"Deleted {db_count} users")
    print("All keys have been removed")
    print("Users can now purchase new keys that will work correctly")
    print()
    return 0

if __name__ == "__main__":
    sys.exit(main())
