# VPN Telegram Bot - Multi-Protocol Support

A Telegram bot that sells VPN access with automatic key generation for Myanmar users, bypassing censorship using VLESS+REALITY and Shadowsocks protocols.

## Features

- **Multi-Protocol Support**: Shadowsocks (working) & VLESS+REALITY (experimental)
- **Unique Per-User Keys**: Each user gets a unique password (UUID-based)
- **Bandwidth Tracking**: Ready for per-user bandwidth limits via Watchdog
- **Device Limits**: Can enforce one device per key
- **Automated Deployment**: Systemd services for bot and VPN server

## Quick Start

### Prerequisites
- Ubuntu 22.04+ server (AWS Mumbai recommended)
- Telegram Bot Token from @BotFather
- SSH access to server

### Installation

```bash
# 1. Clone repository
git clone <repo-url>
cd vpn-bot

# 2. Configure bot token
export BOT_TOKEN="your-telegram-bot-token"

# 3. Install dependencies
pip3 install -r requirements.txt

# 4. Initialize database
python3 <<EOF
from db.database import init_db
init_db()
EOF

# 5. Deploy to server (see DEPLOYMENT.md)
```

## Architecture

- **Bot** (`bot/`): Telegram bot handling user interactions
- **Database** (`db/`): SQLite for user management
- **Watchdog** (`watchdog/`): Traffic monitoring service
- **Config Manager**: Automatic Sing-Box configuration updates

## Configuration

| Protocol | Port | Status |
|---|---|---|
| Shadowsocks | 9388 | ✅ Working |
| VLESS+REALITY | 8443 | ⚠️ Experimental |

## Documentation

- [**DEPLOYMENT.md**](DEPLOYMENT.md) - Complete deployment guide
- [**architecture.md**](architecture.md) - System design overview
- [**vpn-bot.md**](vpn-bot.md) - Configuration reference
- [**walkthrough.md**](walkthrough.md) - Development history

## Usage

1. User sends `/buy` to bot
2. Bot presents protocol choice (Shadowsocks recommended)
3. User sends payment screenshot
4. Bot generates unique key + QR code
5. User imports into v2rayNG or NekoBox

## Current Status

✅ **Production Ready (Shadowsocks)**
- Unique per-user passwords
- Automatic config updates
- Service monitoring

⚠️ **Experimental (VLESS+REALITY)**
- Handshake issues under investigation
- Use for testing only

## Server Details

- **Instance**: AWS EC2 t3.nano (Mumbai)
- **OS**: Ubuntu 22.04
- **VPN Server**: Sing-Box
- **Firewall**: UFW with ports 8443, 9388 open

## License

MIT
