@echo off
echo Setting up UrbanQA...
python -m venv venv
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_lg
mkdir data\raw data\processed data\indexes data\gold_qa
echo Done. Run: venv\Scripts\activate