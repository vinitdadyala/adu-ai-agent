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

# --- MODIFIED parse_insights ---

def parse_insights(analysis_file):
    """Parse the plain text insights file into a structured dictionary."""
    insights = {}
    try:
        with open(analysis_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Match dependency name and version pattern
        pattern = r"(?P<dep>[a-zA-Z0-9\.-]+ \([^)]+\))"
        matches = list(re.finditer(pattern, content))
        if not matches:
            st.warning("❌ No dependencies matched.")
            return {}

        for i in range(len(matches)):
            start = matches[i].start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section = content[start:end].strip()

            lines = section.splitlines()
            if not lines:
                continue

            artifact_match = re.match(r"([^\s\(]+)", lines[0])
            if artifact_match:
                artifact = artifact_match.group(1).lower()
                insights[artifact] = {
                    "deprecated": [],
                    "security": [],
                    "changes": [],
                    "new_methods": "",
                }

                current_key = None
                for line in lines[1:]:
                    line = line.strip()

                    if line.startswith("Security Changes:"):
                        current_key = "security"
                        continue
                    elif line.startswith("Deprecated Methods:"):
                        current_key = "deprecated"
                        continue
                    elif line.startswith("Code Changes:"):
                        current_key = "changes"
                        continue
                    elif line.startswith("Source"):
                        current_key = None
                        continue

                    if current_key and line.startswith("- "):
                        insights[artifact][current_key].append(line[2:])
                    elif current_key and line:
                        # continuation of previous line
                        if insights[artifact][current_key]:
                            insights[artifact][current_key][-1] += " " + line
            else:
                st.warning(f"⚠️ Could not extract artifact name from: {lines[0]}")
    except Exception as e:
        st.error(f"❌ Error parsing insights: {e}")
        return {}

    return insights

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

def analyze_and_replace(java_file, insights, use_llm=True):
    updated_code = []
    modified = False

    st.write(f"🔍 Scanning file: `{java_file}`")

    with open(java_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Show first few lines for debugging
    st.code("".join(lines[:10]), language="java")

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

            # 🛠 Extract proper method names like ClassName.methodName from the string
            deprecated_methods = []
            for m in deprecated_raw:
                deprecated_methods += re.findall(r"([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)\(\)", m)

            for method in deprecated_methods:
                if re.search(r"\b" + re.escape(method) + r"\b", line):
                    st.warning(f"⚠️ Found deprecated usage of `{method}` in line:\n`{original_line.strip()}`")

                    comment = f"// TODO: Deprecated method '{method}' found in {artifact}."
                    replacement = ""

                    context = search_new_method(method, artifact)

                    if use_llm and context:
                        result = llm(deprecated_line=original_line.strip(), context=context)
                        replacement = result.replacement_code.strip()

                    updated_code.append(comment + "\n")
                    if replacement:
                        updated_code.append(replacement + "\n")
                    else:
                        updated_code.append(original_line)

                    modified = True
                    replaced = True
                    break

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

# --- STREAMLIT UI ---
st.title("🧠 Java Auto Upgrader with LLM + Tavily")

project_dir = st.text_input("📁 Enter your Java project directory:")
insights_path = st.text_input("📄 Path to insights file (e.g., insights.txt):")

if project_dir and insights_path:
    insights = parse_insights(insights_path)
    java_files = find_java_files(project_dir)

    if insights:
        st.subheader("📊 Parsed Insights")
        st.json(insights)

        st.subheader("📂 Java Files Found")
        st.write(java_files)

        has_deprecated = any(details.get("deprecated") for details in insights.values())
        if not has_deprecated:
            st.warning("⚠️ No deprecated methods listed in the insights.")

        if st.button("🔧 Analyze & Replace Deprecated Code"):
            any_changes = False
            for file in java_files:
                if analyze_and_replace(file, insights):
                    st.success(f"✅ Updated: `{file}`")
                    any_changes = True
                else:
                    st.info(f"ℹ️ No changes needed in: `{file}`")

            if not any_changes:
                st.warning("🚫 No deprecated code matched or modified.")

        # Section for Tavily method suggestions
        found_suggestions = False
        for artifact, data in insights.items():
            new_methods = data.get("new_methods", "")
            if new_methods.strip():
                found_suggestions = True
                st.markdown(f"**🔹 {artifact}**")
                st.code(new_methods.strip(), language="java")

    else:
        st.error("❌ Failed to parse the insights file. Please check the format or path.")




