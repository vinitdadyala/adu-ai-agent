import requests
import json
import xml.etree.ElementTree as ET

def get_latest_maven_version(group_id, artifact_id):
    """Fetch the latest version of a dependency from Maven Central."""
    group_path = group_id.replace('.', '/')
    url = f"https://repo1.maven.org/maven2/{group_path}/{artifact_id}/maven-metadata.xml"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        latest_version = root.find("./versioning/latest")
        if latest_version is not None:
            return latest_version.text
    return None  # Return None if the version is not found

def update_dependencies(json_file, output_file):
    with open(json_file, "r") as file:
        data = json.load(file)
    
    for dep in data.get("dependencies", []):
        latest_version = get_latest_maven_version(dep["group_id"], dep["artifact_id"])
        if latest_version:
            dep["version"] = latest_version  # Add the latest version to the JSON

    with open(output_file, "w") as file:
        json.dump(data, file, indent=4)

    print(f"Updated dependencies saved to {output_file}")

# Example Usage
update_dependencies("dist/dependencies.json", "dist/updated_dependencies.json")
