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

# Get the script's directory (same as repo directory)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

def log_message(message):
    """Logs messages"""
    print(f"[{datetime.now()}] {message}")

def git_push():
    """Commit and push changes to GitHub"""
    if not GIT_TOKEN:
        log_message("Error: GitHub token is missing.")
        return

    try:
        # Add changes to git
        log_message("Checking for changes in the repository...")
        os.system("git add .")

        # Check if there are any changes to commit
        commit_message = f"Auto commit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)

        if result.returncode != 0:  # If there are changes
            log_message(f"Changes detected, committing and pushing...")
            os.system(f'git commit -m "{commit_message}"')
            os.system("git push origin main")  # Change 'main' if using another branch
            log_message(f"Changes pushed successfully to {GIT_REPO}!")
        else:
            log_message("No changes detected, skipping commit and push.")

    except Exception as e:
        log_message(f"Error: {e}")

# Run git_push every hour
while True:
    git_push()
    time.sleep(3600)  # Wait for 1 hour before running again
