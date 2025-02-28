import xml.etree.ElementTree as ET

def parse_pom(pom_file):
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

    dependencies = root.find('mvn:dependencies', namespaces)
    
    if dependencies is None:
        print("No dependencies found in the pom.xml file.")
        return
    
    for dependency in dependencies.findall('mvn:dependency', namespaces):
        group_id = dependency.find('mvn:groupId', namespaces).text
        artifact_id = dependency.find('mvn:artifactId', namespaces).text
        version = dependency.find('mvn:version', namespaces).text
        print(f"Group ID: {group_id}, Artifact ID: {artifact_id}, Version: {version}")

# Example usage
if __name__ == "__main__":
    pom_file_path = "pom.xml"
    parse_pom(pom_file_path)
