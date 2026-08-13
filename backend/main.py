import json
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yükle
load_dotenv()

app = FastAPI(
    title="BAÜN BİDB Chatbot Backend (Gemini API Entegreli)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
JSON_FILE_PATH = DATA_DIR / "bidb_knowledge.json"

# apıkey
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def load_knowledge_base() -> str:
    """bidb_knowledge.json dosyasını okuyup Gemini'ye prompt olarak hazırlayan fonksiyon."""
    if not JSON_FILE_PATH.exists():
        return "Bilgi tabanı dosyası bulunamadı."
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            text_blocks = []
            for item in data:
                title = item.get("title", "")
                content = item.get("content", "")
                text_blocks.append(f"--- SAYFA: {title} ---\n{content}")
            return "\n\n".join(text_blocks)
    except Exception as e:
        return f"Hata: {e}"

# Gemini API Şemaları (Frontend Widget Uyumlu)
class Part(BaseModel):
    text: str

class Content(BaseModel):
    role: Optional[str] = "user"
    parts: List[Part]

class GeminiRequest(BaseModel):
    contents: List[Content]

@app.get("/")
def home():
    return {"status": "Gemini AI Destekli Backend Sunucusu Aktif!"}

@app.post("/v1beta/models/gemini-pro:generateContent")
@app.post("/v1/chat/completions")
def generate_content(request: GeminiRequest):
    try:
        user_question = request.contents[-1].parts[0].text
    except Exception:
        user_question = ""

    knowledge = load_knowledge_base()

    # Gemini'ye Gönderilecek Akıllı Prompt
    prompt = f"""
Sen Balıkesir Üniversitesi Bilgi İşlem Daire Başkanlığı (BAÜN BİDB) akıllı yardım asistanısın.
Aşağıda üniversitenin bilgi tabanı ve rehber metinleri yer almaktadır:

================ BİLGİ TABANI ================
{knowledge[:15000]}
===============================================

Kullanıcının Sorusu: "{user_question}"

Talimatlar:
1. Sadece yukarıda verilen bilgi tabanına dayanarak kibar, net ve açıklayıcı bir Türkçe yanıt ver.
2. Form isimleri, e-posta ayarları veya adımlar varsa liste halinde düzenli sun.
3. Bilgi tabanında bulunmayan bir konuysa kibarca BAÜN BİDB ile iletişime geçmelerini söyle.
"""

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        ai_reply = response.text
    except Exception as e:
        ai_reply = f"Gemini API yanıt verirken bir sorun oluştu: {str(e)}"

    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": ai_reply}],
                    "role": "model"
                },
                "finishReason": "STOP",
                "index": 0
            }
        ]
    }