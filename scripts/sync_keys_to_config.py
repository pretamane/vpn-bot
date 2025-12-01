#!/usr/bin/env python3
"""
Sync all database keys to sing-box configuration.
This script:
1. Updates null usernames in database to use fallback values
2. Rebuilds sing-box config with ALL active users from database
3. Fixes any previously broken VLESS/SS keys

Run this after fixing the username/closed pipe bugs to repair old keys.
"""

import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db.database import get_db_connection
from bot.config import SINGBOX_CONFIG_PATH

def update_null_usernames():
    """Update all null usernames in database with fallback values."""
    print("Updating null usernames in database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get users with null username
    null_users = cursor.execute('''
        SELECT uuid, telegram_id, username 
        FROM users 
        WHERE username IS NULL OR username = ''
    ''').fetchall()
    
    updated_count = 0
    for row in null_users:
        uuid = row['uuid']
        telegram_id = row['telegram_id']
        fallback_username = f"User{telegram_id}"
        
        cursor.execute('''
            UPDATE users 
            SET username = ? 
            WHERE uuid = ?
        ''', (fallback_username, uuid))
        updated_count += 1
        print(f"  Updated {uuid}: NULL → {fallback_username}")
    
    conn.commit()
    conn.close()
    print(f"✅ Updated {updated_count} null usernames\n")
    return updated_count

def rebuild_singbox_config():
    """Rebuild sing-box configuration with all active users from database."""
    print("Rebuilding sing-box configuration...")
    
    # Load current config
    try:
        with open(SINGBOX_CONFIG_PATH, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found at {SINGBOX_CONFIG_PATH}")
        return False
    
    # Get all active users from database
    conn = get_db_connection()
    users = conn.execute('''
        SELECT uuid, username, protocol, is_active 
        FROM users 
        WHERE is_active = 1
        ORDER BY created_at ASC
    ''').fetchall()
    conn.close()
    
    # Find VLESS and SS inbounds
    vless_inbound = None
    ss_inbound = None
    
    for inbound in config.get('inbounds', []):
        if inbound.get('type') == 'vless':
            vless_inbound = inbound
        elif inbound.get('type') == 'shadowsocks':
            ss_inbound = inbound
    
    if not vless_inbound:
        print("⚠️  No VLESS inbound found in config")
        return False
    
    if not ss_inbound:
        print("⚠️  No Shadowsocks inbound found in config")
        return False
    
    # Clear existing users
    vless_inbound['users'] = []
    ss_inbound['users'] = []
    
    # Rebuild user lists
    vless_count = 0
    ss_count = 0
    
    for user in users:
        uuid = user['uuid']
        username = user['username'] or f"User{uuid[:8]}"
        protocol = user['protocol']
        
        if protocol == 'vless':
            vless_inbound['users'].append({
                "uuid": uuid,
                "flow": "xtls-rprx-vision",
                "name": username
            })
            vless_count += 1
            print(f"  Added VLESS: {username} ({uuid[:8]}...)")
        
        elif protocol == 'ss':
            ss_inbound['users'].append({
                "password": uuid,  # SS uses UUID as password
                "name": username
            })
            ss_count += 1
            print(f"  Added SS: {username} ({uuid[:8]}...)")
    
    # Update v2ray_api stats users if present
    if 'experimental' in config and 'v2ray_api' in config['experimental']:
        stats_config = config['experimental']['v2ray_api'].get('stats', {})
        stats_config['users'] = [u['uuid'] for u in vless_inbound['users']]
        config['experimental']['v2ray_api']['stats'] = stats_config
    
    # Save config
    temp_path = "/tmp/singbox_config.json"
    try:
        with open(temp_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Copy to actual location
        import subprocess
        subprocess.run(["sudo", "cp", temp_path, SINGBOX_CONFIG_PATH], check=True)
        subprocess.run(["rm", temp_path], check=True)
        
        print(f"\n✅ Config rebuilt successfully!")
        print(f"   VLESS users: {vless_count}")
        print(f"   Shadowsocks users: {ss_count}")
        print(f"   Total: {vless_count + ss_count}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to save config: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False

def reload_singbox():
    """Gracefully reload sing-box service."""
    print("Reloading sing-box service...")
    import subprocess
    
    try:
        # Try reload first (graceful)
        subprocess.run(["sudo", "systemctl", "reload", "sing-box"], check=True, timeout=10)
        print("✅ Sing-box reloaded successfully\n")
        return True
    except subprocess.CalledProcessError:
        # Fall back to restart
        print("⚠️  Reload failed, restarting...")
        try:
            subprocess.run(["sudo", "systemctl", "restart", "sing-box"], check=True, timeout=10)
            print("✅ Sing-box restarted successfully\n")
            return True
        except Exception as e:
            print(f"❌ Failed to reload/restart sing-box: {e}\n")
            return False

def main():
    print("=" * 60)
    print("VPN KEY SYNC TOOL")
    print("=" * 60)
    print()
    
    # Step 1: Update null usernames
    update_null_usernames()
    
    # Step 2: Rebuild config
    if not rebuild_singbox_config():
        print("❌ Failed to rebuild config. Exiting.")
        return 1
    
    # Step 3: Reload service
    if not reload_singbox():
        print("⚠️  Config updated but service reload failed.")
        print("   You may need to manually restart sing-box.")
        return 1
    
    print("=" * 60)
    print("✅ ALL DONE! All keys synced successfully.")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
