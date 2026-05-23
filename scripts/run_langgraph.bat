@echo off
REM Starts the LangGraph dev server + the local Agent Chat UI in two windows.
cd /d E:\CS\NLP\urbanqa

echo Starting LangGraph dev server (http://127.0.0.1:2024)...
start "LangGraph server" cmd /k "set HF_HUB_DISABLE_XET=1 && venv-studio\Scripts\langgraph.exe dev --no-browser --no-reload --port 2024"

echo Waiting for the server to come up...
timeout /t 12 /nobreak >nul

echo Starting Agent Chat UI (http://localhost:3000)...
start "Agent Chat UI" cmd /k "cd agent-chat-ui && corepack pnpm dev"

echo.
echo  Chat UI : http://localhost:3000
echo  API     : http://127.0.0.1:2024
echo  Studio  : https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
echo.
echo Close the two opened windows to stop the servers.
pause
