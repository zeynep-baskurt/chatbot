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

# API Anahtarı (.env dosyasından okunur)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def load_file_content(filename: str) -> str:
    """JSON dosyasını data klasöründe veya ana dizinlerde arayıp okur."""
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
                    content = json.dumps(data, ensure_ascii=False, indent=2)
                    print(f"✅ Bulundu ve Yüklendi: {path} ({len(content)} karakter)")
                    return content
            except Exception as e:
                print(f"❌ Dosya Okuma Hatası ({path}): {e}")
                return ""
    print(f"⚠️ Dosya Bulunamadı: {filename}")
    return ""

def load_all_knowledge_bases() -> str:
    """BİDB ve genel BAÜN bilgi tabanlarını birleştirir."""
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
    return {"status": "Gemini AI Destekli Backend Sunucusu Aktif!"}

# Frontend'in gönderdiği tüm URL ve model rotalarını yakalayan fonksiyon
@app.api_route("/{full_path:path}", methods=["GET", "POST", "OPTIONS"])
async def handle_chat_requests(full_path: str, request: Request):
    user_question = ""
    try:
        body = await request.json()
        if "contents" in body and body["contents"]:
            user_question = body["contents"][-1]["parts"][0]["text"]
        elif "messages" in body and body["messages"]:
            user_question = body["messages"][-1]["content"]
        elif "prompt" in body:
            user_question = body["prompt"]
    except Exception:
        user_question = ""

    print(f"\n📩 GELEN İSTEK ROTASI: /{full_path}")
    print(f"💬 GELEN SORU: {user_question}")
    
    knowledge = load_all_knowledge_bases()
    print(f"📊 YÜKLENEN VERİ TABANI BOYUTU: {len(knowledge)} karakter")

    prompt = f"""
Sen Balıkesir Üniversitesi ve Bilgi İşlem Daire Başkanlığı (BAÜN & BİDB) akıllı destek asistanısın.
Aşağıda üniversitenin resmi bilgi tabanları yer almaktadır:

================ BİLGİ TABANI ================
{knowledge}
===============================================

Kullanıcının Sorusu: "{user_question}"

Talimatlar:
1. YALNIZCA yukarıda verilen bilgi tabanındaki verilere dayanarak Türkçe, kurumsal ve net yanıt ver.
2. Bilgi tabanında kesinlikle yer almayan bir konuysa kibarca BAÜN BİDB birimi ile iletişime geçilmesini söyle.
"""

    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        ai_reply = response.text
        print("🤖 CEVAP ÜRETİLDİ.")
    except Exception as e:
        ai_reply = f"Gemini API yanıt verirken bir sorun oluştu: {str(e)}"
        print(f"❌ GEMINI HATASI: {e}")

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
        ],
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": ai_reply
                }
            }
        ]
    }