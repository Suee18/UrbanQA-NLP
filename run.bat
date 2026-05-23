@echo off
REM ============================================================
REM  Germany RAG — power up EVERYTHING with one command.
REM  Usage:  run.bat   (or double-click it)
REM  Starts 3 services, each in its own window:
REM    1. LangGraph dev server   http://127.0.0.1:2024
REM    2. Agent Chat UI          http://localhost:3000
REM    3. Streamlit app          http://localhost:8501
REM ============================================================
cd /d "%~dp0"

echo [1/3] Starting LangGraph dev server (http://127.0.0.1:2024) ...
start "Germany RAG - LangGraph server" cmd /k "set HF_HUB_DISABLE_XET=1 && venv-studio\Scripts\langgraph.exe dev --no-browser --no-reload --port 2024"

echo       waiting for the server to come up ...
timeout /t 12 /nobreak >nul

echo [2/3] Starting Agent Chat UI (http://localhost:3000) ...
start "Germany RAG - Agent Chat UI" cmd /k "cd agent-chat-ui && corepack pnpm dev"

echo [3/3] Starting Streamlit app (http://localhost:8501) ...
start "Germany RAG - Streamlit" cmd /k "set HF_HUB_DISABLE_XET=1 && streamlit run rag\app.py --server.port 8501"

echo.
echo ============================================================
echo  All services launching. Open in your browser:
echo    Chat UI   : http://localhost:3000
echo    Streamlit : http://localhost:8501
echo    LangGraph : http://127.0.0.1:2024
echo    Studio    : https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
echo    Traces    : LangSmith project "germany-rag"
echo.
echo  Close the 3 opened windows to stop everything.
echo ============================================================
pause
