import os
import time
import requests
from datetime import datetime

# GitHub Credentials
GIT_TOKEN = os.getenv('GH_TOKEN')
GIT_USERNAME = "Votingbotm"
GIT_REPO = "Vote"
GIT_BRANCH = "main"
GIT_API_URL = "https://api.github.com"

# Headers for GitHub API requests
HEADERS = {"Authorization": f"token {GIT_TOKEN}", "Accept": "application/vnd.github.v3+json"}

def get_latest_commit():
    """Fetch the latest commit SHA and tree SHA from GitHub"""
    url = f"{GIT_API_URL}/repos/{GIT_USERNAME}/{GIT_REPO}/branches/{GIT_BRANCH}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"❌ GitHub API Error: {response.status_code} - {response.text}")
        return None, None
    
    data = response.json()

    if "commit" not in data:
        print("❌ Error: No 'commit' key in response! Full response:", data)
        return None, None

    commit_sha = data["commit"]["sha"]
    tree_sha = data["commit"]["commit"]["tree"]["sha"]
    return commit_sha, tree_sha

def create_commit(parent_commit_sha, tree_sha):
    """Create a new commit on GitHub"""
    commit_message = f"Auto commit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    commit_data = {
        "message": commit_message,
        "tree": tree_sha,
        "parents": [parent_commit_sha]
    }
    
    commit_url = f"{GIT_API_URL}/repos/{GIT_USERNAME}/{GIT_REPO}/git/commits"
    response = requests.post(commit_url, json=commit_data, headers=HEADERS)

    if response.status_code != 201:
        print(f"❌ Commit creation failed! {response.status_code} - {response.text}")
        return None

    return response.json().get("sha")

def push_commit(commit_sha):
    """Push the new commit to the repository"""
    push_data = {"sha": commit_sha, "force": True}
    push_url = f"{GIT_API_URL}/repos/{GIT_USERNAME}/{GIT_REPO}/git/refs/heads/{GIT_BRANCH}"
    
    response = requests.patch(push_url, json=push_data, headers=HEADERS)

    if response.status_code not in [200, 201]:
        print(f"❌ Push failed! {response.status_code} - {response.text}")
        return None

    return response.json()

def auto_push():
    """Automatically commit and push every 1 hour"""
    while True:
        commit_sha, tree_sha = get_latest_commit()
        if not commit_sha or not tree_sha:
            print("⚠ Skipping commit due to API error.")
            time.sleep(3600)
            continue

        new_commit_sha = create_commit(commit_sha, tree_sha)
        if not new_commit_sha:
            print("⚠ Commit creation failed. Skipping push.")
            time.sleep(3600)
            continue

        push_response = push_commit(new_commit_sha)
        if push_response:
            print(f"✅ Changes pushed successfully: {push_response}")
        else:
            print("⚠ Push failed. Will retry in 1 hour.")

        time.sleep(3600)  # Wait for 1 hour before next push

if __name__ == "__main__":
    auto_push()
            
