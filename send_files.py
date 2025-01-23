import os
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace this with your own values
TOKEN = '7759537035:AAFNvek1S2QXmkFn5VzWojwJPPzNVTuDhgo' # Get the token from environment variable
TARGET_CHAT = '@ActiveForever'  # The chat where the bot will respond

# Create the application
app = ApplicationBuilder().token(TOKEN).build()
scheduler = AsyncIOScheduler()

async def send_db_files(context):
    """Send all .db files in the current directory to the specified chat."""
    chat_id = context.chat_data.get('chat_id', TARGET_CHAT)
    for filename in os.listdir('.'):
        if filename.endswith('.db'):
            await context.bot.send_document(chat_id, document=open(filename, 'rb'))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Respond to the /start command."""
    await update.message.reply_text('This bot will send .db files at 12 AM and 12 PM IST.')
    context.chat_data['chat_id'] = update.message.chat.id  # Store chat ID for later use
    await send_db_files(context)

async def download_file(file_url, filename):
    """Download a file from a URL and save it to the specified filename."""
    try:
        response = requests.get(file_url, allow_redirects=True)
        response.raise_for_status()  # Raise an error for bad responses
        with open(filename, 'wb') as file:
            file.write(response.content)
        logger.info(f"File downloaded successfully: {filename}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading file: {e}")

async def handle_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /dl command to download a file in reply."""
    if update.message.reply_to_message:
        replied_message = update.message.reply_to_message
        if replied_message.document:
            file_id = replied_message.document.file_id
            new_file = await context.bot.get_file(file_id)
            file_url = new_file.file_path
            filename = os.path.basename(file_url)
            download_file(file_url, filename)
            await update.message.reply_text(f"Downloaded file: {filename}")
        else:
            await update.message.reply_text("The replied message does not contain a file.")
    else:
        await update.message.reply_text("Please reply to a message containing a file with the /dl command.")

async def scheduled_task(context):
    """Scheduled task to send .db files."""
    await send_db_files(context)

def main():
    """Main function to start the bot and scheduler."""
    # Set up command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dl", handle_download))

    # Schedule the task to run at 12 AM and 12 PM IST
    scheduler.add_job(scheduled_task, 'cron', hour='0,12', minute='0', timezone='Asia/Kolkata', args=[app])
    
    # Start the scheduler
    scheduler.start()

    # Start the bot
    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
