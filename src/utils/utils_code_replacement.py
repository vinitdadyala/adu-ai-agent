import os
import stat
import re
import streamlit as st
import dspy
import xml.etree.ElementTree as ET
import shutil
from pathlib import Path
from threading import Lock

class CodeReplacementAgent:
    _dspy_lock = Lock()
    _dspy_initialized = False

    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY_NEW")
        with self._dspy_lock:
            if not self._dspy_initialized:
                llm = dspy.LM(model="groq/llama3-8b-8192", api_key=self.groq_api_key)
                dspy.settings.configure(lm=llm)
                CodeReplacementAgent._dspy_initialized = True
        self._initialize_chain()

    def _initialize_chain(self):
        """Initialize the DSPy chain in the current thread context"""
        if "replacement_chain" not in st.session_state:
            st.session_state["replacement_chain"] = dspy.ChainOfThought(self.ReplacementSuggestion)

    class ReplacementSuggestion(dspy.Signature):
        deprecated_line = dspy.InputField()
        context = dspy.InputField()
        replacement_code = dspy.OutputField(desc="Java code to replace the deprecated line with, including full method call with example.")

    def find_java_files(self, base_dir):
        java_files = []
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith(".java"):
                    java_files.append(os.path.join(root, file))
        return java_files

    def clean_code_output(self, llm_response: str) -> str:
        cleaned = re.sub(r"```(java)?", "", llm_response)
        cleaned = re.sub(r"(?i)//\s?TODO:.*", "", cleaned)
        cleaned = re.sub(r"(?i)//.*deprecated.*", "", cleaned)
        return cleaned.strip()

    def normalize_insights(self, insights: dict) -> dict:
        for dep, info in insights.items():
            for key in ["deprecated_methods", "security_changes", "code_changes"]:
                value = info.get(key)
                if isinstance(value, str):
                    if any(phrase in value.lower() for phrase in ["no deprecated", "not explicitly mentioned", "none"]):
                        info[key] = []
                    else:
                        info[key] = [value]
        return insights

    def get_code_change_tasks(self, insights):
        tasks = {}
        for dep, info in insights.items():
            task_list = info.get("code_changes", [])
            if isinstance(task_list, str):
                task_list = [task_list]
            tasks[dep] = [task.strip() for task in task_list if task.strip()]
        return tasks

    def analyze_and_replace(self, file_path, code, code_tasks):
        modified_code = code
        applied_tasks = []

        for dep, tasks in code_tasks.items():
            for task in tasks:
                prompt = f"""
You are an expert Java developer who is trying to upgrade the dependencies of his codebase.

Dependency: {dep}
Upgrade Context:
{task}

Please analyze the following Java code and apply the necessary changes related to the above dependency upgrade.

Instructions:
  1. Modify the code to reflect the upgrade. Replace deprecated methods, usages or with their recommended alternatives along with necessary imports.
  2. Do not change class names, method names, or variable names unless absolutely required.
  3. Do not add extra methods, tests, or boilerplate such as `main()` or logging unless explicitly instructed.
  4. Preserve original formatting and indentation.
  5. Avoid altering existing functionality unless required by the upgrade.
  6. At the end of the file, ADD a comment block summarizing what was changed.
  7. Return only the updated code — no markdown wrappers, no explanations.

---

{modified_code}
"""
                try:
                    result = st.session_state["replacement_chain"](deprecated_line=modified_code, context=prompt)
                    if result and hasattr(result, 'replacement_code') and result.replacement_code:
                        if result.replacement_code != modified_code:
                            applied_tasks.append(f"[{dep}] {task}")
                            modified_code = result.replacement_code
                    else:
                        applied_tasks.append(f"[{dep}] {task} - No code change applied.")
                        st.warning(f"Unexpected response structure or no change required: {result}")
                except Exception as e:
                    st.warning(f"Error analyzing {file_path} with task '{task}': {e}")
        return modified_code, applied_tasks

    def analyze_project_code(self, project_path, insights):
        code_tasks = self.get_code_change_tasks(insights)
        java_files = self.find_java_files(project_path)
        summary = {}

        for file_path in java_files:
            with open(file_path, "r") as f:
                original_code = f.read()

            modified_code, applied_tasks = self.analyze_and_replace(file_path, original_code, code_tasks)

            if applied_tasks and modified_code != original_code:
                with open(file_path, "w") as f:
                    f.write(modified_code)
                summary[file_path] = applied_tasks

        return summary

    def update_pom_with_latest_versions(self, pom_path, dependencies):
        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
        ET.register_namespace('', ns['m'])
        pom_path = Path(pom_path)

        temp_pom = pom_path.parent / f"{pom_path.stem}_temp{pom_path.suffix}"
        backup_pom = pom_path.parent / f"{pom_path.stem}_backup{pom_path.suffix}"

        try:
            shutil.copy2(pom_path, backup_pom)
            tree = ET.parse(pom_path)
            root = tree.getroot()
            updated = False

            for artifact_id, dep_info in dependencies.items():
                group_id = dep_info.get("group_id")
                latest_version = dep_info.get("latest_version")

                for dependency in root.findall(".//m:dependency", ns):
                    g = dependency.find("m:groupId", ns)
                    a = dependency.find("m:artifactId", ns)
                    v = dependency.find("m:version", ns)

                    if g is not None and a is not None and v is not None:
                        if g.text == group_id and a.text == artifact_id and v.text != latest_version:
                            st.text(f"🔄 Updating {group_id}:{artifact_id} from {v.text} to {latest_version}")
                            v.text = latest_version
                            updated = True

            if updated:
                tree.write(pom_path, encoding="utf-8", xml_declaration=True)
                st.success(f"✅ pom.xml updated and saved to {pom_path}")
            else:
                st.info("ℹ️ No updates needed in pom.xml")

        except Exception as e:
            st.error(f"❌ Error updating pom.xml: {e}")

    def cleanup(self):
        if "replacement_chain" in st.session_state:
            del st.session_state["replacement_chain"]


