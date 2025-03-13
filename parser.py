import xml.etree.ElementTree as ET
import json
import logging
import os
import streamlit as st
import analyze_dependencies as ad

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

# Streamlit UI
st.title("POM Dependency Analyzer")
st.write("Upload your `pom.xml` file to extract dependencies.")

uploaded_file = st.file_uploader("Upload POM File", type=["xml"])

if uploaded_file is not None:
    file_content = uploaded_file.getvalue().decode("utf-8")  # Read XML content as string
    dependencies = parse_pom(file_content)

    if dependencies:
        st.success("Dependencies extracted successfully!")
        
        # Display dependencies in a table
        st.write("### Extracted Dependencies:")
        st.table(dependencies)

        # Provide JSON download option
        json_data = json.dumps({"dependencies": dependencies}, indent=4)
        st.download_button(
            label="Download Dependencies as JSON",
            data=json_data,
            file_name="dependencies.json",
            mime="application/json",
        )
        if st.button("Analyze Dependencies Variations"):
            insights = ad.generateDelta()
        
            st.write("\n **Dependency Analysis Report:**\n")
            for artifact, analysis in insights.items():
                st.write(f"🔹 **{artifact}**\n")
                st.write(f"   🔹 Security Changes: {analysis['security_changes']}\n")
                st.write(f"   🔹 Deprecated Methods: {analysis['deprecated_methods']}\n")
                st.write(f"   🔹 Code Changes: {analysis['code_changes']}\n")

    else:
        st.error("No dependencies found in the uploaded file or the file is invalid.")