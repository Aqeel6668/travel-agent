# Travel Agent - Web App (React + TypeScript + Python)

- `backend/`  Python agent (Ollama, free) + FastAPI server on port 8000
- `frontend/` React + TypeScript (Vite) chat UI on port 5173

## Run (two terminals)

Terminal 1 - backend:
    cd backend
    python -m pip install -r requirements.txt
    python -m uvicorn server:app --port 8000

Terminal 2 - frontend:
    cd frontend
    npm install
    npm run dev

Open http://localhost:5173

Ollama must be installed with `ollama pull llama3.2` done.

## How it fits together
Browser (React) --POST /chat--> FastAPI (server.py) --> run_agent() --> Ollama + tools
