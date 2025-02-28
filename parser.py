import xml.etree.ElementTree as ET
import json

def parse_pom(pom_file, output_file):
    try:
        tree = ET.parse(pom_file)
        root = tree.getroot()
        print(f"Successfully read the file: {pom_file}")
    except ET.ParseError as e:
        print(f"Error parsing the file: {e}")
        return
    except FileNotFoundError:
        print(f"File not found: {pom_file}")
        return

    namespaces = {'mvn': 'http://maven.apache.org/POM/4.0.0'}

    dependencies_element = root.find('mvn:dependencies', namespaces)
    
    if dependencies_element is None:
        print("No dependencies found in the pom.xml file.")
        return
    
    dependencies = []
    
    for dependency in dependencies_element.findall('mvn:dependency', namespaces):
        group_id = dependency.find('mvn:groupId', namespaces).text
        artifact_id = dependency.find('mvn:artifactId', namespaces).text
        version_element = dependency.find('mvn:version', namespaces)
        version = version_element.text if version_element is not None else "LATEST"
        
        dependencies.append({
            "group_id": group_id,
            "artifact_id": artifact_id,
            "version": version
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"dependencies": dependencies}, f, indent=4)
    
    print(f"Dependencies written to {output_file}")

# Example usage
if __name__ == "__main__":
    pom_file_path = "pom.xml"
    output_file_path = "dependencies.json"
    parse_pom(pom_file_path, output_file_path)
