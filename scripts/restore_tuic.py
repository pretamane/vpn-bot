import json
import os

CONFIG_PATH = "/etc/sing-box/config.json"

def restore_tuic():
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    # Check if TUIC already exists
    for inbound in config.get('inbounds', []):
        if inbound.get('type') == 'tuic':
            print("TUIC inbound already exists.")
            return

    # Define TUIC inbound
    tuic_inbound = {
        "type": "tuic",
        "tag": "tuic-in",
        "listen": "::",
        "listen_port": 8443,
        "users": [
            {
                "uuid": "750af5a4-05e0-4ab2-80b9-c4d547874ce2",
                "password": "75e4661b98916677967771e43a4fc321",
                "name": "tuic_client_restored"
            }
        ],
        "congestion_control": "bbr",
        "tls": {
            "enabled": True,
            "certificate_path": "/etc/sing-box/cert.pem",
            "key_path": "/etc/sing-box/key.pem",
            "alpn": [
                "h3"
            ]
        }
    }
    
    config['inbounds'].append(tuic_inbound)
    
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ TUIC inbound restored.")

if __name__ == "__main__":
    restore_tuic()
