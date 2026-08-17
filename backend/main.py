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

# Doğrudan data klasöründeki JSON dosyasının yolu (chatbot/data/bidb_knowledge.json)
BASE_DIR = Path(__file__).resolve().parent
JSON_FILE_PATH = BASE_DIR.parent / "data" / "bidb_knowledge.json"

# API Anahtarı
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)

def load_knowledge_base() -> str:
    """data klasöründeki JSON dosyasını okuyup Gemini'ye tam metin olarak verir."""
    if not JSON_FILE_PATH.exists():
        return f"Bilgi tabanı dosyası bulunamadı: {JSON_FILE_PATH}"
    
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return json.dumps(data, ensure_ascii=False, indent=2)
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
{knowledge}
===============================================

Kullanıcının Sorusu: "{user_question}"

Talimatlar:
1. YALNIZCA yukarıda verilen bilgi tabanındaki verilere dayanarak kibar, kurumsal, net ve Türkçe bir yanıt ver.
2. Adımlar, formlar veya bağlantılar varsa madde imleri halinde düzenli sun.
3. Aranan konu bilgi tabanında kesinlikle yoksa uydurma; kibarca kullanıcının BAÜN BİDB birimi ile iletişime geçmesi gerektiğini belirt.
"""

    try:
        model = genai.GenerativeModel('gemini-3.6-flash')
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