import json
import os
import re
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yükle
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

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

# Doğrudan data klasöründeki JSON dosyasının yolu (chatbot/data/bidb_knowledge.json)
BASE_DIR = Path(__file__).resolve().parent
JSON_FILE_PATH = BASE_DIR.parent / "data" / "bidb_knowledge.json"

# API Key .env dosyasından okunur
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def load_knowledge_base() -> str:
    """data klasöründeki JSON dosyasını okuyup Gemini'ye tam metin olarak verir."""
    if not JSON_FILE_PATH.exists():
        return f"Bilgi tabanı dosyası bulunamadı: {JSON_FILE_PATH}"
    
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            text_blocks = []
            if isinstance(data, list):
                for item in data:
                    title = item.get("title", "")
                    content = item.get("content", "")
                    if content:
                        text_blocks.append(f"--- SAYFA: {title} ---\n{content}")
            elif isinstance(data, dict):
                for k, v in data.items():
                    text_blocks.append(f"--- {k} ---\n{v}")
            return "\n\n".join(text_blocks)
    except Exception as e:
        return f"Dosya okunurken hata oluştu: {e}"

# Gemini API Şemaları
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

    prompt = f"""
Sen Balıkesir Üniversitesi Bilgi İşlem Daire Başkanlığı (BAÜN BİDB) akıllı destek asistanısın.
Aşağıda üniversitenin resmi bilgi tabanı yer almaktadır:

================ BİLGİ TABANI ================
{knowledge[:20000]}
===============================================

Kullanıcının Sorusu: "{user_question}"

Talimatlar:
1. Sadece yukarıda verilen bilgi tabanına dayanarak kibar, net ve açıklayıcı bir Türkçe yanıt ver.
2. Form isimleri, e-posta ayarları, akıllı kart prosedürleri veya adımlar varsa liste halinde düzenli sun.
3. Bilgi tabanında bulunmayan bir konuysa kibarca BAÜN BİDB ile iletişime geçmelerini söyle.
"""

    ai_reply = ""
    # Gemini 3.5 ve güncel modelleri sırayla dene
    for model_name in ['gemini-3.5-flash', 'gemini-3.6-flash', 'gemini-flash-latest']:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                ai_reply = response.text
                break
        except Exception as e:
            print(f"Model error ({model_name}): {e}")
            continue

    if not ai_reply:
        ai_reply = "Yanıt üretilirken bir sorun oluştu. Lütfen BAÜN BİDB destek birimi ile iletişime geçin."

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