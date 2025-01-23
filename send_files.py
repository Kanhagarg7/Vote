import os
import asyncio
import requests
from telethon import TelegramClient, events
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

# Replace these with your own values
api_id = '6'
api_hash = 'eb06d4abfb49dc3eeb1aeb98ae0f581e'
bot_token = '7759537035:AAFNvek1S2QXmkFn5VzWojwJPPzNVTuDhgo'
target_chat = '@ActiveForever'  # The chat where the bot will respond

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)
scheduler = AsyncIOScheduler()

async def send_db_files(chat_id):
    """Send all .db files in the current directory to the specified chat."""
    for filename in os.listdir('.'):
        if filename.endswith('.db'):
            await client.send_file(chat_id, filename)

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    """Respond to the /start command."""
    if event.chat.username == target_chat.lstrip('@'):
        await event.respond('This bot will send .db files at 12 AM and 12 PM IST.')
        chat = await client.get_entity(target_chat)
        await send_db_files(chat.id)

@scheduler.scheduled_job('cron', hour='0,12', minute='0', timezone='Asia/Kolkata')
async def scheduled_task():
    """Scheduled task to send .db files."""
    chat = await client.get_entity(target_chat)
    await send_db_files(chat.id)

def download_file(file_url, filename):
    """Download a file from a URL and save it to the specified filename."""
    try:
        response = requests.get(file_url, allow_redirects=True)
        response.raise_for_status()  # Raise an error for bad responses
        with open(filename, 'wb') as file:
            file.write(response.content)
        print(f"File downloaded successfully: {filename}")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")

@client.on(events.NewMessage(pattern='/dl'))
async def handle_download(event):
    """Handle the /dl command to download a file in reply."""
    if event.is_reply:
        replied_message = await event.get_reply_message()
        if replied_message.media:
            file_url = await client.get_file(replied_message)
            filename = os.path.basename(file_url)
            download_file(file_url, filename)
            await event.respond(f"Downloaded file: {filename}")
        else:
            await event.respond("The replied message does not contain a file.")
    else:
        await event.respond("Please reply to a message containing a file with the /dl command.")

async def main():
    """Main function to start the bot and scheduler."""
    await client.start()
    scheduler.start()
    print("Bot is running...")

# Run the main function
asyncio.run(main())
