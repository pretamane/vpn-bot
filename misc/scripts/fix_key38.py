#!/usr/bin/env python3
import json
import subprocess
import sys

# Read config
with open('/etc/sing-box/config.json', 'r') as f:
    config = json.load(f)

# Find SS inbound and add the missing key
for inbound in config['inbounds']:
    if inbound.get('tag') == 'ss-in':
        # Check if key already exists
        existing = [u for u in inbound['users'] if u.get('password') == '0bde5350-b6a9-4ab0-9680-ba18b333b707']
        if existing:
            print("Key already exists")
            sys.exit(0)
        
        # Add the key
        inbound['users'].append({
            'password': '0bde5350-b6a9-4ab0-9680-ba18b333b707',
            'name': 'pretamane-Key38'
        })
        print(f"Added Key #38, total SS users: {len(inbound['users'])}")
        break

# Save config
with open('/etc/sing-box/config.json', 'w') as f:
    json.dump(config, f, indent=2)

# Reload sing-box
result = subprocess.run(['systemctl', 'reload', 'sing-box'], capture_output=True)
if result.returncode == 0:
    print("Sing-box reloaded successfully")
else:
    print(f"Reload failed: {result.stderr.decode()}")
    sys.exit(1)
