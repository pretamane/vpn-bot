"""
Notification system for VPN bot - sends Telegram messages for data usage events.
"""
from telegram import Bot
from bot.config import BOT_TOKEN
import logging

logger = logging.getLogger(__name__)

try:
    bot = Bot(token=BOT_TOKEN)
except Exception as e:
    logger.error(f"Failed to initialize Telegram bot: {e}")
    bot = None


def notify_data_warning(telegram_id, used_gb, limit_gb, percentage):
    """
    Notify user when approaching data limit.
    
    Args:
        telegram_id: User's Telegram ID
        used_gb: Data used in GB
        limit_gb: Data limit in GB
        percentage: Current usage percentage
    """
    if not bot:
        logger.error("Bot not initialized, cannot send notification")
        return False
    
    remaining_gb = limit_gb - used_gb
    
    # Choose emoji and message based on severity
    if percentage >= 95:
        emoji = "🚨"
        urgency = "CRITICAL"
    elif percentage >= 65:
        emoji = "⚠️"
        urgency = "WARNING"
    else:
        emoji = "ℹ️"
        urgency = "NOTICE"
    
    message = f"""
{emoji} *{urgency}: Data Usage Alert*

You've used *{percentage}%* of your data limit!

📊 Usage: {used_gb:.2f} GB / {limit_gb} GB
📉 Remaining: {remaining_gb:.2f} GB

{'⏳ Your key will expire when the limit is reached, but you will get a 24-hour grace period.' if percentage < 100 else ''}
"""
    
    try:
        bot.send_message(chat_id=telegram_id, text=message, parse_mode='Markdown')
        logger.info(f"Sent {percentage}% warning to user {telegram_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to {telegram_id}: {e}")
        return False


def notify_grace_period_start(telegram_id, used_gb, limit_gb):
    """
    Notify user when they've exceeded their limit and grace period starts.
    
    Args:
        telegram_id: User's Telegram ID
        used_gb: Data used in GB
        limit_gb: Data limit in GB
    """
    if not bot:
        logger.error("Bot not initialized, cannot send notification")
        return False
    
    message = f"""
⏳ *Grace Period Started - Data Limit Exceeded*

You've exceeded your data limit!

📊 Usage: {used_gb:.2f} GB / {limit_gb} GB (100%+)

🎁 *24-Hour Grace Period*
Your VPN key will continue working for the next 24 hours, but will automatically expire after that.

💡 *What to do:*
• Purchase a new key with /buy to avoid interruption
• Your grace period ends in 24 hours

Thank you for using MMVPN! 🌐
"""
    
    try:
        bot.send_message(chat_id=telegram_id, text=message, parse_mode='Markdown')
        logger.info(f"Sent grace period notification to user {telegram_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to {telegram_id}: {e}")
        return False


def notify_grace_period_ending(telegram_id, hours_remaining):
    """
    Notify user that grace period is ending soon.
    
    Args:
        telegram_id: User's Telegram ID
        hours_remaining: Hours remaining in grace period
    """
    if not bot:
        logger.error("Bot not initialized, cannot send notification")
        return False
    
    message = f"""
⏰ *Grace Period Ending Soon*

Your 24-hour grace period is almost over!

⏳ Time Remaining: ~{hours_remaining} hours

Your VPN key will automatically expire when the grace period ends.

💡 Purchase a new key now with /buy to avoid service interruption.
"""
    
    try:
        bot.send_message(chat_id=telegram_id, text=message, parse_mode='Markdown')
        logger.info(f"Sent grace period ending warning to user {telegram_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to {telegram_id}: {e}")
        return False


def notify_key_expired(telegram_id, reason='grace_period_ended'):
    """
    Notify user when their key has been expired.
    
    Args:
        telegram_id: User's Telegram ID
        reason: Reason for expiration
    """
    if not bot:
        logger.error("Bot not initialized, cannot send notification")
        return False
    
    reason_text = {
        'grace_period_ended': 'Your 24-hour grace period has ended',
        'data_limit_exceeded': 'Your data limit was exceeded'
    }.get(reason, 'Your key has expired')
    
    message = f"""
🚫 *VPN Key Expired*

{reason_text}.

Your VPN access has been automatically deactivated.

💡 To continue using the VPN, please purchase a new key with /buy

Thank you for using MMVPN! 🌐
"""
    
    try:
        bot.send_message(chat_id=telegram_id, text=message, parse_mode='Markdown')
        logger.info(f"Sent expiration notification to user {telegram_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to {telegram_id}: {e}")
        return False
