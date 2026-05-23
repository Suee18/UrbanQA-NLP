@echo off
REM Starts the Streamlit web UI (answer + node-by-node graph trace).
cd /d E:\CS\NLP\urbanqa
set HF_HUB_DISABLE_XET=1
echo Starting Streamlit at http://localhost:8501 ...
streamlit run rag\app.py --server.port 8501
