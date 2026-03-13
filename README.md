## Quickstart

### 1. Clone and setup
Run the setup script for your OS:

**Mac/Linux**
```bash
bash setup/setup.sh
```

**Windows**
```powershell
setup\setup.bat
```

### 2. Activate environment (every new terminal session)
Activate the virtual environment each time you open a new terminal:

**Mac/Linux**
```bash
source venv/bin/activate
```

**Windows**
```powershell
venv\Scripts\activate
```

### 3. Set up NewsAPI key
1. Register for a free API key at [newsapi.org](https://newsapi.org).
2. Create a `.env` file in the project root and add:

```env
NEWSAPI_KEY=your_key_here
```

Note: `.env` is gitignored, so each teammate needs their own key.

### 4. Run the pipeline
Use the command that matches your workflow:

```bash
# First time: runs everything, including data collection
python main.py

# If raw data already exists: skip collection
python main.py --skip-collection

# Run a specific stage
python main.py --stage cleaner
python main.py --stage segmenter
python main.py --stage Tokenizer
```

### 5. Adding a new library?
```bash
pip install new-library
pip freeze > requirements.txt
git add requirements.txt
git commit -m "add new-library to requirements"
```