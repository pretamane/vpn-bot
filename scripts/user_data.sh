#!/bin/bash
set -e

# Log output
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Starting User Data Setup..."

# 1. Install Dependencies
apt-get update
apt-get install -y python3 python3-pip python3-venv curl

# 2. Install Sing-box
bash <(curl -fsSL https://sing-box.app/deb-install.sh)
systemctl enable sing-box
systemctl start sing-box

# 3. Setup Agent Directory
mkdir -p /opt/mmvpn
cd /opt/mmvpn

# 4. Create Agent Script
cat <<EOF > /opt/mmvpn/agent.py
import json
import subprocess
import os
import secrets
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import logging

# Configuration
SINGBOX_CONFIG_PATH = "/etc/sing-box/config.json"
API_TOKEN = "mmvpn-secret-token-123" # Hardcoded for recovery
PORT = 8000

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="MMVPN Slave Agent")

class User(BaseModel):
    uuid: str
    email: str
    limit_mbps: float = 0

async def verify_token(x_token: str = Header(...)):
    if x_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid Token")

def load_config():
    try:
        with open(SINGBOX_CONFIG_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"inbounds": [{"type": "vless", "tag": "vless-in", "users": []}]}

def save_config(config):
    temp_path = "/tmp/singbox_config.json"
    with open(temp_path, 'w') as f:
        json.dump(config, f, indent=2)
    subprocess.run(["cp", temp_path, SINGBOX_CONFIG_PATH], check=True)
    subprocess.run(["rm", temp_path], check=True)

def reload_service():
    subprocess.run(["systemctl", "reload", "sing-box"], check=True)

@app.post("/user", dependencies=[Depends(verify_token)])
async def add_user(user: User):
    config = load_config()
    target_inbound = None
    for inbound in config.get('inbounds', []):
        if inbound['type'] == 'vless':
            target_inbound = inbound
            break
    
    if not target_inbound:
        # Create default inbound if missing
        target_inbound = {
            "type": "vless",
            "tag": "vless-in",
            "listen": "::",
            "listen_port": 8443,
            "users": []
        }
        if 'inbounds' not in config: config['inbounds'] = []
        config['inbounds'].append(target_inbound)

    users = target_inbound.get('users', [])
    users.append({"uuid": user.uuid, "flow": "xtls-rprx-vision", "name": user.email})
    target_inbound['users'] = users
    
    save_config(config)
    reload_service()
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

# 5. Setup Python Environment
python3 -m venv venv
./venv/bin/pip install fastapi uvicorn pydantic

# 6. Create Systemd Service
cat <<EOF > /etc/systemd/system/mmvpn-agent.service
[Unit]
Description=MMVPN Slave Agent
After=network.target

[Service]
User=root
WorkingDirectory=/opt/mmvpn
ExecStart=/opt/mmvpn/venv/bin/uvicorn agent:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 7. Start Service
systemctl daemon-reload
systemctl enable mmvpn-agent
systemctl restart mmvpn-agent

echo "User Data Setup Complete!"
