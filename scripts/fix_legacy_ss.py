import json
import os
import subprocess
import sys

# Configuration
CONFIG_PATH = "/etc/sing-box/config.json"
SS_LEGACY_PORT = 8388
SS_LEGACY_PASSWORD = "W+UUieKAlVMtz0JS4RA1u7o2b75dVjBF"
SS_METHOD = "chacha20-ietf-poly1305"

def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

def save_config(config):
    temp_path = "/tmp/singbox_config_fix.json"
    try:
        with open(temp_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        subprocess.run(["sudo", "cp", temp_path, CONFIG_PATH], check=True)
        print(f"Config saved to {CONFIG_PATH}")
        os.remove(temp_path)
    except Exception as e:
        print(f"Error saving config: {e}")
        sys.exit(1)

def main():
    print("Checking for Legacy Shadowsocks inbound...")
    config = load_config()
    
    inbounds = config.get('inbounds', [])
    found = False
    
    for inbound in inbounds:
        if inbound.get('listen_port') == SS_LEGACY_PORT:
            print(f"Inbound for port {SS_LEGACY_PORT} already exists.")
            found = True
            break
            
    if not found:
        print(f"Adding Legacy Shadowsocks inbound on port {SS_LEGACY_PORT}...")
        new_inbound = {
            "type": "shadowsocks",
            "tag": "ss-legacy-in",
            "listen": "::",
            "listen_port": SS_LEGACY_PORT,
            "method": SS_METHOD,
            "password": SS_LEGACY_PASSWORD,
            "network": "tcp"
        }
        inbounds.append(new_inbound)
        config['inbounds'] = inbounds
        
        save_config(config)
        
        print("Reloading sing-box service...")
        subprocess.run(["sudo", "systemctl", "reload", "sing-box"], check=True)
        print("Done!")
    else:
        print("No changes needed.")

if __name__ == "__main__":
    main()
