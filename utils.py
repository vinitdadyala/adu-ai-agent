import requests
import pandas as pd
import streamlit as st
import concurrent.futures
import xml.etree.ElementTree as ET

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

# Fetch pom.xml from GitHub repository
def fetch_github_file(owner: str, repo: str, path: str, access_token: str, branch: str = "main") -> str:
    """
    Fetch a file from GitHub repository using Personal Access Token.

    Args:
        owner (str): GitHub repository owner/organization
        repo (str): Repository name
        path (str): Path to file in the repository
        branch (str): Branch name (default: main)
        access_token (str): Personal Access Token with repo scope

    Returns:
        str: Content of the file
    """
    # Construct raw content URL
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"

    # Set up headers with token
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3.raw",
    }

    # Make request
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.text
    else:
        raise Exception(
            f"Failed to fetch file. Status: {response.status_code}\nMessage: {response.text}"
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


import os
import subprocess
import requests

# Clone the repository
def clone_repo(owner: str, repo: str):
    """
    Fetch a file from GitHub repository using Personal Access Token.

    Args:
        owner (str): GitHub repository owner/organization
        repo (str): Repository name
    """
    repo_url = f"git@github.com:{owner}/{repo}.git"
    subprocess.run(["git", "clone", repo_url], check=True)

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
