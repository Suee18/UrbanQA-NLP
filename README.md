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


# Main 
# first time ever — runs everything including data collection
python main.py

# already have raw data, just rerun preprocessing
python main.py --skip-collection

# run one specific stage
python main.py --stage cleaner
python main.py --stage segmenter