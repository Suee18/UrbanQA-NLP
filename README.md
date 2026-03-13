## Quickstart

### 1. Clone and setup
# Mac/Linux
bash setup/setup.sh

# Windows
setup\setup.bat

### 2. Activate environment (every new terminal session)
# Mac/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

### 3. Adding a new library?
pip install new-library
pip freeze > requirements.txt
git add requirements.txt
git commit -m "add new-library to requirements"