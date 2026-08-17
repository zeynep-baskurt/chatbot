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

STOPWORDS = {"balıkesir", "üniversitesi", "üniversitesinde", "baün", "tane", "var", "kaç", "nedir", "nerede", "hakkında", "bir", "bu", "ve", "veya", "ile", "için", "olan"}

def load_all_text_blocks():
    blocks = []
    
    # 1. Load Markdown Knowledge Base if exists
    md_path = BASE_DIR.parent / "baun_librechat_rag.md"
    if not md_path.exists():
        md_path = BASE_DIR.parent / "data" / "baun_librechat_rag.md"
    if md_path.exists():
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                md_text = f.read()
                for b in md_text.split("---"):
                    if b.strip():
                        blocks.append(b.strip())
        except Exception as e:
            print("MD okuma hatası:", e)

    # 2. Load JSON Knowledge Base if exists
    if JSON_FILE_PATH.exists():
        try:
            with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        title = item.get("title", "")
                        content = item.get("content", "")
                        if content:
                            blocks.append(f"--- SAYFA: {title} ---\n{content}")
                elif isinstance(data, dict):
                    for k, v in data.items():
                        blocks.append(f"--- {k} ---\n{v}")
        except Exception as e:
            print("JSON okuma hatası:", e)

    return blocks

def get_relevant_knowledge(user_question: str, max_chars: int = 40000) -> str:
    """RAG mantığıyla kullanıcı sorusuna en alakalı bilgi bloklarını seçer."""
    blocks = load_all_text_blocks()
    if not blocks:
        return "Bilgi tabanı boş veya bulunamadı."
    
    # Soru içerisindeki anahtar kelimeleri çıkar
    words = [w.lower() for w in re.findall(r'\w+', user_question) if len(w) > 2 and w.lower() not in STOPWORDS]
    
    if not words:
        # Anahtar kelime yoksa varsayılan ilk blokları dön
        return "\n\n---\n\n".join(blocks[:5])

    scored_blocks = []
    for block in blocks:
        score = sum(block.lower().count(w) for w in words)
        scored_blocks.append((score, block))

    # Skora göre büyükten küçüğe sırala
    scored_blocks.sort(key=lambda x: x[0], reverse=True)

    selected = []
    current_len = 0
    for score, block in scored_blocks:
        if score == 0 and selected:
            break
        if current_len + len(block) > max_chars:
            break
        selected.append(block)
        current_len += len(block)

    if not selected:
        selected = [b for _, b in scored_blocks[:5]]

    return "\n\n---\n\n".join(selected)

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

    knowledge = get_relevant_knowledge(user_question)

    prompt = f"""
Sen Balıkesir Üniversitesi (BAÜN) resmi akıllı destek asistanısın.
Aşağıda üniversitenin ve Bilgi İşlem Daire Başkanlığı'nın resmi bilgi tabanından kullanıcı sorusuna en alakalı bölümler derlenmiştir:

================ BİLGİ TABANI ================
{knowledge}
===============================================

Kullanıcının Sorusu: "{user_question}"

Talimatlar:
1. Yukarıdaki bilgi tabanından faydalanarak ve genel üniversite bilginle kibar, net ve açıklayıcı bir Türkçe yanıt ver.
2. Bölümler, form isimleri, e-posta ayarları, akademik duyurular, akıllı kart prosedürleri veya adımlar varsa liste halinde düzenli sun.
3. Bilgi tabanında bulunmayan bir konuysa kibarca Balıkesir Üniversitesi / BAÜN BİDB destek birimi ile iletişime geçmelerini söyle.
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