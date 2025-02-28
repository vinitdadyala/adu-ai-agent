# Installation

## 1. Install Visual Studio Code
Download and install **Visual Studio Code** from the official website:  
[VS Code Download](https://code.visualstudio.com/download)

### Windows and MacOS
- Run the installer and follow the default setup.
- Ensure the **"Add to PATH"** option is selected during installation.


## 2. Install Python 3.12
Download and install **Python 3.12** from the official website:  
[Python 3.12 Download](https://www.python.org/downloads/)

### Windows and MacOS
- Run the installer and check **"Add Python to PATH"** before proceeding.

## 3. Clone This Repository

To set up this project locally, follow these steps:

### **1️. Open a Terminal**
- On **Windows**: Open **Git Bash**, **Command Prompt**, or **PowerShell**  
- On **Mac/Linux**: Open the **Terminal**

### **2️. Navigate to the Directory Where You Want to Clone the Repo**
For example:
```sh
cd ~/Projects
```

### **3️. Clone the Repository**
Run the following command:
```sh
git clone https://github.com/vinitdadyala/adu-ai-agent.git
```
## Create a Virtual Environment and Install Dependencies

To set up a virtual environment and install all required libraries, follow these steps:

### . Create a Virtual Environment  
Open a terminal in the project directory and run:  

**On Windows (Command Prompt or PowerShell):**  
```sh
python -m venv .venv
```

**On Mac/Linux:**  
```sh
python3 -m venv .venv
```

This creates a `.venv` folder in the project directory.

### 2️. Activate the Virtual Environment  

**On Windows (Command Prompt):**  
```sh
.venv\Scripts\activate
```
**On Windows (PowerShell):**  
```sh
.venv\Scripts\Activate.ps1
```
(If you get a permissions error, run: `Set-ExecutionPolicy Unrestricted -Scope Process` and try again.)  

**On Mac/Linux:**  
```sh
source .venv/bin/activate
```

Once activated, your terminal should show `(venv)` or `(.venv)` at the beginning of the line.

### 3️. Install Dependencies  
Run the following command to install all required libraries from a text file:  
```sh
pip install -r requirements.txt
```

This will install all dependencies listed in `requirements.txt`.

### 4️. Verify Installation  
Check if the necessary packages are installed:  
```sh
pip list
```

The virtual environment is now set up and ready for use.

## Project Files Overview  

This repository contains two main Python scripts:  

### 1️⃣ `parser.py`  
This script is responsible for parsing an XML file and printing structured dependency details in the console.

#### Usage:  
Run the script using:  
```sh
python parser.py
```
Make sure the required XML file is present in the expected location.

### 2️⃣ `sample.py`  
This script uses the Groq API key and the `dspy` library to establish a connection with an LLM.  

#### Setting Up the API Key  
The API key is stored in a `.env` file. You can add your own key with this method after generating it on 

1. Create a `.env` file in the project directory if it does not already exist.  
2. Add the following line to the `.env` file:  
   ```ini
   GROQ_API_KEY=your_api_key_here
   ```
3. Save the file.

#### Loading the `.env` File  
The script automatically loads environment variables from `.env` using the `dotenv` library. Ensure this library is installed:  
```sh
pip install python-dotenv
```

#### Usage:  
Run the script using:  
```sh
python sample.py
```

If the API key is valid, the script should confirm a successful connection to the LLM by responding to the input prompt.
```sh
Question: What is the color of the sky?
Predicted Answer: Blue on a sunny day
```
