import os
import sqlite3
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.helpers import escape_markdown

from telegram.error import BadRequest
import asyncio 
import time
from datetime import *
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CallbackQueryHandler, ChatMemberHandler, ContextTypes
import sqlite3
img_path = "img/img.png"
BOT_TOKEN = "7948701239:AAHceJ4o62b327roKIPoIwK4tFd58_aSfVA"
redis_uri = "redis://redis-18180.c85.us-east-1-2.ec2.redns.redis-cloud.com:18180"
redis_password = "A75rYUacyUeWBOqAHk0JaeAX4kBmABFv"
owners = [5873900195]
bot_username = "ActiveForever_Votingbot"
API_ID = 6
API_HASH = "eb06d4abfb49dc3eeb1aeb98ae0f581e"

def init_db():
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    
    # Create the pollstable with message_channel_id
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS polls(
            poll_id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_username TEXT NOT NULL,
            creator_id INTEGER NOT NULL,
            votes INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            message_channel_id TEXT  -- Stores the message link (https://t.me/channel/message_id)
        )
    """)

    # Create the voters table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            poll_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            vote_count INTEGER DEFAULT 0,
            ban_until INTEGER DEFAULT 0,
            message_id INTEGER NOT NULL,
            PRIMARY KEY (poll_id, user_id)
        )
    """)

    # Create the user_pollstable
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_polls(
            user_id INTEGER PRIMARY KEY,
            has_created_poll BOOLEAN
        )
    """)

    # Create the poll_votes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS poll_votes (
            poll_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            PRIMARY KEY (poll_id, user_id)
        )
    """)

    conn.commit()
    conn.close()
import sqlite3

def save_message_id_to_db(user_id, poll_id, message_id, message_channel_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE polls SET message_id = ?, message_channel_id = ? WHERE poll_id = ? AND creator_id = ?
    """, (message_id, message_channel_id, poll_id, user_id))
    
    conn.commit()
    conn.close()



def delete_poll_info(poll_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM voters WHERE poll_id = ?", (poll_id,))
    cursor.execute("DELETE FROM polls WHERE poll_id = ?", (poll_id,))
    conn.commit()
    conn.close()
def list(poll_id, user_id, user_name, message_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO poll_votes(poll_id, user_id , user_name, message_id)
        VALUES (?, ? , ?, ?)
    """, (poll_id, user_id, user_name, message_id))
    conn.commit()
    conn.close()

def create_poll(channel_username, creator_id, message_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO polls (channel_username, creator_id, votes, message_id)
        VALUES (?, ?, 0, ?)
    """, (channel_username, creator_id, message_id))
    conn.commit()
    conn.close()
def has_created_poll(user_id: int) -> bool:
    conn = sqlite3.connect('vote_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT has_created_poll FROM user_polls WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    # If the user has no entry, return False (i.e., they haven't created a poll)
    if result is None:
        return False
    return result[0]

def mark_poll_created(user_id: int):
    conn = sqlite3.connect('vote_bot.db')
    cursor = conn.cursor()
    # Insert or update the user's poll creation status
    cursor.execute('''
        INSERT INTO user_polls (user_id, has_created_poll)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET has_created_poll = ?
    ''', (user_id, True, True))
    conn.commit()
    conn.close()
def get_poll_by_channel(channel_username, message_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT poll_id, votes FROM polls WHERE channel_username = ? AND message_id = ?
    """, (channel_username, message_id))
    result = cursor.fetchone()
    conn.close()
    return result
def get_poll_by_id(poll_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT channel_username, votes FROM polls WHERE poll_id = ?
    """, (poll_id,))
    result = cursor.fetchone()
    conn.close()
    return result

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import sqlite3

import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

import re

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ensure the user is authorized to refresh the polls(e.g., only admins)
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    # Fetch all pollsfrom the database
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT poll_id, channel_username, message_channel_id, votes, message_id FROM polls
    """)
    polls = cursor.fetchall()

    if not polls:
        await update.message.reply_text("❌ No polls found to refresh.")
        return

    # Loop through all pollsand update the inline buttons for each message
    for poll in polls:
        poll_id, channel_username, message_channel_id, votes, message_id = poll
        
        # Extract the message ID from the URL (if it's a URL)
        match = re.search(r'(\d+)$', message_channel_id)  # Match the last part of the URL
        if match:
            message_channel_id = match.group(1)  # This gives the numeric message ID
        
        print(f"Updating poll {poll_id} in channel {channel_username} with message_channel_id {message_channel_id} and votes {votes}")

        # Create the new inline button with updated vote count
        new_button = InlineKeyboardMarkup(
            [[InlineKeyboardButton(f"Vote ⚡  ({votes})", callback_data=f"vote:{poll_id}:{message_id}")]]
        )

        try:
            # Try to update the message in the channel with the new inline button
            await context.bot.edit_message_reply_markup(
                chat_id=f"@{channel_username}",  # Correct channel username
                message_id=int(message_channel_id),  # Convert message_channel_id to integer
                reply_markup=new_button
            )
        except TelegramError as e:
            # If the message is not found or any other Telegram-related issue, log and inform the user
            if "Message to edit not found" in str(e):
                print(f"Message with ID {message_channel_id} not found.")
                await update.message.reply_text(f"❌ Failed to update poll {poll_id}: Message not found.")
                
                # Optionally re-send the poll
                await resend_poll(context, poll_id, channel_username, votes)  # Implement resend_poll to re-send the poll message
            else:
                print(f"Error updating poll {poll_id}: {e}")
                await update.message.reply_text(f"❌ Failed to update poll {poll_id}: {e}")

    await update.message.reply_text("✅ All  vote and polls have been refreshed!")


def decrement_vote(poll_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    
    cursor.execute("UPDATE polls SET votes = votes - 1 WHERE poll_id = ?", (poll_id,))
    
    conn.commit()
    conn.close()
def remove_vote_record(poll_id, user_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM poll_votes WHERE poll_id = ? AND user_id = ?", (poll_id, user_id))
    
    conn.commit()
    conn.close()

def increment_vote(poll_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE polls SET votes = votes + 1 WHERE poll_id = ?
    """, (poll_id,))
    conn.commit()
    conn.close()
def reset_poll_votes(poll_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE polls SET votes = 0 WHERE poll_id = ?
    """, (poll_id,))
    conn.commit()
    conn.close()
def has_voted(poll_id, user_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM voters WHERE poll_id = ? AND user_id = ?
    """, (poll_id, user_id))
    result = cursor.fetchone()
    conn.close()
    return bool(result)
def record_vote(poll_id, user_id, message_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    # Ensure that `voted_for` is set properly, for example using `message_id` or `username` # or you can use `username` if it's appropriate
    cursor.execute("""
        INSERT INTO voters (poll_id, user_id, message_id)
        VALUES (?, ?, ?)
    """, (poll_id, user_id, message_id))
    conn.commit()
    conn.close()
def increment_user_vote_count(poll_id, user_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE voters SET vote_count = vote_count + 1 WHERE poll_id = ? AND user_id
= ?
    """, (poll_id, user_id))
    conn.commit()
    conn.close()
def set_user_ban(poll_id, user_id, ban_until):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE voters SET ban_until = ? WHERE user_id = ?
    """, (ban_until, user_id))
    conn.commit()
    conn.close()
from datetime import datetime

def get_user_ban_status(user_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ban_until FROM voters WHERE user_id = ?
    """, (user_id,))
    ban_until = cursor.fetchone()
    conn.close()
    
    if ban_until:
        # If the value is an integer (Unix timestamp), convert it to datetime
        if isinstance(ban_until[0], int):
            return datetime.fromtimestamp(ban_until[0])
        # If it's a string, convert it to datetime using strptime (if applicable)
        elif isinstance(ban_until[0], str):
            return datetime.strptime(ban_until[0], "%Y-%m-%d %H:%M:%S")
    
    return None  # No ban exists

def get_top_users(num_top_users):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()

    # Query to aggregate votes for each user and fetch the top users including poll_id
    cursor.execute("""
        SELECT u.user_id, u.username, SUM(p.votes) AS total_votes, p.poll_id
        FROM users u
        JOIN polls p ON u.user_id = p.creator_id
        GROUP BY u.user_id, u.username, p.poll_id
        ORDER BY total_votes DESC
        LIMIT ?
    """, (num_top_users,))
    
    top_users = cursor.fetchall()
    conn.close()
    
    return top_users
def add_users(user_id, username):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    # Insert new user if not already in the table
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)
    """, (user_id, username))
    conn.commit()
    conn.close()
def delete_db():
    if os.path.exists("vote_bot.db"):
        os.remove("vote_bot.db")
def create_users_table():
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    # Create the 'users' table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            votes INTEGER DEFAULT 0,
            participant_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
def get_poll_link(poll_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT message_channel_id FROM polls WHERE poll_id = ?", (poll_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result[0]  # Returns the message link (https://t.me/channel/12345)
    return None

# Call this function when the bot starts to ensure the table is created

# Command to create a vote poll
async def vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    # Check if the user is authorized (either bot owner or sudo user)
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    # Check if the user is banned
    if is_user_banned(update.effective_user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return

    # Ask the user for the channel username
    await update.message.reply_text("❓  Enter Channel Username With @")

# Message handler to handle channel username
import re
import logging
import urllib.parse

async def handle_channel_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Check if user is authorized
        if not is_authorized(update):
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return

        # Get the channel username
        channel_username = update.message.text.strip("@")
        creator_id = update.effective_user.id
        
        # Generate participation link
        participation_link = f"https://t.me/{context.bot.username}?start={channel_username}"
        
        # Escape URL for HTML
        safe_participation_link = urllib.parse.quote(participation_link, safe=":/?&=")
        
        # Prepare the response message using HTML formatting
        response = (
            f"» Poll created successfully.\n"
            f" • Chat: @{channel_username}\n\n"
            f"<b>Participation Link:</b>\n"
            f"<a href='{safe_participation_link}'>Click Here</a>"
        )
        
        # Send the message to the channel
        message = await context.bot.send_message(
            chat_id=f"@{channel_username}", 
            text=response, 
            parse_mode="HTML", 
            disable_web_page_preview=True
        )
        
        # Use the message ID to create the poll
        create_poll(channel_username, creator_id, message.message_id)
        
        # Notify the user who triggered the command
        await update.message.reply_text(response, parse_mode="HTML", disable_web_page_preview=True)
        
    except Exception as e:
        # Log the exception to help with debugging
        logging.error(f"Error in handle_channel_username: {str(e)}")
        await update.message.reply_text("❌ Something went wrong while creating the poll. Please try again later.")

import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

CHANNEL_USERNAME = "@uuuuyghbb"

async def check_user_membership(user_id, bot, CHANNEL_USERNAME):
    """Check if a user is a member of the specified channel."""
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except BadRequest:
        return False

async def handle_join_button(update, context):
    """Handle the 'I Joined' button press."""
    query = update.callback_query
    user = query.from_user
    callback_data = query.data
    channel_username = callback_data.split("_", 1)[1]  # Extract channel username from callback data

    # Check if the user has joined the channel
    is_member = await check_user_membership(user.id, context.bot, CHANNEL_USERNAME)
    if is_member:
        # Add user to the database
        if not is_user_registered(user.id):
            add_user_to_db(user.id, user.first_name, user.last_name or "", user.username or "")
        await query.edit_message_text(f"✅ You are now registered, {user.first_name}!")
        
        # Create poll
    else:
        await query.answer("❌ You are not a member yet. Please join the channel first.", show_alert=True)

async def start_command(update, context):
    user = update.effective_user
    args = context.args  # Retrieve arguments passed to the command

    if not user:
        await update.message.reply_text("❌ Unable to process your request. User information is missing.")
        return

    # Check if the user is banned
    if is_user_banned(user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return 
    is_member = await check_user_membership(user.id, context.bot, CHANNEL_USERNAME)
    if not is_member:
        # Provide inline buttons to join the channel
        join_link = f"https://t.me/uuuuyghbb"
        keyboard = [
            [InlineKeyboardButton("I Joined ✅", callback_data=f"joined_{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("Join Channel 🔗", url=join_link)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"❌ You must join {CHANNEL_USERNAME} to use the bot.\n"
            "Once you join, click 'I Joined' to register.",
            reply_markup=reply_markup
        )
        return
        # Register the user if not already registered
    if not is_user_registered(user.id):
        add_user_to_db(user.id, user.first_name, user.last_name or "", user.username or "")
        await update.message.reply_text(f"✅ You are now registered, {user.first_name}!")

    # Determine the channel username
    if not args:
        await update.message.reply_text(f"✅ Welcome back, {user.first_name}!\nUse a link to participate in the giveaway.")
        return
    channel_username = args[0]

    if args:
        # Check if the user has already created a poll
        if has_created_poll(user.id):
            await update.message.reply_text(
                "❌ You have already created a poll. You cannot create multiple polls."
            )
            return 
    # Create a new poll
        message = await update.message.reply_text("Creating a unique poll...")
        create_poll(channel_username, user.id, message.message_id)
        poll_info = get_poll_by_channel(channel_username, message.message_id)
        poll_id, votes = poll_info
        add_users(user.id, user.username)

    # Create unique vote button
        message_id = update.message.message_id
        button = InlineKeyboardMarkup(
            [[InlineKeyboardButton(f"Vote ⚡  ({votes})", callback_data=f"vote:{poll_id}:{message_id}")]]
        )


# Escape all user-provided inputs and reserved characters
        response = (
            f"✅ Successfully participated.\n\n"
            f"‣ *User* : {escape_markdown(user.first_name, version=1)} {escape_markdown(user.last_name or '', version=1)}\n"
            f"‣ *User-ID* : `{user.id}`\n"
            f"‣ *Username* : @{escape_markdown(user.username or 'None', version=1)}\n"
            f"‣ *Link* : [{escape_markdown(user.first_name, version=1)}](tg://user?id={user.id})\n"
            f"‣ *Poll ID* : {escape_markdown(str(poll_id), version=1)}\n"
            f"‣ *Message ID* : `{message_id}`\n"
            f"‣ *Note* : Only channel subscribers can vote.\n\n"
            f"×× Created by - [@uuuuyghbb](https://t.me/{escape_markdown(bot_username, version=1)})"
        )

# Send the photo or message
        if os.path.exists(img_path):
            sent_message = await context.bot.send_photo(
                chat_id=f"@{channel_username}",
                caption=response,
                photo=open(img_path, "rb"),
                reply_markup=button,
                parse_mode="Markdown",
            )

        else:
            sent_message = await context.bot.send_message(
                chat_id=f"@{channel_username}",
                text=response,
                reply_markup=button,
                parse_mode="Markdown",
            )

        if sent_message:
            message_channel_id = f"https://t.me/{channel_username}/{sent_message.message_id}"
            save_message_id_to_db(user.id, poll_id, sent_message.message_id, message_channel_id)

        mark_poll_created(user.id)
        await update.message.reply_text("✅ You have successfully participated in the voting!")

# Handle vote functionality and track user voting attemptsr 

async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    try:
        # Extract poll_id and message_id from the callback data
        poll_id, message_id = map(int, query.data.split(":")[1:])
    except ValueError:
        await query.answer("❌  Invalid data received.", show_alert=True)
        return
    # Fetch user data from the database
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT vote_count, ban_until, message_id FROM voters WHERE user_id = ?
    """, (user_id,))
    user_data = cursor.fetchone()    # Fetch the user data from the database
    if user_data:
        vote_count, ban_until, user_message_id = user_data
    else:
        vote_count, ban_until, user_message_id = 0, None, None
    conn.close()
    # Get the current time to check ban status
    current_time = datetime.now()
    # Check if the user is banned
    ban_until = get_user_ban_status(user_id)
    if ban_until and current_time < ban_until:
        await query.answer(f"⛔  You are banned from voting until {ban_until}.", show_alert=True)
        return

    # Check if the user has already voted for another message
    if user_message_id and user_message_id != message_id:
        await query.answer(f"Hey {user_name}, You already voted. You can't vote for others now.", show_alert=True)
        return
    # Check if the user has already voted for the current poll (message_id)
    if user_message_id == message_id:
        # User has already voted for the same message
        await query.answer(f"Hey {user_name}, You have already voted. You can't vote again.", show_alert=True)
        return
    try:
        chat_member = await context.bot.get_chat_member("@uuuuyghbb", user_id)
        if chat_member.status not in ["member", "administrator", "creator"]:
            raise BadRequest("❌  You must join @uuuuyghbb to vote.")
    except BadRequest as e:
        await query.answer(str(e), show_alert=True)
        return
    # Fetch poll info (not yet implemented, assuming function exists)
    poll_info = get_poll_by_id(poll_id)
    if not poll_info:
        await query.answer("❌  Poll not found.", show_alert=True)
        return
    # Increment the vote count for the poll
    increment_vote(poll_id)
    # Record the user's vote in the database
    record_vote(poll_id, user_id, message_id)
    # recording who voted whom
    list(poll_id, user_id, user_name, message_id)
    # Fetch updated vote count
    poll_info = get_poll_by_id(poll_id)
    new_votes = poll_info[1]
    # Fetch poll info
# message_channel_id

    # Update the inline button with the new vote count
    new_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"Vote ⚡  ({new_votes})", callback_data=f"vote:{poll_id}:{message_id}")]]
    )
    await query.message.edit_reply_markup(reply_markup=new_button)
    # Check if the user has exceeded the repeated click limit
    if vote_count >= 5:
    # Ban the user for 2 hours
        ban_until = current_time + timedelta(hours=2)
        set_user_ban(poll_id, user_id, ban_until)
        await query.answer(
            "❌  You have clicked too many times. You are now banned for 2 hours.",
            show_alert=True,
        )
        return

    # Increment the user's vote count
    increment_user_vote_count(poll_id, user_id)
    # Notify the user that the vote has been counted
    await query.answer("✅  Your vote has been counted!")
    # Notify the user about attempts left before ban (if needed)
    if vote_count + 1 < 5:
        await query.answer(
            f"❌  You have already clicked. Attempts left before ban: {5 - (vote_count + 1)}.",
            show_alert=True,
        )
# Handle when a user leaves the channel
# Command to stop and display top users
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != "ActiveForever":
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    # Default number of top users to display
    num_top_users = 3
    if context.args:
        try:
            num_top_users = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid argument. Please enter a valid number (e.g., /stop 2).")
            return

    # Fetch the top users based on highest votes
    top_users = get_top_users(num_top_users)

    # If no top users are found, notify the user
    if not top_users:
        await update.message.reply_text("❌ No users found who have participated in the poll.")
        return

    # Prepare the top users message
    top_message = ""
    for i, (user_id, username, votes, poll_id) in enumerate(top_users):
        # If no username is found, define a placeholder
        username = username if username else f"{user_id}"
        # Escape the username to avoid markdown parsing errors
        username = escape_markdown(username, version=1)
        # Add this user to the top list message
        top_message += f"🎖 *{i+1}. User:* @{username}, *Total Votes:* {votes}\n"

    # Send the top users message
    await update.message.reply_text(
        f"Top {len(top_users)} Participants by Total Votes:\n\n{top_message}", parse_mode="Markdown"
    )

    # Notify the user about the database deletion
    await update.message.reply_text("❌ The database has been deleted.")
    delete_db()


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_user_banned(update.effective_user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return

    num_top_users = 3
    if context.args:
        try:
            num_top_users = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid argument. Please enter a valid number (e.g., /top 2).")
            return

    # Fetch the top users based on highest votes
    top_users = get_top_users(num_top_users)

    # If no top users are found, notify the user
    if not top_users:
        await update.message.reply_text("❌ No users found who have participated in the poll.")
        return

    # Prepare the top users message
    top_message = ""
    for i, (user_id, username, votes, poll_id) in enumerate(top_users):
        # If no username is found, define a placeholder
        username = username if username else f"{user_id}"
        # Escape the username to avoid markdown parsing errors
        username = escape_markdown(username, version=1)
        # Add this user to the top list message
        top_message += f"🎖 *{i+1}. User:* @{username}, *Total Votes:* {votes}, *Poll ID:* {poll_id}\n"

    # Send the top users message
    await update.message.reply_text(f"Top {len(top_users)} Participants by Total Votes:\n\n{top_message}", parse_mode="Markdown")



async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_user_banned(update.effective_user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return
    commands = """
Available Commands:
/start - Start the bot
/help - Show this help message
/broadcast - Broadcast a message (Owner only)
/current - Get your Voting information
/top - Get top users (use /top or /top 2..100)

Owners Only:
/list - Get all voters of a poll
/delete_poll - For deleting poll if player break rules
/vote - Start Voting (Owner Only)
/stats - Get bot statistics
/stop - For stop Voting 
/addsudo - To addsudo
/delsudo - To delete sudo
/listsudo - List all sudo Users
/ban - To ban Users
/unban - To Unban Users
/listsudo - List all ban Users
"""
    await update.message.reply_text(commands)
from telegram.helpers import escape_markdown

async def current_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_user_banned(update.effective_user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return

    user = update.effective_user

    try:
        with sqlite3.connect("vote_bot.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT polls.channel_username, polls.message_id, SUM(voters.vote_count) as user_votes
                FROM polls
                JOIN voters ON polls.poll_id = voters.poll_id
                WHERE voters.user_id = ?
                GROUP BY polls.channel_username, polls.message_id
            """, (user.id,))
            user_data = cursor.fetchone()

    except sqlite3.Error as e:
        await update.message.reply_text("❌ An error occurred while accessing the database.")
        print(f"Database error: {e}")
        return

    if not user_data:
        await update.message.reply_text("❌ You have not participated in any active voting session.")
        return

    if user_data:
        channel_username, message_id, user_votes = user_data
        channel_username = escape_markdown(channel_username or "Unknown", version=1)
        user_votes = user_votes or 0

        user_message = (
            f"⭐ *Your Participation Details:*\n"
            f"⭐ *Channel:* @{channel_username}\n"
            f"⭐ *Your Votes:* {user_votes}\n"
       )
        await update.message.reply_text(user_message, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ You have not participated in any active voting session.")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


# Function to add a user to the database
# Info command to retrieve user info from the database
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_user_banned(update.effective_user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return
    user = None
    # Check if the command is a reply to a message
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    elif context.args:
        identifier = context.args[0]
        # Try fetching the user by ID or username
        if identifier.isdigit():
            user_id = int(identifier)
            conn = sqlite3.connect("bot_main.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user_data = cursor.fetchone()
            conn.close()

            if user_data:
                user = {
                    'user_id': user_data[0],
                    'first_name': user_data[1],
                    'last_name': user_data[2],
                    'username': user_data[3]
                }
        else:
            username = identifier.lstrip("@")
            conn = sqlite3.connect("bot_main.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user_data = cursor.fetchone()
            conn.close()

            if user_data:
                user = {
                    'user_id': user_data[0],
                    'first_name': user_data[1],
                    'last_name': user_data[2],
                    'username': user_data[3]
                }

    # If user information is still not available
    if not user:
        await update.message.reply_text("❌ Could not retrieve user information. Make sure the user ID or username is correct.")
        return

    # Prepare the user information
    user_info = (
        f" *User Information:*\n"
        f" *First Name:* {user['first_name']}\n"
        f" *User ID:* `{user['user_id']}`\n"
        f" *Username:* @{user['username'] if user['username'] else 'N/A'}\n"
        f" *Inline Mention:* [{user['first_name']}](tg://user?id={user['user_id']})"
    )

    # Send the information
    await update.message.reply_text(user_info, parse_mode="Markdown")

import re

def clean_name(text: str) -> str:
    """Remove all types of brackets from the text."""
    import re

    # Regex pattern to match all types of brackets
    bracket_pattern = re.compile(r'[\[\]\(\)\{\}\<\>]')
    
    # Remove brackets
    return bracket_pattern.sub('', text)


def escape_url(user_id: int) -> str:
    """Generate a user ID URL for Telegram."""
    return f"{user_id}"

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    if is_user_banned(update.effective_user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return
    # Check if poll_id is provided as an argument
    if not context.args:
        await update.message.reply_text("❌ Please provide a poll_id.")
        return
    
    try:
        poll_id = int(context.args[0])  # Expecting poll_id as the first argument
    except ValueError:
        await update.message.reply_text("❌ Invalid poll_id. Please provide a valid poll_id.")
        return

    # Connect to the database and fetch voters for the poll
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, user_name, message_id FROM poll_votes WHERE poll_id = ?
    """, (poll_id,))
    voters = cursor.fetchall()
    conn.close()

    if not voters:
        await update.message.reply_text(f"❌ No voters found for poll {poll_id}.")
        return

    # Prepare the list of users with inline mentions
    user_mentions = []
    for idx, (user_id, user_name, _) in enumerate(voters):
        # Clean the user_name to remove brackets, emojis, and symbols
        cleaned_name = clean_name(user_name)
        mention = f"[{cleaned_name}](tg://user?id={escape_url(user_id)})"
        user_mentions.append(f"{idx + 1}. {mention}")
    
    # Split the list into chunks of 20 mentions per message
    chunk_size = 30
    chunks = [
        user_mentions[i:i + chunk_size]
        for i in range(0, len(user_mentions), chunk_size)
    ]

    # Send each chunk as a separate message
    for idx, chunk in enumerate(chunks):
        voters_list = "\n".join(chunk)
        try:
            # Prepare the message and send it
            message = f"Users who voted for poll id {poll_id} (Part {idx + 1}):\n\n{voters_list}"
            await update.message.reply_text(
                message,
                parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"Error sending message: {e}")
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext

# Function to connect to the database and retrieve channel_username for a given poll_id
def get_message_id_by_poll_id(poll_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT message_id FROM polls WHERE poll_id = ?", (poll_id,))
    result = cursor.fetchone()
    conn.close
def get_channel_by_poll_id(poll_id):
    # Open the SQLite database
    conn = sqlite3.connect('vote_bot.db')
    cursor = conn.cursor()

    # Query to get the channel_username for the given poll_id
    cursor.execute("SELECT channel_username FROM polls WHERE poll_id = ?", (poll_id,))
    result = cursor.fetchone()

    # Close the database connection
    conn.close()

    if result:
        return result[0]  # Return the channel username
    else:
        return None  # Return None if no result found

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

async def delete_poll(update: Update, context: CallbackContext):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    # Extract poll_id from command arguments
    try:
        poll_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text('Usage: /delete_poll <poll_id>')
        return

    # Retrieve poll details (message_channel_id is the actual message ID)
    poll_info = get_poll_info(poll_id)  # (channel_username, message_id, message_channel_id)
    if not poll_info:
        await update.message.reply_text(f"No poll found with ID {poll_id}.")
        return
    
    channel_username, message_id, message_channel_id = poll_info  # Unpack the tuple

    # Ask for confirmation
    confirm_message = (
        f"Are you sure you want to disqualify Poll {poll_id} from @{channel_username}?"
    )
    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data=f"delete_{poll_id}_yes"),
            InlineKeyboardButton("No", callback_data=f"delete_{poll_id}_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(confirm_message, reply_markup=reply_markup)

import re

# Function to extract message ID from URL
def extract_message_id_from_url(url: str) -> int:
    match = re.search(r'/(\d+)$', url)
    if match:
        return int(match.group(1))  # Return the message ID as an integer
    return None  # Return None if the URL is not in the correct format

async def confirm_delete_poll(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Extract poll ID from callback data
    data = query.data
    parts = data.split('_')
    poll_id = int(parts[1])

    if "yes" in data:
        # Retrieve poll details
        poll_info = get_poll_info(poll_id)  # (channel_username, message_id, message_channel_id)
        if not poll_info:
            await query.edit_message_text(text=f"Error: Poll {poll_id} not found.")
            return
        
        channel_username, message_id, message_channel_id = poll_info  # Unpack the tuple

        # Check if message_channel_id is a URL, if so, extract the message ID
        if isinstance(message_channel_id, str) and message_channel_id.startswith('https://t.me/'):
            message_channel_id = extract_message_id_from_url(message_channel_id)

        # If the message_id could not be extracted, inform the user
        if not message_channel_id:
            await query.edit_message_text(text="❌ Invalid message ID.")
            return

        chat_id = f"@{channel_username}"

        update_status = []

        try:
            # Forward the poll message to the user who called the command
            message = await context.bot.forward_message(
                chat_id=update.effective_chat.id, from_chat_id=chat_id, message_id=message_channel_id
            )

            if not message:
                await query.edit_message_text(text="Error: Could not retrieve poll message.")
                return

            # Check if the message is a photo or text
            if message.caption:
                # If the message has a caption (photo message), update the caption
                updated_caption = message.caption + "\n\n**THIS POLL HAS BEEN DISQUALIFIED FROM THE GIVEAWAY**"
                await context.bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_channel_id,
                    caption=updated_caption,
                    parse_mode="Markdown",
                    reply_markup=None  # Remove inline buttons
                )
            else:
                # If it's a text message, update the text
                updated_text = message.text + "\n\n**THIS POLL HAS BEEN DISQUALIFIED FROM THE GIVEAWAY**"
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_channel_id,
                    text=updated_text,
                    parse_mode="Markdown",
                    reply_markup=None  # Remove inline buttons
                )

            update_status.append(f"✅ Poll message updated in @{channel_username}.")
        
        except Exception as e:
            update_status.append(f"❌ Failed to update poll message. Error: {str(e)}")

        # Delete poll info from the database after processing
        delete_poll_info(poll_id)

        # Provide final status to the user
        await query.edit_message_text(text="\n".join(update_status))

    else:
        await query.edit_message_text(text="Poll disqualification canceled.")

def get_poll_info(poll_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT channel_username, message_id, message_channel_id FROM polls WHERE poll_id = ?", (poll_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    return result if result else None  # Returns (channel_username, message_id, message_channel_id) or None if not found

import sqlite3
from telegram.ext import Application, CommandHandler

def create_db():
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        is_banned INTEGER DEFAULT 0
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sudo_users (
        user_id INTEGER PRIMARY KEY,
        username TEXT
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS polls(
        poll_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        channel_username TEXT,
        message_id INTEGER,
        votes INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )""")

    conn.commit()
    conn.close()

# Add User Function
def add_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
                   (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()
def add_user_to_db(user_id, first_name, last_name, username):
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, first_name, last_name, username) VALUES (?, ?, ?, ?)",
                   (user_id, first_name, last_name, username))
    conn.commit()
    conn.close()


# Function to check if user exists in the database
def is_user_registered(user_id):
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None
    
# Add Sudo Function
def add_sudo(user_id, username):
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO sudo_users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

# Remove Sudo Function
def remove_sudo(user_id):
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sudo_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Ban User Function
def ban_user(user_id):
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Unban User Function
def unban_user(user_id):
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Get Sudo Users Function
def get_bot_main_db():
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username FROM sudo_users")
    result = cursor.fetchall()
    conn.close()
    return result

# Get Banned Users Function
def get_banned_users():
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username FROM users WHERE is_banned = 1")
    result = cursor.fetchall()
    conn.close()
    return result

def is_user_banned(user_id):
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

from telegram import Update
from telegram.ext import ContextTypes
import sqlite3

import sqlite3
from telegram import Update
from telegram.ext import ContextTypes

async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if the command was invoked with a reply
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    else:
        # Check if the command was invoked with a username or user ID
        if context.args:
            arg = context.args[0]

            # Check if the argument is a valid user ID (digit only)
            if arg.isdigit():
                user_id = int(arg)
                conn = sqlite3.connect("bot_main.db")
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                user_data = cursor.fetchone()
                conn.close()

                if user_data:
                    target_user = {
                        'user_id': user_data[0],
                        'first_name': user_data[1],
                        'last_name': user_data[2],
                        'username': user_data[3]
                    }
                else:
                    target_user = None
            else:
                # Otherwise, assume it's a username
                username = arg.lstrip('@')
                conn = sqlite3.connect("bot_main.db")
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                user_data = cursor.fetchone()
                conn.close()

                if user_data:
                    target_user = {
                        'user_id': user_data[0],
                        'first_name': user_data[1],
                        'last_name': user_data[2],
                        'username': user_data[3]
                    }
                else:
                    target_user = None
        else:
            target_user = None
    
    # If no user was found, notify the command initiator
    if target_user is None:
        await update.message.reply_text("❌ Target user not found. Please reply to a user, or provide a valid username or user ID.")
        return None
    else:
        # Return the user data from the database
        return target_user


def is_authorized(update: Update) -> bool:
    user = update.effective_user
    if user.id == 5873900195:  # Replace with your bot's owner's user ID
        return True

    # Check if the user is in the sudo users list
    return is_sudo_user(user.id)
import sqlite3
from telegram import Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Function to check if the user is authorized (in sudo or admin)
# Function to check if the user is in the sudo list
def is_sudo_user(user_id):
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sudo_users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None
    
import sqlite3
from telegram import Update
from telegram.ext import ContextTypes

# Command: Add Sudo
async def addsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    target_user = await get_target_user(update, context)
    if target_user:
        add_sudo(target_user['user_id'], target_user['username'])
        await update.message.reply_text(f"✅ @{target_user['username']} added to sudo list.")

# Command: Remove Sudo
async def delsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    target_user = await get_target_user(update, context)
    if target_user:
        remove_sudo(target_user['user_id'])
        await update.message.reply_text(f"✅ @{target_user['username']} removed from sudo list.")

# Command: Ban User
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    target_user = await get_target_user(update, context)
    if target_user:
        ban_user(target_user['user_id'])
        await update.message.reply_text(f"✅ @{target_user['username']} has been banned.")

# Command: Unban User
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    target_user = await get_target_user(update, context)
    if target_user:
        unban_user(target_user['user_id'])
        await update.message.reply_text(f"✅ @{target_user['username']} has been unbanned.")

# Command: List All Sudo Users
async def listsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    sudo_users = get_sudo_users()
    if sudo_users:
        sudo_list = "\n".join([f"@{user[1]}" for user in sudo_users])
        await update.message.reply_text(f"📜 Sudo Users:\n{sudo_list}")
    else:
        await update.message.reply_text("❌ No sudo users found.")

# Command: List All Banned Users
async def listban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    banned_users = get_banned_users()
    if banned_users:
        banned_list = "\n".join([f"@{user[1]}" for user in banned_users])
        await update.message.reply_text(f"📜 Banned Users:\n{banned_list}")
    else:
        await update.message.reply_text("❌ No banned users found.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    # Query the database for the total number of users
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    conn.close()

    # Send the total user count
    await update.message.reply_text(f"📊 Total registered users: {total_users}")
async def broadcast_message(context: ContextTypes.DEFAULT_TYPE, message_text: str):
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()

    # Fetch all user IDs from the database
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    total_users = len(users)
    success_count = 0
    fail_count = 0

    # Iterate through all users and send the message
    for user in users:
        user_id = user[0]
        try:
            await context.bot.send_message(chat_id=user_id, text=message_text)
            success_count += 1
        except Exception as e:
            # Handle errors (e.g., user blocked the bot or deleted their account)
            fail_count += 1
            print(f"Failed to send message to {user_id}: {e}")

    # Return the results
    return total_users, success_count, fail_count

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    # Check if a message was provided
    if not context.args:
        await update.message.reply_text("❌ Please provide a message to broadcast. Usage: /broadcast Your message here")
        return

    # Combine arguments to form the broadcast message
    message_text = " ".join(context.args)

    # Notify the admin about the start of the broadcast
    await update.message.reply_text("✅ Starting the broadcast...")

    # Perform the broadcast
    total_users, success_count, fail_count = await broadcast_message(context, message_text)

    # Send a summary of the results
    await update.message.reply_text(
        f"✅ Broadcast completed!\n\n"
        f"📊 Total Users: {total_users}\n"
        f"✅ Successful: {success_count}\n"
        f"❌ Failed: {fail_count}"
    )

def vote_poll(poll_id: int, user_id: int, votes: int, user_name: str, message_id: int):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    try:
        # Check if the poll exists
        cursor.execute("SELECT votes FROM polls WHERE poll_id = ?", (poll_id,))
        poll = cursor.fetchone()
        if not poll:
            raise ValueError("Poll not found.")

        # Update the votes in the poll
        cursor.execute("UPDATE polls SET votes = votes + ? WHERE poll_id = ?", (votes, poll_id))

        # Log or update the voter's information
        cursor.execute("""
            INSERT INTO voters (poll_id, user_id, vote_count, message_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(poll_id, user_id) DO UPDATE SET
                vote_count = vote_count + excluded.vote_count
        """, (poll_id, user_id, votes, message_id))

        # Add the user to poll_votes table
        cursor.execute("""
            INSERT OR IGNORE INTO poll_votes (poll_id, user_id, user_name, message_id)
            VALUES (?, ?, ?, ?)
        """, (poll_id, user_id, user_name, message_id))

        conn.commit()
        return f"Successfully added {votes} votes to poll {poll_id}."

    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
    finally:
        conn.close()


# Command handler for /addvote
from telegram import Update
from telegram.ext import CallbackContext

# Command handler for /addvote
async def addvote(update: Update, context: CallbackContext):
    try:
        # Check if user is authorized
        if not is_authorized(update):
            return

        # Parse arguments
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("Usage: /addvote <poll_id> <no_of_votes>")
            return

        # Extract poll_id and votes
        poll_id = int(args[0])
        votes = int(args[1])

        # Ensure votes are valid
        if votes <= 0:
            await update.message.reply_text("The number of votes must be greater than 0.")
            return

        # Get user details
        user_id = update.effective_user.id
        user_name = update.effective_user.full_name
        message_id = update.message.message_id

        # Call vote_poll function
        result = vote_poll(poll_id=poll_id, user_id=user_id, votes=votes, user_name=user_name, message_id=message_id)
        await update.message.reply_text(result)

    except ValueError:
        await update.message.reply_text("Invalid input. Please use the correct format: /addvote <poll_id> <no_of_votes>.")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import sqlite3
import re

async def update_inline_button_periodically(context):

    """ Periodically checks membership, updates vote counts and inline buttons every 1 minute """
    while True:
        await asyncio.sleep(60)  # Wait for 1 minute before checking again

        # Fetch all pollsfrom the database
        conn = sqlite3.connect("vote_bot.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT poll_id, channel_username, message_channel_id, votes, message_id FROM polls
        """)
        polls = cursor.fetchall()

        if not polls:
            print("No polls found to refresh.")
            continue  # No pollsto refresh, continue checking in the next cycle

        # Loop through all pollsand update the inline buttons for each message
        for poll in polls:
            poll_id, channel_username, message_channel_id, votes, message_id = poll

            # Extract the message ID from the URL (if it's a URL)
            match = re.search(r'(\d+)$', message_channel_id)  # Match the last part of the URL
            if match:
                message_channel_id = match.group(1)  # This gives the numeric message ID

            print(f"Checking membership and updating poll {poll_id} in channel {channel_username} with message_channel_id {message_channel_id} and votes {votes}")

            # Check membership of users who voted in this poll
            cursor.execute("""
                SELECT user_id FROM poll_votes WHERE poll_id = ?
            """, (poll_id,))
            users = cursor.fetchall()

            for user in users:
                user_id = user[0]
                try:
                    # Check if the user is still a member of the channel
                    chat_member = await context.bot.get_chat_member(f"@{channel_username}", user_id)
                    if chat_member.status not in ["member", "administrator", "creator"]:
                        # If user left the channel, decrease their vote count
                        print(f"User {user_id} has left the channel. Decreasing their vote.")
                        decrease_vote_count(poll_id, user_id)
                except Exception as e:
                    print(f"Error checking membership for user {user_id}: {e}")

            # After checking membership, update the vote count and the inline button
            await update_vote_count_and_inline_button(poll_id, message_id, context)

        conn.close()

def decrease_vote_count(poll_id, user_id):
    """ Remove only one vote from the poll for the specific user when they leave the channel. """
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()

    # Check if the user has a vote recorded
    cursor.execute("""
        SELECT COUNT(*) FROM poll_votes WHERE poll_id = ? AND user_id = ?
    """, (poll_id, user_id))
    vote_exists = cursor.fetchone()[0]  # Returns 1 if vote exists, 0 if not

    if vote_exists:
        # Remove the user's vote from poll_votes
        cursor.execute("""
            DELETE FROM poll_votes WHERE poll_id = ? AND user_id = ?
        """, (poll_id, user_id))

        # Decrease the total vote count for the poll **by 1**
        cursor.execute("""
            UPDATE polls SET votes = votes - 1 WHERE poll_id = ? AND votes > 0
        """, (poll_id,))

        # Remove the user from the voters table (so they can vote again later)
        cursor.execute("""
            DELETE FROM voters WHERE poll_id = ? AND user_id = ?
        """, (poll_id, user_id))

        conn.commit()

    conn.close()


channel_username = "uuuuyghbb"
async def update_vote_count_and_inline_button(poll_id, message_id, context):
    """ Updates the vote count and inline button after checking membership """
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT poll_id, channel_username, message_channel_id, votes, message_id FROM polls
    """)
    polls = cursor.fetchall()

    if not polls:
        await update.message.reply_text("❌ No polls found to refresh.")
        return

    # Loop through all pollsand update the inline buttons for each message
    for poll in polls:
        poll_id, channel_username, message_channel_id, votes, message_id = poll
        
        # Extract the message ID from the URL (if it's a URL)
        match = re.search(r'(\d+)$', message_channel_id)  # Match the last part of the URL
        if match:
            message_channel_id = match.group(1)  # This gives the numeric message ID
        
        print(f"Updating poll {poll_id} in channel {channel_username} with message_channel_id {message_channel_id} and votes {votes}")

        # Create the new inline button with updated vote count
        new_button = InlineKeyboardMarkup(
            [[InlineKeyboardButton(f"Vote ⚡  ({votes})", callback_data=f"vote:{poll_id}:{message_id}")]]
        )

        try:
            # Try to update the message in the channel with the new inline button
            await context.bot.edit_message_reply_markup(
                chat_id=f"@{channel_username}",  # Correct channel username
                message_id=int(message_channel_id),  # Convert message_channel_id to integer
                reply_markup=new_button
            )
        except TelegramError as e:
            # If the message is not found or any other Telegram-related issue, log and inform the user
            if "Message to edit not found" in str(e):
                print(f"Message with ID {message_channel_id} not found.")
                print(f"❌ Failed to update poll {poll_id}: Message not found.")
                
                # Optionally re-send the poll
                await resend_poll(context, poll_id, channel_username, votes)  # Implement resend_poll to re-send the poll message
            else:
                print(f"Error updating poll {poll_id}: {e}")
                print(f"❌ Failed to update poll {poll_id}: {e}")
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext


async def bash_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("Usage: /bash <command>")
        return
    
    command = " ".join(context.args)  # Join arguments into a single command
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        output = result.stdout if result.stdout else result.stderr
    except Exception as e:
        output = str(e)
    
    # Ensure output is within Telegram's message limit
    if len(output) > 4000:
        output = output[:4000] + "\n\n[Output Truncated]"
    
    await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")
import os
import glob
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

async def upload_files(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("Usage: /ul <filename_pattern>\nExample: /ul vote_bot*")
        return
    
    pattern = " ".join(context.args)  # Get the pattern from user input
    files = glob.glob(pattern)  # Find matching files
    
    if not files:
        await update.message.reply_text("No matching files found.")
        return

    for file_path in files:
        if os.path.isfile(file_path):
            try:
                await update.message.reply_document(document=open(file_path, "rb"))
            except Exception as e:
                await update.message.reply_text(f"Error uploading {file_path}: {str(e)}")



import os
import base64
import requests
import time
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import threading

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = "7469236370:AAH0_dD-7ZjdbepID5z2YhKjY_FpSX6K6Qg"

# GitHub Credentials
GIT_TOKEN = os.getenv("GH_TOKEN")  # GitHub token stored in Heroku environment
GIT_USERNAME = "Votingbotm"
GIT_REPO = "Vote"
GIT_API_URL = "https://api.github.com"
GIT_BRANCH = "main"

if not GIT_TOKEN:
    raise ValueError("❌ GitHub token is missing in environment variables!")

# Function to upload a file to GitHub
def upload_to_github(file_path, github_path):
    """Uploads a file (SQLite DB) to GitHub using the API."""
    
    url = f"{GIT_API_URL}/repos/{GIT_USERNAME}/{GIT_REPO}/contents/{github_path}"
    headers = {"Authorization": f"token {GIT_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    # Read the file and encode it as Base64
    try:
        with open(file_path, "rb") as file:
            content = base64.b64encode(file.read()).decode("utf-8")
    except FileNotFoundError:
        print(f"⚠ File not found: {file_path}")
        return None

    # Get the latest SHA of the file (required for updating an existing file)
    response = requests.get(url, headers=headers)
    sha = None
    if response.status_code == 200:  # File exists, get SHA
        sha = response.json().get("sha")

    # Prepare commit data
    commit_message = f"📦 Auto Backup: {os.path.basename(file_path)} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    data = {
        "message": commit_message,
        "content": content,
        "branch": GIT_BRANCH
    }
    if sha:
        data["sha"] = sha  # Required for updating an existing file

    # Upload file to GitHub
    upload_response = requests.put(url, json=data, headers=headers)
    
    if upload_response.status_code in [200, 201]:
        print(f"✅ Successfully uploaded {file_path} to GitHub.")
        return upload_response.json()
    else:
        print(f"❌ Upload failed for {file_path}: {upload_response.json()}")
        return None

# Function to backup database files
def backup_databases():
    """Backs up both SQLite database files to GitHub."""
    files_to_backup = {
        "vote_bot.db": "vote_bot.db",
        "bot_main.db": "bot_main.db"
    }
    
    for local_path, github_path in files_to_backup.items():
        upload_to_github(local_path, github_path)

# Auto backup function with initial 1-hour delay
def auto_backup():
    """Waits for 1 hour before starting, then backs up every 1 hour."""
    print("🕒 Waiting 1 hour before first commit...")
    time.sleep(3600)  # Wait for 1 hour

    while True:
        print("🔄 Running backup...")
        backup_databases()
        time.sleep(3600)  # Wait for 1 hour before the next commit

# Telegram command to manually trigger backup
async def backup_command(update: Update, context: CallbackContext):
    """Telegram command to manually trigger backup."""
    await update.message.reply_text("⏳ Backing up database files...")

    backup_databases()
    await update.message.reply_text("✅ Database backup completed!")

# Setup Telegram bot
async def bash_comman(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("Usage: /bash <command>")
        return
    
    command = " ".join(context.args)  # Join arguments into a single command
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        output = result.stdout if result.stdout else result.stderr
    except Exception as e:
        output = str(e)
    
    # Ensure output is within Telegram's message limit
    if len(output) > 4000:
        output = output[:4000] + "\n\n[Output Truncated]"
    
    await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")
import os
import glob
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

async def upload_file(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("Usage: /ul <filename_pattern>\nExample: /ul vote_bot*")
        return
    
    pattern = " ".join(context.args)  # Get the pattern from user input
    files = glob.glob(pattern)  # Find matching files
    
    if not files:
        await update.message.reply_text("No matching files found.")
        return

    for file_path in files:
        if os.path.isfile(file_path):
            try:
                await update.message.reply_document(document=open(file_path, "rb"))
            except Exception as e:
                await update.message.reply_text(f"Error uploading {file_path}: {str(e)}")

# Run t

# Your main function to start the bot
def bot1():
    # Create the application with the provided BOT_TOKEN
    application = Application.builder().token(BOT_TOKEN).build()

    # Start the periodic task of updating inline buttons every minute within the event loop
    application.job_queue.run_repeating(update_inline_button_periodically, interval=60, first=0)

    # Add all your command handlers
    application.add_handler(CommandHandler("vote", vote_command))
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_username))
    application.add_handler(CallbackQueryHandler(handle_vote, pattern=r"^vote:"))
    application.add_handler(CommandHandler("top", top))
    application.add_handler(CommandHandler("bash", bash_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("current", current_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("delete_poll", delete_poll))
    application.add_handler(CallbackQueryHandler(confirm_delete_poll, pattern=r"^delete_"))
    application.add_handler(CommandHandler("addsudo", addsudo))
    application.add_handler(CommandHandler("delsudo", delsudo))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("listsudo", listsudo))
    application.add_handler(CommandHandler("listban", listban))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("refresh", refresh))
    application.add_handler(CommandHandler("addvotes", addvote))
    application.add_handler(CommandHandler("ul", upload_files))
    # Add callback handler for inline button presses
    application.add_handler(CallbackQueryHandler(handle_join_button, pattern="^joined_"))
    application.run_polling()
def bot2():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("backup", backup_command)) 
    app.add_handler(CommandHandler("bash", bash_comman))
    app.add_handler(CommandHandler("ul", upload_file))# Telegram command: /backup

# Start auto backup in a separate thread
    threading.Thread(target=auto_backup, daemon=True).start()



    # Start polling to handle updates
    app.run_polling()


if __name__ == "__main__":
    try:
        # Initialize databases
        init_db()
        create_db()
        create_users_table()

        # Run both bots concurrently
        from threading import Thread
        
        # Create threads for both bots
        thread1 = Thread(target=bot1)
        thread2 = Thread(target=bot2)

        # Start the threads
        thread1.start()
        thread2.start()

        # Wait for both threads to finish
        thread1.join()
        thread2.join()

    except Exception as e:
        print(f"Error occurred: {e}")
