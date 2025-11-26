# Deployment Guide

## Server Setup

### 1. Provision AWS Instance

```bash
# Launch t3.nano in ap-south-1 (Mumbai)
# AMI: Ubuntu 22.04 LTS
# Security Group: Allow 22, 8443, 9388
```

### 2. Configure Security Group

Open the following ports in AWS Console → EC2 → Security Groups:

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 22 | TCP | Your IP | SSH |
| 8443 | TCP | 0.0.0.0/0 | VLESS |
| 9388 | TCP | 0.0.0.0/0 | Shadowsocks |

### 3. Install Dependencies on Server

```bash
# SSH into server
ssh -i your-key.pem ubuntu@<SERVER_IP>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Sing-Box
bash -c "$(curl -fsSL https://sing-box.sagernet.org/install.sh)"

# Install Python dependencies
sudo apt install python3-pip sqlite3 -y
pip3 install python-telegram-bot qrcode pillow
```

### 4. Deploy Bot Files

```bash
# From your local machine
scp -i your-key.pem -r bot/ ubuntu@<SERVER_IP>:/home/ubuntu/vpn-bot/
scp -i your-key.pem -r db/ ubuntu@<SERVER_IP>:/home/ubuntu/vpn-bot/
scp -i your-key.pem -r watchdog/ ubuntu@<SERVER_IP>:/home/ubuntu/vpn-bot/
```

### 5. Configure Sing-Box

```bash
# On server
sudo mkdir -p /etc/sing-box /var/log/singbox
sudo cp updated_server_config.json /etc/sing-box/config.json
sudo chown ubuntu:ubuntu /etc/sing-box/config.json
```

### 6. Setup Systemd Services

```bash
# Sing-Box service
sudo cp sing-box.service /etc/systemd/system/
sudo systemctl enable sing-box
sudo systemctl start sing-box

# VPN Bot service
sudo cp bot/vpn-bot.service /etc/systemd/system/
sudo systemctl enable vpn-bot
sudo systemctl start vpn-bot
```

### 7. Configure Firewall

```bash
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 8443/tcp
sudo ufw allow 9388/tcp
sudo ufw status
```

## Bot Configuration

Edit `bot/config.py`:

```python
SERVER_IP = "YOUR.AWS.IP.HERE"
PUBLIC_KEY = "YOUR_REALITY_PUBLIC_KEY"
SHORT_ID = "YOUR_SHORT_ID"
BOT_TOKEN = "YOUR:TELEGRAM_BOT_TOKEN"
```

## Updating the Bot

```bash
# Update bot code
scp -i your-key.pem bot/main.py ubuntu@<SERVER_IP>:/home/ubuntu/vpn-bot/bot/
scp -i your-key.pem bot/config.py ubuntu@<SERVER_IP>:/home/ubuntu/vpn-bot/bot/

# Restart service
ssh -i your-key.pem ubuntu@<SERVER_IP> "sudo systemctl restart vpn-bot"
```

## Monitoring

```bash
# Check bot status
sudo systemctl status vpn-bot

# Check Sing-Box status
sudo systemctl status sing-box

# View bot logs
sudo journalctl -u vpn-bot -f

# View Sing-Box logs
sudo journalctl -u sing-box -f
```

## Troubleshooting

### Bot Not Starting

```bash
# Check logs
sudo journalctl -u vpn-bot -n 50

# Common issues:
# - Missing BOT_TOKEN environment variable
# - Database file permissions
# - Python dependencies not installed
```

### Sing-Box Failing

```bash
# Check config syntax
sudo sing-box check -c /etc/sing-box/config.json

# Common issues:
# - Port already in use
# - Invalid JSON syntax
# - Missing fields in config
```

### Connection Refused

1. **Check AWS Security Group** - Ensure ports are open
2. **Check UFW** - `sudo ufw status`  
3. **Check sing-box** - `sudo systemctl status sing-box`
4. **Test port** - `nc -zv <SERVER_IP> 9388`

## Bandwidth Limiting (Future)

To enable bandwidth limits:

1. Enable V2Ray API in Sing-Box config
2. Start Watchdog service
3. Bot will enforce daily limits from database

See `watchdog/service.py` for implementation.
