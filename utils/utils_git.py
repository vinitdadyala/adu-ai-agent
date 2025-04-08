import datetime
import os
import subprocess
import time
from git import Repo
import shutil
import requests
import stat
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


def handle_remove_readonly(func, path, exc):
    # Called when rmtree hits a permission error
    os.chmod(path, os.stat.S_IWRITE)
    func(path)

def remove_repo_if_exists(target_path: str, repo: str) -> None:
    repo_path = os.path.join(target_path, repo)
    if os.path.exists(repo_path):
        try:
            # Attempt to remove it directly
            shutil.rmtree(repo_path, onerror=handle_remove_readonly)
        except Exception as e:
            print(f"⚠️ Direct delete failed. Trying rename workaround: {e}")
            # Fallback: Rename the folder so it's out of the way
            backup_path = f"{repo_path}_old_{int(time.time())}"
            try:
                os.rename(repo_path, backup_path)
                print(f"📁 Renamed locked repo folder to: {backup_path}")
            except Exception as rename_error:
                raise ValueError(f"❌ Failed to rename locked repo folder: {rename_error}")

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

        remove_repo_if_exists(target_path, repo)
        
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


def branch_exists(branch_name: str) -> bool:
    """
    Check if a remote branch exists.

    Args:
        branch_name (str): Name of the branch to check

    Returns:
        bool: True if branch exists, False otherwise

    Raises:
        subprocess.CalledProcessError: If git command fails
    """
    subprocess.run(["git", "fetch"], check=True)
    branches = subprocess.run(["git", "branch", "-r"], capture_output=True, text=True).stdout
    return f"origin/{branch_name}" in branches


def create_branch(branch_name: str) -> None:
    """
    Create a new git branch and push it to remote if it doesn't exist.

    Args:
        branch_name (str): Name of the branch to create

    Raises:
        subprocess.CalledProcessError: If git command fails
    """
    if not branch_exists(branch_name):
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)


def generate_branch_name(base_name: str) -> str:
    """
    Generate a unique branch name with timestamp.

    Args:
        base_name (str): Base name for the branch (e.g., 'feature/update')

    Returns:
        str: Branch name with timestamp (e.g., 'feature/update_20240402_103000')
    """
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{base_name}_{timestamp}"


def commit_and_push_changes(branch_name: str) -> None:
    """
    Stage, commit, and push changes to the specified branch.

    Args:
        branch_name (str): Name of the branch to push changes to

    Raises:
        subprocess.CalledProcessError: If any git command fails
    """
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Upgrade dependencies"], check=True)
    subprocess.run(["git", "push", "origin", branch_name], check=True)


# Create a pull request
def create_pull_request(owner: str, repo: str, token: str, branch_name: str, base_branch="main") -> str:
    """
    Create a pull request and return its URL.

    Args:
        owner (str): Repository owner
        repo (str): Repository name
        token (str): GitHub access token
        branch_name (str): Branch name to create PR from

    Returns:
        str: URL of the created pull request or empty string if creation fails
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "title": "Dependency Upgrade PR",
        "head": branch_name,
        "base": base_branch,
        "body": "This PR upgrades dependencies in pom.xml"
    }
    
    # try:
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    
    pr_data = response.json()
    pr_url = pr_data.get("html_url")
    
    if pr_url:
        return pr_url
       
    # except requests.exceptions.RequestException as e:
    #     return f"Failed to create PR: {str(e)}"
