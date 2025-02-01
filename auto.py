import os
import requests
import time
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = "7469236370:AAH0_dD-7ZjdbepID5z2YhKjY_FpSX6K6Qg"

# GitHub Credentials
GIT_TOKEN = os.getenv("GH_TOKEN")  # Heroku environment variable for GitHub token
GIT_USERNAME = "Votingbotm"
GIT_REPO = "Vote"
GIT_API_URL = "https://api.github.com"
GIT_BRANCH = "main"

if not GIT_TOKEN:
    raise ValueError("GitHub token is not set in environment variables!")

# Create a commit
def create_commit():
    url = f"{GIT_API_URL}/repos/{GIT_USERNAME}/{GIT_REPO}/branches/{GIT_BRANCH}"
    headers = {"Authorization": f"token {GIT_TOKEN}"}
    
    # Fetch branch details
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ GitHub API Error: {response.status_code} - {response.json()}")
        return None

    branch_data = response.json()
    commit_sha = branch_data.get("commit", {}).get("sha")
    
    if not commit_sha:
        print("⚠ No commit SHA found! Check if the branch exists.")
        return None

    # Get the latest commit details to fetch the correct tree SHA
    commit_url = f"{GIT_API_URL}/repos/{GIT_USERNAME}/{GIT_REPO}/git/commits/{commit_sha}"
    commit_response = requests.get(commit_url, headers=headers)
    
    if commit_response.status_code != 200:
        print(f"❌ Error fetching commit details: {commit_response.json()}")
        return None

    commit_data = commit_response.json()
    tree_sha = commit_data.get("tree", {}).get("sha")

    if not tree_sha:
        print("⚠ No tree SHA found! Cannot proceed.")
        return None

    # Create the commit with the correct tree SHA
    commit_message = f"Auto commit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    commit_data = {
        "message": commit_message,
        "tree": tree_sha,  # Use the correct tree SHA
        "parents": [commit_sha]
    }

    commit_url = f"{GIT_API_URL}/repos/{GIT_USERNAME}/{GIT_REPO}/git/commits"
    commit_response = requests.post(commit_url, json=commit_data, headers=headers)

    if commit_response.status_code != 201:
        print(f"❌ Commit creation failed: {commit_response.json()}")
        return None

    return commit_response.json()

# Auto-push function (Starts after 1 hour)
def auto_push():
    print("Waiting for 1 hour before starting the first commit...")
    time.sleep(3600)  # Wait for 1 hour before the first commit

    while True:
        push_response = push_commit()
        if push_response:
            print(f"✅ Changes pushed: {push_response}")
        else:
            print("⚠ No changes pushed due to an error.")
        time.sleep(3600)  # Push every 1 hour after the first commit

# Telegram command to manually commit changes
async def commit_command(update: Update, context: CallbackContext):
    await update.message.reply_text("⏳ Pushing current changes to GitHub...")

    push_response = push_commit()
    if push_response:
        await update.message.reply_text("✅ Changes successfully pushed to GitHub!")
    else:
        await update.message.reply_text("❌ Failed to push changes. Check logs for details.")

# Setup Telegram bot
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("commit", commit_command))

# Start auto push in a separate thread
import threading
threading.Thread(target=auto_push, daemon=True).start()

# Run the bot
app.run_polling()
