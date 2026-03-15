"""FastAPI backend for the AI Personal Assistant."""

import json
import os
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from agent import stream_response

app = FastAPI(title="AI Personal Assistant API", version="1.0.0")

# CORS for mobile app
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]


@app.get("/health")
async def health():
    return {"status": "ok", "model": "claude-opus-4-6"}


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time streaming AI responses."""
    await websocket.accept()
    try:
        while True:
            # Receive message history from client
            data = await websocket.receive_text()
            payload = json.loads(data)
            messages = payload.get("messages", [])

            # Stream response events back to client
            async for event in stream_response(messages):
                await websocket.send_text(event)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(
            json.dumps({"type": "error", "message": str(e)})
        )


@app.post("/chat")
async def chat_http(request: ChatRequest):
    """HTTP endpoint for non-streaming chat (fallback)."""
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    full_text = ""
    tool_events = []

    async for event_str in stream_response(messages):
        event = json.loads(event_str)
        if event["type"] == "text_delta":
            full_text += event["text"]
        elif event["type"] in ("tool_executing", "tool_result"):
            tool_events.append(event)

    return {
        "response": full_text,
        "tool_events": tool_events,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
