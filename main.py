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
from telegram.helpers import escape_html

from telegram.error import BadRequest
import time
from datetime import *
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CallbackQueryHandler, ChatMemberHandler, ContextTypes
import sqlite3
from datetime import datetime
import logging
import urllib.parse
import re
import telegram

img_path = "img/img.png"
BOT_TOKEN = "7593876189:AAExsIGMoAs8eokv45xQA3h5IyW2-ZHg2KA"
owners = [5873900195]  # ActiveForever
special_users = [5873900195, 6574063018]  # ActiveForever and TeamKanha (replace with actual ID)
bot_username = "ActiveForever_Votingbot"

def init_db():
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    
    # Channel-specific polls table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_polls(
            channel_username TEXT PRIMARY KEY,
            creator_id INTEGER NOT NULL,
            current_poll_id INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 0,
            message_id INTEGER,
            message_channel_id TEXT
        )
    """)

    # Channel-specific poll participants
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS poll_participants(
            channel_username TEXT,
            poll_id INTEGER,
            user_id INTEGER,
            user_name TEXT,
            join_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (channel_username, poll_id, user_id)
        )
    """)

    # Channel votes (one vote per user per channel)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_votes (
            channel_username TEXT,
            user_id INTEGER,
            user_name TEXT,
            vote_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (channel_username, user_id)
        )
    """)

    # Updated user sessions (allows multiple channel participation)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions(
            user_id INTEGER,
            channel_username TEXT,
            session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, channel_username)
        )
    """)

    conn.commit()
    conn.close()

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

    conn.commit()
    conn.close()

def create_users_table():
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_banned INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# Channel poll management functions
def create_channel_poll(channel_username, creator_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    
    # Check if channel already has an active poll
    cursor.execute("SELECT is_active FROM channel_polls WHERE channel_username = ?", (channel_username,))
    result = cursor.fetchone()
    
    if result and result[0]:
        conn.close()
        return False, "Channel already has an active poll"
    
    # Create or update channel poll
    cursor.execute("""
        INSERT OR REPLACE INTO channel_polls 
        (channel_username, creator_id, current_poll_id, is_active)
        VALUES (?, ?, 0, 1)
    """, (channel_username, creator_id))
    
    conn.commit()
    conn.close()
    return True, "Poll created successfully"

def stop_channel_poll(channel_username, user_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    
    # Check if user is the creator
    cursor.execute("SELECT creator_id FROM channel_polls WHERE channel_username = ?", (channel_username,))
    result = cursor.fetchone()
    
    if not result or result[0] != user_id:
        conn.close()
        return False, "You are not the creator of this poll"
    
    # Stop the poll
    cursor.execute("""
        UPDATE channel_polls SET is_active = 0 
        WHERE channel_username = ?
    """, (channel_username,))
    
    conn.commit()
    conn.close()
    return True, "Poll stopped successfully"

def get_user_active_channels(user_id):
    """Get all channels where user is currently participating"""
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT us.channel_username 
        FROM user_sessions us
        JOIN channel_polls cp ON us.channel_username = cp.channel_username
        WHERE us.user_id = ? AND cp.is_active = 1
    """, (user_id,))
    channels = [row[0] for row in cursor.fetchall()]
    conn.close()
    return channels

def get_user_created_channels(user_id):
    """Get all channels where user is the creator"""
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT channel_username 
        FROM channel_polls 
        WHERE creator_id = ? AND is_active = 1
    """, (user_id,))
    channels = [row[0] for row in cursor.fetchall()]
    conn.close()
    return channels

def can_join_poll(user_id, channel_username):
    """Check if user can join a poll"""
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    
    # Check if user is creator of this channel
    cursor.execute("SELECT creator_id FROM channel_polls WHERE channel_username = ?", (channel_username,))
    result = cursor.fetchone()
    if result and result[0] == user_id:
        conn.close()
        return False, "You cannot join your own voting session"
    
    # Check if user already joined this channel
    cursor.execute("SELECT 1 FROM user_sessions WHERE user_id = ? AND channel_username = ?", 
                  (user_id, channel_username))
    if cursor.fetchone():
        conn.close()
        return False, "You have already joined this channel's poll"
    
    # Check if user has reached max limit (5 channels)
    cursor.execute("""
        SELECT COUNT(*) FROM user_sessions us
        JOIN channel_polls cp ON us.channel_username = cp.channel_username
        WHERE us.user_id = ? AND cp.is_active = 1
    """, (user_id,))
    active_sessions = cursor.fetchone()[0]
    
    if active_sessions >= 5:
        conn.close()
        return False, "You have reached the maximum limit of 5 active polls"
    
    conn.close()
    return True, "Can join"

def add_user_channel_session(user_id, channel_username):
    """Add user to a channel session"""
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO user_sessions (user_id, channel_username)
        VALUES (?, ?)
    """, (user_id, channel_username))
    conn.commit()
    conn.close()

def remove_user_channel_session(user_id, channel_username):
    """Remove user from a specific channel session"""
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM user_sessions 
        WHERE user_id = ? AND channel_username = ?
    """, (user_id, channel_username))
    conn.commit()
    conn.close()

def remove_all_user_sessions(user_id):
    """Remove user from all channel sessions"""
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_poll_participant(channel_username, user_id, user_name):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    
    # Get current poll_id and increment
    cursor.execute("SELECT current_poll_id FROM channel_polls WHERE channel_username = ?", (channel_username,))
    result = cursor.fetchone()
    current_poll_id = result[0] if result else 0
    new_poll_id = current_poll_id + 1
    
    # Update poll_id
    cursor.execute("""
        UPDATE channel_polls SET current_poll_id = ? 
        WHERE channel_username = ?
    """, (new_poll_id, channel_username))
    
    # Add participant
    cursor.execute("""
        INSERT OR IGNORE INTO poll_participants 
        (channel_username, poll_id, user_id, user_name)
        VALUES (?, ?, ?, ?)
    """, (channel_username, new_poll_id, user_id, user_name))
    
    conn.commit()
    conn.close()
    return new_poll_id

def get_channel_participants(channel_username, creator_id):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    
    # Check if user is the creator
    cursor.execute("SELECT creator_id FROM channel_polls WHERE channel_username = ?", (channel_username,))
    result = cursor.fetchone()
    
    if not result or result[0] != creator_id:
        conn.close()
        return None, "You are not the creator of this poll"
    
    cursor.execute("""
        SELECT poll_id, user_id, user_name FROM poll_participants 
        WHERE channel_username = ? ORDER BY poll_id
    """, (channel_username,))
    
    participants = cursor.fetchall()
    conn.close()
    return participants, None

def vote_in_channel(channel_username, user_id, user_name):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    
    # Check if channel has active poll
    cursor.execute("SELECT is_active FROM channel_polls WHERE channel_username = ?", (channel_username,))
    result = cursor.fetchone()
    
    if not result or not result[0]:
        conn.close()
        return False, "No active poll in this channel"
    
    # Check if user already voted
    cursor.execute("SELECT 1 FROM channel_votes WHERE channel_username = ? AND user_id = ?", 
                  (channel_username, user_id))
    if cursor.fetchone():
        conn.close()
        return False, "You have already voted in this channel"
    
    # Add vote
    cursor.execute("""
        INSERT INTO channel_votes (channel_username, user_id, user_name)
        VALUES (?, ?, ?)
    """, (channel_username, user_id, user_name))
    
    conn.commit()
    conn.close()
    return True, "Vote recorded successfully"

def get_channel_vote_count(channel_username):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM channel_votes WHERE channel_username = ?", (channel_username,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_channel_top_voters(channel_username):
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pp.poll_id, pp.user_name, pp.user_id, pp.join_time
        FROM poll_participants pp
        WHERE pp.channel_username = ?
        ORDER BY pp.poll_id
        LIMIT 10
    """, (channel_username,))
    
    top_users = cursor.fetchall()
    conn.close()
    return top_users

# Poll info functions for delete_poll functionality
def get_poll_info(poll_id):
    """Get poll information by poll_id"""
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT channel_username, message_id, message_channel_id 
        FROM channel_polls 
        WHERE current_poll_id = ? AND is_active = 1
    """, (poll_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def delete_poll_info(poll_id):
    """Delete poll info from database"""
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM channel_polls 
        WHERE current_poll_id = ?
    """, (poll_id,))
    conn.commit()
    conn.close()

def extract_message_id_from_url(url):
    """Extract message ID from Telegram URL"""
    try:
        # Extract message ID from URL like https://t.me/channel/123
        parts = url.split('/')
        if len(parts) > 0:
            return int(parts[-1])
    except (ValueError, IndexError):
        pass
    return None

def is_authorized(update):
    """Check if user is authorized (owner)"""
    return update.effective_user.id in owners

def is_allowed(update):
    """Check if user is allowed (special user)"""
    return update.effective_user.id in special_users

# User management functions
def add_user_to_db(user_id, first_name, last_name, username):
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, first_name, last_name, username) VALUES (?, ?, ?, ?)",
                   (user_id, first_name, last_name, username))
    conn.commit()
    conn.close()

def is_user_registered(user_id):
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def ban_user(user_id):
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_banned_users():
    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, first_name FROM users WHERE is_banned = 1")
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

def is_special_user(user_id):
    return user_id in special_users

CHANNEL_USERNAME = "@Trusted_Sellers_of_Pd"

async def check_user_membership(user_id, bot, channel_username):
    """Check if a user is a member of the specified channel."""
    try:
        chat_member = await bot.get_chat_member(channel_username, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except BadRequest:
        return False

# Command handlers
async def vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    
    if is_user_banned(update.effective_user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return
    
    # Check if user already has created channels (no limit on creating)
    created_channels = get_user_created_channels(update.effective_user.id)
    if created_channels:
        channels_list = ", ".join([f"@{ch}" for ch in created_channels])
        await update.message.reply_text(f"❌ You already have active polls in: {channels_list}\nUse /stop to end them first.")
        return

    await update.message.reply_text("❓ Enter Channel Username With @")

async def handle_channel_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if is_user_banned(update.effective_user.id):
            await update.message.reply_text("❌ You are banned from using this command.")
            return

        channel_username = update.message.text.strip("@")
        creator_id = update.effective_user.id
        
        # Try to create poll
        success, message = create_channel_poll(channel_username, creator_id)
        if not success:
            await update.message.reply_text(f"❌ {message}")
            return
        
        participation_link = f"https://t.me/{context.bot.username}?start={channel_username}"
        safe_participation_link = urllib.parse.quote(participation_link, safe=":/?&=")
        
        response = (
            f"» Poll created successfully.\n"
            f" • Chat: @{channel_username}\n\n"
            f"<b>Participation Link:</b>\n"
            f"<a href='{safe_participation_link}'>Click Here</a>"
        )
        
        message = await context.bot.send_message(
            chat_id=f"@{channel_username}", 
            text=response, 
            parse_mode="HTML", 
            disable_web_page_preview=True
        )
        
        await update.message.reply_text(response, parse_mode="HTML", disable_web_page_preview=True)
        
    except Exception as e:
        logging.error(f"Error in handle_channel_username: {str(e)}")
        await update.message.reply_text("❌ Something went wrong while creating the poll. Please try again later.")

async def start_command(update, context):
    user = update.effective_user
    args = context.args

    if not user:
        await update.message.reply_text("❌ Unable to process your request. User information is missing.")
        return

    if is_user_banned(user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return 
        
    is_member = await check_user_membership(user.id, context.bot, CHANNEL_USERNAME)
    if not is_member:
        join_link = f"https://t.me/Trusted_Sellers_of_Pd"
        keyboard = [
            [InlineKeyboardButton("Join Channel 🔗", url=join_link)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"❌ You must join {CHANNEL_USERNAME} to use the bot.",
            reply_markup=reply_markup
        )
        return

    if not is_user_registered(user.id):
        add_user_to_db(user.id, user.first_name, user.last_name or "", user.username or "")
        await update.message.reply_text(f"✅ You are now registered, {user.first_name}!")

    if not args:
        await update.message.reply_text(f"✅ Welcome back, {user.first_name}!\nUse a link to participate in the giveaway.")
        return

    channel_username = args[0]
    
    # Check if channel has active poll
    conn = sqlite3.connect("vote_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_active FROM channel_polls WHERE channel_username = ?", (channel_username,))
    result = cursor.fetchone()
    conn.close()
    
    if not result or not result[0]:
        await update.message.reply_text("❌ No active poll in this channel.")
        return

    # Check if user can join this poll
    can_join, error_message = can_join_poll(user.id, channel_username)
    if not can_join:
        await update.message.reply_text(f"❌ {error_message}")
        return

    # Add user to poll participants
    poll_id = add_poll_participant(channel_username, user.id, user.first_name)
    add_user_channel_session(user.id, channel_username)
    
    vote_count = get_channel_vote_count(channel_username)
    button = InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"Vote ⚡ ({vote_count})", callback_data=f"vote:{channel_username}")]]
    )

    response = (
        f"✅ Successfully participated.\n\n"
        f"‣ *User* : {escape_markdown(user.first_name, version=1)} {escape_markdown(user.last_name or '', version=1)}\n"
        f"‣ *User-ID* : `{user.id}`\n"
        f"‣ *Username* : @{escape_markdown(user.username or 'None', version=1)}\n"
        f"‣ *Link* : [{escape_markdown(user.first_name, version=1)}](tg://user?id={user.id})\n"
        f"‣ *Poll ID* : {escape_markdown(str(poll_id), version=1)}\n"
        f"‣ *Note* : Only channel subscribers can vote.\n\n"
        f"×× Created by - [@Trusted_Sellers_of_Pd](https://t.me/Trusted_Sellers_of_Pd)"
    )

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
            disable_web_page_preview=True
        )

    await update.message.reply_text("✅ You have successfully participated in the voting!")

async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_name = query.from_user.first_name

    try:
        channel_username = query.data.split(":")[1]
    except (ValueError, IndexError):
        await query.answer("❌ Invalid data received.", show_alert=True)
        return

    # Check if user is a member of the channel
    try:
        chat_member = await context.bot.get_chat_member(f'@{channel_username}', user_id)
        if chat_member.status not in ["member", "administrator", "creator"]:
            raise BadRequest(f"❌ You must join @{channel_username} to vote.")
    except BadRequest as e:
        await query.answer(str(e), show_alert=True)
        return

    # Vote in channel
    success, message = vote_in_channel(channel_username, user_id, user_name)
    
    if not success:
        await query.answer(f"❌ {message}", show_alert=True)
        return

    # Update button with new vote count
    vote_count = get_channel_vote_count(channel_username)
    new_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"Vote ⚡ ({vote_count})", callback_data=f"vote:{channel_username}")]]
    )
    await query.message.edit_reply_markup(reply_markup=new_button)
    await query.answer("✅ Your vote has been counted!")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_user_banned(update.effective_user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return

    user_id = update.effective_user.id
    created_channels = get_user_created_channels(user_id)
    
    if not created_channels:
        await update.message.reply_text("❌ You don't have any active polls.")
        return
    
    stopped_channels = []
    for channel in created_channels:
        success, message = stop_channel_poll(channel, user_id)
        if success:
            stopped_channels.append(channel)
    
    if stopped_channels:
        channels_list = ", ".join([f"@{ch}" for ch in stopped_channels])
        await update.message.reply_text(f"✅ Polls stopped in: {channels_list}")
    else:
        await update.message.reply_text("❌ Failed to stop any polls.")

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_user_banned(update.effective_user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return

    user_id = update.effective_user.id
    
    if context.args:
        # Get top for specific channel
        channel_username = context.args[0].strip("@")
        top_users = get_channel_top_voters(channel_username)
        
        if not top_users:
            await update.message.reply_text(f"❌ No participants found for @{channel_username}.")
            return
        
        top_message = f"🏆 Top participants in @{channel_username}:\n\n"
        for i, (poll_id, user_name, user_id, join_time) in enumerate(top_users[:10]):
            user_name = escape_markdown(user_name, version=1)
            top_message += f"🎖 *{i+1}. {user_name}* (ID: {poll_id})\n"
        
        await update.message.reply_text(top_message, parse_mode="Markdown")
        return
    
    # Get top for user's active channels
    active_channels = get_user_active_channels(user_id)
    if not active_channels:
        await update.message.reply_text("❌ You are not participating in any active voting polls. Use /top {channel_username} to get stats.")
        return
    
    # Show top for each active channel
    for channel in active_channels:
        top_users = get_channel_top_voters(channel)
        
        if not top_users:
            await update.message.reply_text(f"❌ No participants found for @{channel}.")
            continue
        
        top_message = f"🏆 Top participants in @{channel}:\n\n"
        for i, (poll_id, user_name, user_id, join_time) in enumerate(top_users[:10]):
            user_name = escape_markdown(user_name, version=1)
            top_message += f"🎖 *{i+1}. {user_name}* (ID: {poll_id})\n"
        
        await update.message.reply_text(top_message, parse_mode="Markdown")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_user_banned(update.effective_user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return

    user_id = update.effective_user.id
    
    # Check if poll_id is provided as an argument
    if context.args:
        try:
            requested_poll_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid poll_id. Please provide a valid poll_id.")
            return
    else:
        requested_poll_id = None

    # Check if user has any created polls
    created_channels = get_user_created_channels(user_id)
    if not created_channels:
        await update.message.reply_text("❌ You don't have any active polls.")
        return
    
    # Process each created channel
    for channel in created_channels:
        # Verify user is the creator of the channel poll
        conn = sqlite3.connect("vote_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT creator_id FROM channel_polls WHERE channel_username = ?", (channel,))
        result = cursor.fetchone()
        
        if not result or result[0] != user_id:
            conn.close()
            continue
        
        # Get voters who voted in this channel (people who clicked vote button)
        cursor.execute("""
            SELECT cv.user_id, cv.user_name 
            FROM channel_votes cv
            WHERE cv.channel_username = ?
            ORDER BY cv.vote_time
        """, (channel,))
        
        voters = cursor.fetchall()
        conn.close()

        if not voters:
            await update.message.reply_text(f"❌ No voters found for poll in @{channel}.")
            continue

        # Clean user names and create mentions
        def clean_name(text: str) -> str:
            import re
            bracket_pattern = re.compile(r'[\[\]\(\)\{\}\<\>]')
            return bracket_pattern.sub('', text)

        user_mentions = []
        for idx, (voter_user_id, user_name) in enumerate(voters):
            cleaned_name = clean_name(user_name)
            mention = f"[{cleaned_name}](tg://user?id={voter_user_id})"
            user_mentions.append(f"{idx + 1}. {mention}")
        
        # Split into chunks of 30 users per message
        chunk_size = 30
        chunks = [user_mentions[i:i + chunk_size] for i in range(0, len(user_mentions), chunk_size)]

        # Send each chunk as a separate message
        total_voters = len(voters)
        for idx, chunk in enumerate(chunks):
            start_num = (idx * chunk_size) + 1
            end_num = min((idx + 1) * chunk_size, total_voters)
            
            voters_list = "\n".join(chunk)
            
            try:
                message = (
                    f"👥 **Voters in @{channel} ({start_num}-{end_num} of {total_voters}):**\n\n"
                    f"{voters_list}"
                )
                await update.message.reply_text(message, parse_mode="Markdown")
            except Exception as e:
                await update.message.reply_text(f"❌ Error sending message part {idx + 1}: {e}")
                
        # Send summary message for this channel
        await update.message.reply_text(
            f"✅ **Summary for @{channel}:** Found {total_voters} total voters\n"
            f"📊 **Poll ID requested:** {requested_poll_id if requested_poll_id else 'All'} (showing all voters in your channel)"
        )


async def delete_poll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update) and not is_allowed(update):
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

def fix_html_links(text):
    """
    Fixes HTML links by ensuring they follow the correct format.
    Proper format: <a href="url">text</a> → text (url)
    """
    return re.sub(r'<a href="(.*?)">(.*?)</a>', r'\2 (\1)', text)

async def confirm_delete_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                # Escape caption before applying strikethrough formatting
                escaped_caption = escape_html(message.caption)
                fixed_caption = fix_html_links(escaped_caption)  # Fix broken links
                updated_caption = f"<s>{fixed_caption}</s>\n\n<b>THIS POLL HAS BEEN DISQUALIFIED FROM THE GIVEAWAY</b>"

                await context.bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_channel_id,
                    caption=updated_caption,
                    parse_mode=telegram.constants.ParseMode.HTML,
                    reply_markup=None  # Remove inline buttons
                )
            else:
                # Escape text before applying strikethrough formatting
                escaped_text = escape_html(message.text)
                fixed_text = fix_html_links(escaped_text)  # Fix broken links
                updated_text = f"<s>{fixed_text}</s>\n\n<b>THIS POLL HAS BEEN DISQUALIFIED FROM THE GIVEAWAY</b>"

                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_channel_id,
                    text=updated_text,
                    parse_mode=telegram.constants.ParseMode.HTML,
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

async def current_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_user_banned(update.effective_user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return

    user_id = update.effective_user.id
    active_channels = get_user_active_channels(user_id)
    created_channels = get_user_created_channels(user_id)
    
    if not active_channels and not created_channels:
        await update.message.reply_text("❌ You are not participating in any active voting sessions and have no created polls.")
        return
    
    # Show created polls first
    if created_channels:
        for channel in created_channels:
            vote_count = get_channel_vote_count(channel)
            channel_escaped = escape_markdown(channel, version=1)
            
            creator_message = (
                f"👑 *Your Created Poll:*\n"
                f"⭐ *Channel:* @{channel_escaped}\n"
                f"⭐ *Total Votes:* {vote_count}\n"
                f"⭐ *Status:* Creator\n"
            )
            await update.message.reply_text(creator_message, parse_mode="Markdown")
    
    # Show participating polls
    if active_channels:
        for channel in active_channels:
            vote_count = get_channel_vote_count(channel)
            
            # Check if user has voted
            conn = sqlite3.connect("vote_bot.db")
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM channel_votes WHERE channel_username = ? AND user_id = ?", 
                          (channel, user_id))
            has_voted = cursor.fetchone() is not None
            conn.close()
            
            channel_escaped = escape_markdown(channel, version=1)
            
            participant_message = (
                f"🎯 *Participating In:*\n"
                f"⭐ *Channel:* @{channel_escaped}\n"
                f"⭐ *Total Votes:* {vote_count}\n"
                f"⭐ *Your Vote Status:* {'✅ Voted' if has_voted else '❌ Not Voted'}\n"
            )
            await update.message.reply_text(participant_message, parse_mode="Markdown")
    
    # Show summary
    total_sessions = len(active_channels) + len(created_channels)
    summary_message = (
        f"📊 *Summary:*\n"
        f"📝 *Created Polls:* {len(created_channels)}\n"
        f"🎯 *Participating In:* {len(active_channels)}\n"
        f"📈 *Total Active Sessions:* {total_sessions}/6 (5 max participating + 1 created)\n"
    )
    await update.message.reply_text(summary_message, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_user_banned(update.effective_user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return
        
    commands = """
📋 **Available Commands:**

**General Commands:**
/start - Start the bot or join a poll
/help - Show this help message
/current - Get your current voting information (all channels)
/top - Get top users in your channels
/top @channel - Get top users in specific channel

**Poll Management:**
/vote - Start a new voting poll (max 1 created poll)
/stop - Stop all your created polls
/list - Get all participants in your polls
/delete_poll - Delete all your created polls

**Participation Rules:**
• You can join up to 5 different polls
• You cannot join the same channel twice
• You cannot join your own voting session
• Only channel members can vote

**Admin Commands (Special Users Only):**
/ban - Ban a user
/unban - Unban a user  
/listban - List all banned users
/broadcast - Broadcast a message
/stats - Get bot statistics

**Note:** You can participate in multiple polls simultaneously but can only create one poll at a time.
"""
    await update.message.reply_text(commands)

# Admin commands
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_special_user(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("❌ Usage: /ban <user_id> or reply to a message")
        return

    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        target_username = update.message.reply_to_message.from_user.username or "Unknown"
    else:
        try:
            target_user_id = int(context.args[0])
            target_username = "Unknown"
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid user ID or reply to a message.")
            return

    ban_user(target_user_id)
    await update.message.reply_text(f"✅ User {target_user_id} (@{target_username}) has been banned.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_special_user(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("❌ Usage: /unban <user_id> or reply to a message")
        return

    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        target_username = update.message.reply_to_message.from_user.username or "Unknown"
    else:
        try:
            target_user_id = int(context.args[0])
            target_username = "Unknown"
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid user ID or reply to a message.")
            return

    unban_user(target_user_id)
    await update.message.reply_text(f"✅ User {target_user_id} (@{target_username}) has been unbanned.")

async def listban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_special_user(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    banned_users = get_banned_users()
    if not banned_users:
        await update.message.reply_text("❌ No banned users found.")
        return

    banned_list = "\n".join([f"• {user_id} (@{username or 'Unknown'}) - {first_name or 'Unknown'}" 
                            for user_id, username, first_name in banned_users])
    await update.message.reply_text(f"📜 **Banned Users:**\n\n{banned_list}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_special_user(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    # Get statistics
    conn_main = sqlite3.connect("bot_main.db")
    cursor_main = conn_main.cursor()
    cursor_main.execute("SELECT COUNT(*) FROM users")
    total_users = cursor_main.fetchone()[0]
    cursor_main.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
    banned_users = cursor_main.fetchone()[0]
    conn_main.close()

    conn_vote = sqlite3.connect("vote_bot.db")
    cursor_vote = conn_vote.cursor()
    cursor_vote.execute("SELECT COUNT(*) FROM channel_polls WHERE is_active = 1")
    active_polls = cursor_vote.fetchone()[0]
    cursor_vote.execute("SELECT COUNT(*) FROM channel_votes")
    total_votes = cursor_vote.fetchone()[0]
    cursor_vote.execute("SELECT COUNT(DISTINCT user_id) FROM user_sessions")
    active_participants = cursor_vote.fetchone()[0]
    conn_vote.close()

    stats_message = (
        f"📊 **Bot Statistics:**\n\n"
        f"👥 Total Users: {total_users}\n"
        f"🚫 Banned Users: {banned_users}\n"
        f"🗳 Active Polls: {active_polls}\n"
        f"🎯 Active Participants: {active_participants}\n"
        f"✅ Total Votes Cast: {total_votes}"
    )
    
    await update.message.reply_text(stats_message)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_special_user(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if update.message.reply_to_message:
        message_text = update.message.reply_to_message.text
    else:
        if not context.args:
            await update.message.reply_text("❌ Please provide a message to broadcast or reply to a message with /broadcast")
            return
        message_text = " ".join(context.args)

    await update.message.reply_text("✅ Starting the broadcast...")

    conn = sqlite3.connect("bot_main.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
    users = cursor.fetchall()
    conn.close()

    total_users = len(users)
    success_count = 0
    fail_count = 0

    for user in users:
        user_id = user[0]
        try:
            await context.bot.send_message(chat_id=user_id, text=message_text)
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"Failed to send message to {user_id}: {e}")

    await update.message.reply_text(
        f"✅ Broadcast completed!\n\n"
        f"📊 Total Users: {total_users}\n"
        f"✅ Successful: {success_count}\n"
        f"❌ Failed: {fail_count}"
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_user_banned(update.effective_user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return

    user = None
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        user_info = {
            'user_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name or "",
            'username': user.username or ""
        }
    elif context.args:
        identifier = context.args[0]
        if identifier.isdigit():
            user_id = int(identifier)
            conn = sqlite3.connect("bot_main.db")
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, first_name, last_name, username FROM users WHERE user_id = ?", (user_id,))
            user_data = cursor.fetchone()
            conn.close()

            if user_data:
                user_info = {
                    'user_id': user_data[0],
                    'first_name': user_data[1],
                    'last_name': user_data[2] or "",
                    'username': user_data[3] or ""
                }
            else:
                user_info = None
        else:
            username = identifier.lstrip("@")
            conn = sqlite3.connect("bot_main.db")
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, first_name, last_name, username FROM users WHERE username = ?", (username,))
            user_data = cursor.fetchone()
            conn.close()

            if user_data:
                user_info = {
                    'user_id': user_data[0],
                    'first_name': user_data[1],
                    'last_name': user_data[2] or "",
                    'username': user_data[3] or ""
                }
            else:
                user_info = None
    else:
        user_info = None

    if not user_info:
        await update.message.reply_text("❌ Could not retrieve user information. Make sure the user ID or username is correct.")
        return

    user_message = (
        f"👤 **User Information:**\n"
        f"📝 **First Name:** {user_info['first_name']}\n"
        f"📝 **Last Name:** {user_info['last_name'] or 'N/A'}\n"
        f"🆔 **User ID:** `{user_info['user_id']}`\n"
        f"👤 **Username:** @{user_info['username'] or 'N/A'}\n"
        f"🔗 **Mention:** [{user_info['first_name']}](tg://user?id={user_info['user_id']})"
    )

    await update.message.reply_text(user_message, parse_mode="Markdown")

# New command to leave a specific poll
async def leave_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_user_banned(update.effective_user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return

    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /leave @channel_username")
        return
    
    channel_username = context.args[0].strip("@")
    active_channels = get_user_active_channels(user_id)
    
    if channel_username not in active_channels:
        await update.message.reply_text(f"❌ You are not participating in @{channel_username}.")
        return
    
    remove_user_channel_session(user_id, channel_username)
    await update.message.reply_text(f"✅ You have left the poll in @{channel_username}.")

def delete_db():
    """Delete the voting database (for testing purposes)"""
    if os.path.exists("vote_bot.db"):
        os.remove("vote_bot.db")
    if os.path.exists("bot_main.db"):
        os.remove("bot_main.db")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset all databases (Owner only - for testing)"""
    if update.effective_user.id != 5873900195:  # ActiveForever only
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    delete_db()
    init_db()
    create_db()
    create_users_table()
    await update.message.reply_text("✅ All databases have been reset.")

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by Updates."""
    logging.error(f"Update {update} caused error {context.error}")

# Main function
if __name__ == "__main__":
    # Initialize databases
    init_db()
    create_db() 
    create_users_table()
    
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # Create the application
    application = ApplicationBuilder().token(BOT_TOKEN).get_updates_connect_timeout(30).build()

    # Add command handlers
    application.add_handler(CommandHandler("vote", vote_command))
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("current", current_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("delete_poll", delete_poll_command))
    # Admin commands
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("listban", listban_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("reset", reset_command))
    
    # Message and callback handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_username))
    application.add_handler(CallbackQueryHandler(handle_vote, pattern=r"^vote:"))
    application.add_handler(CallbackQueryHandler(confirm_delete_poll, pattern=r"^delete_"))
    
    # Error handler
    application.add_error_handler(error_handler)

    # Start polling
    print("🚀 Bot started successfully!")
    application.run_polling()
