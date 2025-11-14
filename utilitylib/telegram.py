import requests
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import BOT_TOKEN

TOKEN = BOT_TOKEN

class ChatBot:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
    
    def send_message(self, chat_id: str, text: str, parse_mode = "HTML"):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode, "link_preview_options": {"is_disabled": True}}
        response = requests.post(url, json=data)
        if not response.ok: 
            raise Exception(f"Telegram API error: {response.text}")


# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Try /command something")


async def command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /command <add|remove|list> ...")
        return

    sub = context.args[0]  # "add" / "remove" / "list" ...
    rest = context.args[1:]

    if sub == "add":
        # handle add
        await update.message.reply_text(f"Adding: {' '.join(rest)}")
    elif sub == "remove":
        await update.message.reply_text(f"Removing: {' '.join(rest)}")
    elif sub == "list":
        await update.message.reply_text("Listing items...")
    else:
        await update.message.reply_text("Unknown subcommand")


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Status: Bot is running")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
Available commands:
/start - Start the bot
/command <add|remove|list> - Manage items
/status - Check bot status
/help - Show this help message
"""
    await update.message.reply_text(help_text)


async def main():
    # Create application
    app = ApplicationBuilder().token(TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("command", command_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("help", help_handler))

    # Start polling
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
