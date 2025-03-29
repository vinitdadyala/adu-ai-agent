import os
import dspy
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from tavily import TavilyClient

import utils;

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
        llm = dspy.LM(model="groq/llama3-70b-8192", api_key=groq_api_key)
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


# Function to clear DSPy from session state after analysis
def cleanup_dspy():
    if "analyze_dependency" in st.session_state:
        del st.session_state["analyze_dependency"]


# Streamlit UI
st.title("Dependency Analyzer")

github_repo_url = st.text_input("Enter the Github repo URL:")
# github_repo_url = https://github.com/techneo1/AI-Engineering
if github_repo_url:
    owner, repo = utils.parse_github_url(github_repo_url)

    try:
        # Get GitHub token from environment
        GITHUB_PERSONAL_ACCESS_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not GITHUB_PERSONAL_ACCESS_TOKEN:
            raise ValueError("GITHUB_TOKEN not found in .env file")
    
        # Replace with actual repository details
        pom_content = utils.fetch_github_file(
            owner=owner, repo=repo, path="pom.xml", access_token=GITHUB_PERSONAL_ACCESS_TOKEN, branch="master"
        )

        # Optionally save to file
        pom_file_path = "dist/pom.xml"
        with open(pom_file_path, "w") as f:
            f.write(pom_content)

        if pom_file_path:
            dependencies = utils.parse_pom(pom_file_path)

            # Fetch latest versions before showing the table
            dependencies = utils.fetch_latest_versions(dependencies)

            # Convert dependencies to DataFrame and add index
            df = pd.DataFrame(dependencies).T.reset_index()
            df.index += 1  # Start index from 1
            df.rename(columns={"index": "Artifact"}, inplace=True)

            st.write(f"### Total Dependencies in pom.xml: {len(dependencies)}")  # Show count
            st.table(df)  # Now it includes "latest_version"

            # Store dependencies in session state
            st.session_state["dependencies"] = dependencies
        else:
            st.error("No pom.xml found in the provided directory.")

    except Exception as e:
        st.error(f"Error: {str(e)}")

# Ensure dependencies exist before analysis
if st.button("Analyze Dependencies"):
    if "dependencies" in st.session_state:
        dependencies = st.session_state["dependencies"]
        insights = analyze_dependencies(dependencies)
        st.session_state["insights"] = insights
        cleanup_dspy()
    else:
        st.error("Dependencies not loaded. Please check if pom.xml was found.")


if "show_analysis" not in st.session_state:
    st.session_state["show_analysis"] = False

if "insights" in st.session_state:
    st.session_state["show_analysis"] = True

if st.session_state["show_analysis"]:
    with st.expander("Analysis Report", expanded=True):
        report_lines = []

        for i, (artifact, analysis) in enumerate(
            st.session_state["insights"].items(), start=1
        ):
            st.markdown(
                f"### {i}. {artifact} ({dependencies[artifact]['current_version']} → {dependencies[artifact]['latest_version']})"
            )
            st.write(f"**Severity Level:** {analysis['severity_level']}")
            st.write(f"**Security Changes:** {analysis['security_changes']}")
            st.write(f"**Deprecated Methods:** {analysis['deprecated_methods']}")
            st.write(f"**Code Changes:** {analysis['code_changes']}")

            report_lines.append(
                f"{i}. {artifact} ({dependencies[artifact]['current_version']} → {dependencies[artifact]['latest_version']})"
            )
            report_lines.append(f"Severity Level: {analysis['severity_level']}")
            report_lines.append(f"Security Changes: {analysis['security_changes']}")
            report_lines.append(f"Deprecated Methods: {analysis['deprecated_methods']}")
            report_lines.append(f"Code Changes: {analysis['code_changes']}")
            report_lines.append("-" * 50)

            if analysis["sources"]:
                st.write("**Related Articles:**")
                for j, url in enumerate(analysis["sources"], start=1):
                    st.markdown(f"- [Source {j}]({url})")
                    report_lines.append(f"Source {j}: {url}")

        report_text = "\n".join(report_lines)
        st.download_button(
            "Download Analysis Report", report_text, "analysis_report.txt", "text/plain"
        )
