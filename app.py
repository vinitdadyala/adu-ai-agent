import streamlit as st
import os

import shutil

from main import analyze_and_replace, analyze_dependencies
from utils import parse_pom
from utils_git import clone_github_repo, commit_and_push_changes, create_pull_request, generate_branch_name, parse_github_url

st.set_page_config(page_title="AI Dependency Upgrader", layout="wide")
st.title("AI Dependency Upgrader")

github_url = st.text_input("GitHub Repository URL")
access_token = st.text_input("GitHub Token", type="password")

if st.button("🚀 Run Full Upgrade Flow"):
    try:
        with st.spinner("⏳ Cloning repository..."):
            target_path = "/tmp/test"
            repo_path = clone_github_repo(github_url, target_path, access_token)
            st.write(f"✅ Repo cloned at: `{repo_path}`")
            st.write("📁 Files at root:", os.listdir(repo_path))  # 👈 Show contents
            os.chdir(repo_path)

        with st.spinner("🌿 Creating new branch..."):
            # Create branch
            branch_name = generate_branch_name("upgrade_deps")
            os.system(f"git checkout -b {branch_name}")

        with st.spinner("🔍 Analyzing dependencies..."):
            # Parse pom.xml & generate input_prompt.json
            pom_path = os.path.join(repo_path, "pom.xml")
            if not os.path.exists(pom_path):
                st.error("No pom.xml found at root of repo.")
                st.stop()
            parse_pom(pom_path)

            # Run DSPy Analysis
            insights = analyze_dependencies("input_prompt.json")
            st.success("Dependency insights ready ✅")
            st.code(insights, language="markdown")

        with st.spinner("🛠️ Updating Java source code..."):
            # Apply code changes based on insights
            result = analyze_and_replace(repo_path, insights)
            st.success("Code replacement done ✅")
            st.code(result)

        with st.spinner("📤 Committing and pushing changes..."):
            # Commit + Push
            commit_and_push_changes(branch_name)

        with st.spinner("🔃 Creating pull request..."):
            # PR creation
            owner, repo = parse_github_url(github_url)
            pr_url = create_pull_request(owner, repo, access_token, branch_name)
            st.success(f"🎉 PR Created: [View PR]({pr_url})")

        # Optional: Cleanup
        shutil.rmtree(repo_path)

    except Exception as e:
        st.error(f"❌ Error: {e}")
