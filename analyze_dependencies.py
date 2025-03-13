import os
import json
import dspy
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
LOG_FILE = "project.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a"),
        logging.StreamHandler()
    ]
)

# Fetch Groq API key from environment variables
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY not found in environment variables")

# Corrected: Configure DSPy to use Groq's Llama3.3 70B model
llm = dspy.LM(
    model="groq/llama3-70b-8192",
    api_key=groq_api_key
)
dspy.settings.configure(lm=llm)

# Define DSPy Signature for Dependency Analysis
class DependencyAnalysis(dspy.Signature):
    """Analyzes dependency updates and provides insights."""
    dependency_info = dspy.InputField()
    security_changes = dspy.OutputField(desc="Security risks mitigated or introduced")
    deprecated_methods = dspy.OutputField(desc="Deprecated methods or breaking changes")
    code_changes = dspy.OutputField(desc="Probable code modifications needed")

# Create DSPy predictor using ChainOfThought
analyze_dependency = dspy.ChainOfThought(DependencyAnalysis)

def read_input_prompt(file_path="input_prompt.json"):
    """Reads the input JSON containing dependency details."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {e}")
        return None

def generate_dependency_insights(dependencies):
    """Calls DSPy LLM to fetch insights for each dependency."""
    insights = {}

    # for artifact, details in dependencies:
    #     dependency_info = (
    #         f"Artifact: {artifact}, Group ID: {details['group_id']}, "
    #         f"Current Version: {details['current_version']}, Latest Version: {details['latest_version']}"
    #     )
    for artifact, dep in dependencies.items():
        details = dep
        # print(f"Artifact: {artifact}, Group ID: {dep.group_id}, Current Version: {dep.current_version}, Latest Version: {dep.latest_version}")
        dependency_info = (
            f"Artifact: {artifact}, Group ID: {dep.group_id}, "
            f"Current Version: {dep.current_version}, Latest Version: {dep.latest_version}"
        )

        logging.info(f"Analyzing dependency: {artifact}")

        # Call DSPy LLM for analysis
        response = analyze_dependency(dependency_info=dependency_info)

        insights[artifact] = {
            "security_changes": response.security_changes,
            "deprecated_methods": response.deprecated_methods,
            "code_changes": response.code_changes
        }
        # print(f"insights: {insights}")

    return insights

def main():
    """Main function to process dependencies and fetch insights."""
    dependencies = read_input_prompt()

    if not dependencies:
        logging.error("No dependencies found to analyze.")
        return

    insights = generate_dependency_insights(dependencies)

    print("\n **Dependency Analysis Report:**\n")
    for artifact, analysis in insights.items():
        print(f"🔹 **{artifact}**\n")
        print(f"   🔹 Security Changes: {analysis['security_changes']}\n")
        print(f"   🔹 Deprecated Methods: {analysis['deprecated_methods']}\n")
        print(f"   🔹 Code Changes: {analysis['code_changes']}\n")

if __name__ == "__main__":
    main()

def generateDelta(dependencies):
    # dependencies = read_input_prompt()
    print(f"dependencies: {dependencies}")
    if not dependencies:
        logging.error("No dependencies found to analyze.")
        return

    insights = generate_dependency_insights(dependencies)

    # print("\n **Dependency Analysis Report:**\n")
    # for artifact, analysis in insights.items():
    #     print(f"🔹 **{artifact}**\n")
    #     print(f"   🔹 Security Changes: {analysis['security_changes']}\n")
    #     print(f"   🔹 Deprecated Methods: {analysis['deprecated_methods']}\n")
    #     print(f"   🔹 Code Changes: {analysis['code_changes']}\n")

    return insights
