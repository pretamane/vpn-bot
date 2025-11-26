Core Goal Recap
You want to run a lightweight proxy service where:

✅ Each user gets a unique key (UUID)
✅ 12 Mbps symmetric speed cap (download + upload)
✅ 5 GB/day bandwidth cap (resets at 00:00 UTC+6.5)
✅ 1 device per key (prevent sharing)
✅ Users use freely available Android/iOS apps — no custom app
✅ Onboarding & payments via Telegram bot + KBZ/Wave Pay
✅ Fully automated, minimal manual work
Let’s break it down.

📱 Client-Side: Which Apps Can Users Use? (No Custom App Needed)
✅ All users can use these freely available, open-source apps — no development required:

Android
Hiddify Next
(
GitHub APK
)
• Supports VLESS + REALITY natively
• Imports configs via QR/sub link
• Clean, non-technical UI
• Actively maintained for censorship-heavy regions
iOS
Stash
(
TestFlight
) or
Shadowrocket
• Stash: open-source, supports Sing-Box configs
• Shadowrocket: paid, but reliable (many MM users have it)
Windows/macOS/Linux
Sing-Box GUI
or
Nekoray
• For power users (optional)

🔧 How users get configs:
You send them a subscription link (e.g., https://api.yourserver.com/sub?id=UUID) or QR code → app auto-imports VLESS+REALITY config.

→ No app development. No Play Store. No review risk.

💬 User Onboarding & Payments: Telegram Bot vs Website
Setup Cost
$0 (free bot API)
$0–$5/mo (domain + hosting)
Development Effort
Low (Python +
python-telegram-bot
)
Medium (frontend + backend API)
Myanmar UX
✅ Excellent (everyone uses Telegram)
⚠️ Good, but requires browser
Payment Verification
✅ Easy: user sends
KBZ/Wave Pay screenshot
→ bot verifies via OCR/text extraction
✅ Possible, but needs image upload + moderation
Automation
✅ Fully automatable (auto-issue key after payment confirmed)
✅ Possible, but more complex
Trust & Support
✅ High (real-time chat, manual override)
⚠️ Lower (impersonal)

🏆 Verdict: Telegram bot is the clear winner for Myanmar — low cost, high trust, minimal friction. 

🤖 Telegram Bot Conversation Flow (Step-by-Step)
Here’s the ideal user journey — simple, secure, and automatable:

User starts bot:
→ /start
👉 Bot replies:
“Welcome to [Your Service]! 🇲🇲
✅ 12 Mbps speed | 5 GB/day | 1 device/key
💰 Price: 3,000 MMK/month
📲 Send /buy to get started.” 
User sends /buy:
👉 Bot replies:
“Please send 3,000 MMK to:
KBZ: 09-XXXXXXXX
Wave: 09XXXXXXXX
📌 After payment, send a screenshot of success here.” 
User sends payment screenshot:
👉 Bot:
“✅ Payment received! Verifying…”
→ Backend checks image (OCR or manual queue)
→ On success:
“🔑 Your key is ready!
📥 Scan this QR to import into Hiddify:
[QR CODE]
🔗 Or copy link:
https://sub.yourserver.com/uuid/abc123
💡 Tip: Only use on 1 device!” 
Daily usage alert (optional):
“📊 Today: 4.2 GB used (84% of 5 GB). Reset at midnight.” 
Renewal reminder (Day 28):
“🔄 Your plan expires in 2 days. Send /renew to continue.” 
✅ No human needed after initial setup — verification can be semi-automated (e.g., flag low-confidence OCR for manual check).

⚙️ Sing-Box Enforcement Architecture (High-Level Data Flow)
Here’s how the server side enforces your rules — clean, modular, lightweight:



1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
[User Device] 
   ↓ (VLESS+REALITY, UUID=abc123)
[Sing-Box Server (AWS Mumbai)]
   ├── ✅ Inbound: VLESS+REALITY (port 443)
   ├── ✅ Observer: Tracks per-UUID:
   │      • total_down_bytes, total_up_bytes
   │      • active_connections (IP, duration)
   │
   └── [Watchdog Daemon] (runs every 60s)
          ↓
          • Reads stats via Sing-Box API (/traffic, /connections)
          • For UUID=abc123:
               – If current_day_bytes > 5 GB → set outbound to "block"
               – If speed > 12 Mbps → log & warn (or kick)
               – If active_connections > 1 → kick extras
          • Writes daily usage to DB (SQLite)
          • Resets counters at 00:00 MM time (UTC+6:30)
🔑 Key Components:
Sing-Box Core
Proxy + stats collection
Go binary
Watchdog
Enforces limits
Python script (systemd service)
User DB
Stores UUID, expiry, daily counters
SQLite (single file)
Telegram Bot
Handles onboarding/payments
Python + Telegram Bot API
Sub Server
Serves configs to users
Simple HTTP (e.g., Caddy)

✅ No external DB, no cloud costs — runs on t3a.nano ($3.50/mo).

📊 Cost & Maintenance Summary
AWS Mumbai (t3a.nano)
$3.50/mo
Low
Domain (e.g.,
fast.mm
)
~$2/yr
One-time
Telegram Bot Hosting
$0 (run on same server)
Low
Total
~$4/mo
✅ Fully sustainable

→ With just 5 paying users (3,000 MMK × 5 = ~$5.50), you’re profitable.

## 🔐 Configuration Reference (Source of Truth)
These are the verified settings for the AWS Mumbai server. All bots and clients must use these values.

| Parameter | Value |
| :--- | :--- |
| **Server IP** | `43.205.90.213` |
| **Public Key** | `8PMOqMLABvJNa7UeZfFAH5WXiRAC6gpdWziIUWa2pEE` |
| **Short ID** | `794f772c` |
| **Server Name** | `www.microsoft.com` |
| **Port** | `443` |