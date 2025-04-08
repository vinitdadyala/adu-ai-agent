import streamlit as st
import os

import shutil

from utils_code_analysis import analyze_and_replace, analyze_dependencies
from utils import dependencies_to_dataframe, fetch_latest_versions, find_pom_file, parse_pom
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
            try:
                pom_path = find_pom_file(repo_path)
            except FileNotFoundError:
                st.error("No pom.xml found in the repository.")
                st.stop()
            dependencies=parse_pom(pom_path)

            # Run DSPy Analysis
            dependencies = parse_pom(pom_path)
            dependencies = fetch_latest_versions(dependencies)
            st.subheader("📦 Parsed Dependencies")
            st.dataframe(dependencies_to_dataframe(dependencies))
            insights = analyze_dependencies(dependencies)
            st.success("Dependency insights ready ✅")
            st.markdown("### 📊 Dependency Insights")
            for artifact, insight in insights.items():
                with st.expander(f"📦 {artifact} ({insight.get('severity_level', 'Unknown')})"):
                    st.markdown(f"**🔐 Security Changes:**\n```\n{insight['security_changes']}\n```", unsafe_allow_html=True)
                    st.markdown(f"**🧹 Deprecated Methods:**\n```\n{insight['deprecated_methods']}\n```", unsafe_allow_html=True)
                    st.markdown(f"**🛠 Code Changes:**\n```\n{insight['code_changes']}\n```", unsafe_allow_html=True)
                    st.markdown(f"**🚨 Severity Level:** `{insight['severity_level']}`")
                    st.markdown("**🔗 Sources:**")
                    for src in insight["sources"]:
                        st.markdown(f"- [{src}]({src})")


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
