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

<<<<<<< HEAD
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
=======
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
>>>>>>> 7bac3f49c1f1843c3262dc5a58a08fe727ce49a6

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

<<<<<<< HEAD
    knowledge = get_relevant_knowledge(user_question)

    prompt = f"""
Sen Balıkesir Üniversitesi (BAÜN) resmi akıllı destek asistanısın.
Aşağıda üniversitenin ve Bilgi İşlem Daire Başkanlığı'nın resmi bilgi tabanından kullanıcı sorusuna en alakalı bölümler derlenmiştir:
=======
    print(f"📩 Gelen Soru: {user_question}")
    knowledge = load_all_knowledge_bases()

    prompt = f"""
Sen Balıkesir Üniversitesi ve Bilgi İşlem Daire Başkanlığı (BAÜN & BİDB) akıllı destek asistanısın.
Aşağıda üniversitenin resmi bilgi tabanı yer almaktadır:
>>>>>>> 7bac3f49c1f1843c3262dc5a58a08fe727ce49a6

================ BİLGİ TABANI ================
{knowledge}
===============================================

Kullanıcının Sorusu: "{user_question}"

Talimatlar:
<<<<<<< HEAD
1. Yukarıdaki bilgi tabanından faydalanarak ve genel üniversite bilginle kibar, net ve açıklayıcı bir Türkçe yanıt ver.
2. Bölümler, form isimleri, e-posta ayarları, akademik duyurular, akıllı kart prosedürleri veya adımlar varsa liste halinde düzenli sun.
3. Bilgi tabanında bulunmayan bir konuysa kibarca Balıkesir Üniversitesi / BAÜN BİDB destek birimi ile iletişime geçmelerini söyle.
=======
1. YALNIZCA yukarıda verilen bilgi tabanındaki verilere dayanarak Türkçe, kurumsal, net ve açıklayıcı bir yanıt ver.
2. Bilgi tabanında kesinlikle yer almayan bir konuysa kibarca BAÜN BİDB birimi ile iletişime geçilmesi gerektiğini belirt.
>>>>>>> 7bac3f49c1f1843c3262dc5a58a08fe727ce49a6
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