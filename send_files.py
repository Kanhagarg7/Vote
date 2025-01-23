
### Explanation:
#- **Scheduler**: The `apscheduler` library is used to schedule tasks at specific times.
#- **Time Zone**: The bot is set to send files at 12 AM and 12 PM IST using the `Asia/Kolkata` timezone.
#- **Chat Check**: The bot checks if the command is issued in the `@ActiveForever` chat before responding.
#- **File Sending**: The `send_db_files` function is called at the scheduled times to send the `.db` files. ```python
# Ensure you have the necessary libraries installed
# You can install them using pip if you haven't already
# pip install telethon apscheduler pytz

import os
import asyncio
from telethon import TelegramClient, events
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import pytz

# Replace these with your own values
api_id = '6'
api_hash = 'eb06d4abfb49dc3eeb1aeb98ae0f581e'
bot_token = '7759537035:AAFNvek1S2QXmkFn5VzWojwJPPzNVTuDhgo'
target_chat = '@ActiveForever'  # The chat where the bot will respond

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)
scheduler = AsyncIOScheduler()

async def send_db_files(chat_id):
    for filename in os.listdir('.'):
        if filename.endswith('.db'):
            await client.send_file(chat_id, filename)

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.chat.username == target_chat.lstrip('@'):
        await event.respond('This bot will send .db files at 12 AM and 12 PM IST.')
        chat = await client.get_entity(target_chat)
        await send_db_files(chat.id)

@scheduler.scheduled_job('cron', hour='0,12', minute='0', timezone='Asia/Kolkata')
async def scheduled_task():
    chat = await client.get_entity(target_chat)
    await send_db_files(chat.id)

async def main():
    await client.start()
    scheduler.start()
    print("Bot is running...")

# Run the main function
asyncio.run(main())
