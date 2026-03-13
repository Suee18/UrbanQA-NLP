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

### 3. Set up NewsAPI key
Register for a free API key at https://newsapi.org
Create a .env file in the project root and add:

NEWSAPI_KEY=your_key_here

Note: .env is gitignored — every teammate needs their own key.

### 4. Run the pipeline
# First time — runs everything including data collection
python main.py

# Already have raw data, just rerun preprocessing
python main.py --skip-collection

# Run one specific stage
python main.py --stage cleaner
python main.py --stage segmenter
python main.py --stage Tokenizer

### 5. Adding a new library?
pip install new-library
pip freeze > requirements.txt
git add requirements.txt
git commit -m "add new-library to requirements"