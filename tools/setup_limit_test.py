import json
import os
import subprocess
import sys

CONFIG_PATH = "/etc/sing-box/config.json"
LIMITED_PORT = 10001
LIMITED_UUID = "11111111-1111-1111-1111-111111111111"
LIMIT_RATE = "12mbit" # 12 Mbps for testing

def setup_config():
    print(f"Reading {CONFIG_PATH}...")
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)

    # Find main inbound to copy TLS settings
    main_inbound = None
    for inbound in config['inbounds']:
        if inbound['type'] == 'vless' and inbound.get('tls', {}).get('enabled'):
            main_inbound = inbound
            break
    
    if not main_inbound:
        print("Error: Could not find main VLESS inbound to copy TLS settings.")
        return False

    # Check if limited inbound exists
    limited_inbound = None
    for inbound in config['inbounds']:
        if inbound.get('tag') == 'vless-limited-in':
            limited_inbound = inbound
            break
    
    if not limited_inbound:
        print("Creating new limited inbound...")
        limited_inbound = {
            "type": "vless",
            "tag": "vless-limited-in",
            "listen": "::",
            "listen_port": LIMITED_PORT,
            "users": [
                {
                    "uuid": LIMITED_UUID,
                    "flow": "xtls-rprx-vision",
                    "name": "limit-test"
                }
            ],
            "tls": main_inbound['tls']
        }
        config['inbounds'].append(limited_inbound)
    else:
        print("Limited inbound already exists. Updating user...")
        limited_inbound['listen_port'] = LIMITED_PORT
        limited_inbound['users'] = [{
            "uuid": LIMITED_UUID,
            "flow": "xtls-rprx-vision",
            "name": "limit-test"
        }]

    print("Saving config...")
    with open("/tmp/singbox_config_limit.json", 'w') as f:
        json.dump(config, f, indent=2)
    
    subprocess.run(["sudo", "cp", "/tmp/singbox_config_limit.json", CONFIG_PATH], check=True)
    subprocess.run(["sudo", "systemctl", "reload", "sing-box"], check=True)
    print("Sing-box reloaded.")
    return True

def setup_tc():
    print("Setting up Traffic Control (TC)...")
    interface = "eth0" # Assuming eth0, need to verify
    
    # Check interface
    try:
        subprocess.run(["ip", "link", "show", interface], check=True, capture_output=True)
    except:
        # Try ens5 or similar if eth0 fails
        try:
            interface = "ens5"
            subprocess.run(["ip", "link", "show", interface], check=True, capture_output=True)
        except:
            print("Error: Could not find eth0 or ens5 interface.")
            return False

    # Simple HTB setup using replace to overwrite existing rules
    cmds = [
        f"sudo tc qdisc replace dev {interface} root handle 1: htb default 10",
        f"sudo tc class replace dev {interface} parent 1: classid 1:1 htb rate {LIMIT_RATE} burst 32k",
        f"sudo tc filter replace dev {interface} protocol ip parent 1:0 prio 1 u32 match ip sport {LIMITED_PORT} 0xffff flowid 1:1",
        f"sudo tc filter replace dev {interface} protocol ipv6 parent 1:0 prio 1 u32 match ip6 sport {LIMITED_PORT} 0xffff flowid 1:1"
    ]
    
    for cmd in cmds:
        try:
            subprocess.run(cmd, shell=True, check=True, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            print(f"Error running TC: {e.stderr.decode()}")

    print(f"TC rules applied on {interface} for port {LIMITED_PORT} limit {LIMIT_RATE}")
    return True

if __name__ == "__main__":
    if setup_config():
        setup_tc()
        print(f"\nSUCCESS! Test User Configured.")
        print(f"UUID: {LIMITED_UUID}")
        print(f"Port: {LIMITED_PORT}")
        print(f"Limit: {LIMIT_RATE}")
