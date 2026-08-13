import sys
from pathlib import Path

# Data klasöründeki dosyaları içe aktarabilmek için yolu ekliyoruz
from scraper import get_llm_response

sys.path.append(str(Path(__file__).resolve().parent.parent / "data"))
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Bizim Yapay Zeka Backend")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

@app.get("/")
def home():
    return {"status": "Backend calisiyor!"}

@app.post("/v1/chat/completions")
def chat(request: ChatRequest):
    user_message = request.messages[-1].content if request.messages else "Merhaba"
    bot_response = f"Backend mesajınızı aldı: '{user_message}'"

    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": bot_response
                },
                "finish_reason": "stop"
            }
        ]
    }