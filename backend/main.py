import os
import re
import json
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

# Path setup
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

# Load .env file
env_path = BASE_DIR / ".env"
if not env_path.exists():
    env_path = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=env_path)

# FastAPI uygulamasını oluştur
app = FastAPI(
    title="BAÜN BİDB Chatbot Backend",
    version="1.0.0"
)

# Tüm kaynaklardan gelen isteklere izin ver (CORS engellerini kaldırır)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key yapılandırması
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def turkish_lower(text: str) -> str:
    if not text:
        return ""
    return text.replace('İ', 'i').replace('I', 'ı').lower()

STOPWORDS = {"balıkesir", "üniversitesi", "üniversitesinde", "baün", "tane", "var", "kaç", "nedir", "nerede", "hakkında", "bir", "bu", "ve", "veya", "ile", "için", "olan"}

def load_all_text_blocks():
    """Markdown ve JSON bilgi tabanlarını bloklar halinde okur."""
    blocks = []
    
    # 1. Markdown dosyasını kontrol et
    md_paths = [
        PROJECT_ROOT / "baun_librechat_rag.md",
        DATA_DIR / "baun_librechat_rag.md",
        BASE_DIR / "baun_librechat_rag.md"
    ]
    for md_path in md_paths:
        if md_path.exists():
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    md_text = f.read()
                    for b in md_text.split("---"):
                        if b.strip():
                            blocks.append(b.strip())
                print(f"✅ MD Yüklendi: {md_path.name}")
                break
            except Exception as e:
                print("MD okuma hatası:", e)

    # 2. JSON dosyalarını kontrol et
    json_filenames = ["bidb_knowledge.json", "baun_knowledge_base.json"]
    for filename in json_filenames:
        json_paths = [DATA_DIR / filename, PROJECT_ROOT / filename, BASE_DIR / filename]
        for path in json_paths:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
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
                    print(f"✅ JSON Yüklendi: {path.name}")
                    break
                except Exception as e:
                    print(f"JSON okuma hatası ({filename}):", e)

    return blocks

def get_relevant_knowledge(user_question: str, max_chars: int = 40000) -> str:
    """Soruya en uygun bilgi bloklarını seçer."""
    blocks = load_all_text_blocks()
    if not blocks:
        return "Bilgi tabanı boş veya bulunamadı."
    
    words = [turkish_lower(w) for w in re.findall(r'\w+', user_question) if len(w) > 2 and turkish_lower(w) not in STOPWORDS]
    
    if not words:
        return "\n\n---\n\n".join(blocks[:8])

    scored_blocks = []
    for block in blocks:
        score = sum(turkish_lower(block).count(w) for w in words)
        scored_blocks.append((score, block))

    scored_blocks.sort(key=lambda x: x[0], reverse=True)

    selected = []
    current_len = 0
    for score, block in scored_blocks:
        if score == 0 and selected:
            break
        if current_len + len(block) > max_chars:
            continue
        selected.append(block)
        current_len += len(block)

    if not selected:
        selected = [b for _, b in scored_blocks[:5]]

    return "\n\n---\n\n".join(selected)

@app.get("/")
def home():
    return {"status": "BAÜN BİDB Chatbot Backend Sunucusu Aktif!"}

# İstekleri karşılayan ana fonksiyon
@app.api_route("/{full_path:path}", methods=["GET", "POST", "OPTIONS"])
async def handle_chat_completion(request: Request, full_path: str = ""):
    if request.method == "OPTIONS":
        return {"status": "ok"}
        
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

    print(f"\n📩 Gelen Soru: {user_question}")
    knowledge = get_relevant_knowledge(user_question)

    prompt = f"""
Sen Balıkesir Üniversitesi ve Bilgi İşlem Daire Başkanlığı (BAÜN & BİDB) akıllı destek asistanısın.
Aşağıda üniversitenin resmi bilgi tabanından kullanıcının sorusuyla en alakalı derlenen bilgiler yer almaktadır:

================ BİLGİ TABANI ================
{knowledge}
===============================================

Kullanıcının Sorusu: "{user_question}"

Talimatlar:
1. YALNIZCA yukarıda verilen bilgi tabanındaki verilere dayanarak Türkçe, kurumsal, net ve açıklayıcı bir yanıt ver.
2. Bölümler, form isimleri, e-posta ayarları, akademik duyurular, akıllı kart prosedürleri veya adımlar varsa liste halinde düzenli sun.
3. Bilgi tabanında kesinlikle yer almayan bir konuysa kibarca Balıkesir Üniversitesi / BAÜN BİDB destek birimi ile iletişime geçilmesi gerektiğini belirt.
"""

    ai_reply = ""
    # Resmî ve geçerli Gemini modellerini sırayla dene
    valid_models = ['gemini-1.5-flash-latest', 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    for model_name in valid_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                ai_reply = response.text
                break
        except Exception as e:
            print(f"Model deneme hatası ({model_name}): {e}")
            continue

    if not ai_reply:
        ai_reply = "Yanıt üretilirken bir sorun oluştu. Lütfen API anahtarınızı veya BAÜN BİDB destek birimini kontrol edin."

    print(f"🤖 Üretilen Yanıt: {ai_reply[:80]}...")

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