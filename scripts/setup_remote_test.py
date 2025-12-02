import json
import os
import subprocess
import sys

# Configuration
CONFIG_PATH = "/etc/sing-box/config.json"
TEST_UUID = "11111111-1111-1111-1111-111111111111"
TEST_PASSWORD = "test-password-123"
TEST_TAG = "Antigravity-Test-Key"

def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

def save_config(config):
    temp_path = "/tmp/singbox_config_test.json"
    try:
        with open(temp_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        subprocess.run(["sudo", "cp", temp_path, CONFIG_PATH], check=True)
        print(f"Config saved to {CONFIG_PATH}")
        os.remove(temp_path)
    except Exception as e:
        print(f"Error saving config: {e}")
        sys.exit(1)

def add_test_user():
    print(f"Adding test user ({TEST_TAG}) to all inbounds...")
    config = load_config()
    changed = False
    
    for inbound in config.get('inbounds', []):
        # VLESS / TUIC (User-based)
        if inbound['type'] in ['vless', 'tuic']:
            users = inbound.get('users', [])
            # Check if exists
            if not any(u['uuid'] == TEST_UUID for u in users):
                print(f"Adding to {inbound['type']} inbound ({inbound.get('tag')})...")
                users.append({"uuid": TEST_UUID, "name": TEST_TAG})
                inbound['users'] = users
                changed = True
        
        # Shadowsocks (Password-based for multi-user, or single?)
        # Our config uses 'users' list for SS too in sing-box 1.8+ usually, or 'password' for single.
        # Let's check the structure.
        if inbound['type'] == 'shadowsocks':
             # If it has 'users', add to it.
            if 'users' in inbound:
                users = inbound.get('users', [])
                if not any(u['password'] == TEST_PASSWORD for u in users):
                    print(f"Adding to {inbound['type']} inbound ({inbound.get('tag')})...")
                    users.append({"password": TEST_PASSWORD, "name": TEST_TAG})
                    inbound['users'] = users
                    changed = True
            # If it's single user (legacy?), we might not be able to add without breaking others.
            # But our main SS (9388) should be multi-user.
            
    if changed:
        save_config(config)
        print("Reloading sing-box service...")
        subprocess.run(["sudo", "systemctl", "reload", "sing-box"], check=True)
        print("Done!")
    else:
        print("Test user already exists in relevant inbounds.")

if __name__ == "__main__":
    add_test_user()
