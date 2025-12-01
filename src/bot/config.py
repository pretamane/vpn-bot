import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_USERNAME = "@pretamane"  # Admin Telegram username for support

# Payment Details
KBZ_PAY_NUMBER = os.getenv("KBZ_PAY_NUMBER")
WAVE_PAY_NUMBER = os.getenv("WAVE_PAY_NUMBER")

# Server Configuration
SERVER_IP = os.getenv("SERVER_IP")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")
SHORT_ID = os.getenv("SHORT_ID")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8443"))
SERVER_NAME = os.getenv("SERVER_NAME")

# Shadowsocks Configuration (Working Protocol)
SS_SERVER = os.getenv("SS_SERVER", SERVER_IP)
SS_PORT = int(os.getenv("SS_PORT", "9388"))
SS_METHOD = os.getenv("SS_METHOD", "chacha20-ietf-poly1305")
SS_PASSWORD = os.getenv("SS_PASSWORD")

# Additional Protocols
TUIC_PORT = int(os.getenv("TUIC_PORT", "2083"))
VLESS_PLAIN_PORT = int(os.getenv("VLESS_PLAIN_PORT", "8444"))

# User Limits
MAX_KEYS_PER_USER = int(os.getenv("MAX_KEYS_PER_USER", "1"))

# Paths
SINGBOX_CONFIG_PATH = os.getenv("SINGBOX_CONFIG_PATH", "/etc/sing-box/config.json")
