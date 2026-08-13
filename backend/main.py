from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(
    title="BAÜN BİDB Chatbot Backend (Gemini API Compatible)",
    version="1.0.0"
)

# CORS Ayarı
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Gemini API Şemaları ---

class Part(BaseModel):
    text: str

class Content(BaseModel):
    role: Optional[str] = "user"
    parts: List[Part]

class GeminiRequest(BaseModel):
    contents: List[Content]

@app.get("/")
def home():
    return {"status": "Gemini Uyumlu Backend Sunucusu Aktif!"}

# Gemini Uyumlu Endpoint Yapısı: :generateContent
@app.post("/v1beta/models/gemini-pro:generateContent")
@app.post("/v1/chat/completions")  # Esneklik için OpenAI uç noktasına da destek verir
def generate_content(request: GeminiRequest):
    # Kullanıcıdan gelen son mesajı/metni alıyoruz
    try:
        user_text = request.contents[-1].parts[0].text
    except (IndexError, AttributeError):
        user_text = ""

    # Geçici yanıt (İleride data/LLM modülünüz buraya bağlanacak)
    bot_response_text = f"Backend (Gemini formatı) mesajınızı aldı: '{user_text}'"

    # Gemini API Response Formatı
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": bot_response_text
                        }
                    ],
                    "role": "model"
                },
                "finishReason": "STOP",
                "index": 0
            }
        ]
    }