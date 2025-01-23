import os
import requests
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import pytz
from datetime import datetime

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Use your bot token directly (not recommended for production)
TOKEN = '7759537035:AAFNvek1S2QXmkFn5VzWojwJPPzNVTuDhgo'  # Replace with your actual token
TARGET_CHAT = '@ActiveForever'  # The chat where the bot will respond

# Create the application
app = ApplicationBuilder().token(TOKEN).build()

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

async def download_file(file_id, filename, context):
    """Download a file from Telegram and save it to the current directory."""
    try:
        new_file = await context.bot.get_file(file_id)
        await new_file.download_to_drive(filename)  # Download the file to the specified filename
        logger.info(f"File downloaded successfully: {filename}")
    except Exception as e:
        logger.error(f"Error downloading file: {e}")

async def handle_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /dl command to download a file in reply."""
    if update.message.reply_to_message:
        replied_message = update.message.reply_to_message
        if replied_message.document:
            file_id = replied_message.document.file_id
            filename = replied_message.document.file_name  # Get the original file name
            await download_file(file_id, filename, context)  # Download the file
            
            # Get the full path of the saved file
            full_path = os.path.abspath(filename)
            await update.message.reply_text(f"Downloaded file: {filename}\nSaved at: {full_path}")
        else:
            await update.message.reply_text("The replied message does not contain a file.")
    else:
        await update.message.reply_text("Please reply to a message containing a file with the /dl command.")

async def scheduled_task(context):
    """Scheduled task to send .db files."""
    await send_db_files(context)

async def schedule_jobs(context):
    """Schedule jobs to run at specific times."""
    while True:
        now = datetime.now(pytz.timezone('Asia/Kolkata'))
        # Check if it's 12 AM or 12 PM
        if now.hour == 0 and now.minute == 0:
            await send_db_files(context)
        elif now.hour == 12 and now.minute == 0:
            await send_db_files(context)
        await asyncio.sleep(60)  # Wait for a minute before checking again

def main():
    """Main function to start the bot."""
    # Set up command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dl", handle_download))

    # Start the job scheduler
    app.job_queue.run_repeating(schedule_jobs, interval=60, first=0)

    # Start the bot
    app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
