#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}Starting MMVPN Slave Node Installation...${NC}"

# 1. Install Dependencies
echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv curl

# 2. Install Sing-box
echo "Installing Sing-box..."
bash <(curl -fsSL https://sing-box.app/deb-install.sh)
sudo systemctl enable sing-box
sudo systemctl start sing-box

# 3. Setup Agent Directory
echo "Setting up Agent..."
sudo mkdir -p /opt/mmvpn
sudo cp agent.py /opt/mmvpn/agent.py

# 4. Setup Python Environment
echo "Setting up Python venv..."
cd /opt/mmvpn
sudo python3 -m venv venv
sudo ./venv/bin/pip install fastapi uvicorn pydantic

# 5. Create Systemd Service
echo "Creating systemd service..."
cat <<EOF | sudo tee /etc/systemd/system/mmvpn-agent.service
[Unit]
Description=MMVPN Slave Agent
After=network.target

[Service]
User=root
WorkingDirectory=/opt/mmvpn
Environment="AGENT_TOKEN=$(openssl rand -hex 16)"
ExecStart=/opt/mmvpn/venv/bin/uvicorn agent:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 6. Start Service
echo "Starting Agent Service..."
sudo systemctl daemon-reload
sudo systemctl enable mmvpn-agent
sudo systemctl restart mmvpn-agent

# 7. Print Token
TOKEN=$(sudo systemctl show -p Environment mmvpn-agent | grep AGENT_TOKEN | cut -d= -f2)
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "Agent Token: ${GREEN}$TOKEN${NC}"
echo "Save this token! You will need it for the Master server."
