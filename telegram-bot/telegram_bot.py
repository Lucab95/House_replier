import logging
from telegram import Update, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackContext
import os
import dotenv
from queue import Queue
dotenv.load_dotenv("../.env")

# Configure logging 
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory storage for subscribed chat IDs (for production, use a persistent store)
subscribers = set()

def start(update: Update, context: CallbackContext) -> None:
    """Send a welcome message that explains what the bot does and shows the chat ID."""
    chat_id = update.effective_chat.id
    welcome_message = (
        "Hello and welcome!\n\n"
        "I'm a notifications bot. I monitor new apartment listings and send you alerts.\n\n"
        "Your chat ID is: *{}*\n\n"
        "Use /subscribe to start receiving notifications.\n"
        "For a list of commands, try /help."
    ).format(chat_id)
    update.message.reply_text(welcome_message, parse_mode="Markdown")

def subscribe(update: Update, context: CallbackContext) -> None:
    """Subscribe the user for notifications."""
    chat_id = update.effective_chat.id
    if chat_id in subscribers:
        update.message.reply_text("You are already subscribed for notifications!")
    else:
        subscribers.add(chat_id)
        update.message.reply_text("You've been subscribed! You'll now receive notifications.")

def unsubscribe(update: Update, context: CallbackContext) -> None:
    """Unsubscribe the user from notifications."""
    chat_id = update.effective_chat.id
    if chat_id in subscribers:
        subscribers.remove(chat_id)
        update.message.reply_text("You've been unsubscribed. You will no longer receive notifications.")
    else:
        update.message.reply_text("You weren't subscribed.")

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a help message that lists available commands and explains what they do."""
    help_text = (
        "Here are the available commands:\n\n"
        "/start - Start the bot and see your chat ID\n"
        "/subscribe - Subscribe to notifications\n"
        "/unsubscribe - Unsubscribe from notifications\n"
        "/help - Show this help message\n\n"
        "----\n"
        "Bot Editing Commands (set via BotFather):\n"
        "/setname - Change the bot's name\n"
        "/setdescription - Change the bot's description\n"
        "/setabouttext - Change the 'about' information for the bot\n"
        "/setuserpic - Change the bot's profile photo\n"
        "/setcommands - Change the list of bot commands\n"
        "/deletebot - Delete the bot\n\n"
        "Note: The above editing commands are managed through BotFather, not directly by this bot."
    )
    update.message.reply_text(help_text)

def main():
    # Replace with your actual Telegram bot token
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    queue = Queue()
    updater = Updater(TOKEN, update_queue=queue)
    dp = updater.dispatcher

    # Register command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("subscribe", subscribe))
    dp.add_handler(CommandHandler("unsubscribe", unsubscribe))
    dp.add_handler(CommandHandler("help", help_command))
    
    # Start the bot (using polling for simplicity)
    updater.start_polling()
    logger.info("Bot started...")
    updater.idle()

if __name__ == '__main__':
    main()
