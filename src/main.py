import streamlit as st
import mlflow
import os
from pathlib import Path
import subprocess
import tempfile
import streamlit as st
from utils.utils import parse_pom, fetch_latest_versions, dependencies_to_dataframe, find_pom_file
from utils.utils_git import clone_github_repo, generate_branch_name, commit_and_push_changes, create_pull_request, parse_github_url
from utils.utils_git import parse_github_url
from utils.utils_code_analysis import analyze_dependencies  # Your DSPy Groq chain
from utils.utils_code_replacement import analyze_and_replace, analyze_project_code, get_replacement_llm, normalize_insights, update_pom_with_latest_versions

st.session_state.clear()

st.set_page_config(page_title="Java Auto-Upgrader", layout="wide")
st.title("🚀 Java Dependency & Code Auto-Upgrader")

# --- INPUTS ---
github_url = st.text_input("🔗 GitHub Repository URL")
access_token = st.text_input("🔐 GitHub Access Token (optional if public)", type="password")

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("Migration to new agentic flow")

if st.button("🚀 Run Dependency Analysis"):
    try:
        with mlflow.start_run(run_name="Dependency Analysis"):
            mlflow.log_param("Analaysis begin", st.session_state)   

        with st.spinner("⏳ Cloning repository..."):
            temp_dir = Path(tempfile.mkdtemp())  # e.g., C:\Users\<you>\AppData\Local\Temp\...
            repo_path = temp_dir / "repo"
            repo_path = Path(clone_github_repo(github_url, str(repo_path), access_token))
            st.write(f"✅ Repo cloned at: `{repo_path}`")
            st.write("📁 Files at root:", os.listdir(repo_path))
            original_cwd = os.getcwd()
            os.chdir(repo_path)

        with st.spinner("🌿 Creating upgrade branch..."):
            branch_name = generate_branch_name("upgrade_deps")
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, check=True)
            st.info(f"✅ Switched to new branch: `{branch_name}`")

        with st.spinner("📄 Parsing pom.xml..."):
            pom_path = None
            for root, _, files in os.walk(repo_path):
                if "pom.xml" in files:
                    pom_path = os.path.join(root, "pom.xml")
                    break
            if not pom_path:
                st.error("❌ `pom.xml` not found.")
                st.stop()

            dependencies = parse_pom(pom_path)
            dependencies = fetch_latest_versions(dependencies)

        st.subheader("📋 Parsed Dependencies")
        st.dataframe(dependencies_to_dataframe(dependencies))

        with st.spinner("🧠 Analyzing with DSPy (Groq)..."):
            insights = analyze_dependencies(dependencies)
            st.success("Dependency insights generated ✅")

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

        # --- STORE STATE ---
        st.session_state["repo_path"] = repo_path
        st.session_state["branch_name"] = branch_name
        st.session_state["insights"] = insights
        st.session_state["github_url"] = github_url
        st.session_state["access_token"] = access_token
        st.session_state["dependencies"] = dependencies

        st.success("✅ Analysis complete. Proceed to the next step below.")
        mlflow.log_param("Analaysis completed", st.session_state)
        os.chdir(original_cwd)

        # repo_path = st.session_state["repo_path"]
        # insights = st.session_state["insights"]
        # dependencies = st.session_state["dependencies"]
        # branch_name = st.session_state["branch_name"]
        # github_url = st.session_state["github_url"]
        # access_token = st.session_state["access_token"]
        insights = normalize_insights(insights)
        pom_path=find_pom_file(repo_path)


        # if st.checkbox("🔍 Show Raw Insights"):
        #     st.json(insights)

        # if st.button("🔧 Run Code Replacement"):
        #     try:
        with st.spinner("📦 Updating pom.xml with latest dependency versions..."):
            update_pom_with_latest_versions(pom_path, dependencies)
            st.success("📦 pom.xml updated with latest dependency versions.")
        dspy_chain = get_replacement_llm()
        with st.spinner("🧠 Rewriting Java code based on insights..."):
            result_summary = analyze_project_code(repo_path, insights)
            st.success(f"✅ Java source code updated. {len(result_summary)} files modified.")

            if result_summary:
                st.subheader("🪄 Files Modified")
                for full_path in result_summary:
                    file_name = os.path.basename(full_path)
                    st.markdown(f"- `{file_name}`")

        # --- Replacement Summary Section ---
        st.subheader("🪄 Replacement Summary")
        for full_path, changes in result_summary.items():
            file_name = os.path.basename(full_path)
            with st.expander(file_name):
                if changes:
                    for change in changes:
                        st.markdown(f"- {change}")
                else:
                    st.markdown("_No specific changes listed._")

        with st.spinner("📤 Committing and pushing to GitHub..."):
            commit_and_push_changes(branch_name, repo_path)

        with st.spinner("🔃 Creating Pull Request..."):
            owner, repo = parse_github_url(github_url)
            pr_url = create_pull_request(owner, repo, access_token, branch_name)
            st.success(f"🎉 Pull Request Created: [View PR]({pr_url})")

    except Exception as e:
        st.error(f"❌ Something went wrong: {e}")
        mlflow.log_param("Error", e)
