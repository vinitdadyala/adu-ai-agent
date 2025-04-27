import os
import re
import dspy
import streamlit as st
from dotenv import load_dotenv
from tavily import TavilyClient
from threading import Lock

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY_NEW")
tavily_api_key = os.getenv("TAVILY_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY not found in environment variables")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY not found in environment variables")

class DependencyAnalysisAgent:
    _dspy_lock = Lock()
    _dspy_initialized = False

    def __init__(self):
        self.search_client = TavilyClient(api_key=tavily_api_key)
        with self._dspy_lock:
            if not self._dspy_initialized:
                llm = dspy.LM(model="groq/llama3-8b-8192", api_key=groq_api_key)
                dspy.settings.configure(lm=llm)
                DependencyAnalysisAgent._dspy_initialized = True
        self._initialize_chain()

    def _initialize_chain(self):
        """Initialize the DSPy chain in the current thread context"""
        if "analyze_dependency" not in st.session_state:
            st.session_state["analyze_dependency"] = dspy.ChainOfThought(self.DependencyAnalysis)

    class DependencyAnalysis(dspy.Signature):
        web_insights = dspy.InputField()
        security_changes = dspy.OutputField(desc="List of security risks mitigated or introduced")
        deprecated_methods = dspy.OutputField(desc="List of deprecated methods or breaking changes")
        code_changes = dspy.OutputField(desc="List of probable code modifications needed")
        severity_level = dspy.OutputField(desc="Classify impact as High, Moderate, or Low")

    def fetch_web_insights(self, artifact, latest_version, current_version):
        query = (
            f"Classify the security impact of upgrading {artifact} from {current_version} to {latest_version} "
            f"as High, Moderate, or Low. Provide detailed information on security changes, deprecated methods, and code modifications."
        )
        try:
            response = self.search_client.search(query, max_results=6, search_depth="basic")
            if response and response["results"]:
                insights = "\n".join([r["content"] for r in response["results"]])
                sources = [r["url"] for r in response["results"][:2]]
                return insights, sources
        except Exception:
            return "No insights available.", ["No sources found."]

    def analyze_dependencies(self, dependencies):
        insights = {}
        for artifact, details in dependencies.items():
            web_insights, sources = self.fetch_web_insights(
                artifact, details["latest_version"], details["current_version"]
            )

            if not web_insights.strip():
                web_insights = f"No significant web insights found for {artifact}. Perform a standard dependency upgrade analysis."

            response = st.session_state["analyze_dependency"](web_insights=web_insights)

            insights[artifact] = {
                "security_changes": response.security_changes,
                "deprecated_methods": response.deprecated_methods,
                "code_changes": response.code_changes,
                "severity_level": response.severity_level,
                "sources": sources,
            }

        return insights

    def cleanup(self):
        if "analyze_dependency" in st.session_state:
            del st.session_state["analyze_dependency"]
