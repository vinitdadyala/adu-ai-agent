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

### **UI Previews**:
1. **When GitHub Repo details OR access are not good **:  
   <img width="432" alt="image" src="https://github.com/user-attachments/assets/f2f89c8a-dd5d-4a1d-beb4-e8bd51ceec0d" />

2. **When dependencies are found for valid GitHub repo Url**:  
   <img width="432" alt="image" src="https://github.com/user-attachments/assets/5c810da6-f3a6-469c-b848-ed93f33621b2" />


---

## 2️⃣ `Runnning the Unit tests`  
As of now, functions under `utils.py` are covered

### **Run the tests**:
```sh
pytest --cov=utils --cov-report=term-missing utils_test.py 
```
