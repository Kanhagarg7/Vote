import os
import requests
from datetime import datetime
import time

# Retrieve the GitHub token and other details from environment variables
GIT_TOKEN = os.getenv('GH_TOKEN')  # Heroku environment variable for GitHub token
GIT_USERNAME = "Votingbotm"  # Your GitHub username
GIT_REPO = "Vote"  # Your GitHub repository name
GIT_API_URL = "https://api.github.com"
GIT_BRANCH = "main"  # Your Git branch (default 'main')

# Ensure the token is available
if not GIT_TOKEN:
    raise ValueError("GitHub token is not set in environment variables!")

# Prepare commit data
def create_commit():
    # Get the latest commit sha
    url = f"{GIT_API_URL}/repos/{GIT_USERNAME}/{GIT_REPO}/branches/{GIT_BRANCH}"
    headers = {"Authorization": f"token {GIT_TOKEN}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 401:
        print("❌ GitHub API Error: Bad credentials (401). Check your token.")
        return None
    elif response.status_code != 200:
        print(f"❌ GitHub API Error: {response.status_code} - {response.json()}")
        return None

    branch_data = response.json()
    commit_sha = branch_data.get("commit", {}).get("sha")

    if not commit_sha:
        print("⚠ No commit SHA found! Check if the branch exists.")
        return None

    commit_message = f"Auto commit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    commit_data = {
        "message": commit_message,
        "tree": commit_sha,
        "parents": [commit_sha]
    }

    # Create a commit via GitHub API
    commit_url = f"{GIT_API_URL}/repos/{GIT_USERNAME}/{GIT_REPO}/git/commits"
    commit_response = requests.post(commit_url, json=commit_data, headers=headers)

    if commit_response.status_code != 201:
        print(f"❌ Commit creation failed: {commit_response.json()}")
        return None

    return commit_response.json()

# Push commit to GitHub
def push_commit():
    # Create the commit
    commit_response = create_commit()
    if commit_response is None:
        return None

    commit_sha = commit_response["sha"]

    # Push the commit to the branch
    push_data = {
        "sha": commit_sha
    }

    push_url = f"{GIT_API_URL}/repos/{GIT_USERNAME}/{GIT_REPO}/git/refs/heads/{GIT_BRANCH}"
    push_response = requests.patch(push_url, json=push_data, headers={"Authorization": f"token {GIT_TOKEN}"})

    return push_response.json()

# Push changes every 1 hour, but start after 1 hour of running the script
def auto_push():
    print("Waiting for 1 hour before starting the first commit...")
    time.sleep(3600)  # Wait for 1 hour before the first commit

    while True:
        # Push changes every 1 hour
        push_response = push_commit()
        if push_response:
            print(f"Changes pushed: {push_response}")
        else:
            print("⚠ No changes pushed due to an error.")
        time.sleep(3600)  # Push every 1 hour after the first one

if __name__ == "__main__":
    auto_push()
    
