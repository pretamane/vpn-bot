import sys
import os
import asyncio
from telegram import Bot, BotCommand

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from bot.config import BOT_TOKEN

async def set_commands():
    bot = Bot(token=BOT_TOKEN)
    
    commands = [
        BotCommand("start", "All Available Options"),
        BotCommand("buy", "Quickly Buy a Key"),
        BotCommand("status", "Check the Keys, Usages & Expiry Times"),
        BotCommand("help", "Contact the Seller"),
        BotCommand("admin", "Admin Dashboard (Password Required)")
    ]
    
    from telegram import BotCommandScopeDefault, BotCommandScopeAllPrivateChats
    
    print("Clearing existing commands...")
    try:
        await bot.delete_my_commands(scope=BotCommandScopeDefault())
        await bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())
        print("✅ Cleared old commands.")
    except Exception as e:
        print(f"⚠️ Warning clearing commands: {e}")

    print("Updating bot commands...")
    # Explicitly set scope to Default
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    print("✅ Success! Menu button updated for Default Scope.")
    
    # Explicitly set scope to All Private Chats
    await bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())
    print("✅ Success! Menu button updated for All Private Chats.")
    
    # VERIFICATION
    print("\nVerifying commands from API...")
    current_commands = await bot.get_my_commands(scope=BotCommandScopeDefault())
    print(f"Current Commands (Default Scope): {current_commands}")
    
    if len(current_commands) == len(commands):
        print("✅ API confirms commands are set!")
    else:
        print("❌ API mismatch! Commands might not be set correctly.")

if __name__ == "__main__":
    asyncio.run(set_commands())
