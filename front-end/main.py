import os
import json
import dspy
import pandas as pd
import xml.etree.ElementTree as ET
import requests
import streamlit as st
from dotenv import load_dotenv
import concurrent.futures
from tavily import TavilyClient  

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY not found in environment variables")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY not found in environment variables")

# Initialize DSPy and Groq LLM
def get_dspy_analyzer():
    if "analyze_dependency" not in st.session_state:
        llm = dspy.LM(model="groq/llama3-70b-8192", api_key=groq_api_key)
        dspy.settings.configure(lm=llm)
        st.session_state["analyze_dependency"] = dspy.ChainOfThought(DependencyAnalysis)

    return st.session_state["analyze_dependency"]

search_client = TavilyClient(api_key=tavily_api_key)

# DSPy Signature for Dependency Analysis
class DependencyAnalysis(dspy.Signature):
    web_insights = dspy.InputField()
    security_changes = dspy.OutputField(desc="List of security risks mitigated or introduced")
    deprecated_methods = dspy.OutputField(desc="List of deprecated methods or breaking changes")
    code_changes = dspy.OutputField(desc="List of probable code modifications needed")
    severity_level = dspy.OutputField(desc="Classify impact as High, Moderate, or Low")

def find_pom_file(project_directory):
    for root, dirs, files in os.walk(project_directory):
        if "pom.xml" in files:
            return os.path.join(root, "pom.xml")
    return None

# Parse pom.xml file
def parse_pom(pom_file):
    tree = ET.parse(pom_file)
    root = tree.getroot()

    ns = {'mvn': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}

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

# Fetch web insights using Tavily
def fetch_web_insights(artifact, latest_version, current_version):
    query = (
        f"Classify the security impact of upgrading {artifact} from {current_version} to {latest_version} "
        f"as High, Moderate, or Low. Provide detailed information on security changes, deprecated methods, and code modifications."
    )
    try:
        response = search_client.search(query, max_results=6, search_depth="basic")

        if response and response["results"]:
            insights = "\n".join([r["content"] for r in response["results"]])
            sources = [r["url"] for r in response["results"][:2]]
            return insights, sources
    except Exception:
        return "No insights available.", ["No sources found."]

# Analyze dependencies using DSPy
def analyze_dependencies(dependencies):
    insights = {}
    analyze_dependency = get_dspy_analyzer()

    for artifact, details in dependencies.items():
        web_insights, sources = fetch_web_insights(artifact, details["latest_version"], details["current_version"])

        if not web_insights.strip():
            web_insights = f"No significant web insights found for {artifact}. Perform a standard dependency upgrade analysis."

        response = analyze_dependency(web_insights=web_insights)

        insights[artifact] = {
            "security_changes": response.security_changes,
            "deprecated_methods": response.deprecated_methods,
            "code_changes": response.code_changes,
            "severity_level": response.severity_level,
            "sources": sources
        }

    return insights

# Function to clear DSPy from session state after analysis
def cleanup_dspy():
    if "analyze_dependency" in st.session_state:
        del st.session_state["analyze_dependency"]

# Fetch pom.xml from GitHub repository
def fetch_github_file(owner: str, repo: str, path: str, branch: str = "main") -> str:
    """
    Fetch a file from GitHub repository using Personal Access Token.
    
    Args:
        owner (str): GitHub repository owner/organization
        repo (str): Repository name
        path (str): Path to file in the repository
        branch (str): Branch name (default: main)
    
    Returns:
        str: Content of the file
    """
    # Construct raw content URL
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"

    # Get GitHub token from environment
    GITHUB_PERSONAL_ACCESS_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not GITHUB_PERSONAL_ACCESS_TOKEN:
        raise ValueError("GITHUB_TOKEN not found in .env file")
    
    # Set up headers with token
    headers = {
        "Authorization": f"Bearer {GITHUB_PERSONAL_ACCESS_TOKEN}",
        "Accept": "application/vnd.github.v3.raw"
    }
    
    # Make request
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to fetch file. Status: {response.status_code}\nMessage: {response.text}")

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
    github_url = github_url.replace('.git', '')
    
    # Handle SSH URL format
    if github_url.startswith('git@'):
        github_url = github_url.split('git@github.com:')[1]
    
    # Handle HTTPS URL format
    elif github_url.startswith(('http://', 'https://')):
        github_url = github_url.split('github.com/')[1]
    
    # Split into owner and repo
    try:
        owner, repo = github_url.split('/')
        return owner.strip(), repo.strip()
    except ValueError:
        raise ValueError(
            "Invalid GitHub URL format. Expected format: owner/repo or full GitHub URL"
        )

# Streamlit UI
st.title("Dependency Analyzer")

github_repo_url = st.text_input("Enter the Github repo URL:")
# github_repo_url = https://github.com/techneo1/AI-Engineering
if github_repo_url:
    owner, repo = parse_github_url(github_repo_url)

    try:
        # Replace with actual repository details
        pom_content = fetch_github_file(
            owner=owner,
            repo=repo,
            path="pom.xml",
            branch="master"
        )

        st.success("Successfully fetched pom.xml:")
        st.code(pom_content, language="xml")    

        # Optionally save to file
        pom_file_path = "dist/pom.xml"
        with open(pom_file_path, "w") as f:
            f.write(pom_content)
        
        if pom_file_path:
            dependencies = parse_pom(pom_file_path)

            # Fetch latest versions before showing the table
            dependencies = fetch_latest_versions(dependencies)

            # Convert dependencies to DataFrame and add index
            df = pd.DataFrame(dependencies).T.reset_index()
            df.index += 1  # Start index from 1
            df.rename(columns={"index": "Artifact"}, inplace=True)

            st.write(f"### Total Dependencies Found: {len(dependencies)}")  # Show count
            st.table(df)  # Now it includes "latest_version"

            # Store dependencies in session state
            st.session_state["dependencies"] = dependencies
        else:
            st.error("No pom.xml found in the provided directory.")
        
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Ensure dependencies exist before analysis
if st.button("Analyze Dependencies"):
    if "dependencies" in st.session_state:
        dependencies = st.session_state["dependencies"]
        insights = analyze_dependencies(dependencies)
        st.session_state["insights"] = insights
        cleanup_dspy()
    else:
        st.error("Dependencies not loaded. Please check if pom.xml was found.")


if "show_analysis" not in st.session_state:
    st.session_state["show_analysis"] = False

if "insights" in st.session_state:
    st.session_state["show_analysis"] = True

if st.session_state["show_analysis"]:
    with st.expander("Analysis Report", expanded=True):
        report_lines = []
        
        for i, (artifact, analysis) in enumerate(st.session_state["insights"].items(), start=1):
            st.markdown(f"### {i}. {artifact} ({dependencies[artifact]['current_version']} → {dependencies[artifact]['latest_version']})")
            st.write(f"**Severity Level:** {analysis['severity_level']}")
            st.write(f"**Security Changes:** {analysis['security_changes']}")
            st.write(f"**Deprecated Methods:** {analysis['deprecated_methods']}")
            st.write(f"**Code Changes:** {analysis['code_changes']}")

            report_lines.append(f"{i}. {artifact} ({dependencies[artifact]['current_version']} → {dependencies[artifact]['latest_version']})")
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
        st.download_button("Download Analysis Report", report_text, "analysis_report.txt", "text/plain")
