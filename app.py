import streamlit as st
import json
import dependency_sync as ds
import analyze_dependencies as ad
# import pandas as pd

# Streamlit UI
st.title("POM Dependency Analyzer")
st.write("Upload your `pom.xml` file to extract dependencies.")

uploaded_file = st.file_uploader("Upload POM File", type=["xml"], key="pom_file_uploader")

if uploaded_file is not None:
    file_content = uploaded_file.getvalue().decode("utf-8")  # Read XML content as string
    dependencies = ds.update_dependencies(file_content)

    if dependencies:
        st.success("Dependencies extracted successfully!")
        
       # Convert dependencies map to a list of dictionaries for display
        dependencies_list = [
            {
                "artifact_id": artifact_id,
                "group_id": dep.group_id,
                "current_version": dep.current_version,
                "latest_version": dep.latest_version
            }
            for artifact_id, dep in dependencies.items()
        ]
        

        # Display dependencies in a table
        st.write("### Extracted Dependencies:")
        st.table(dependencies_list)

        # Provide JSON download option
        # json_data = json.dumps({"dependencies": dependencies}, indent=4)
        # st.download_button(
        #     label="Download Dependencies as JSON",
        #     data=dependencies,
        #     file_name="dependencies.json",
        #     mime="application/json",
        # )
        if st.button("Analyze Dependencies Variations"):
            insights = ad.generateDelta(dependencies)
        
            st.write("\n **Dependency Analysis Report:**\n")
            for artifact, analysis in insights.items():
                st.write(f"🔹 **{artifact}**\n")
                st.write(f"   🔹 Security Changes: {analysis['security_changes']}\n")
                st.write(f"   🔹 Deprecated Methods: {analysis['deprecated_methods']}\n")
                st.write(f"   🔹 Code Changes: {analysis['code_changes']}\n")

    else:
        st.error("No dependencies found in the uploaded file or the file is invalid.")