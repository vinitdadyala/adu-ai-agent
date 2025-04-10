import os
import streamlit as st
from utils.utils import find_pom_file
from utils.utils_code_replacement import analyze_and_replace, analyze_project_code, get_replacement_llm, normalize_insights, update_pom_with_latest_versions
from utils.utils_git import commit_and_push_changes, create_pull_request, parse_github_url

# --- PAGE CONFIG ---
st.set_page_config(page_title="🧹 Code Replacement", layout="wide")
st.title("🧹 Java Code Upgrader")
st.markdown("Update deprecated or insecure Java code using insights from your dependency analysis.")

# --- REQUIRE ANALYSIS ---
if "repo_path" not in st.session_state or "insights" not in st.session_state:
    st.warning("⚠️ Please run Dependency Analysis first.")
    st.page_link("1_📦_Dependency_Analysis.py", label="⬅️ Go to Dependency Analysis")
    st.stop()

repo_path = st.session_state["repo_path"]
insights = st.session_state["insights"]
branch_name = st.session_state["branch_name"]
github_url = st.session_state["github_url"]
access_token = st.session_state["access_token"]
insights = normalize_insights(insights)
pom_path=find_pom_file(repo_path)


if st.checkbox("🔍 Show Raw Insights"):
    st.json(insights)

if st.button("🔧 Run Code Replacement"):
    try:
        with st.spinner("📦 Updating pom.xml with latest dependency versions..."):
            update_pom_with_latest_versions(pom_path, insights)
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
        st.error(f"❌ Something went wrong during code replacement: {e}")
