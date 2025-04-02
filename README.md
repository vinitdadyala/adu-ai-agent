# Usage

### Pre-requisites  
Follow this [Setup Guide](https://github.com/vinitdadyala/adu-ai-agent/blob/main/SETUP.md).

---

## 1️⃣ `main.py`  
Accepts Github Url details and parses a `pom.xml` file under the root level of the repo to give a detailed analysis report

### **Run the script**:
```sh
streamlit run main.py
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
