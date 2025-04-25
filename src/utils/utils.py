import requests
import pandas as pd
import streamlit as st
import concurrent.futures
import xml.etree.ElementTree as ET
import os


# Parse pom.xml file
def parse_pom(pom_path: str) -> dict:
    tree = ET.parse(pom_path)
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
            latest_version = root.find(".//latest")
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
        return 
    

# Dummy method as of now. Need to replace with actual script
def update_pom_versions(pom_path: str, dependencies: dict) -> None:
    """
    Update dependency versions in pom.xml, handling different namespace prefixes.

    Args:
        pom_path (str): Path to the pom.xml file
        dependencies (dict): Dictionary of dependencies with their latest versions

    Returns:
        None
    """
    tree = ET.parse(pom_path)
    root = tree.getroot()
    
    # Handle different possible namespace prefixes
    if "}" in root.tag:
        namespace = root.tag.split("}")[0].strip("{")
        ns = {
            "mvn": namespace,
            "ns0": namespace  # Add ns0 as alternative prefix
        }
    else:
        ns = {}
    
    # Try both namespace prefixes
    for prefix in ["mvn", "ns0"]:
        for dep in root.findall(f".//{prefix}:dependency", ns):
            artifact_id = dep.find(f"{prefix}:artifactId", ns)
            if artifact_id is not None and artifact_id.text in dependencies:
                version = dep.find(f"{prefix}:version", ns)
                latest_version = dependencies[artifact_id.text]["latest_version"]
                if version is not None:
                    version.text = latest_version
    
    tree.write(pom_path, encoding='UTF-8', xml_declaration=True)

def find_pom_file(repo_path: str) -> str:
    for root, dirs, files in os.walk(repo_path):
        if "pom.xml" in files:
            pom_path=os.path.join(root, "pom.xml")  # Full path
            print(pom_path)
            return pom_path
    raise FileNotFoundError("No pom.xml found in the repository.")
