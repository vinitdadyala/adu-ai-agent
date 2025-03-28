import os
import requests
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