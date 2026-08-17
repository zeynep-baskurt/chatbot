import json
import os
from pathlib import Path
from fastapi import FastAPI
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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def load_file_content(filename: str) -> str:
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
                    print(f" Bulundu ve Yüklendi: {path} ({len(content)} karakter)")
                    return content
            except Exception as e:
                print(f" Dosya Okuma Hatası ({path}): {e}")
                return ""
    print(f" Dosya Bulunamadı: {filename}")
    return ""

def load_all_knowledge_bases() -> str:
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

    print(f"\n GELEN SORU: {user_question}")
    knowledge = load_all_knowledge_bases()
    print(f" TOPLAM BİLGİ TABANI BOYUTU: {len(knowledge)} karakter")

    prompt = f"""
Sen Balıkesir Üniversitesi ve Bilgi İşlem Daire Başkanlığı (BAÜN & BİDB) akıllı destek asistanısın.
Aşağıda üniversitenin resmi bilgi tabanları yer almaktadır:

================ BİLGİ TABANI ================
{knowledge}
===============================================

Kullanıcının Sorusu: "{user_question}"

Talimatlar:
1. YALNIZCA yukarıda verilen bilgi tabanındaki verilere dayanarak Türkçe, kurumsal ve net yanıt ver.
2. Bilgi tabanında yer alan bilgileri doğrudan aktar.
3. Bilgi tabanında kesinlikle bulunmayan bir konuysa kibarca BAÜN BİDB birimi ile iletişime geçilmesini söyle.
"""

    try:
        # En stabil model adı
        model = genai.GenerativeModel('gemini-3.6-flash-latest')
        response = model.generate_content(prompt)
        ai_reply = response.text
        print(" GEMINI CEVABI ÜRETTİ.")
    except Exception as e:
        ai_reply = f"Gemini API yanıt verirken bir sorun oluştu: {str(e)}"
        print(f" GEMINI API HATASI: {str(e)}")

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