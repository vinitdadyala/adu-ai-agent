import streamlit as st

st.session_state.clear()

st.set_page_config(page_title="Java Auto-Upgrader", layout="wide")
st.title("🚀 Java Dependency & Code Auto-Upgrader")

st.markdown("""
Welcome to the **Java Auto-Upgrader**!  
This tool helps you **analyze your `pom.xml`**, detect **deprecated/insecure dependencies**, and then **automatically update** your Java code using **AI-powered replacements**.

---

### 🧭 How to Use:
1. 👉 Go to **Dependency Analysis** to upload or analyze your project.
2. 🧹 After analysis, navigate to **Code Replacement** to apply updates.
3. 🔃 The tool will create a Pull Request with all changes!

---
""")

st.page_link("pages/code_analysis.py", label="➡️ Start with Dependency Analysis", icon="📦")
