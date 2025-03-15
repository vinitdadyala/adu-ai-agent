import xml.etree.ElementTree as ET
import json
import logging
import os
import requests

LOG_FILE = "project.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a"), 
        logging.StreamHandler()
    ]
)

def parse_pom(pom_file):
    """Parses a pom.xml file and extracts dependencies."""
    
    if not os.path.exists(pom_file):
        logging.error(f"File not found: {pom_file}")
        return {}

    try:
        tree = ET.parse(pom_file)
        root = tree.getroot()
        logging.info(f"Successfully read the file: {pom_file}")
    except ET.ParseError as e:
        logging.error(f"Error parsing the file: {e}")
        return {}

    namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''
    ns = {'mvn': namespace} if namespace else {}

    dependencies_element = root.find('mvn:dependencies', ns)

    if dependencies_element is None:
        logging.warning("No dependencies found in the pom.xml file.")
        return {}

    dependencies = {}

    for dependency in dependencies_element.findall('mvn:dependency', ns):
        group_id = dependency.find('mvn:groupId', ns)
        artifact_id = dependency.find('mvn:artifactId', ns)
        version_element = dependency.find('mvn:version', ns)

        if group_id is not None and artifact_id is not None:
            artifact_key = artifact_id.text
            dependencies[artifact_key] = {
                "group_id": group_id.text,
                "current_version": version_element.text if version_element is not None else "LATEST",
                "latest_version": None  # Placeholder for latest version
            }

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

def update_dependencies(pom_file, output_file="input_prompt.json"):
    dependencies = parse_pom(pom_file)

    if not dependencies:
        logging.error("No dependencies found to update.")
        return

    for artifact, details in dependencies.items():
        latest_version = get_latest_maven_version(details["group_id"], artifact)
        details["latest_version"] = latest_version if latest_version else "UNKNOWN"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(dependencies, file, indent=4)

    logging.info(f"Updated dependencies saved to {output_file}")

if __name__ == "__main__":
    pom_file_path = "pom.xml"
    output_file_path = "dist/input_prompt.json"  # Output file name

    update_dependencies(pom_file_path, output_file_path)
