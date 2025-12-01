#!/usr/bin/env python3
"""
Audit script to find all keys in database that are missing from sing-box config
"""
import sqlite3
import json
import sys

DB_PATH = "/home/ubuntu/vpn-bot/src/db/vpn_bot.db"
CONFIG_PATH = "/etc/sing-box/config.json"

# Get all keys from database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT uuid, username, protocol FROM users ORDER BY created_at")
db_keys = cursor.fetchall()
conn.close()

# Load sing-box config
with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

# Extract all UUIDs/passwords from sing-box config by protocol
config_keys = {
    'vless': set(),
    'vlessplain': set(),
    'ss': set(),
    'tuic': set()
}

for inbound in config['inbounds']:
    tag = inbound.get('tag', '')
    users = inbound.get('users', [])
    
    if tag == 'vless-in':  # VLESS+REALITY
        for user in users:
            if 'uuid' in user:
                config_keys['vless'].add(user['uuid'])
    
    elif tag == 'vless-plain-in':  # Plain VLESS
        for user in users:
            if 'uuid' in user:
                config_keys['vlessplain'].add(user['uuid'])
    
    elif tag == 'ss-in':  # Shadowsocks
        for user in users:
            if 'password' in user:
                config_keys['ss'].add(user['password'])
    
    elif tag == 'tuic-in':  # TUIC
        for user in users:
            if 'uuid' in user:
                config_keys['tuic'].add(user['uuid'])

# Compare
print("="*60)
print("KEY AUDIT REPORT")
print("="*60)
print()

missing_keys = []
for uuid, username, protocol in db_keys:
    # Normalize protocol name
    proto_key = protocol.lower()
    if proto_key == 'admin_tuic':
        proto_key = 'tuic'
    
    if proto_key not in config_keys:
        print(f"⚠️  Unknown protocol: {protocol} for {username}")
        continue
    
    if uuid not in config_keys[proto_key]:
        missing_keys.append((uuid, username, protocol))
        print(f"❌ MISSING: {username} ({protocol})")
        print(f"   UUID: {uuid}")
        print()

if not missing_keys:
    print("✅ All database keys are present in sing-box config!")
else:
    print("="*60)
    print(f"SUMMARY: {len(missing_keys)} keys missing from sing-box")
    print("="*60)
    
    # Output JSON for easy processing
    print("\nMissing keys (JSON):")
    print(json.dumps([{"uuid": k[0], "name": k[1], "protocol": k[2]} for k in missing_keys], indent=2))

sys.exit(len(missing_keys))
