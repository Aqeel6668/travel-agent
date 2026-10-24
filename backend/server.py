"""
Small web API around the agent, so the React app can talk to it.

Run:  python -m uvicorn server:app --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from travel_agent import SYSTEM_PROMPT, run_agent

app = FastAPI(title="Travel Agent API")

# Allow the React dev server to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# One conversation history per browser session (kept in memory)
sessions: dict[str, list] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ResetRequest(BaseModel):
    session_id: str


@app.post("/chat")
def chat(req: ChatRequest):
    messages = sessions.setdefault(
        req.session_id, [{"role": "system", "content": SYSTEM_PROMPT}]
    )
    messages.append({"role": "user", "content": req.message})
    try:
        reply, tools = run_agent(messages)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {e}. Is Ollama running and is llama3.2 installed?",
        )
    return {"reply": reply, "tools": tools}


@app.post("/reset")
def reset(req: ResetRequest):
    sessions.pop(req.session_id, None)
    return {"ok": True}
