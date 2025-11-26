#!/bin/bash
set -e

# Configuration
SINGBOX_VERSION="1.9.0" # Check for latest
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/etc/sing-box"
LOG_DIR="/var/log/singbox"

echo "=== SingBox + Watchdog Setup ==="

# 1. Install Dependencies
echo "[1/5] Installing dependencies..."
sudo apt update && sudo apt install -y curl wget jq python3

# 2. Install SingBox
if [ -f "$INSTALL_DIR/sing-box" ]; then
    echo "[2/5] SingBox already installed."
else
    echo "[2/5] Installing SingBox..."
    wget https://github.com/SagerNet/sing-box/releases/download/v${SINGBOX_VERSION}/sing-box-${SINGBOX_VERSION}-linux-amd64.tar.gz
    tar -xzvf sing-box-${SINGBOX_VERSION}-linux-amd64.tar.gz
    sudo mv sing-box-${SINGBOX_VERSION}-linux-amd64/sing-box $INSTALL_DIR/
    rm -rf sing-box-${SINGBOX_VERSION}-linux-amd64*
    sudo chmod +x $INSTALL_DIR/sing-box
fi

# 3. Generate Config
echo "[3/5] Generating Configuration..."
sudo mkdir -p $CONFIG_DIR
sudo mkdir -p $LOG_DIR
# Try nobody:nogroup, fall back to nobody:nobody, then root
if getent group nogroup >/dev/null; then
    sudo chown -R nobody:nogroup $LOG_DIR
elif getent group nobody >/dev/null; then
    sudo chown -R nobody:nobody $LOG_DIR
else
    sudo chown -R root:root $LOG_DIR
fi

# Generate Keys
UUID=$(cat /proc/sys/kernel/random/uuid)
KEYS=$($INSTALL_DIR/sing-box generate reality-keypair)
PRIVATE_KEY=$(echo "$KEYS" | grep "PrivateKey" | awk '{print $2}')
PUBLIC_KEY=$(echo "$KEYS" | grep "PublicKey" | awk '{print $2}')
SHORT_ID=$(openssl rand -hex 4)

cat > $CONFIG_DIR/config.json <<EOF
{
  "log": {
    "level": "info",
    "output": "$LOG_DIR/access.log",
    "timestamp": true
  },
  "inbounds": [
    {
      "type": "vless",
      "tag": "vless-in",
      "listen": "::",
      "listen_port": 443,
      "users": [
        {
          "uuid": "$UUID",
          "flow": "xtls-rprx-vision"
        }
      ],
      "tls": {
        "enabled": true,
        "server_name": "www.microsoft.com",
        "reality": {
          "enabled": true,
          "handshake": {
            "server": "www.microsoft.com",
            "server_port": 443
          },
          "private_key": "$PRIVATE_KEY",
          "short_id": ["$SHORT_ID"]
        }
      }
    }
  ],
  "outbounds": [
    {
      "type": "direct",
      "tag": "direct"
    }
  ]
}
EOF

# 4. Setup Watchdog
echo "[4/5] Setting up Watchdog..."
sudo cp /home/guest/.gemini/antigravity/scratch/watchdog.py $INSTALL_DIR/watchdog.py
sudo chmod +x $INSTALL_DIR/watchdog.py

# 5. Systemd Services
echo "[5/5] Creating Systemd Services..."

# SingBox Service
cat > /etc/systemd/system/sing-box.service <<EOF
[Unit]
Description=Sing-Box Service
Documentation=https://sing-box.sagernet.org
After=network.target nss-lookup.target

[Service]
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
ExecStart=$INSTALL_DIR/sing-box run -c $CONFIG_DIR/config.json
Restart=on-failure
RestartSec=10s
LimitNOFILE=infinity

[Install]
WantedBy=multi-user.target
EOF

# Watchdog Service
cat > /etc/systemd/system/sing-box-watchdog.service <<EOF
[Unit]
Description=Sing-Box Watchdog
After=sing-box.service

[Service]
ExecStart=/usr/bin/python3 $INSTALL_DIR/watchdog.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload and Start
sudo systemctl daemon-reload
sudo systemctl enable sing-box sing-box-watchdog
sudo systemctl restart sing-box sing-box-watchdog

echo "=== Setup Complete ==="
echo "UUID: $UUID"
echo "Public Key: $PUBLIC_KEY"
echo "Short ID: $SHORT_ID"
