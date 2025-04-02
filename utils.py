import requests
import pandas as pd
import streamlit as st
import concurrent.futures
import xml.etree.ElementTree as ET
import subprocess
import os
from git import Repo


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

# Parse pom.xml file
def parse_pom(pom_file):
    tree = ET.parse(pom_file)
    root = tree.getroot()

    ns = {"mvn": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}

    dependencies = {}
    for dep in root.findall("mvn:dependencies/mvn:dependency", ns):
        group_id = dep.find("mvn:groupId", ns)
        artifact_id = dep.find("mvn:artifactId", ns)
        version = dep.find("mvn:version", ns)

        if group_id is not None and artifact_id is not None:
            dependencies[artifact_id.text] = {
                "group_id": group_id.text,
                "current_version": version.text if version is not None else "LATEST",
            }

    return dependencies

# Fetch latest version from Maven Central
def get_latest_version(group_id, artifact_id):
    url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/maven-metadata.xml"

    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            latest_version = root.find("./versioning/latest")
            return latest_version.text if latest_version is not None else "UNKNOWN"
    except requests.RequestException:
        return "UNKNOWN"


# Fetch latest versions in parallel
def fetch_latest_versions(dependencies):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(get_latest_version, details["group_id"], artifact): artifact
            for artifact, details in dependencies.items()
        }
        for future in concurrent.futures.as_completed(futures):
            artifact = futures[future]
            dependencies[artifact]["latest_version"] = future.result()

    return dependencies

# Convert dependencies to DataFrame and add index
def dependencies_to_dataframe(dependencies):
    df = pd.DataFrame(dependencies).T.reset_index()
    df.index += 1  # Start index from 1
    df.rename(columns={"index": "Artifact"}, inplace=True)
    return df


# Generate Analysis Report
def generate_analysis_report(dependencies, insights):
    with st.expander("Analysis Report", expanded=True):

        report_lines = []
        for i, (artifact, analysis) in enumerate(
            insights.items(), start=1
        ):
            st.markdown(
                f"### {i}. {artifact} ({dependencies[artifact]['current_version']} → {dependencies[artifact]['latest_version']})"
            )
            st.write(f"**Severity Level:** {analysis['severity_level']}")
            st.write(f"**Security Changes:** {analysis['security_changes']}")
            st.write(f"**Deprecated Methods:** {analysis['deprecated_methods']}")
            st.write(f"**Code Changes:** {analysis['code_changes']}")

            report_lines.append(
                f"{i}. {artifact} ({dependencies[artifact]['current_version']} → {dependencies[artifact]['latest_version']})"
            )
            report_lines.append(f"Severity Level: {analysis['severity_level']}")
            report_lines.append(f"Security Changes: {analysis['security_changes']}")
            report_lines.append(f"Deprecated Methods: {analysis['deprecated_methods']}")
            report_lines.append(f"Code Changes: {analysis['code_changes']}")
            report_lines.append("-" * 50)

            if analysis["sources"]:
                st.write("**Related Articles:**")
                for j, url in enumerate(analysis["sources"], start=1):
                    st.markdown(f"- [Source {j}]({url})")
                    report_lines.append(f"Source {j}: {url}")

        report_text = "\n".join(report_lines)
        st.download_button(
            "Download Analysis Report", report_text, "analysis_report.txt", "text/plain"
        )


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

def file_exists(file_path: str) -> bool:
    """
    Check if a file exists in the repository.

    Args:
        file_path (str): Path to the file to check

    Returns:
        bool: True if file exists, False otherwise
    """
    try:
        return os.path.isfile(file_path)
    except Exception as e:
        print(f"Error checking file existence: {str(e)}")
        return False