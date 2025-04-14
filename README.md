# Usage

### Pre-requisites  
Follow this [Setup Guide](https://github.com/vinitdadyala/adu-ai-agent/blob/main/SETUP.md).

---

## 1️⃣ `home.py`  
Accepts Github Url details and parses a `pom.xml` file under the root level of the repo to give a detailed analysis report

### **Run the script**:
```sh
streamlit run home.py
```

## 2️⃣ `Runnning the Unit tests`  
As of now, functions under `utils.py` are covered

### **Run the tests**:
```sh
# Run just the specific tests
pytest utils_git_test.py -v -k "test_create_pull_request"

# Run with coverage
pytest --cov=utils_git --cov-report=term-missing utils_git_test.py -v
```
## Application Overview

![image](https://github.com/user-attachments/assets/75eea749-9ee8-4c48-b1ff-cd56dea04bce)

<img width="1511" alt="image" src="https://github.com/user-attachments/assets/d038f755-8371-45db-9364-3276ee693a70" />

<img width="757" alt="image" src="https://github.com/user-attachments/assets/02622aa5-a517-4c61-8aee-3e3b37cb8693" />

<img width="582" alt="image" src="https://github.com/user-attachments/assets/406eec66-930c-4856-89fa-336ef451441e" />



