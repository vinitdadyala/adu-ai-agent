import os
import re
import dspy
import streamlit as st
from dotenv import load_dotenv
from tavily import TavilyClient

import utils
import utils_git
import utils_code_replacement

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY not found in environment variables")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY not found in environment variables")


# Initialize DSPy and Groq LLM
def get_dspy_analyzer():
    if "analyze_dependency" not in st.session_state:
        llm = dspy.LM(model="groq/llama-3.3-70b-versatile", api_key=groq_api_key)
        dspy.settings.configure(lm=llm)
        st.session_state["analyze_dependency"] = dspy.ChainOfThought(DependencyAnalysis)

    return st.session_state["analyze_dependency"]


search_client = TavilyClient(api_key=tavily_api_key)


# DSPy Signature for Dependency Analysis
class DependencyAnalysis(dspy.Signature):
    web_insights = dspy.InputField()
    security_changes = dspy.OutputField(
        desc="List of security risks mitigated or introduced"
    )
    deprecated_methods = dspy.OutputField(
        desc="List of deprecated methods or breaking changes"
    )
    code_changes = dspy.OutputField(desc="List of probable code modifications needed")
    severity_level = dspy.OutputField(desc="Classify impact as High, Moderate, or Low")


# Fetch web insights using Tavily
def fetch_web_insights(artifact, latest_version, current_version):
    query = (
        f"Classify the security impact of upgrading {artifact} from {current_version} to {latest_version} "
        f"as High, Moderate, or Low. Provide detailed information on security changes, deprecated methods, and code modifications."
    )
    try:
        response = search_client.search(query, max_results=6, search_depth="basic")

        if response and response["results"]:
            insights = "\n".join([r["content"] for r in response["results"]])
            sources = [r["url"] for r in response["results"][:2]]
            return insights, sources
    except Exception:
        return "No insights available.", ["No sources found."]


# Analyze dependencies using DSPy
def analyze_dependencies(dependencies):
    insights = {}
    analyze_dependency = get_dspy_analyzer()

    for artifact, details in dependencies.items():
        web_insights, sources = fetch_web_insights(
            artifact, details["latest_version"], details["current_version"]
        )

        if not web_insights.strip():
            web_insights = f"No significant web insights found for {artifact}. Perform a standard dependency upgrade analysis."

        response = analyze_dependency(web_insights=web_insights)

        insights[artifact] = {
            "security_changes": response.security_changes,
            "deprecated_methods": response.deprecated_methods,
            "code_changes": response.code_changes,
            "severity_level": response.severity_level,
            "sources": sources,
        }

    return insights

def analyze_and_replace(java_file, insights, use_llm=True):
    updated_code = []
    modified = False

    st.write(f"🔍 Scanning file: `{java_file}`")

    with open(java_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    st.code("".join(lines[:10]), language="java")  # Preview for debugging

    llm = utils_code_replacement.get_replacement_llm() if use_llm else None

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

                    context = utils_code_replacement.search_new_method(method, artifact)

                    if use_llm and context:
                        result = llm(deprecated_line=original_line.strip(), context=context)
                        replacement = utils_code_replacement.clean_code_output(result.replacement_code)
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


# Function to clear DSPy from session state after analysis
def cleanup_dspy():
    if "analyze_dependency" in st.session_state:
        del st.session_state["analyze_dependency"]
