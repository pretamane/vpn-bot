import logging
import uuid
import qrcode
import io
import sys
import os

# Add parent directory to path to import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from db.database import add_user, get_user, init_db, get_active_key_count, get_user_stats
from bot.config import BOT_TOKEN, KBZ_PAY_NUMBER, WAVE_PAY_NUMBER, SERVER_IP, PUBLIC_KEY, SHORT_ID, SERVER_PORT, SERVER_NAME, SS_SERVER, SS_PORT, SS_METHOD, SS_PASSWORD, MAX_KEYS_PER_USER

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🛒 Buy VPN Key", callback_data="menu_buy")],
        [InlineKeyboardButton("📊 My Status", callback_data="menu_status")],
        [InlineKeyboardButton("🆘 Help & Support", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        f"Welcome {user.mention_html()}! 🇲🇲\n\n"
        "✅ 12 Mbps speed | 5 GB/day | 1 device/key\n"
        "💰 Price: 3,000 MMK/month\n\n"
        "Select an option below:",
        reply_markup=reply_markup
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send payment instructions and protocol selection."""
    keyboard = [
        [InlineKeyboardButton("🟢 Shadowsocks (Recommended)", callback_data="protocol_ss")],
        [InlineKeyboardButton("🔵 VLESS+REALITY (Experimental)", callback_data="protocol_vless")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Check if called from callback or command
    if update.callback_query:
        message_func = update.callback_query.message.reply_text
    else:
        message_func = update.message.reply_text
        
    await message_func(
        "Choose your VPN protocol:",
        reply_markup=reply_markup
    )

async def handle_protocol_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle protocol selection."""
    query = update.callback_query
    await query.answer()
    
    protocol = query.data.split("_")[1]  # "ss" or "vless"
    context.user_data['protocol'] = protocol
    
    protocol_name = "Shadowsocks" if protocol == "ss" else "VLESS+REALITY"
    await query.edit_message_text(
        f"✅ Selected: {protocol_name}\n\n"
        f"Please send 3,000 MMK to:\n\n"
        f"KBZ: {KBZ_PAY_NUMBER}\n"
        f"Wave: {WAVE_PAY_NUMBER}\n\n"
        "📌 After payment, send a screenshot of success here."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment screenshot."""
    user = update.effective_user
    photo_file = await update.message.photo[-1].get_file()
    
    # In a real app, we would save the photo and verify it.
    # For now, we'll just mock the verification.
    
    await update.message.reply_text("✅ Payment received! Verifying...")
    
    # Simulate processing time
    # In reality, this might be manual or async
    
    # Check if user has reached key limit
    active_count = get_active_key_count(user.id)
    if active_count >= MAX_KEYS_PER_USER:
        await update.message.reply_text(
            f"⚠️ You already have {active_count} active key(s).\n"
            f"Maximum allowed: {MAX_KEYS_PER_USER}\n\n"
            "Please use your existing key or contact support."
        )
        return
    
    # Generate UUID
    user_uuid = str(uuid.uuid4())
    
    # Add to DB
    if add_user(user_uuid, user.id, user.username):
        # Get user's protocol choice (default to SS if not set)
        protocol = context.user_data.get('protocol', 'ss')
        
        # Only update Sing-Box config for VLESS (SS doesn't need individual users)
        if protocol == 'vless':
            from bot.config_manager import add_user_to_config
            try:
                add_user_to_config(user_uuid, f"user_{user.id}")
            except Exception as e:
                logger.error(f"Failed to update config: {e}")
                await update.message.reply_text("⚠️ Account created but VPN activation failed. Contact support.")
                return

        # Generate link based on protocol
        if protocol == 'ss':
            # Generate Shadowsocks link with unique password (UUID)
            import base64
            ss_credential = f"{SS_METHOD}:{user_uuid}"
            ss_encoded = base64.b64encode(ss_credential.encode()).decode()
            vpn_link = f"ss://{ss_encoded}@{SS_SERVER}:{SS_PORT}#VPN-Bot-{user.first_name}"
            protocol_name = "Shadowsocks"
            
            # Add user to SS config for tracking
            from bot.config_manager import add_ss_user
            try:
                add_ss_user(user_uuid, f"user_{user.id}")
            except Exception as e:
                logger.error(f"Failed to add SS user to config: {e}")
                # Continue anyway - user can still connect with shared credentials
        else:
            # Generate VLESS Link
            vpn_link = f"vless://{user_uuid}@{SERVER_IP}:{SERVER_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=chrome&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#VPN-Bot-{user.first_name}"
            protocol_name = "VLESS+REALITY"
        
        # Generate QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(vpn_link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        bio = io.BytesIO()
        img.save(bio)
        bio.seek(0)
        
        await update.message.reply_text(
            f"🔑 Your {protocol_name} key is ready!\n\n"
            f"🔗 Copy link:\n`{vpn_link}`\n\n"
            f"💡 Tip: Only use on 1 device!",
            parse_mode="Markdown"
        )
        await update.message.reply_photo(bio, caption="Scan this QR to import")
        
    else:
        await update.message.reply_text("❌ Error generating key. Please contact support.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    # Check if called from callback or command
    if update.callback_query:
        message_func = update.callback_query.message.reply_text
    else:
        message_func = update.message.reply_text
        
    await message_func("Need help? Contact @admin for support!")

async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command to show user stats."""
    user = update.effective_user
    stats = get_user_stats(user.id)
    
    # Check if called from callback or command
    if update.callback_query:
        message_func = update.callback_query.message.reply_text
    else:
        message_func = update.message.reply_text

    if not stats:
        await message_func("You don't have any VPN keys yet. Use /buy to get one!")
        return
        
    msg = "📊 *Your VPN Status*\n\n"
    for i, s in enumerate(stats, 1):
        status_icon = "✅" if s['is_active'] else "🔴"
        usage_gb = s['daily_usage_bytes'] / (1024**3)
        limit_gb = s['data_limit_gb']
        
        msg += f"🔑 *Key {i}* {status_icon}\n"
        msg += f"ID: `{s['uuid']}`\n"
        msg += f"Usage Today: `{usage_gb:.2f} GB` / `{limit_gb} GB`\n"
        msg += f"Status: {'Active' if s['is_active'] else 'Banned/Inactive'}\n"
        msg += f"Expires: {s['expiry_date'][:10]}\n\n"
        
    await message_func(msg, parse_mode='Markdown')

async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle main menu button clicks."""
    query = update.callback_query
    await query.answer()
    
    action = query.data.split("_")[1]
    
    if action == "buy":
        # Call buy logic directly
        await buy(update, context)
    elif action == "status":
        # Call status logic directly
        await handle_status(update, context)
    elif action == "help":
        # Call help logic directly
        await help_command(update, context)

def main() -> None:
    """Start the bot."""
    # Initialize DB
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", handle_status))
    
    # Handle protocol selection callbacks
    application.add_handler(CallbackQueryHandler(handle_protocol_choice, pattern="^protocol_"))
    
    # Handle main menu callbacks
    application.add_handler(CallbackQueryHandler(handle_menu_callback, pattern="^menu_"))
    
    # Handle photos for payment verification
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Handle text to guide user
    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Please send a **photo** of your payment receipt to get your key.", parse_mode="Markdown")

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
