import mlflow
import os
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Dict, Optional, List

import streamlit as st
from utils.utils import (
    find_pom_file, 
    parse_pom, 
    fetch_latest_versions, 
    dependencies_to_dataframe
)
from utils.utils_git import (
    clone_github_repo, 
    generate_branch_name,
    parse_github_url, 
    commit_and_push_changes, 
    create_pull_request
)
from utils.utils_code_analysis import analyze_dependencies
from utils.utils_code_replacement import (
    analyze_and_replace,
    analyze_project_code,
    get_replacement_llm,
    normalize_insights,
    update_pom_with_latest_versions
)

@dataclass
class AnalysisState:
    """State management for dependency analysis"""
    repo_path: Optional[Path] = None
    branch_name: Optional[str] = None
    insights: Optional[Dict] = None
    dependencies: Optional[Dict] = None
    github_url: Optional[str] = None
    access_token: Optional[str] = None

class DependencyAnalyzer:
    def __init__(self):
        self.state = AnalysisState()
        self.setup_mlflow()
        self.setup_page()

    def setup_mlflow(self):
        """Configure MLflow tracking"""
        mlflow.set_tracking_uri("http://localhost:5000")
        mlflow.set_experiment("Migration to new agentic flow")

    def setup_page(self):
        """Configure Streamlit page"""
        st.title("📦 Java Dependency Analyzer")
        st.markdown("Analyze and modernize your Java project with AI-powered insights.")

    def get_user_inputs(self):
        """Collect user inputs"""
        self.state.github_url = st.text_input("🔗 GitHub Repository URL")
        self.state.access_token = st.text_input(
            "🔐 GitHub Access Token (optional if public)", 
            type="password"
        )

    def clone_repository(self):
        """Clone and setup repository"""
        with st.spinner("⏳ Cloning repository..."):
            temp_dir = Path(tempfile.mkdtemp())
            repo_path = temp_dir / "repo"
            self.state.repo_path = Path(clone_github_repo(
                self.state.github_url, 
                str(repo_path), 
                self.state.access_token
            ))
            st.write(f"✅ Repo cloned at: `{self.state.repo_path}`")
            return os.getcwd()

    def create_branch(self):
        """Create new branch for updates"""
        with st.spinner("🌿 Creating upgrade branch..."):
            self.state.branch_name = generate_branch_name("upgrade_deps")
            subprocess.run(
                ["git", "checkout", "-b", self.state.branch_name], 
                cwd=self.state.repo_path, 
                check=True
            )
            st.info(f"✅ Switched to new branch: `{self.state.branch_name}`")

    def analyze_dependencies(self):
        """Analyze project dependencies"""
        with st.spinner("📄 Parsing pom.xml..."):
            pom_path = next(
                (p for p in self.state.repo_path.rglob("pom.xml")), 
                None
            )
            if not pom_path:
                raise FileNotFoundError("❌ pom.xml not found")

            self.state.dependencies = parse_pom(str(pom_path))
            self.state.dependencies = fetch_latest_versions(self.state.dependencies)

            st.subheader("📋 Parsed Dependencies")
            st.dataframe(dependencies_to_dataframe(self.state.dependencies))

            with st.spinner("🧠 Analyzing with DSPy (Groq)..."):
                self.state.insights = analyze_dependencies(self.state.dependencies)
                st.success("✅ Dependency insights generated")
            return pom_path

    def display_insights(self):
        """Display analysis results"""
        st.markdown("### 📊 Dependency Insights")
        for artifact, insight in self.state.insights.items():
            with st.expander(f"📦 {artifact} ({insight.get('severity_level', 'Unknown')})"):
                st.markdown(f"**🔐 Security Changes:**\n```\n{insight['security_changes']}\n```")
                st.markdown(f"**🧹 Deprecated Methods:**\n```\n{insight['deprecated_methods']}\n```")
                st.markdown(f"**🛠 Code Changes:**\n```\n{insight['code_changes']}\n```")
                st.markdown(f"**🚨 Severity Level:** `{insight['severity_level']}`")
                st.markdown("**🔗 Sources:**")
                for src in insight["sources"]:
                    st.markdown(f"- [{src}]({src})")

    def save_state(self):
        """Save analysis state"""
        st.session_state.update({
            "repo_path": self.state.repo_path,
            "branch_name": self.state.branch_name,
            "insights": self.state.insights,
            "github_url": self.state.github_url,
            "access_token": self.state.access_token,
            "dependencies": self.state.dependencies
        })

    def update_code(self, pom_path: Path):
        """Update project code with new dependencies"""
        try:
            with st.spinner("📦 Updating pom.xml..."):
                update_pom_with_latest_versions(pom_path, self.state.dependencies)
                st.success("📦 pom.xml updated")

            dspy_chain = get_replacement_llm()
            with st.spinner("🧠 Rewriting Java code..."):
                result_summary = analyze_project_code(
                    self.state.repo_path, 
                    self.state.insights
                )
                st.success(f"✅ Code updated: {len(result_summary)} files modified")
                return result_summary
        except Exception as e:
            st.error(f"❌ Code update failed: {str(e)}")
            return None

    def create_pull_request(self, result_summary: Dict):
        """Create and push pull request"""
        try:
            with st.spinner("📤 Committing changes..."):
                commit_and_push_changes(
                    self.state.branch_name, 
                    self.state.repo_path
                )

            with st.spinner("🔃 Creating Pull Request..."):
                owner, repo = parse_github_url(self.state.github_url)
                pr_url = create_pull_request(
                    owner, 
                    repo, 
                    self.state.access_token, 
                    self.state.branch_name
                )
                st.success(f"🎉 [View Pull Request]({pr_url})")
        except Exception as e:
            st.error(f"❌ Pull request creation failed: {str(e)}")

    def display_results(self, result_summary: Dict):
        """Display code modification results"""
        if result_summary:
            st.subheader("🪄 Files Modified")
            for full_path in result_summary:
                file_name = os.path.basename(full_path)
                st.markdown(f"- `{file_name}`")

            st.subheader("🪄 Replacement Summary")
            for full_path, changes in result_summary.items():
                file_name = os.path.basename(full_path)
                with st.expander(file_name):
                    if changes:
                        for change in changes:
                            st.markdown(f"- {change}")
                    else:
                        st.markdown("_No specific changes listed._")

    def run(self):
        """Main execution flow"""
        self.get_user_inputs()

        if st.button("🚀 Run Dependency Analysis"):
            try:
                with mlflow.start_run(run_name="Dependency Analysis"):
                    mlflow.log_param("Analysis begin", st.session_state)
                    original_cwd = self.clone_repository()
                    self.create_branch()
                    pom_path = self.analyze_dependencies()
                    self.display_insights()
                    self.save_state()

                    if st.checkbox("🔍 Show Raw Insights"):
                        st.json(self.state.insights)

                    result_summary = self.update_code(pom_path)
                    if result_summary:
                        self.display_results(result_summary)
                        self.create_pull_request(result_summary)

                    st.success("✅ Analysis complete!")
                    mlflow.log_param("Analysis completed", st.session_state)
                    os.chdir(original_cwd)

            except Exception as e:
                st.error(f"❌ Something went wrong: {str(e)}")
                mlflow.log_param("Error", str(e))

if __name__ == "__main__":
    analyzer = DependencyAnalyzer()
    analyzer.run()