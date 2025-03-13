import xml.etree.ElementTree as ET
import json
import logging
import os
import requests
from Dependency import Dependency

LOG_FILE = "project.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a"), 
        logging.StreamHandler()
    ]
)

def parse_pom(file_content):
    """Parses the uploaded pom.xml file and extracts dependencies."""

    try:
        tree = ET.ElementTree(ET.fromstring(file_content))
        root = tree.getroot()
        logging.info(f"Successfully read the file")
    except ET.ParseError as e:
        logging.error(f"Error parsing the file: {e}")
        return None

    namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
    ns = {'mvn': namespace} if namespace else {}

    dependencies_element = root.find('mvn:dependencies', ns)

    if dependencies_element is None:
        logging.warning("No dependencies found in the pom.xml file.")
        return None

    dependencies = []

    for dependency in dependencies_element.findall('mvn:dependency', ns):
        group_id = dependency.find('mvn:groupId', ns)
        artifact_id = dependency.find('mvn:artifactId', ns)
        version_element = dependency.find('mvn:version', ns)

        if group_id is not None and artifact_id is not None:
            dependencies.append({
                "group_id": group_id.text,
                "artifact_id": artifact_id.text,
                "version": version_element.text if version_element is not None else "LATEST"
            })

    return dependencies 

def get_latest_maven_version(group_id, artifact_id):
    """Fetch the latest version of a dependency from Maven Central."""
    group_path = group_id.replace('.', '/')
    url = f"https://repo1.maven.org/maven2/{group_path}/{artifact_id}/maven-metadata.xml"

    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            latest_version = root.find("./versioning/latest")
            return latest_version.text if latest_version is not None else None
    except requests.RequestException as e:
        logging.error(f"Error fetching latest version for {group_id}:{artifact_id} - {e}")

    return None

def update_dependencies(file_content):
    
    pom_dependencies = parse_pom(file_content)
    dependency_map = {}

    if not pom_dependencies:
        logging.error("No dependencies found to update.")
        return pom_dependencies
    
    for dep in pom_dependencies:
        latest_version = get_latest_maven_version(dep["group_id"], dep["artifact_id"])
        # print(f"latest_version::: {latest_version}")
        if latest_version:
            dependencies_obj = Dependency(dep["group_id"], dep["artifact_id"], dep["version"], latest_version)
            dependency_map[dep["artifact_id"]] = dependencies_obj
            dep["version"] = latest_version  # Add the latest version to the JSON

    # for artifact, details in dependencies:
    #     latest_version = get_latest_maven_version(details["group_id"], artifact)
    #     details["latest_version"] = latest_version if latest_version else "UNKNOWN"

    return dependency_map