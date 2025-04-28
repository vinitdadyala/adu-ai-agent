import os
import re
import dspy
import streamlit as st
import mlflow
from dotenv import load_dotenv
from tavily import TavilyClient
from threading import Lock
import time

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
            mlflow.log_param(f"search_query_{artifact}", query)
            start_time = time.time()
            
            response = self.search_client.search(query, max_results=6, search_depth="basic")
            
            if response and response["results"]:
                insights = "\n".join([r["content"] for r in response["results"]])
                sources = [r["url"] for r in response["results"][:2]]
                
                # Log search metrics
                mlflow.log_metric(f"search_results_count_{artifact}", len(response["results"]))
                mlflow.log_param(f"search_sources_{artifact}", str(sources))
                mlflow.log_metric(f"search_time_{artifact}", time.time() - start_time)
                
                return insights, sources
        except Exception as e:
            mlflow.log_param(f"search_error_{artifact}", str(e))
            return "No insights available.", ["No sources found."]

    def analyze_dependencies(self, dependencies):
        insights = {}
        start_time = time.time()
        total_deps = len(dependencies)
        mlflow.log_metric("total_dependencies_to_analyze", total_deps)
        
        severity_counts = {"High": 0, "Moderate": 0, "Low": 0}
        processed_count = 0
        
        for artifact, details in dependencies.items():
            web_insights, sources = self.fetch_web_insights(
                artifact, details["latest_version"], details["current_version"]
            )

            if not web_insights.strip():
                web_insights = f"No significant web insights found for {artifact}. Perform a standard dependency upgrade analysis."
                mlflow.log_param(f"no_insights_{artifact}", True)

            response = st.session_state["analyze_dependency"](web_insights=web_insights)
            processed_count += 1
            mlflow.log_metric("dependencies_processed", processed_count)

            # Clean up severity level string to be MLflow-compatible
            severity = response.severity_level.strip()
            # Extract just High, Moderate, or Low from potentially longer text
            severity = re.search(r'(High|Moderate|Low)', severity, re.IGNORECASE)
            if severity:
                severity = severity.group(1).capitalize()
            else:
                severity = "Unknown"
            
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            # Log dependency-specific metrics
            mlflow.log_param(f"dependency_{artifact}_current_version", details["current_version"])
            mlflow.log_param(f"dependency_{artifact}_target_version", details["latest_version"])
            mlflow.log_param(f"dependency_{artifact}_severity", severity)
            
            if response.security_changes:
                mlflow.log_param(f"security_changes_{artifact}", str(response.security_changes)[:250])
            
            if response.deprecated_methods:
                mlflow.log_param(f"deprecated_methods_{artifact}", str(response.deprecated_methods)[:250])

            insights[artifact] = {
                "security_changes": response.security_changes,
                "deprecated_methods": response.deprecated_methods,
                "code_changes": response.code_changes,
                "severity_level": severity,
                "sources": sources,
            }

        # Log summary metrics with clean metric names
        analysis_time = time.time() - start_time
        mlflow.log_metric("total_analysis_time_seconds", analysis_time)
        for severity, count in severity_counts.items():
            # Use clean metric names
            mlflow.log_metric(f"severity_{severity.lower()}_count", count)
        
        return insights

    def cleanup(self):
        if "analyze_dependency" in st.session_state:
            del st.session_state["analyze_dependency"]
            mlflow.log_param("cleanup_status", "success")
