import os
import json
import dspy
import xml.etree.ElementTree as ET
import requests
import streamlit as st
from dotenv import load_dotenv
import concurrent.futures
from tavily import TavilyClient  

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY not found in environment variables")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY not found in environment variables")

def get_dspy_analyzer():
    if "analyze_dependency" not in st.session_state:
        llm = dspy.LM(model="groq/llama3-70b-8192", api_key=groq_api_key)
        dspy.settings.configure(lm=llm) 
        st.session_state["analyze_dependency"] = dspy.ChainOfThought(DependencyAnalysis)

    return st.session_state["analyze_dependency"]

search_client = TavilyClient(api_key=tavily_api_key)

# Define DSPy Signature for Dependency Analysis
class DependencyAnalysis(dspy.Signature):
    web_insights = dspy.InputField()
    security_changes = dspy.OutputField(desc="List of security risks mitigated or introduced")
    deprecated_methods = dspy.OutputField(desc="List of deprecated methods or breaking changes")
    code_changes = dspy.OutputField(desc="List of probable code modifications needed")
    severity_level = dspy.OutputField(desc="Classify impact as High, Moderate, or Low")

def parse_pom(pom_file):
    """Parses a pom.xml file and extracts dependencies."""
    tree = ET.parse(pom_file)
    root = tree.getroot()

    ns = {'mvn': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}

    dependencies = {}
    for dep in root.findall("mvn:dependencies/mvn:dependency", ns):
        group_id = dep.find("mvn:groupId", ns)
        artifact_id = dep.find("mvn:artifactId", ns)
        version = dep.find("mvn:version", ns)

        if group_id is not None and artifact_id is not None:
            dependencies[artifact_id.text] = {
                "group_id": group_id.text,
                "current_version": version.text if version is not None else "LATEST",
            }

    return dependencies

def get_latest_version(group_id, artifact_id):
    """Fetches the latest version from Maven Central."""
    url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/maven-metadata.xml"

    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            latest_version = root.find("./versioning/latest")
            return latest_version.text if latest_version is not None else "UNKNOWN"
    except requests.RequestException:
        return "UNKNOWN"

def fetch_latest_versions(dependencies):
    """Fetch latest versions in parallel."""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(get_latest_version, details["group_id"], artifact): artifact
            for artifact, details in dependencies.items()
        }
        for future in concurrent.futures.as_completed(futures):
            artifact = futures[future]
            dependencies[artifact]["latest_version"] = future.result()

    return dependencies

def fetch_web_insights(artifact, latest_version, current_version):
    """Fetches real-time insights and severity classification for a dependency update."""
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
        return "Failed to fetch web insights.", ["Error fetching sources."]

def analyze_dependencies(dependencies):
    """Fetch web insights and analyze dependencies one by one to ensure correct LLM processing."""
    insights = {}
    analyze_dependency = get_dspy_analyzer()  # Get the DSPy LLM analyzer

    for artifact, details in dependencies.items():
        web_insights, sources = fetch_web_insights(artifact, details["latest_version"], details["current_version"])

        # Fallback in case no insights are found
        if not web_insights.strip():
            web_insights = f"No significant web insights found for {artifact}. Perform a standard dependency upgrade analysis."

        # Process each dependency individually in LLM
        response = analyze_dependency(web_insights=web_insights)

        insights[artifact] = {
            "security_changes": response.security_changes,
            "deprecated_methods": response.deprecated_methods,
            "code_changes": response.code_changes,
            "severity_level": response.severity_level,
            "sources": sources  
        }

    return insights


def get_severity_color(severity):
    color_map = {
        "High": ("🔴 High", "#ff4d4d"),
        "Moderate": ("🟡 Moderate", "#ffcc00"),
        "Low": ("🟢 Low", "#4caf50")
    }
    return color_map.get(severity, ("⚪ Unknown", "#cccccc"))

# Streamlit UI
st.title("Dependency Analyzer")

uploaded_file = st.file_uploader("Upload pom.xml", type=["xml"])

if uploaded_file:
    dependencies = parse_pom(uploaded_file)
    dependencies = fetch_latest_versions(dependencies)
    st.table(dependencies)

    if st.button("Analyze Dependencies"):
        insights = analyze_dependencies(dependencies)
        st.session_state["insights"] = insights  

if "show_analysis" not in st.session_state:
    st.session_state["show_analysis"] = False 

if "insights" in st.session_state:
    st.session_state["show_analysis"] = True 

if st.session_state["show_analysis"]:
    with st.expander("📊 Analysis Report", expanded=True):
        for artifact, analysis in st.session_state["insights"].items():
            severity, color = get_severity_color(analysis["severity_level"])

            st.markdown(f"### {artifact} ({dependencies[artifact]['current_version']} → {dependencies[artifact]['latest_version']})")

            # Severity Badge
            st.markdown(
                f'<div display: inline-block; font-weight: bold;">{severity} Severity</div>',
                unsafe_allow_html=True
            )

            # Security Analysis
            st.write(f"🔹 **Security Changes:** {analysis['security_changes']}")
            st.write(f"🔹 **Deprecated Methods:** {analysis['deprecated_methods']}")
            st.write(f"🔹 **Code Changes:** {analysis['code_changes']}")

            # Hyperlinks to sources
            if analysis["sources"]:
                st.write("🔗 **Related Articles:**")
                for i, url in enumerate(analysis["sources"], 1):
                    st.markdown(f"- [{artifact} Source {i}]({url})")

            st.write("---")
