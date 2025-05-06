import streamlit as st
import mlflow
import os
import time
from pathlib import Path
import subprocess
import tempfile
from utils.utils import parse_pom, fetch_latest_versions, dependencies_to_dataframe, find_pom_file
from utils.git_utils import clone_github_repo, generate_branch_name, commit_and_push_changes, create_pull_request, parse_github_url
from agents.dependency_analysis import DependencyAnalysisAgent
from agents.code_replacement import CodeReplacementAgent

st.session_state.clear()

st.set_page_config(page_title="Java Auto-Upgrader", layout="wide")

# Sidebar configuration
with st.sidebar:
    st.divider()
    github_url = st.text_input("🔗 GitHub Repository URL")
    access_token = st.text_input("🔐 GitHub Access Token (optional if public)", type="password")
    st.divider()
    with st.expander("ℹ️ About", expanded=False):
        st.markdown("""
        ### Java Dependency Upgrader
        
        This tool helps you:
        - 🔍 Analyze dependencies
        - ⬆️ Upgrade to latest versions
        - 🔧 Fix compatibility issues
        - 🤖 Auto-generate PRs
        
        [Documentation](https://github.com/vinitdadyala/adu-ai-agent?tab=readme-ov-file#java-dependency--code-auto-upgrader-)
        """)
   
# Main area title
st.title("🚀 Java Dependency & Code Auto-Upgrader")

# Initialize agents
if 'dependency_agent' not in st.session_state:
    st.session_state['dependency_agent'] = DependencyAnalysisAgent()
if 'code_agent' not in st.session_state:
    st.session_state['code_agent'] = CodeReplacementAgent()

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("Java Dependency Upgrade Analysis")

if st.button("🚀 Run Dependency Analysis and Replace Code"):
    try:
        start_time = time.time()
        with mlflow.start_run(run_name="Java Dependency Upgrade") as parent_run:
            try:
                # Log parent run parameters
                mlflow.log_param("github_url", github_url)
                mlflow.log_param("has_access_token", bool(access_token))
                
                st.markdown("## 1. Dependency Analysis")
                with st.spinner("⏳ Cloning repository..."):
                    temp_dir = Path(tempfile.mkdtemp())
                    repo_path = temp_dir / "repo"
                    repo_path = Path(clone_github_repo(github_url, str(repo_path), access_token))
                    mlflow.log_param("repo_path", str(repo_path))
                    st.info(f"✅ Repo cloned at: `{repo_path}`")
                    # st.write("📁 Files at root:", os.listdir(repo_path))
                    original_cwd = os.getcwd()
                    os.chdir(repo_path)

                with st.spinner("🌿 Creating upgrade branch..."):
                    branch_name = generate_branch_name("upgrade_deps")
                    subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, check=True)
                    mlflow.log_param("branch_name", branch_name)
                    st.info(f"✅ Switched to new branch: `{branch_name}`")

                # Dependency Analysis Phase
                with mlflow.start_run(run_name="Dependency Analysis", nested=True) as dep_run:
                    with st.spinner("📄 Parsing pom.xml..."):
                        pom_path = find_pom_file(repo_path)
                        if not pom_path:
                            st.error("❌ `pom.xml` not found.")
                            mlflow.log_param("error", "pom.xml not found")
                            st.stop()

                        dependencies = parse_pom(pom_path)
                        dependencies = fetch_latest_versions(dependencies)
                        mlflow.log_metric("total_dependencies", len(dependencies))

                    st.subheader("📋 Parsed Dependencies")
                    st.dataframe(dependencies_to_dataframe(dependencies))

                    with st.spinner("🧠 Analyzing with DSPy (Groq)..."):
                        insights = st.session_state['dependency_agent'].analyze_dependencies(dependencies)
                        mlflow.log_param("analysis_insights", str(insights)[:250])

                # Display insights
                st.markdown("### 📊 Dependency Insights")
                for artifact, insight in insights.items():
                    with st.expander(f"📦 {artifact} ({insight.get('severity_level', 'Unknown')})"):
                        st.markdown(f"**🔐 Security Changes:**\n```\n{insight['security_changes']}\n```")
                        st.markdown(f"**🧹 Deprecated Methods:**\n```\n{insight['deprecated_methods']}\n```")
                        st.markdown(f"**🛠 Code Changes:**\n```\n{insight['code_changes']}\n```")
                        st.markdown(f"**🚨 Severity Level:** `{insight['severity_level']}`")
                        st.markdown("**🔗 Sources:**")
                        for src in insight["sources"]:
                            st.markdown(f"- [{src}]({src})")

                # Store state
                st.session_state.update({
                    "repo_path": repo_path,
                    "branch_name": branch_name,
                    "insights": insights,
                    "github_url": github_url,
                    "access_token": access_token,
                    "dependencies": dependencies
                })

                st.markdown("## 2. Code replacement")
                os.chdir(original_cwd)

                # Code Replacement Phase
                with mlflow.start_run(run_name="Code Replacement", nested=True) as code_run:
                    insights = st.session_state['code_agent'].normalize_insights(insights)

                    with st.spinner("📦 Updating pom.xml with latest dependency versions..."):
                        st.session_state['code_agent'].update_pom_with_latest_versions(pom_path, dependencies)
                        st.info("📦 pom.xml updated with latest dependency versions.")

                    with st.spinner("🧠 Rewriting Java code based on insights..."):
                        result_summary = st.session_state['code_agent'].analyze_project_code(repo_path, insights)
                        mlflow.log_metric("files_modified", len(result_summary) if result_summary else 0)
                        st.info(f"✅ Java source code updated. {len(result_summary)} files modified.")

                        if result_summary:
                            st.subheader("🪄 Files Modified")
                            for full_path in result_summary:
                                file_name = os.path.basename(full_path)
                                st.markdown(f"- `{file_name}`")

                # Git Operations Phase
                with mlflow.start_run(run_name="Git Operations", nested=True) as git_run:
                    with st.spinner("📤 Committing and pushing to GitHub..."):
                        commit_and_push_changes(branch_name, repo_path)
                        mlflow.log_param("git_commit_status", "success")

                    with st.spinner("🔃 Creating Pull Request..."):
                        owner, repo = parse_github_url(github_url)
                        pr_url = create_pull_request(owner, repo, access_token, branch_name)
                        mlflow.log_param("pr_url", pr_url)
                        st.success(f"🎉 Pull Request Created: [View PR]({pr_url})")

                # Log final execution metrics in parent run
                end_time = time.time()
                execution_time = end_time - start_time
                mlflow.log_metric("execution_time_seconds", execution_time)
                mlflow.set_tag("run_status", "completed")

            except Exception as e:
                st.error(f"❌ Something went wrong: {e}")
                mlflow.log_param("error", str(e))
                mlflow.set_tag("run_status", "failed")

            finally:
                # Cleanup and log final status
                st.session_state['dependency_agent'].cleanup()
                st.session_state['code_agent'].cleanup()
                if not mlflow.active_run():
                    mlflow.end_run()
                else:
                    mlflow.set_tag("run_status", "completed")
    except Exception as outer_e:
        st.error(f"❌ Fatal error occurred: {outer_e}")
        if mlflow.active_run():
            mlflow.set_tag("run_status", "failed")
            mlflow.end_run()
