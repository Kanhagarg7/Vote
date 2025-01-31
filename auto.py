import os
import subprocess
import time
from datetime import datetime
import requests
import schedule
import threading

# Retrieve credentials and tokens from environment variables
GIT_TOKEN = "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"
GIT_USERNAME = "Votingbotm"
GIT_REPO = "Vote"

# Retrieve bot token and channel ID from environment variables
TOKEN = "7469236370:AAH0_dD-7ZjdbepID5z2YhKjY_FpSX6K6Qg" # Replace 'your_bot_api_key' with default or use environment variable
CHANNEL_ID = "-1002291896465"# Replace with your channel ID or use environment variable
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
# Get the script directory (same as repo directory)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "main.py")

def log_message(message):
    """Send message to Telegram and print log"""
    print(f"[{datetime.now()}] {message}")
    
    # Send the log to the Telegram channel
    try:
        response = requests.post(
            TELEGRAM_API_URL,
            data={"chat_id": CHANNEL_ID, "text": message}
        )
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending message to Telegram: {e}")

def run_main():
    """Continuously run main.py and log output"""
    while True:
        if os.path.exists(MAIN_SCRIPT):
            log_message("Starting main.py...")
            process = subprocess.Popen(
                ["python3", MAIN_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # Log main.py output in real-time
            for line in process.stdout:
                log_message(f"[main.py] {line.strip()}")

            for line in process.stderr:
                log_message(f"[main.py ERROR] {line.strip()}")

            process.wait()
            log_message("main.py stopped, restarting in 5 seconds...")

        else:
            log_message("main.py not found in repository.")
        
        time.sleep(5)  # Restart after 5 seconds

def git_push():
    """Commit and push changes to GitHub"""
    if not GIT_TOKEN:
        log_message("Error: GitHub token is missing.")
        return

    try:
        os.chdir(SCRIPT_DIR)
        remote_url = f"https://{GIT_USERNAME}:{GIT_TOKEN}@github.com/{GIT_USERNAME}/{GIT_REPO}.git"
        os.system("git remote set-url origin " + remote_url)
        
        log_message("Adding changes to Git...")
        os.system("git add .")
        
        commit_message = f"Auto commit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        os.system(f'git commit -m "{commit_message}"')

        log_message("Pushing to GitHub...")
        os.system("git push origin main")  # Change 'main' if using another branch
        
        log_message("Changes pushed successfully!")

    except Exception as e:
        log_message(f"Error during Git push: {e}")

# Schedule auto Git push every hour
schedule.every(1).hours.do(git_push)

# Run main.py in a separate thread
if __name__ == "__main__":
    # Start the main.py process in a separate threa
    
    # Keep the script running and execute scheduled tasks
    log_message(f"Git auto-push script running in {SCRIPT_DIR} with main.py...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute
