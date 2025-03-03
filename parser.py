import xml.etree.ElementTree as ET
import json
import logging
import os

LOG_FILE = "project.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a"), 
        logging.StreamHandler()  
    ]
)

def parse_pom(pom_file, output_file=None):
    """Parses a pom.xml file and extracts dependencies."""
    
    if not os.path.exists(pom_file):
        logging.error(f"File not found: {pom_file}")
        return None

    try:
        tree = ET.parse(pom_file)
        root = tree.getroot()
        logging.info(f"Successfully read the file: {pom_file}")
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

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({"dependencies": dependencies}, f, indent=4)
        logging.info(f"Dependencies written to {output_file}")

    return dependencies 

if __name__ == "__main__":
    pom_file_path = "pom.xml"
    output_file_path = "dependencies.json"
    
    result = parse_pom(pom_file_path, output_file_path)
    if result:
        logging.info("Final output:\n" + json.dumps(result, indent=4))