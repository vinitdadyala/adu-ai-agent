import os
import re
import streamlit as st
from tavily import TavilyClient
import dspy

# --- SETUP ---
groq_api_key = os.getenv("GROQ_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")
search_client = TavilyClient(api_key=tavily_api_key)

# DSPy LLM Setup
class ReplacementSuggestion(dspy.Signature):
    deprecated_line = dspy.InputField()
    context = dspy.InputField()
    replacement_code = dspy.OutputField(desc="The updated Java code line(s) to replace deprecated usage.")

def get_replacement_llm():
    if "dspy_configured" not in st.session_state:
        dspy.settings.configure(lm=dspy.LM(model="groq/llama-3.3-70b-versatile", api_key=groq_api_key))
        st.session_state["dspy_configured"] = True

    if "replacement_chain" not in st.session_state:
        st.session_state.replacement_chain = dspy.ChainOfThought(ReplacementSuggestion)

    return st.session_state.replacement_chain

# --- CORE UTILS ---
def find_java_files(base_dir):
    java_files = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".java"):
                java_files.append(os.path.join(root, file))
    return java_files

def search_new_method(method, artifact):
    query = f"Java replacement for deprecated {method} in {artifact} with updated method with usage"
    try:
        result = search_client.search(query=query, max_results=2, search_depth="basic")
        if result and result['results']:
            print(result)
            return result['results'][0]['content']
    except Exception as e:
        st.warning(f"Search error: {e}")
    return ""

def clean_code_output(llm_response: str) -> str:
    """Remove Markdown formatting and unnecessary comments from LLM response."""
    cleaned = re.sub(r"```(java)?", "", llm_response)
    cleaned = re.sub(r"(?i)//\s?TODO:.*", "", cleaned)
    cleaned = re.sub(r"(?i)//.*deprecated.*", "", cleaned)
    return cleaned.strip()

def analyze_and_replace(java_file, insights, use_llm=True):
    updated_code = []
    modified = False

    st.write(f"🔍 Scanning file: `{java_file}`")

    with open(java_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    st.code("".join(lines[:10]), language="java")  # Preview for debugging

    llm = get_replacement_llm() if use_llm else None

    for line in lines:
        original_line = line
        line_lower = line.lower()
        replaced = False

        for artifact, details in insights.items():
            artifact = artifact.lower()
            deprecated_raw = details.get("deprecated", [])
            if not deprecated_raw:
                continue

            # Extract methods like Class.method()
            deprecated_methods = []
            for m in deprecated_raw:
                deprecated_methods += re.findall(r"([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\(\)", m)

            for method in deprecated_methods:
                if re.search(r"\b" + re.escape(method) + r"\b", line):
                    st.warning(f"⚠️ Deprecated method `{method}` used in:\n`{original_line.strip()}`")

                    context = search_new_method(method, artifact)

                    if use_llm and context:
                        result = llm(deprecated_line=original_line.strip(), context=context)
                        replacement = clean_code_output(result.replacement_code)
                        updated_code.append(replacement + "\n")
                        modified = True
                        replaced = True
                    else:
                        updated_code.append(original_line)
                        modified = True
                        replaced = True

                    break  # Only one replacement per line

            if replaced:
                break

        if not replaced:
            updated_code.append(original_line)

    if modified:
        with open(java_file, "w", encoding="utf-8") as f:
            f.writelines(updated_code)
        return True

    return False

def analyze_project_code(directory, insights, use_llm=True):
    modified_files = []

    has_deprecated = any(details.get("deprecated") for details in insights.values())
    if not has_deprecated:
        st.warning("⚠️ Insights file has no deprecated methods listed.")
        return modified_files

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".java"):
                java_file = os.path.join(root, file)
                changed = analyze_and_replace(java_file, insights, use_llm)
                if changed:
                    modified_files.append(java_file)
                else:
                    st.info(f"No changes: {java_file}")

    return modified_files



