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

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

# API Anahtarı
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)

def load_file_content(filename: str) -> str:
    """Belirtilen JSON dosyasını önce data klasöründe, yoksa ana dizinde arayıp okur."""
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
                return f"Hata ({filename}): {e}"
    return ""

def load_all_knowledge_bases() -> str:
    """Hem BİDB hem de BAÜN genel bilgi tabanlarını birleştirir."""
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

    knowledge = load_all_knowledge_bases()

    prompt = f"""
Sen Balıkesir Üniversitesi ve Bilgi İşlem Daire Başkanlığı (BAÜN & BİDB) akıllı destek asistanısın.
Aşağıda üniversitenin birleştirilmiş resmi bilgi tabanları yer almaktadır:

================ BİLGİ TABANI ================
{knowledge}
===============================================

Kullanıcının Sorusu: "{user_question}"

Talimatlar:
1. YALNIZCA yukarıda verilen bilgi tabanlarındaki verilere dayanarak kibar, kurumsal, net ve Türkçe bir yanıt ver.
2. Adımlar, formlar veya bağlantılar varsa madde imleri halinde düzenli sun.
3. Aranan konu bilgi tabanlarında kesinlikle yoksa uydurma; kibarca kullanıcının BAÜN ilgili birimi ile iletişime geçmesi gerektiğini belirt.
"""

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
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