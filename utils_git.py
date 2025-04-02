import os
import subprocess
from git import Repo
import shutil
import requests

# Parse GitHub URL
def parse_github_url(github_url: str) -> tuple[str, str]:
    """
    Parse GitHub repository URL to extract owner and repo name.

    Args:
        github_url (str): GitHub repository URL in any of these formats:
            - https://github.com/owner/repo
            - git@github.com:owner/repo.git
            - owner/repo

    Returns:
        tuple[str, str]: Repository owner and name
    """
    # Remove .git extension if present
    github_url = github_url.replace(".git", "")

    # Handle SSH URL format
    if github_url.startswith("git@"):
        github_url = github_url.split("git@github.com:")[1]

    # Handle HTTPS URL format
    elif github_url.startswith(("http://", "https://")):
        parts = github_url.split("github.com/")
        if len(parts) < 2:
            raise ValueError("Invalid GitHub URL format. URL must contain 'github.com/'")
        github_url = parts[1]

    # Split into owner and repo
    try:
        owner, repo = github_url.split("/")
        return owner.strip(), repo.strip()
    except ValueError:
        raise ValueError(
            "Invalid GitHub URL format. Expected format: owner/repo or full GitHub URL"
        )

def is_repo_cloned(target_path: str, repo_name: str) -> bool:
    """
    Check if repository is already cloned at the target path.
    
    Args:
        target_path (str): Base path where repos are cloned
        repo_name (str): Name of the repository
        
    Returns:
        bool: True if repo exists and is a git repo, False otherwise
    """
    repo_path = os.path.join(target_path, repo_name)
    try:
        Repo(repo_path)
        return True
    except:
        return False

def remove_repo_if_exists(target_path: str, repo: str) -> None:
    """
    Remove repository directory if it exists.
    
    Args:
        target_path (str): Base path where repos are cloned
        repo (str): Name of the repository
    """
    repo_path = os.path.join(target_path, repo)
    if os.path.exists(repo_path):
        try:
            shutil.rmtree(repo_path)
        except Exception as e:
            raise ValueError(f"Failed to remove existing repository: {str(e)}")

# Clone the repository
def clone_github_repo(github_url: str, target_path: str, access_token: str = None) -> str:
    """
    Clone a GitHub repository to the specified path.

    Args:
        github_url (str): GitHub repository URL
        target_path (str): Local path where to clone the repository
        access_token (str, optional): GitHub personal access token for private repos

    Returns:
        str: Path to the cloned repository
    """
    try:
        # Parse the GitHub URL to get owner and repo
        owner, repo = parse_github_url(github_url)
        
        # Create clone URL with token if provided
        if access_token:
            clone_url = f"https://{access_token}@github.com/{owner}/{repo}.git"
        else:
            clone_url = f"https://github.com/{owner}/{repo}.git"
        
        # Create target directory if it doesn't exist
        os.makedirs(target_path, exist_ok=True)
        
        # Clone the repository
        repo_path = os.path.join(target_path, repo)
        Repo.clone_from(clone_url, repo_path)
        
        return repo_path
        
    except Exception as e:
        raise ValueError(f"Failed to clone repository: {str(e)}")

# Check if branch exists
def branch_exists(branch_name: str):
    subprocess.run(["git", "fetch"], check=True)
    branches = subprocess.run(["git", "branch", "-r"], capture_output=True, text=True).stdout
    return f"origin/{branch_name}" in branches

# Create a new branch if not exists
def create_branch(branch_name: str):
    if not branch_exists(branch_name):
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)

# Push changes to branch
def commit_and_push_changes(branch_name: str):
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Upgrade dependencies"], check=True)
    subprocess.run(["git", "push", "origin", branch_name], check=True)

# Create a pull request
def create_pull_request(owner: str, repo: str, token: str, branch_name: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {"Authorization": f"token {token}"}
    data = {
        "title": "Dependency Upgrade PR",
        "head": branch_name,
        "base": "main",
        "body": "This PR upgrades dependencies in pom.xml"
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        print("Pull request created successfully!")
    else:
        print(f"Failed to create PR: {response.text}")
