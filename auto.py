import os
import schedule
import time
import subprocess
from datetime import datetime

# Securely retrieve the GitHub token from environment variables
GIT_TOKEN = "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"
GIT_USERNAME = "Votingbotm"
GIT_REPO = "Vote"

# Get the script directory (same as repo directory)
import os
import schedule
import time
import subprocess
from datetime import datetime
import threading

# 🔥 
# Get the script's directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "main.py")

def log_message(message):
    """Prints logs with timestamps"""
    print(f"[{datetime.now()}] {message}")

def run_main():
    """Continuously runs main.py and logs output"""
    while True:
        if os.path.exists(MAIN_SCRIPT):
            log_message("Starting main.py...")
            process = subprocess.Popen(["python3", MAIN_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
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
    """Commit and push changes using a GitHub token and log output"""
    if not GIT_TOKEN:
        log_message("Error: GitHub token is missing. Set it using 'export GITHUB_TOKEN=your_token'")
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
        log_message(f"Error: {e}")

# Run main.py in a separate thread
threading.Thread(target=run_main, daemon=True).start()

# Schedule auto Git push every hour
schedule.every(1).hours.do(git_push)

log_message(f"Git auto-push script running in {SCRIPT_DIR} with main.py...")

# Keep the script running
while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute
