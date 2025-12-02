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
from bot.config import BOT_TOKEN, KBZ_PAY_NUMBER, WAVE_PAY_NUMBER, SERVER_IP, PUBLIC_KEY, SHORT_ID, SERVER_PORT, SERVER_NAME, SS_SERVER, SS_PORT, SS_METHOD, SS_PASSWORD, SS_LEGACY_PORT, SS_LEGACY_PASSWORD, TUIC_PORT, VLESS_PLAIN_PORT, MAX_KEYS_PER_USER, ADMIN_ID, ADMIN_PASSWORD, ADMIN_USERNAME

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

async def handle_protocol_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle protocol selection."""
    query = update.callback_query
    await query.answer()
    
    # Check if admin TUIC selected
    if query.data == "protocol_admin_tuic":
        context.user_data['protocol'] = 'admin_tuic'
        context.user_data['awaiting_admin_password'] = True
        await query.edit_message_text(
            "🔐 **Admin-Only Protocol Selected**\n\n"
            "This is ThawZin's dedicated India TUIC server.\n"
            "Please enter the admin password:",
            parse_mode="Markdown"
        )
        return
    
    protocol = query.data.split("_", 1)[1]  # "ss", "vless", "tuic", "vlessplain", "ss_legacy"
    context.user_data['protocol'] = protocol
    
    # Map protocol codes to display names
    protocol_map = {
        "ss": "Shadowsocks (9388) -> Sing-Box",
        "vless": "VLESS Reality (443) -> Sing-Box",
        "tuic": "TUIC v5 (2083) -> Sing-Box",
        "vlessplain": "VLESS + TLS (8444) -> Sing-Box",
        "ss_legacy": "Shadowsocks (8388) -> Sing-Box"
    }
    protocol_name = protocol_map.get(protocol, "Unknown")
    
    await query.edit_message_text(
        f"Selected: {protocol_name}\n\n"
        f"Please send 3,000 MMK to:\n\n"
        f"KBZ: {KBZ_PAY_NUMBER}\n"
        f"Wave: {WAVE_PAY_NUMBER}\n\n"
        "After payment, send a screenshot of success here."
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send payment instructions and protocol selection."""
    keyboard = [
        [InlineKeyboardButton("VLESS Reality (443) -> Sing-Box", callback_data="protocol_vless")],
        [InlineKeyboardButton("Shadowsocks (9388) -> Sing-Box", callback_data="protocol_ss")],
        [InlineKeyboardButton("TUIC v5 (2083) -> Sing-Box", callback_data="protocol_tuic")],
        [InlineKeyboardButton("VLESS + TLS (8444) -> Sing-Box", callback_data="protocol_vlessplain")],
        [InlineKeyboardButton("Shadowsocks (8388) -> Sing-Box", callback_data="protocol_ss_legacy")],
        [InlineKeyboardButton("Admin TUIC (8443) -> tuic-server", callback_data="protocol_admin_tuic")]
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

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages (for admin password input)."""
    user = update.effective_user
    text = update.message.text
    
    # Check if awaiting admin password
    if context.user_data.get('awaiting_admin_password'):
        ADMIN_PASSWORD = "#ThawZin2k77!"
        
        if text == ADMIN_PASSWORD:
            # Password correct - generate admin TUIC key
            context.user_data['awaiting_admin_password'] = False
            
            import uuid as uuid_lib
            user_uuid = str(uuid_lib.uuid4())
            key_tag = f"{user.username or user.first_name}-AdminTUIC-{user.id}"
            
            # Generate TUIC link for legacy server on port 8443
            # This is the dedicated India server (legacy tuic-server)
            vpn_link = f"tuic://{user_uuid}:{user_uuid}@{SERVER_IP}:8443?congestion_control=bbr&alpn=h3&sni=www.microsoft.com#{key_tag}"
            
            # Add to database (skip sing-box config as this uses legacy tuic-server)
            from db.database import add_user
            if add_user(user_uuid, user.id, user.username or user.first_name or f"User{user.id}", 
                       'admin_tuic', user.language_code, user.is_premium):
                
                # Generate QR Code
                import qrcode
                import io
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(vpn_link)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                bio = io.BytesIO()
                img.save(bio)
                bio.seek(0)
                
                await update.message.reply_text(
                    f"✅ **Admin TUIC Key Generated!**\n\n"
                    f"🔐 **Thailand's Dedicated India Server**\n"
                    f"[Link] Copy link:\n`{vpn_link}`\n\n"
                    f"[Tip] For personal use only!",
                    parse_mode="Markdown"
                )
                await update.message.reply_photo(bio, caption="Scan this QR to import")
            else:
                await update.message.reply_text("❌ Error generating key. Contact support.")
        else:
            # Wrong password
            await update.message.reply_text(
                "❌ **Incorrect Password**\n\n"
                "Access denied. This feature is admin-only.",
                parse_mode="Markdown"
            )
            context.user_data['awaiting_admin_password'] = False
        
        return
    
    # Handle other text messages (if any)
    await update.message.reply_text("Please use the /start command to see available options.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment screenshot."""
    user = update.effective_user
    photo_file = await update.message.photo[-1].get_file()
    
    # Download image temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        await photo_file.download_to_drive(tmp.name)
        tmp_path = tmp.name
        
    try:
        # 1. NSFW Detection
        detector = get_nsfw_detector()
        if detector:
            try:
                predictions = detector.detect(tmp_path)
                nsfw_classes = ['EXPOSED_GENITALIA', 'EXPOSED_BREAST_F', 'EXPOSED_BUTTOCKS', 'EXPOSED_ANUS']
                is_nsfw = any(
                    pred['class'] in nsfw_classes and pred['score'] > 0.6
                    for pred in predictions
                )
                if is_nsfw:
                    await update.message.reply_text("Inappropriate content detected.", parse_mode="Markdown")
                    return
            except Exception as e:
                logger.error(f"NSFW detection failed: {e}")

        # 2. OCR & Payment Validation
        await update.message.reply_text("Verifying payment slip... (this may take a few seconds)")
        
        from services.ocr_service import ocr_service
        from services.payment_validator import payment_validator, InvalidReceiptError
        from db.database import is_transaction_used, add_transaction
        
        # Extract text
        text_lines = ocr_service.extract_text(tmp_path)
        
        if not text_lines:
            await update.message.reply_text("Could not read text from image. Please send a clear screenshot.")
            return
            
        # Validate receipt
        try:
            data = payment_validator.validate_receipt(text_lines)
            
            TEST_SLIP_ID = "01003984021770423212"
            
            if data['transaction_id'] == TEST_SLIP_ID:
                await update.message.reply_text(
                    f"The Test Banking Slip is being utilized.\n"
                    f"Transaction ID: {data['transaction_id']}\n"
                    f"User: {user.username or user.first_name}"
                )
            else:
                # Check for duplicates
                if is_transaction_used(data['transaction_id']):
                    await update.message.reply_text(f"Transaction ID `{data['transaction_id']}` has already been used!", parse_mode="Markdown")
                    return
                    
                # Check amount (allow small margin of error or exact match)
                if data['amount'] < 3000:
                    await update.message.reply_text(f"Amount `{data['amount']}` is less than required 3,000 MMK.", parse_mode="Markdown")
                    return
                    
                # Success! Record transaction
                add_transaction(user.id, data['provider'], data['transaction_id'], data['amount'])
                await update.message.reply_text(f"Payment Verified!\nProvider: {data['provider']}\nTID: `{data['transaction_id']}`", parse_mode="Markdown")
            
        except InvalidReceiptError as e:
            await update.message.reply_text(f"Invalid Receipt: {str(e)}\n\nPlease make sure to upload a valid KBZ Pay or Wave Pay slip.")
            return
        except Exception as e:
            logger.error(f"Validation error: {e}")
            await update.message.reply_text("Error verifying receipt. Please contact support.")
            return

    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    
    # Key limit removed - users can buy as many keys as they want with valid payments
    # Each payment must be unique (no duplicate transaction IDs)
    
    # Generate UUID
    user_uuid = str(uuid.uuid4())
    
    # Calculate key index for tagging
    current_stats = get_user_stats(user.id)
    key_index = len(current_stats) + 1
    
    # Sanitize name for tag (remove special chars) with proper fallback
    raw_name = user.username or user.first_name or f"User{user.id}"
    safe_name = "".join(c for c in raw_name if c.isalnum())
    if not safe_name: safe_name = "User"
    key_tag = f"{safe_name}-Key{key_index}"
    
    # Get user's protocol choice (default to SS if not set) - MUST be before add_user!
    protocol = context.user_data.get('protocol', 'ss')
    
    # Ensure username is never None (use fallback for DB storage)
    db_username = user.username or user.first_name or f"User{user.id}"
    
    # Add to DB
    if add_user(user_uuid, user.id, db_username, protocol, user.language_code, user.is_premium):
        # Update Sing-Box config based on protocol
        try:
            if protocol == 'vless':
                from bot.config_manager import add_user_to_config
                add_user_to_config(user_uuid, key_tag)
            elif protocol == 'tuic':
                from bot.config_manager import add_tuic_user
                add_tuic_user(user_uuid, key_tag)
            elif protocol == 'vlessplain':
                from bot.config_manager import add_vless_plain_user
                add_vless_plain_user(user_uuid, key_tag)
            # SS and SS Legacy don't need individual user config updates (Legacy uses shared password)
        except Exception as e:
            logger.error(f"Failed to update config for {protocol}: {e}")
            await update.message.reply_text("Account created but VPN activation failed. Contact support.")
            return

        # Generate link based on protocol
        if protocol == 'ss':
            # Generate Shadowsocks link with unique password (UUID)
            import base64
            ss_credential = f"{SS_METHOD}:{user_uuid}"
            ss_encoded = base64.b64encode(ss_credential.encode()).decode()
            vpn_link = f"ss://{ss_encoded}@{SS_SERVER}:{SS_PORT}#{key_tag}"
            protocol_name = "Shadowsocks"
            
        elif protocol == 'tuic':
            # Generate TUIC Link (must use cert's CN for SNI)
            vpn_link = f"tuic://{user_uuid}:{user_uuid}@{SERVER_IP}:{TUIC_PORT}?congestion_control=bbr&alpn=h3&sni=www.microsoft.com#{key_tag}"
            protocol_name = "TUIC"
            
        elif protocol == 'vlessplain':
            # Generate Plain VLESS Link (VLESS over TCP/TLS, must use cert's CN for SNI)
            vpn_link = f"vless://{user_uuid}@{SERVER_IP}:{VLESS_PLAIN_PORT}?security=tls&encryption=none&type=tcp&sni=www.microsoft.com#{key_tag}"
            protocol_name = "Plain VLESS"
            
        elif protocol == 'ss_legacy':
            # Generate Legacy Shadowsocks Link (Shared Password)
            import base64
            ss_credential = f"{SS_METHOD}:{SS_LEGACY_PASSWORD}"
            ss_encoded = base64.b64encode(ss_credential.encode()).decode()
            vpn_link = f"ss://{ss_encoded}@{SS_SERVER}:{SS_LEGACY_PORT}#{key_tag}"
            protocol_name = "Shadowsocks (Standalone)"
            
        else:  # Default to VLESS+REALITY
            # Generate VLESS+REALITY Link
            vpn_link = f"vless://{user_uuid}@{SERVER_IP}:{SERVER_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=randomized&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#{key_tag}"
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
        
    await message_func(f"Need help? Contact {ADMIN_USERNAME} for support!")

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
        
    # Header for the first message
    header = "[Status] *Your VPN Status*\n\n"
    
    current_msg = header
    MAX_LENGTH = 4000  # Leave some buffer
    
    for i, s in enumerate(stats, 1):
        status_icon = "✅" if s['is_active'] else "❌"
        usage_gb = s['daily_usage_bytes'] / (1024**3)
        limit_gb = s['data_limit_gb']
        protocol = s.get('protocol', 'ss')
        uuid = s['uuid']
        
        # Generate protocol-specific key
        if protocol == 'vless':
            # Generate VLESS Link
            vpn_link = f"vless://{uuid}@{SERVER_IP}:{SERVER_PORT}?security=reality&encryption=none&pbk={PUBLIC_KEY}&fp=chrome&type=tcp&flow=xtls-rprx-vision&sni={SERVER_NAME}&sid={SHORT_ID}#VPN-Bot-{user.first_name}-Key{i}"
            protocol_name = "VLESS+REALITY"
        else:
            # Generate Shadowsocks Link
            import base64
            ss_credential = f"{SS_METHOD}:{uuid}"
            ss_encoded = base64.b64encode(ss_credential.encode()).decode()
            vpn_link = f"ss://{ss_encoded}@{SS_SERVER}:{SS_PORT}#VPN-Bot-{user.first_name}-Key{i}"
            protocol_name = "Shadowsocks"
        
        # Build key info block
        key_block = ""
        status_text = 'Active' if s['is_active'] else 'Inactive/Banned'
        key_block += f"*[Key {i}]* {protocol_name} {status_icon}\n"
        key_block += f"Status: {status_text}\n"
        key_block += f"Usage: `{usage_gb:.2f} GB` / `{limit_gb} GB`\n"
        key_block += f"Expires: {s['expiry_date'][:10]}\n\n"
        key_block += f"*Your VPN Link:*\n`{vpn_link}`\n\n"
        key_block += "━━━━━━━━━━━━━━━\n\n"
        
        # Check if adding this block would exceed limit
        if len(current_msg) + len(key_block) > MAX_LENGTH:
            # Send current chunk
            await message_func(current_msg, parse_mode='Markdown')
            # Start new chunk
            current_msg = key_block
        else:
            current_msg += key_block
            
    # Add footer to the last message
    current_msg += "_💡 Tip: Copy the link above to import into your VPN app_"
        
    # Send the final (or only) chunk
    if current_msg:
        await message_func(current_msg, parse_mode='Markdown')

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
    
    # Handle text messages (password verification, etc) - using function defined earlier
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
