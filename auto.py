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

# Get the script's directory (same as repo directory
# GitHub repository detail
GIT_API_URL = "https://api.github.com"
GIT_BRANCH = "main"  # Modify if you're using another branch

# Prepare commit data
def create_commit():
    # Get the latest commit sha
    url = f"{GIT_API_URL}/repos/{GIT_USERNAME}/{GIT_REPO}/branches/{GIT_BRANCH}"
    headers = {"Authorization": f"token {GIT_TOKEN}"}
    response = requests.get(url, headers=headers)
    branch_data = response.json()

    commit_sha = branch_data["commit"]["sha"]

    # Create new commit object
    commit_message = f"Auto commit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    commit_data = {
        "message": commit_message,
        "tree": commit_sha,
        "parents": [commit_sha]
    }

    # Create a commit via GitHub API
    commit_url = f"{GIT_API_URL}/repos/{GIT_USERNAME}/{GIT_REPO}/git/commits"
    commit_response = requests.post(commit_url, json=commit_data, headers=headers)
    
    return commit_response.json()

# Push commit to GitHub
def push_commit():
    # Create the commit
    commit_response = create_commit()
    commit_sha = commit_response["sha"]

    # Push the commit to the branch
    push_data = {
        "sha": commit_sha
    }

    push_url = f"{GIT_API_URL}/repos/{GIT_USERNAME}/{GIT_REPO}/git/refs/heads/{GIT_BRANCH}"
    push_response = requests.patch(push_url, json=push_data, headers={"Authorization": f"token {GIT_TOKEN}"})

    return push_response.json()

# Push changes every 1 hour
def auto_push():
    while True:
        # Push changes
        push_response = push_commit()
        print(f"Changes pushed: {push_response}")
        time.sleep(3600)  # Push every 1 hour

if __name__ == "__main__":
    auto_push()
    
