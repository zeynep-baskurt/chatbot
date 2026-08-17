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
load_dotenv(dotenv_path=env_path)

app = FastAPI(
    title="BAÜN BİDB Chatbot Backend (Gemini API & RAG Entegreli)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key .env dosyasından okunur
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

STOPWORDS = {"balıkesir", "üniversitesi", "üniversitesinde", "baün", "tane", "var", "kaç", "nedir", "nerede", "hakkında", "bir", "bu", "ve", "veya", "ile", "için", "olan"}

def load_all_text_blocks():
    """Tüm bilgi tabanı kaynaklarını (Markdown ve JSON) metin bloklarına ayırarak yükler."""
    blocks = []
    
    # 1. Load Markdown Knowledge Base if exists
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
                break
            except Exception as e:
                print("MD okuma hatası:", e)

    # 2. Load JSON Knowledge Bases
    json_filenames = ["bidb_knowledge.json", "baun_knowledge_base.json"]
    for filename in json_filenames:
        json_path = DATA_DIR / filename
        if not json_path.exists():
            json_path = PROJECT_ROOT / filename
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
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
                print(f"JSON okuma hatası ({filename}):", e)

    return blocks

def get_relevant_knowledge(user_question: str, max_chars: int = 40000) -> str:
    """RAG mantığıyla kullanıcı sorusuna en alakalı bilgi bloklarını seçer."""
    blocks = load_all_text_blocks()
    if not blocks:
        return "Bilgi tabanı boş veya bulunamadı."
    
    # Soru içerisindeki anahtar kelimeleri çıkar
    words = [w.lower() for w in re.findall(r'\w+', user_question) if len(w) > 2 and w.lower() not in STOPWORDS]
    
    if not words:
        # Anahtar kelime yoksa varsayılan ilk 8 bloğu dön
        return "\n\n---\n\n".join(blocks[:8])

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

@app.get("/")
def home():
    return {"status": "BAÜN BİDB Chatbot Backend Sunucusu Aktif!"}

# Widget ve API İsteklerini Karşılayan Genel Endpoint (Hem OpenAI hem Gemini formatı destekli)
@app.api_route("/api/v1/chat/completions", methods=["POST", "OPTIONS"])
@app.api_route("/v1/chat/completions", methods=["POST", "OPTIONS"])
@app.api_route("/completions", methods=["POST", "OPTIONS"])
@app.api_route("/chat/completions", methods=["POST", "OPTIONS"])
@app.api_route("/v1beta/models/{model_name:path}:generateContent", methods=["POST", "OPTIONS"])
async def handle_chat_completion(request: Request):
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

    print(f"📩 Gelen Soru: {user_question}")
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
    # Gemini modellerini sırayla dene (güncel modeller)
    for model_name in ['gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-flash-latest', 'gemini-pro-latest']:
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
        ai_reply = "Yanıt üretilirken bir sorun oluştu. Lütfen BAÜN BİDB destek birimi ile iletişime geçin."

    print(f"✅ Üretilen Yanıt ({len(ai_reply)} kr): {ai_reply[:100]}...")

    # Hem OpenAI hem Gemini formatında yanıt döndürür
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

# Catch-all endpoint
@app.api_route("/{full_path:path}", methods=["GET", "POST", "OPTIONS"])
async def catch_all(request: Request, full_path: str):
    if request.method == "OPTIONS":
        return {"status": "ok"}
    return await handle_chat_completion(request)