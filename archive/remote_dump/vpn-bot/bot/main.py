import logging
import uuid
import qrcode
import io
import sys
import os
import tempfile

# Add parent directory to path to import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from db.database import add_user, get_user, init_db, get_active_key_count, get_user_stats, get_all_users, delete_user, activate_user, deactivate_user
from bot.config import BOT_TOKEN, KBZ_PAY_NUMBER, WAVE_PAY_NUMBER, SERVER_IP, PUBLIC_KEY, SHORT_ID, SERVER_PORT, SERVER_NAME, SS_SERVER, SS_PORT, SS_METHOD, SS_PASSWORD, MAX_KEYS_PER_USER, ADMIN_ID, ADMIN_PASSWORD

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize NSFW detector (lazy load to avoid startup delay)
nsfw_detector = None

def get_nsfw_detector():
    global nsfw_detector
    if nsfw_detector is None:
        try:
            from nudenet import NudeDetector
            nsfw_detector = NudeDetector()
            logger.info("NudeNet detector initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize NudeNet: {e}")
            nsfw_detector = False  # Mark as failed to avoid retrying
    return nsfw_detector if nsfw_detector is not False else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("[Buy] Buy VPN Key", callback_data="menu_buy")],
        [InlineKeyboardButton("[Status] My Status", callback_data="menu_status")],
        [InlineKeyboardButton("[Help] Help & Support", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        f"Welcome {user.mention_html()}! [MM]\n\n"
        "[+] 12 Mbps speed | 5 GB/day | 1 device/key\n"
        "[$] Price: 3,000 MMK/month\n\n"
        "Select an option below:",
        reply_markup=reply_markup
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send payment instructions and protocol selection."""
    keyboard = [
        [InlineKeyboardButton("[SS] Shadowsocks (Recommended)", callback_data="protocol_ss")],
        [InlineKeyboardButton("[VLESS] VLESS+REALITY (Experimental)", callback_data="protocol_vless")]
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
        f"[+] Selected: {protocol_name}\n\n"
        f"Please send 3,000 MMK to:\n\n"
        f"KBZ: {KBZ_PAY_NUMBER}\n"
        f"Wave: {WAVE_PAY_NUMBER}\n\n"
        "[!] After payment, send a screenshot of success here."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment screenshot."""
    user = update.effective_user
    photo_file = await update.message.photo[-1].get_file()
    
    # Download image temporarily for NSFW detection
    detector = get_nsfw_detector()
    if detector:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                await photo_file.download_to_drive(tmp.name)
                tmp_path = tmp.name
            
            try:
                # Run NSFW detection
                predictions = detector.detect(tmp_path)
                
                # Check for explicit NSFW content
                nsfw_classes = ['EXPOSED_GENITALIA', 'EXPOSED_BREAST_F', 'EXPOSED_BUTTOCKS', 'EXPOSED_ANUS']
                is_nsfw = any(
                    pred['class'] in nsfw_classes and pred['score'] > 0.6
                    for pred in predictions
                )
                
                if is_nsfw:
                    await update.message.reply_text(
                        "⚠️ *Inappropriate content detected.*\n\n"
                        "Please upload a valid payment screenshot.\n\n"
                        "If you believe this is an error, contact support.",
                        parse_mode="Markdown"
                    )
                    return
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        except Exception as e:
            logger.error(f"NSFW detection failed: {e}")
            # Continue with payment processing if detection fails
    
    await update.message.reply_text("[+] Payment received! Verifying...")
    
    # Simulate processing time
    # In reality, this might be manual or async
    
    # Check if user has reached key limit
    active_count = get_active_key_count(user.id)
    if active_count >= MAX_KEYS_PER_USER:
        await update.message.reply_text(
            f"[!] You already have {active_count} active key(s).\n"
            f"Maximum allowed: {MAX_KEYS_PER_USER}\n\n"
            "Please use your existing key or contact support."
        )
        return
    
    # Generate UUID
    user_uuid = str(uuid.uuid4())
    
    # Add to DB
    if add_user(user_uuid, user.id, user.username, user.language_code, user.is_premium):
        # Get user's protocol choice (default to SS if not set)
        protocol = context.user_data.get('protocol', 'ss')
        
        # Only update Sing-Box config for VLESS (SS doesn't need individual users)
        if protocol == 'vless':
            from bot.config_manager import add_user_to_config
            try:
                add_user_to_config(user_uuid, f"user_{user.id}")
            except Exception as e:
                logger.error(f"Failed to update config: {e}")
                await update.message.reply_text("[!] Account created but VPN activation failed. Contact support.")
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
            f"[Key] Your {protocol_name} key is ready!\n\n"
            f"[Link] Copy link:\n`{vpn_link}`\n\n"
            f"[Tip] Only use on 1 device!",
            parse_mode="Markdown"
        )
        await update.message.reply_photo(bio, caption="Scan this QR to import")
        
    else:
        await update.message.reply_text("[X] Error generating key. Please contact support.")

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
        
    msg = "[Status] *Your VPN Status*\n\n"
    for i, s in enumerate(stats, 1):
        status_icon = "[OK]" if s['is_active'] else "[Inactive]"
        usage_gb = s['daily_usage_bytes'] / (1024**3)
        limit_gb = s['data_limit_gb']
        
        msg += f"[Key] *Key {i}* {status_icon}\n"
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

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin dashboard entry point."""
    # Ask for password
    await update.message.reply_text(
        "🔒 *Admin Access*\n\nPlease enter the admin password to continue:",
        parse_mode="Markdown"
    )
    # Set state to waiting for password
    context.user_data['waiting_for_admin_pass'] = True

async def show_admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the actual dashboard."""
    keyboard = [
        [InlineKeyboardButton("👥 List Users", callback_data="admin_list_users")],
        [InlineKeyboardButton("📊 System Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Check if called from callback or message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🛡️ *Admin Dashboard*\n\nSelect an action:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "🛡️ *Admin Dashboard*\n\nSelect an action:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin menu actions."""
    query = update.callback_query
    
    # Verify session (simple check)
    if not context.user_data.get('admin_authenticated'):
        await query.answer("Session expired. Please login again with /admin", show_alert=True)
        return
        
    await query.answer()
    data = query.data
    
    if data == "admin_close":
        await query.message.delete()
        context.user_data['admin_authenticated'] = False # Logout
        return
        
    if data == "admin_list_users":
        users = get_all_users()
        if not users:
            await query.edit_message_text("No users found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_home")]]))
            return
            
        msg = "👥 *Registered Users*\n\n"
        keyboard = []
        
        for u in users[:10]: # Show last 10 users
            status = "🟢" if u['is_active'] else "🔴"
            msg += f"{status} `{u['username'] or u['telegram_id']}`\n"
            keyboard.append([InlineKeyboardButton(f"Manage {u['username'] or u['telegram_id']}", callback_data=f"admin_user_{u['uuid']}")])
            
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_home")])
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data == "admin_home":
        await show_admin_dashboard(update, context)
        
    elif data.startswith("admin_user_"):
        uuid = data.split("_")[2]
        user_data = get_user(uuid)
        
        if not user_data:
            await query.edit_message_text("User not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_list_users")]]))
            return
            
        status = "Active" if user_data['is_active'] else "Banned"
        msg = f"👤 *User Details*\n\n"
        msg += f"ID: `{user_data['telegram_id']}`\n"
        msg += f"Username: @{user_data['username']}\n"
        msg += f"UUID: `{user_data['uuid']}`\n"
        msg += f"Status: {status}\n"
        msg += f"Limit: {user_data['data_limit_gb']} GB\n"
        
        keyboard = [
            [InlineKeyboardButton("🔑 Show Keys", callback_data=f"admin_keys_{uuid}")],
            [InlineKeyboardButton("🚫 Ban" if user_data['is_active'] else "✅ Unban", callback_data=f"admin_toggle_{uuid}")],
            [InlineKeyboardButton("🗑️ Delete", callback_data=f"admin_delete_{uuid}")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_list_users")]
        ]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data.startswith("admin_keys_"):
        uuid = data.split("_")[2]
        user_data = get_user(uuid)
        
        if not user_data:
            await query.answer("User not found", show_alert=True)
            return
            
        # Generate VLESS Link
        vless_link = f"vless://{uuid}@{SERVER_IP}:{SERVER_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=chrome&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#VPN-Bot-{user_data['username'] or 'User'}"
        
        # Generate SS Link
        import base64
        ss_credential = f"{SS_METHOD}:{uuid}"
        ss_encoded = base64.b64encode(ss_credential.encode()).decode()
        ss_link = f"ss://{ss_encoded}@{SS_SERVER}:{SS_PORT}#VPN-Bot-{user_data['username'] or 'User'}"
        
        msg = f"🔑 *Keys for {user_data['username'] or user_data['telegram_id']}*\n\n"
        msg += f"**VLESS+REALITY:**\n`{vless_link}`\n\n"
        msg += f"**Shadowsocks:**\n`{ss_link}`\n\n"
        msg += "_Note: Check which protocol the user actually purchased._"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data=f"admin_user_{uuid}")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin_toggle_"):
        uuid = data.split("_")[2]
        user_data = get_user(uuid)
        if user_data['is_active']:
            deactivate_user(uuid)
        else:
            activate_user(uuid)
        
        # Refresh view
        await handle_admin_callback(update, context) 
        
    elif data.startswith("admin_delete_"):
        uuid = data.split("_")[2]
        from bot.config_manager import remove_ss_user, remove_vless_user
        remove_ss_user(uuid)
        remove_vless_user(uuid)
        delete_user(uuid)
        await query.answer("User deleted", show_alert=True)
        
        # Go back to list
        update.callback_query.data = "admin_list_users"
        await handle_admin_callback(update, context)

    elif data == "admin_stats":
        import psutil
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        msg = "📊 *System Stats*\n\n"
        msg += f"CPU: {cpu}%\n"
        msg += f"RAM: {ram}%\n"
        msg += f"Disk: {disk}%\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_home")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

def main() -> None:
    """Start the bot."""
    # Initialize DB
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", handle_status))
    application.add_handler(CommandHandler("admin", admin_command))
    
    # Handle protocol selection callbacks
    application.add_handler(CallbackQueryHandler(handle_protocol_choice, pattern="^protocol_"))
    
    # Handle main menu callbacks
    application.add_handler(CallbackQueryHandler(handle_menu_callback, pattern="^menu_"))
    
    # Handle admin callbacks
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^admin_"))
    
    # Handle photos for payment verification
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Handle text to guide user
    # Handle text to guide user or verify password
    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Check if waiting for admin password
        if context.user_data.get('waiting_for_admin_pass'):
            if update.message.text == ADMIN_PASSWORD:
                context.user_data['waiting_for_admin_pass'] = False
                context.user_data['admin_authenticated'] = True
                await update.message.reply_text("✅ Access Granted!")
                await show_admin_dashboard(update, context)
            else:
                await update.message.reply_text("❌ Incorrect password. Access denied.")
                context.user_data['waiting_for_admin_pass'] = False
            return

        await update.message.reply_text("Please send a **photo** of your payment receipt to get your key.", parse_mode="Markdown")

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
