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
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_main():
    """Run main.py"""
    main_script = os.path.join(SCRIPT_DIR, "main.py")
    if os.path.exists(main_script):
        print(f"[{datetime.now()}] Running main.py...")
        subprocess.run(["python3", main_script], check=True)
    else:
        print(f"[{datetime.now()}] main.py not found in {SCRIPT_DIR}")

def git_push():
    """Commit and push changes using a GitHub token"""
    if not GIT_TOKEN:
        print("Error: GitHub token is missing. Set it using 'export GITHUB_TOKEN=your_token'")
        return

    try:
        os.chdir(SCRIPT_DIR)
        remote_url = f"https://{GIT_USERNAME}:{GIT_TOKEN}@github.com/{GIT_USERNAME}/{GIT_REPO}.git"
        os.system("git remote set-url origin " + remote_url)
        os.system("git add .")
        commit_message = f"Auto commit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        os.system(f'git commit -m "{commit_message}"')
        os.system("git push origin main")  # Change 'main' if using another branch
        print(f"[{datetime.now()}] Changes pushed from {SCRIPT_DIR} successfully!")
    except Exception as e:
        print(f"Error: {e}")

# Schedule tasks
schedule.every(1).hours.do(git_push)  
schedule.every(1).hours.do(run_main)  

print(f"Git auto-push script running in {SCRIPT_DIR}...")

while True:
    schedule.run_pending()
    time.sleep(60)  
