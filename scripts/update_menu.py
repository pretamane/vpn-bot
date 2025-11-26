import asyncio
from telegram import Bot, BotCommand
from bot.config import BOT_TOKEN

async def set_commands():
    bot = Bot(token=BOT_TOKEN)
    
    commands = [
        BotCommand("start", "Main Menu"),
        BotCommand("buy", "Get VPN Key"),
        BotCommand("status", "Check Usage & Expiry"),
        BotCommand("help", "Get Support")
    ]
    
    print("Updating bot commands...")
    await bot.set_my_commands(commands)
    print("✅ Success! Menu button updated.")

if __name__ == "__main__":
    asyncio.run(set_commands())
