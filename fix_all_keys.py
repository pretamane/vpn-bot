#!/usr/bin/env python3
"""
Fix script to add all missing keys to sing-box config
"""
import json
import subprocess
import sys

CONFIG_PATH = "/etc/sing-box/config.json"

# Missing keys from audit
missing_keys = [
  {"uuid": "f445fd15-ff00-4ec7-b6f6-59f352ae859d", "name": "pretamane", "protocol": "ss"},
  {"uuid": "ff987cc3-cf0d-4e58-978d-5f17ca9b9397", "name": "pretamane", "protocol": "ss"},
  {"uuid": "7f581343-d4a1-4b56-9687-45b424b80245", "name": "pretamane", "protocol": "ss"},
  {"uuid": "e22bedb4-85d9-4f3c-831e-6239267c313e", "name": "pretamane", "protocol": "ss"},
  {"uuid": "ce246272-ddf0-4b2b-a7da-9c5caf56418f", "name": "pretamane", "protocol": "vless"},
  {"uuid": "194da18d-6a6b-4aa8-815f-259d95e46404", "name": "pretamane", "protocol": "vless"},
  {"uuid": "1bffff1a-7468-40c6-ab9a-1587ac46ef07", "name": "pretamane", "protocol": "vless"},
  {"uuid": "44c827e4-4d7f-4679-8ccf-81046477d344", "name": "pretamane", "protocol": "ss"},
  {"uuid": "95ca54db-c68d-49cd-9029-0148986376fb", "name": "pretamane", "protocol": "vless"},
  {"uuid": "af2b8026-4988-4b87-bfe1-8ea9a5359589", "name": "unknown", "protocol": "vless"},
  {"uuid": "f6671d91-a300-4dc6-a8c1-60db4c34d839", "name": "pretamane", "protocol": "vless"},
  {"uuid": "98644d0b-3fb1-4925-bd0e-823f02828ebc", "name": "pretamane", "protocol": "vless"},
  {"uuid": "94394b9a-742e-4bfd-8b55-5372245d744d", "name": "pretamane", "protocol": "ss"},
  {"uuid": "fb4c40d9-2a90-4572-96de-dbe5ea262774", "name": "pretamane", "protocol": "vless"},
  {"uuid": "fb2ca8d1-d119-498d-a124-cb1cebde9d70", "name": "pretamane", "protocol": "vless"},
  {"uuid": "eb6c366c-dffe-498e-add5-325841773ba4", "name": "pretamane", "protocol": "vless"},
  {"uuid": "ff34d204-2ad5-452b-a476-a2ba25707504", "name": "pretamane", "protocol": "vless"},
  {"uuid": "d79329be-e051-4d33-b93d-8f4ceb674d05", "name": "pretamane", "protocol": "ss"},
  {"uuid": "eef39008-e289-414b-aa1c-96d8cc7c8634", "name": "pretamane", "protocol": "tuic"},
  {"uuid": "b527e025-c63a-4b50-93f5-eca6a52e4b4b", "name": "pretamane", "protocol": "tuic"},
  {"uuid": "0500fc26-e3c7-4bd4-b547-c1e84afb0004", "name": "pretamane", "protocol": "tuic"},
  {"uuid": "df180e2b-c3f9-4962-b87c-b978490e212d", "name": "pretamane", "protocol": "tuic"},
  {"uuid": "bd9188e7-62c1-422a-b46b-ed2d48bcf6cb", "name": "pretamane", "protocol": "ss"},
  {"uuid": "eede8800-9f3b-44f2-8519-b3a886348646", "name": "pretamane", "protocol": "vlessplain"},
  {"uuid": "9dade52d-bc7b-47ef-b958-0ff7c30a7c0d", "name": "pretamane", "protocol": "ss"},
  {"uuid": "48b8125e-7fe5-42bb-a46e-6966ba4a279c", "name": "pretamane", "protocol": "ss"},
  {"uuid": "1b4c1dfe-0a6b-4024-b705-4f90317e60ff", "name": "pretamane", "protocol": "admin_tuic"},
  {"uuid": "0de0c653-06c4-48b3-9c49-aae959bb2e43", "name": "ThawZin9649", "protocol": "admin_tuic"},
  {"uuid": "54430ff4-ae72-48e3-9902-d6000c7f2ce0", "name": "ThawZin", "protocol": "admin_tuic"},
  {"uuid": "b2ec2ce5-d476-4d53-8364-920c97ea45ac", "name": "ThawZin9649", "protocol": "ss"},
  {"uuid": "e7266cfb-9a75-46da-a22f-52c70b3e067d", "name": "pretamane", "protocol": "ss"},
  {"uuid": "535097b2-0e65-4b5d-9de2-c441ee069851", "name": "pretamane", "protocol": "ss"},
  {"uuid": "1c29160c-a3f3-4545-bcfa-c87fd7ae5f05", "name": "pretamane", "protocol": "admin_tuic"}
]

# Load config
with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

# Group by protocol
to_add = {
    'vless': [],
    'vlessplain': [],
    'ss': [],
    'tuic': [],
    'admin_tuic': []
}

for key in missing_keys:
    proto = key['protocol']
    if proto == 'admin_tuic':
        to_add['tuic'].append(key)  # admin_tuic uses same inbound as tuic
    else:
        to_add[proto].append(key)

# Add keys to config
added = 0
for inbound in config['inbounds']:
    tag = inbound.get('tag', '')
    
    if tag == 'vless-in':  # VLESS+REALITY
        for key in to_add['vless']:
            inbound['users'].append({
                'uuid': key['uuid'],
                'flow': 'xtls-rprx-vision',
                'name': key['name'] or 'unknown'
            })
            added += 1
            print(f"Added VLESS+REALITY: {key['name']}")
    
    elif tag == 'vless-plain-in':  #Plain VLESS
        for key in to_add['vlessplain']:
            inbound['users'].append({
                'uuid': key['uuid'],
                'name': key['name'] or 'unknown'
            })
            added += 1
            print(f"Added VLESS Plain: {key['name']}")
    
    elif tag == 'ss-in':  # Shadowsocks
        for key in to_add['ss']:
            inbound['users'].append({
                'password': key['uuid'],
                'name': key['name'] or 'unknown'
            })
            added += 1
            print(f"Added Shadowsocks: {key['name']}")
    
    elif tag == 'tuic-in':  # TUIC
        for key in to_add['tuic']:
            inbound['users'].append({
                'uuid': key['uuid'],
                'password': key['uuid'],
                'name': key['name'] or 'unknown'
            })
            added += 1
            print(f"Added TUIC: {key['name']}")

print(f"\n✓ Added {added} keys to config")

# Save config
with open(CONFIG_PATH, 'w') as f:
    json.dump(config, f, indent=2)

print("✓ Config saved")

# Reload sing-box
result = subprocess.run(['systemctl', 'reload', 'sing-box'], capture_output=True)
if result.returncode == 0:
    print("✓ Sing-box reloaded successfully")
else:
    print(f"✗ Reload failed: {result.stderr.decode()}")
    sys.exit(1)

print("\n✅ All missing keys have been added!")
