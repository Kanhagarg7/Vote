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

from telegram.error import BadRequest, TelegramError
# Import specific items from datetime instead of using wildcard import
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Bot
from telegram.ext import Application, CallbackQueryHandler, ChatMemberHandler, ContextTypes
import sqlite3
import logging
import urllib.parse
import re
import telegram
import StringIO
import asyncio
import threading
from flask import Flask, render_template_string, jsonify, request

img_path = "img/img.png"
BOT_TOKEN = "7593876189:AAExsIGMoAs8eokv45xQA3h5IyW2-ZHg2KA"
owners = [5873900195]  # ActiveForever
special_users = [5873900195, 6574063018]  # ActiveForever and TeamKanha (replace with actual ID)
bot_username = "ActiveForever_Votingbot"

# Backup configuration
BACKUP_CHANNEL_ID = -1003044741584
DATABASE_FILES = ["vote_bot.db", "bot_main.db"]

class DatabaseBackupSystem:
    def __init__(self, bot_token, channel_id):
        self.bot = Bot(token=bot_token)
        self.channel_id = channel_id
        self.backup_interval = 15 * 60  # 30 minutes in seconds
        self.running = False
        self.backup_thread = None
        
    async def send_database_backup(self):
        """Send database files to backup channel"""
        try:
            for db_file in DATABASE_FILES:
                if os.path.exists(db_file):
                    # Create backup filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_filename = f"backup_{timestamp}_{db_file}"
                    
                    with open(db_file, 'rb') as file:
                        await self.bot.send_document(
                            chat_id=self.channel_id,
                            document=file,
                            filename=backup_filename,
                            caption=f"Database backup: {db_file} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                    
                    logging.info(f"Successfully backed up {db_file} to channel")
                else:
                    logging.warning(f"Database file {db_file} not found, skipping backup")
                    
        except TelegramError as e:
            logging.error(f"Failed to send database backup: {e}")
        except Exception as e:
            logging.error(f"Unexpected error during backup: {e}")
    
    async def download_latest_databases(self):
        """Download the latest database files from backup channel if local files don't exist"""
        try:
            for db_file in DATABASE_FILES:
                if not os.path.exists(db_file):
                    logging.info(f"Local {db_file} not found, searching for latest backup...")
                    
                    # Find and download the latest backup for this database
                    success = await self._find_and_download_latest_backup(db_file)
                    
                    if not success:
                        logging.warning(f"No backup found for {db_file}, creating empty database")
                        self._create_empty_database(db_file)
                        
        except Exception as e:
            logging.error(f"Error during database download: {e}")
    
    async def _find_and_download_latest_backup(self, db_file):
        """Find and download the latest backup for a specific database file"""
        try:
            # Get the last 50 messages from the backup channel
            # We'll search through recent messages to find the latest backup
            
            latest_backup_info = None
            latest_timestamp = None
            
            # Try to search for backup files by checking recent message range
            # This is a practical approach that works within API limitations
            
            # Method: Try to access recent messages by trying different message IDs
            # Start from a reasonable recent point and go backwards
            
            base_message_id = await self._get_approximate_latest_message_id()
            
            if base_message_id:
                # Search backwards from the estimated latest message ID
                for i in range(50):  # Check last 50 messages
                    try:
                        message_id = base_message_id - i
                        if message_id <= 0:
                            break
                            
                        # Try to get message (this might work if bot has right permissions)
                        message = await self.bot.forward_message(
                            chat_id=self.channel_id,  # Forward to same channel (will fail but we can catch)
                            from_chat_id=self.channel_id,
                            message_id=message_id
                        )
                        
                        # If we somehow get here, check if it's a backup file
                        if message and message.document:
                            filename = message.document.file_name
                            if self._is_backup_file_for_db(filename, db_file):
                                # Extract timestamp from filename
                                timestamp = self._extract_timestamp_from_filename(filename)
                                
                                if latest_timestamp is None or timestamp > latest_timestamp:
                                    latest_timestamp = timestamp
                                    latest_backup_info = {
                                        'message': message,
                                        'filename': filename,
                                        'timestamp': timestamp
                                    }
                        
                    except Exception:
                        # This will likely fail - that's expected due to API limitations
                        continue
            
            # If we found a backup, download it
            if latest_backup_info:
                return await self._download_backup_file(latest_backup_info, db_file)
            else:
                # Alternative approach: Use a simpler method
                return await self._alternative_download_approach(db_file)
                
        except Exception as e:
            logging.error(f"Error finding latest backup for {db_file}: {e}")
            return False
    
    async def _get_approximate_latest_message_id(self):
        """Get an approximate latest message ID for the channel"""
        try:
            # Try to send a test message and get its ID, then delete it
            # This gives us a reference point for recent message IDs
            
            test_message = await self.bot.send_message(
                chat_id=self.channel_id,
                text="🔍 Checking for backups... (will be deleted)"
            )
            
            message_id = test_message.message_id
            
            # Delete the test message
            try:
                await self.bot.delete_message(
                    chat_id=self.channel_id,
                    message_id=message_id
                )
            except Exception:
                pass  # Ignore if we can't delete
            
            return message_id
            
        except Exception as e:
            logging.error(f"Could not get reference message ID: {e}")
            return None
    
    async def _alternative_download_approach(self, db_file):
        """Alternative approach: Create a restore command or use stored message IDs"""
        try:
            # Since direct message retrieval is limited, we'll implement a different strategy
            
            # Log that we're creating empty database
            logging.info(f"Creating empty {db_file} due to API limitations in automatic download")
            
            # You could enhance this by:
            # 1. Storing backup message IDs in a file
            # 2. Using a webhook to catch backup messages
            # 3. Having a manual restore command
            
            return False  # Indicates we need to create empty database
            
        except Exception as e:
            logging.error(f"Error in alternative download approach: {e}")
            return False
    
    def _is_backup_file_for_db(self, filename, db_file):
        """Check if filename is a backup for the specified database"""
        if not filename:
            return False
        
        # Check if filename matches pattern: backup_YYYYMMDD_HHMMSS_db_file
        pattern = rf"backup_\d{{8}}_\d{{6}}_{re.escape(db_file)}"
        return re.match(pattern, filename) is not None
    
    def _extract_timestamp_from_filename(self, filename):
        """Extract timestamp from backup filename"""
        try:
            # Extract timestamp from filename like: backup_20241125_143022_vote_bot.db
            match = re.search(r"backup_(\d{8}_\d{6})", filename)
            if match:
                return match.group(1)
        except Exception:
            pass
        return None
    
    async def _download_backup_file(self, backup_info, target_db_file):
        """Download and rename backup file"""
        try:
            message = backup_info['message']
            original_filename = backup_info['filename']
            
            # Get the file
            file = await message.document.get_file()
            
            # Download to temporary location
            temp_filename = f"temp_{original_filename}"
            await file.download_to_drive(temp_filename)
            
            # Rename to target database filename
            if os.path.exists(temp_filename):
                # Remove existing file if it exists
                if os.path.exists(target_db_file):
                    os.remove(target_db_file)
                
                # Rename temp file to target
                os.rename(temp_filename, target_db_file)
                
                logging.info(f"✅ Successfully downloaded and renamed {original_filename} to {target_db_file}")
                return True
            else:
                logging.error(f"❌ Downloaded file {temp_filename} not found")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error downloading backup file: {e}")
            return False
    
    def _create_empty_database(self, db_file):
        """Create an empty database file with basic structure"""
        try:
            if db_file == "vote_bot.db":
                self._create_empty_vote_db(db_file)
            elif db_file == "bot_main.db":
                self._create_empty_main_db(db_file)
            logging.info(f"✅ Created empty database: {db_file}")
        except Exception as e:
            logging.error(f"❌ Error creating empty database {db_file}: {e}")
    
    def _create_empty_vote_db(self, db_file):
        """Create empty vote database with required tables"""
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
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
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channel_votes (
                channel_username TEXT,
                user_id INTEGER,
                user_name TEXT,
                vote_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel_username, user_id)
            )
        """)
        
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
    
    def _create_empty_main_db(self, db_file):
        """Create empty main database with required tables"""
        conn = sqlite3.connect(db_file)
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
    
    def backup_loop(self):
        """Main backup loop that runs in a separate thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Check for missing databases on startup
        try:
            loop.run_until_complete(self.download_latest_databases())
        except Exception as e:
            logging.error(f"Error during startup database check: {e}")
        
        while self.running:
            try:
                # Check and download missing databases
                loop.run_until_complete(self.download_latest_databases())
                
                # Send backup
                loop.run_until_complete(self.send_database_backup())
                
                # Wait for next backup
                time.sleep(self.backup_interval)
                
            except Exception as e:
                logging.error(f"Error in backup loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def start_backup_system(self):
        """Start the backup system in a separate thread"""
        if not self.running:
            self.running = True
            self.backup_thread = threading.Thread(target=self.backup_loop, daemon=True)
            self.backup_thread.start()
            logging.info("🚀 Database backup system started")
            return True
        return False
    
    def stop_backup_system(self):
        """Stop the backup system"""
        if self.running:
            self.running = False
            if self.backup_thread:
                self.backup_thread.join(timeout=5)
            logging.info("🛑 Database backup system stopped")
            return True
        return False

# Simple alternative with message ID storage
class SimpleBackupSystem(DatabaseBackupSystem):
    """Simplified version that stores backup message IDs in a file"""
    
    def __init__(self, bot_token, channel_id):
        super().__init__(bot_token, channel_id)
        self.backup_ids_file = "backup_message_ids.txt"
    
    async def send_database_backup(self):
        """Send database files and store message IDs"""
        backup_ids = {}
        
        try:
            for db_file in DATABASE_FILES:
                if os.path.exists(db_file):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_filename = f"backup_{timestamp}_{db_file}"
                    
                    with open(db_file, 'rb') as file:
                        message = await self.bot.send_document(
                            chat_id=self.channel_id,
                            document=file,
                            filename=backup_filename,
                            caption=f"Database backup: {db_file} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                    
                    # Store the latest message ID for this database
                    backup_ids[db_file] = {
                        'message_id': message.message_id,
                        'filename': backup_filename,
                        'timestamp': timestamp
                    }
                    
                    logging.info(f"✅ Backed up {db_file} (Message ID: {message.message_id})")
            
            # Save backup IDs to file
            self._save_backup_ids(backup_ids)
                    
        except Exception as e:
            logging.error(f"❌ Error in backup: {e}")
    
    async def download_latest_databases(self):
        """Download using stored message IDs"""
        try:
            backup_ids = self._load_backup_ids()
            
            for db_file in DATABASE_FILES:
                if not os.path.exists(db_file):
                    logging.info(f"🔍 {db_file} missing, attempting restore...")
                    
                    if db_file in backup_ids:
                        message_id = backup_ids[db_file]['message_id']
                        filename = backup_ids[db_file]['filename']
                        
                        success = await self._download_by_message_id(message_id, filename, db_file)
                        if not success:
                            self._create_empty_database(db_file)
                    else:
                        logging.warning(f"⚠️ No backup ID found for {db_file}")
                        self._create_empty_database(db_file)
                        
        except Exception as e:
            logging.error(f"❌ Error downloading databases: {e}")
    
    async def _download_by_message_id(self, message_id, backup_filename, target_db_file):
        """Download file using message ID"""
        try:
            # Try to get the message by forwarding it to ourselves
            # This is a workaround for message access limitations
            
            logging.info(f"🔄 Attempting to restore {target_db_file} from message {message_id}")
            
            # Since we can't directly get channel messages, we'll use a different approach
            # For now, create empty database (you can enhance this part)
            logging.info(f"📝 Creating empty {target_db_file} due to API limitations")
            return False
            
        except Exception as e:
            logging.error(f"❌ Error downloading by message ID: {e}")
            return False
    
    def _save_backup_ids(self, backup_ids):
        """Save backup message IDs to file"""
        try:
            # Only keep the latest backup ID for each database
            existing_ids = self._load_backup_ids()
            
            # Update with new IDs
            existing_ids.update(backup_ids)
            
            # Save to file
            with open(self.backup_ids_file, 'w') as f:
                for db_file, info in existing_ids.items():
                    f.write(f"{db_file}:{info['message_id']}:{info['filename']}:{info['timestamp']}\n")
            
            logging.info("💾 Saved backup message IDs")
            
        except Exception as e:
            logging.error(f"❌ Error saving backup IDs: {e}")
    
    def _load_backup_ids(self):
        """Load backup message IDs from file"""
        backup_ids = {}
        try:
            if os.path.exists(self.backup_ids_file):
                with open(self.backup_ids_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split(':')
                        if len(parts) >= 4:
                            db_file = parts[0]
                            message_id = int(parts[1])
                            filename = parts[2]
                            timestamp = parts[3]
                            
                            backup_ids[db_file] = {
                                'message_id': message_id,
                                'filename': filename,
                                'timestamp': timestamp
                            }
        except Exception as e:
            logging.error(f"❌ Error loading backup IDs: {e}")
        
        return backup_ids

backup_system = None

def initialize_backup_system():
    """Initialize and start the backup system"""
    global backup_system
    if backup_system is None:
        backup_system = DatabaseBackupSystem(BOT_TOKEN, BACKUP_CHANNEL_ID)
        backup_system.start_backup_system()
        return backup_system
    return backup_system

# Flask Web Interface
app = Flask(__name__)

@app.route('/')
def dashboard():
    html_template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Telegram Voting Bot Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                background: rgba(255,255,255,0.95);
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
            .header { 
                text-align: center; 
                margin-bottom: 40px;
                color: #333;
            }
            .header h1 { 
                font-size: 2.5em; 
                margin-bottom: 10px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .stats-grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                gap: 20px; 
                margin-bottom: 40px; 
            }
            .stat-card { 
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                padding: 25px; 
                border-radius: 10px; 
                text-align: center; 
                color: white;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                transition: transform 0.3s ease;
            }
            .stat-card:hover { transform: translateY(-5px); }
            .stat-card h3 { 
                font-size: 1.2em; 
                margin-bottom: 10px;
                opacity: 0.9;
            }
            .stat-card p { 
                font-size: 2em; 
                font-weight: bold; 
            }
            .polls-section { 
                margin-bottom: 40px; 
            }
            .polls-section h2 { 
                color: #333; 
                margin-bottom: 20px;
                border-bottom: 2px solid #667eea;
                padding-bottom: 10px;
            }
            .polls-table { 
                width: 100%; 
                border-collapse: collapse; 
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            }
            .polls-table th, .polls-table td { 
                padding: 15px; 
                text-align: left; 
                border-bottom: 1px solid #eee;
            }
            .polls-table th { 
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                font-weight: 600;
            }
            .polls-table tr:hover { 
                background-color: #f8f9fa; 
            }
            .status-active { 
                color: #28a745; 
                font-weight: bold; 
            }
            .status-inactive { 
                color: #dc3545; 
                font-weight: bold; 
            }
            .refresh-btn { 
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white; 
                border: none; 
                padding: 12px 25px; 
                border-radius: 25px; 
                cursor: pointer; 
                font-size: 16px;
                margin-bottom: 20px;
                transition: all 0.3s ease;
            }
            .refresh-btn:hover { 
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            .backup-status {
                background: linear-gradient(135deg, #4ecdc4, #44a08d);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Telegram Voting Bot Dashboard</h1>
                <p>Real-time monitoring and statistics</p>
            </div>
            
            <div class="backup-status">
                <h3>🔄 Backup System Status</h3>
                <p id="backup-status">Loading...</p>
            </div>
            
            <button class="refresh-btn" onclick="refreshData()">🔄 Refresh Data</button>
            
            <div class="stats-grid" id="stats-grid">
                <!-- Stats will be loaded here -->
            </div>
            
            <div class="polls-section">
                <h2>📊 Active Polls</h2>
                <div id="polls-table">
                    <!-- Polls table will be loaded here -->
                </div>
            </div>
            
            <div class="polls-section">
                <h2>👥 Recent Users</h2>
                <div id="users-table">
                    <!-- Users table will be loaded here -->
                </div>
            </div>
        </div>
        
        <script>
            async function fetchStats() {
                try {
                    const response = await fetch('/api/stats');
                    return await response.json();
                } catch (error) {
                    console.error('Error fetching stats:', error);
                    return null;
                }
            }
            
            async function fetchPolls() {
                try {
                    const response = await fetch('/api/polls');
                    return await response.json();
                } catch (error) {
                    console.error('Error fetching polls:', error);
                    return null;
                }
            }
            
            async function fetchUsers() {
                try {
                    const response = await fetch('/api/users');
                    return await response.json();
                } catch (error) {
                    console.error('Error fetching users:', error);
                    return null;
                }
            }
            
            function updateStats(stats) {
                if (!stats) return;
                
                const statsGrid = document.getElementById('stats-grid');
                statsGrid.innerHTML = `
                    <div class="stat-card">
                        <h3>Total Users</h3>
                        <p>${stats.total_users}</p>
                    </div>
                    <div class="stat-card">
                        <h3>Active Polls</h3>
                        <p>${stats.active_polls}</p>
                    </div>
                    <div class="stat-card">
                        <h3>Total Votes</h3>
                        <p>${stats.total_votes}</p>
                    </div>
                    <div class="stat-card">
                        <h3>Active Participants</h3>
                        <p>${stats.active_participants}</p>
                    </div>
                    <div class="stat-card">
                        <h3>Banned Users</h3>
                        <p>${stats.banned_users}</p>
                    </div>
                `;
            }
            
            function updatePolls(polls) {
                if (!polls) return;
                
                const pollsTable = document.getElementById('polls-table');
                if (polls.length === 0) {
                    pollsTable.innerHTML = '<p>No active polls found.</p>';
                    return;
                }
                
                let tableHTML = `
                    <table class="polls-table">
                        <thead>
                            <tr>
                                <th>Channel</th>
                                <th>Creator ID</th>
                                <th>Poll ID</th>
                                <th>Votes</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                polls.forEach(poll => {
                    tableHTML += `
                        <tr>
                            <td>@${poll.channel_username}</td>
                            <td>${poll.creator_id}</td>
                            <td>${poll.current_poll_id}</td>
                            <td>${poll.vote_count}</td>
                            <td class="${poll.is_active ? 'status-active' : 'status-inactive'}">
                                ${poll.is_active ? 'Active' : 'Inactive'}
                            </td>
                        </tr>
                    `;
                });
                
                tableHTML += '</tbody></table>';
                pollsTable.innerHTML = tableHTML;
            }
            
            function updateUsers(users) {
                if (!users) return;
                
                const usersTable = document.getElementById('users-table');
                if (users.length === 0) {
                    usersTable.innerHTML = '<p>No users found.</p>';
                    return;
                }
                
                let tableHTML = `
                    <table class="polls-table">
                        <thead>
                            <tr>
                                <th>User ID</th>
                                <th>Name</th>
                                <th>Username</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                users.slice(0, 20).forEach(user => {
                    tableHTML += `
                        <tr>
                            <td>${user.user_id}</td>
                            <td>${user.first_name} ${user.last_name || ''}</td>
                            <td>@${user.username || 'N/A'}</td>
                            <td class="${user.is_banned ? 'status-inactive' : 'status-active'}">
                                ${user.is_banned ? 'Banned' : 'Active'}
                            </td>
                        </tr>
                    `;
                });
                
                tableHTML += '</tbody></table>';
                usersTable.innerHTML = tableHTML;
            }
            
            function updateBackupStatus() {
                const backupStatus = document.getElementById('backup-status');
                backupStatus.innerHTML = 'Backup system running - Next backup in 30 minutes';
            }
            
            async function refreshData() {
                const [stats, polls, users] = await Promise.all([
                    fetchStats(),
                    fetchPolls(),
                    fetchUsers()
                ]);
                
                updateStats(stats);
                updatePolls(polls);
                updateUsers(users);
                updateBackupStatus();
            }
            
            // Initial load
            refreshData();
            
            // Auto refresh every 30 seconds
            setInterval(refreshData, 30000);
        </script>
    </body>
    </html>
    '''
    return html_template

@app.route('/api/stats')
def api_stats():
    try:
        # Get statistics from main database
        conn_main = sqlite3.connect("bot_main.db")
        cursor_main = conn_main.cursor()
        cursor_main.execute("SELECT COUNT(*) FROM users")
        total_users = cursor_main.fetchone()[0]
        cursor_main.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
        banned_users = cursor_main.fetchone()[0]
        conn_main.close()

        # Get statistics from vote database
        conn_vote = sqlite3.connect("vote_bot.db")
        cursor_vote = conn_vote.cursor()
        cursor_vote.execute("SELECT COUNT(*) FROM channel_polls WHERE is_active = 1")
        active_polls = cursor_vote.fetchone()[0]
        cursor_vote.execute("SELECT COUNT(*) FROM channel_votes")
        total_votes = cursor_vote.fetchone()[0]
        cursor_vote.execute("SELECT COUNT(DISTINCT user_id) FROM user_sessions")
        active_participants = cursor_vote.fetchone()[0]
        conn_vote.close()

        return jsonify({
            'total_users': total_users,
            'banned_users': banned_users,
            'active_polls': active_polls,
            'total_votes': total_votes,
            'active_participants': active_participants
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/polls')
def api_polls():
    try:
        conn = sqlite3.connect("vote_bot.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cp.channel_username, cp.creator_id, cp.current_poll_id, cp.is_active,
                   (SELECT COUNT(*) FROM channel_votes cv WHERE cv.channel_username = cp.channel_username) as vote_count
            FROM channel_polls cp
            ORDER BY cp.current_poll_id DESC
        """)
        polls = cursor.fetchall()
        conn.close()

        poll_list = []
        for poll in polls:
            poll_list.append({
                'channel_username': poll[0],
                'creator_id': poll[1],
                'current_poll_id': poll[2],
                'is_active': poll[3],
                'vote_count': poll[4]
            })

        return jsonify(poll_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users')
def api_users():
    try:
        conn = sqlite3.connect("bot_main.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, first_name, last_name, username, is_banned
            FROM users
            ORDER BY user_id DESC
            LIMIT 50
        """)
        users = cursor.fetchall()
        conn.close()

        user_list = []
        for user in users:
            user_list.append({
                'user_id': user[0],
                'first_name': user[1],
                'last_name': user[2],
                'username': user[3],
                'is_banned': user[4]
            })

        return jsonify(user_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not user:
        await update.message.reply_text("❌ Unable to process your request. User information is missing.")
        return

    if is_user_banned(user.id):
        await update.message.reply_text("❌ You are banned from using this command.")
        return
        
    # Register user if not already registered
    if not is_user_registered(user.id):
        add_user_to_db(user.id, user.first_name, user.last_name or "", user.username or "")
        await update.message.reply_text(f"✅ You are now registered, {user.first_name}!")

    # Handle both direct command (/start) and deep links (t.me/bot?start=channel)
    payload = None
    if update.message and update.message.text:
        parts = update.message.text.split(' ', 1)
        if len(parts) > 1:
            payload = parts[1]
    elif context.args:
        payload = context.args[0] if context.args else None

    if not payload:
        # No channel specified - show welcome message
        await update.message.reply_text(
            f"✅ Welcome back, {user.first_name}!\n"
            "Use a participation link to join a giveaway."
        )
        return

    channel_username = payload.strip('@')  # Remove @ if present
    
    # Check channel membership before proceeding with poll participation
    try:
        is_member = await check_user_membership(user.id, context.bot, CHANNEL_USERNAME)
        if not is_member:
            join_link = f"https://t.me/{CHANNEL_USERNAME}"
            keyboard = [[InlineKeyboardButton("Join Channel 🔗", url=join_link)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"❌ You must join @{CHANNEL_USERNAME} to participate.",
                reply_markup=reply_markup
            )
            return
    except Exception as e:
        logging.error(f"Error checking membership: {str(e)}")
        await update.message.reply_text("❌ Couldn't verify channel membership. Please try again.")
        return

    # Check if channel has active poll
    try:
        conn = sqlite3.connect("vote_bot.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT is_active, creator_id 
            FROM channel_polls 
            WHERE channel_username = ?
        """, (channel_username,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            await update.message.reply_text("❌ No poll found in this channel.")
            return
            
        is_active, creator_id = result
        
        if not is_active:
            await update.message.reply_text("❌ This poll is not active.")
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
        button = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Vote ⚡ ({vote_count})", callback_data=f"vote:{channel_username}")]
        ])

        response = (
            f"✅ New participant!\n\n"
            f"‣ *User* : {escape_markdown(user.first_name, version=2)} {escape_markdown(user.last_name or '', version=2)}\n"
            f"‣ *User-ID* : `{user.id}`\n"
            f"‣ *Username* : @{escape_markdown(user.username or 'None', version=2)}\n"
            f"‣ *Poll ID* : {escape_markdown(str(poll_id), version=2)}\n"
            f"‣ *Note* : Only channel subscribers can vote.\n\n"
            f"×× Created by - [@{CHANNEL_USERNAME}](https://t.me/{CHANNEL_USERNAME})"
        )

        # Try to send to channel
        try:
            if os.path.exists(img_path):
                await context.bot.send_photo(
                    chat_id=f"@{channel_username}",
                    caption=response,
                    photo=open(img_path, "rb"),
                    reply_markup=button,
                    parse_mode="MarkdownV2",
                )
            else:
                await context.bot.send_message(
                    chat_id=f"@{channel_username}",
                    text=response,
                    reply_markup=button,
                    parse_mode="MarkdownV2",
                    disable_web_page_preview=True
                )
        except Exception as e:
            logging.error(f"Error sending to channel @{channel_username}: {str(e)}")
            # Remove the participation since we couldn't notify the channel
            remove_user_channel_session(user.id, channel_username)
            await update.message.reply_text("❌ Couldn't notify the channel. Please try again later.")
            return
            
        await update.message.reply_text("✅ You have successfully participated in the voting!")
        
    except Exception as e:
        logging.error(f"Error in start command: {str(e)}")
        await update.message.reply_text("❌ An error occurred. Please try again later.")
        
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
        
import io
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send complete application logs since startup"""
    if not is_special_user(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to view logs.")
        return

    # Create a StringIO buffer to capture logs
    log_buffer = io.StringIO()
    
    # Get all existing log handlers
    root_logger = logging.getLogger()
    handlers = root_logger.handlers
    
    try:
        # Add our StringIO handler temporarily
        buffer_handler = logging.StreamHandler(log_buffer)
        buffer_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        root_logger.addHandler(buffer_handler)
        
        # Force flush all existing logs to our buffer
        for handler in handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
        
        # Get the log content
        log_content = log_buffer.getvalue()
        
        # Remove our temporary handler
        root_logger.removeHandler(buffer_handler)
        
        if not log_content:
            await update.message.reply_text("No logs available yet.")
            return
            
        # Clean the logs (remove debug/error if needed)
        cleaned_logs = []
        for line in log_content.split('\n'):
            if 'DEBUG' not in line and 'ERROR' not in line:
                cleaned_logs.append(line)
        
        final_logs = '\n'.join(cleaned_logs)
        
        # Create a clean header
        log_header = (
            f"📜 Application Logs\n"
            f"🕒 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📊 Total Lines: {len(cleaned_logs)}\n\n"
        )
        
        full_content = log_header + final_logs
        
        # Determine whether to send as text or document
        if len(full_content) <= 4000:  # Telegram message limit
            await update.message.reply_text(f"<pre>{full_content}</pre>", 
                                          parse_mode='HTML')
        else:
            # Create in-memory file
            with io.BytesIO() as bio:
                bio.write(full_content.encode('utf-8'))
                bio.seek(0)
                
                await update.message.reply_document(
                    document=bio,
                    filename=f"bot_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    caption="Full application logs"
                )
                
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to get logs: {str(e)}")
    finally:
        # Ensure we clean up our handler
        if 'buffer_handler' in locals():
            root_logger.removeHandler(buffer_handler)
        log_buffer.close()
# Add this to your command handlers:
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
            user_name = escape_markdown(user_name, version=2)
            top_message += f"🎖 *{i+1}\\. {user_name}* \\(ID: {poll_id}\\)\n"
        
        await update.message.reply_text(top_message, parse_mode="MarkdownV2")
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
            user_name = escape_markdown(user_name, version=2)
            top_message += f"🎖 *{i+1}\\. {user_name}* \\(ID: {poll_id}\\)\n"
        
        await update.message.reply_text(top_message, parse_mode="MarkdownV2")

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
                await update.message.reply_text(message, parse_mode="MarkdownV2")
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

def safe_html_escape(text):
    """
    Safely escape HTML content while preserving markdown-style links
    """
    if not text:
        return ""
    
    # First escape HTML entities
    escaped_text = html.escape(text)
    
    return escaped_text

def fix_html_links(text):
    """
    Convert HTML links to plain text format for better display
    """
    if not text:
        return ""
    
    # Convert <a href="url">text</a> to text (url)
    link_pattern = re.compile(r'<a href="([^"]*)"[^>]*>([^<]*)</a>')
    fixed_text = link_pattern.sub(r'\2 (\1)', text)
    
    return fixed_text

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
                # Safely escape caption before applying strikethrough formatting
                escaped_caption = safe_html_escape(message.caption)
                fixed_caption = fix_html_links(escaped_caption)  # Fix broken links
                updated_caption = f"<s>{fixed_caption}</s>\n\n<b>THIS POLL HAS BEEN DISQUALIFIED FROM THE GIVEAWAY</b>"

                await context.bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_channel_id,
                    caption=updated_caption,
                    parse_mode="HTML",
                    reply_markup=None  # Remove inline buttons
                )
            else:
                # Safely escape text before applying strikethrough formatting
                escaped_text = safe_html_escape(message.text)
                fixed_text = fix_html_links(escaped_text)  # Fix broken links
                updated_text = f"<s>{fixed_text}</s>\n\n<b>THIS POLL HAS BEEN DISQUALIFIED FROM THE GIVEAWAY</b>"

                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_channel_id,
                    text=updated_text,
                    parse_mode="HTML",
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
            channel_escaped = escape_markdown(channel, version=2)
            
            creator_message = (
                f"👑 *Your Created Poll:*\n"
                f"⭐ *Channel:* @{channel_escaped}\n"
                f"⭐ *Total Votes:* {vote_count}\n"
                f"⭐ *Status:* Creator\n"
            )
            await update.message.reply_text(creator_message, parse_mode="MarkdownV2")
    
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
            
            channel_escaped = escape_markdown(channel, version=2)
            
            participant_message = (
                f"🎯 *Participating In:*\n"
                f"⭐ *Channel:* @{channel_escaped}\n"
                f"⭐ *Total Votes:* {vote_count}\n"
                f"⭐ *Your Vote Status:* {'✅ Voted' if has_voted else '❌ Not Voted'}\n"
            )
            await update.message.reply_text(participant_message, parse_mode="MarkdownV2")
    
    # Show summary
    total_sessions = len(active_channels) + len(created_channels)
    summary_message = (
        f"📊 *Summary:*\n"
        f"📝 *Created Polls:* {len(created_channels)}\n"
        f"🎯 *Participating In:* {len(active_channels)}\n"
        f"📈 *Total Active Sessions:* {total_sessions}/6 \\(5 max participating \\+ 1 created\\)\n"
    )
    await update.message.reply_text(summary_message, parse_mode="MarkdownV2")

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

    await update.message.reply_text(user_message, parse_mode="MarkdownV2")

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
    
    # Initialize backup system
    initialize_backup_system()
    
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
    application.add_handler(CommandHandler("logs", logs_command))
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
    
    # Start Flask web interface in a separate thread
    def run_flask():
        app.run(host='0.0.0.0', port=5000, debug=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Register cleanup function

    # Start polling
    print("🚀 Bot started successfully!")
    print("🌐 Web dashboard available at http://localhost:5000")
    application.run_polling()
