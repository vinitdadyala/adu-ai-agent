# Java Dependency & Code Auto-Upgrader 🚀

Java Dependency & Code Auto-Upgrader (ADU-AI-Agent) is a sophisticated MLOps-enabled tool built with Python that automates the process of analyzing and upgrading Java dependencies in Maven projects. 

## Technical Overview 🔍

### 1. Architecture & Core Technologies 🏗️
- **Frontend**: Streamlit-based web interface 🌐
- **Backend**: Python with MLflow for experiment tracking and monitoring 🐍
- **AI Integration**: DSPy framework with Groq LLM for dependency analysis 🤖
- **Version Control**: Git integration for automated PR creation 🔄

### 2. Key Capabilities ⚡
- Automated POM file parsing and dependency version analysis 📊
- Security vulnerability assessment 🛡️
- Deprecated method detection 🔍
- Intelligent code modification suggestions 💡
- Automated pull request generation with suggested updates ⚙️

### 3. MLOps Features 📈
- Experiment tracking via MLflow 📊
- Metrics and parameter logging 📝
- Run history and artifact storage 🗄️
- Performance monitoring 📉

### 4. Infrastructure 🌐
- Local MLflow server for experiment tracking (port 5000)
- MLflow UI for visualization (port 5001)
- Streamlit server for web interface

The system employs a modular architecture with separate agents for dependency analysis and code replacement, backed by comprehensive unit testing and version control integration.

---

# Usage

### Pre-requisites  
Follow this [Setup Guide](https://github.com/vinitdadyala/adu-ai-agent/blob/main/SETUP.md).

---
## 1. `Start MLflow for Tracking, experimentation and evaluation` [MANDATORY step]

### **Start MLFLOW Local tracking**
```sh
mlflow ui --port 5001
```
### **Start MLFLOW server for experiments**
```sh
mlflow server --host 127.0.0.1 --port 5000
```

## 2. `Starting the UI`  
Accepts Github Url details and parses a `pom.xml` file under the root level of the repo to give a detailed analysis report

### **Run the script**:
```sh
streamlit run src/main.py
```

## 3. `Runnning the Unit tests`  
As of now, functions under `utils.py` are covered

### **Run the tests**:
```sh
# Run just the specific tests
pytest utils_git_test.py -v -k "test_create_pull_request"

# Run with coverage
pytest --cov=utils_git --cov-report=term-missing utils_git_test.py -v
```


## 4. Application Overview

![image](https://github.com/user-attachments/assets/ddb45a44-189e-4485-9ec6-33787e253c0f)

![image](https://github.com/user-attachments/assets/75eea749-9ee8-4c48-b1ff-cd56dea04bce)

<img width="1511" alt="image" src="https://github.com/user-attachments/assets/d038f755-8371-45db-9364-3276ee693a70" />

<img width="757" alt="image" src="https://github.com/user-attachments/assets/02622aa5-a517-4c61-8aee-3e3b37cb8693" />

<img width="582" alt="image" src="https://github.com/user-attachments/assets/406eec66-930c-4856-89fa-336ef451441e" />



