#!/bin/bash
echo "Setting up UrbanQA..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_lg
mkdir -p data/raw data/processed data/indexes data/gold_qa
echo "Done. Run: source venv/bin/activate"