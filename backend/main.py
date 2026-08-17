import json
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="BAÜN BİDB Chatbot Backend (Gemini API Entegreli)",
    version="1.0.0"
)

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

# API Anahtarı
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)

def load_file_content(filename: str) -> str:
    """JSON dosyalarını data veya proje ana dizininde arar."""
    paths_to_check = [
        DATA_DIR / filename,
        PROJECT_ROOT / filename,
        BASE_DIR / filename
    ]
    for path in paths_to_check:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return json.dumps(data, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Dosya okuma hatası ({filename}): {e}")
                return ""
    return ""

def load_all_knowledge_bases() -> str:
    """Hem BİDB hem BAÜN genel bilgi tabanlarını birleştirir."""
    bidb_data = load_file_content("bidb_knowledge.json")
    baun_data = load_file_content("baun_knowledge_base.json")
    
    combined = []
    if bidb_data:
        combined.append(f"=== BAÜN BİDB BİLGİ TABANI ===\n{bidb_data}")
    if baun_data:
        combined.append(f"=== BAÜN GENEL BİLGİ TABANI ===\n{baun_data}")
        
    if not combined:
        return "Bilgi tabanı dosyaları bulunamadı."
        
    return "\n\n".join(combined)

@app.get("/")
def home():
    return {"status": "Backend Sunucusu Aktif!"}

# Widget'ın istek attığı tüm endpoint varyasyonları (completions, v1/chat/completions vb.)
@app.post("/completions")
@app.post("/v1/chat/completions")
@app.post("/chat/completions")
@app.post("/v1beta/models/{model_name:path}:generateContent")
@app.post("/chat")
@app.api_route("/{full_path:path}", methods=["GET", "POST", "OPTIONS"])
async def handle_requests(request: Request, full_path: str = ""):
    # Gelen soru metnini çıkar
    user_question = ""
    try:
        body = await request.json()
        if "messages" in body and body["messages"]:
            user_question = body["messages"][-1].get("content", "")
        elif "contents" in body and body["contents"]:
            user_question = body["contents"][-1]["parts"][0]["text"]
        elif "prompt" in body:
            user_question = body["prompt"]
    except Exception:
        user_question = ""

    print(f"📩 Gelen Soru: {user_question}")
    knowledge = load_all_knowledge_bases()

    prompt = f"""
Sen Balıkesir Üniversitesi ve Bilgi İşlem Daire Başkanlığı (BAÜN & BİDB) akıllı destek asistanısın.
Aşağıda üniversitenin resmi bilgi tabanı yer almaktadır:

================ BİLGİ TABANI ================
{knowledge}
===============================================

Kullanıcının Sorusu: "{user_question}"

Talimatlar:
1. YALNIZCA yukarıda verilen bilgi tabanındaki verilere dayanarak Türkçe, kurumsal, net ve açıklayıcı bir yanıt ver.
2. Bilgi tabanında kesinlikle yer almayan bir konuysa kibarca BAÜN BİDB birimi ile iletişime geçilmesi gerektiğini belirt.
"""

    try:
        model = genai.GenerativeModel('gemini-3.6-flash')
        response = model.generate_content(prompt)
        ai_reply = response.text
    except Exception as e:
        ai_reply = f"Gemini API yanıt verirken bir sorun oluştu: {str(e)}"
        print(f"❌ API Hatası: {e}")

    # Hem OpenAI hem Gemini yanıt şablonunu aynı anda döndürür
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": ai_reply
                },
                "index": 0,
                "finish_reason": "stop"
            }
        ],
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