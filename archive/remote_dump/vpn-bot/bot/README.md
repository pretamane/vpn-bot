# Telegram Bot Setup Guide

## 1. Get a Bot Token
1. Open Telegram and search for **@BotFather**.
2. Send the command `/newbot`.
3. Follow the prompts to name your bot.
4. Copy the **HTTP API Token** provided (e.g., `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`).

## 2. Configuration
You can configure the bot in two ways:

### Option A: Environment Variables (Recommended)
Set the `BOT_TOKEN` environment variable before running:
```bash
export BOT_TOKEN="your_token_here"
export ADMIN_ID="your_telegram_id" # Optional, for admin commands
```

### Option B: Edit Config File
Open `bot/config.py` and replace the placeholder:
```python
BOT_TOKEN = os.getenv("BOT_TOKEN", "123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
```

## 3. Install Dependencies
Make sure you have the required Python packages:
```bash
pip install python-telegram-bot qrcode
```

## 4. Run the Bot
Run the main script from the project root:
```bash
# From /home/guest/tzdump/vpn-bot/
python3 bot/main.py
```

## 5. Usage
- Send `/start` to see the welcome message.
- Send `/buy` to see payment instructions.
- Send a photo (any photo for now) to simulate payment verification and get a VPN key.
