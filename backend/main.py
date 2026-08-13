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

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
JSON_FILE_PATH = DATA_DIR / "bidb_knowledge.json"

# apıkey
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def load_knowledge_base() -> str:
    """bidb_knowledge.json dosyasını okuyup Gemini'ye prompt olarak hazırlayan fonksiyon."""
    if not JSON_FILE_PATH.exists():
        return "Bilgi tabanı dosyası bulunamadı."
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        query_lower = query.lower().strip()
        matched_results = []

        # 1. Tam cümle araması
        if isinstance(data, list):
            for item in data:
                item_str = json.dumps(item, ensure_ascii=False).lower()
                if query_lower in item_str:
                    matched_results.append(item)

        # 2. Tam eşleşme yoksa, anlamlı anahtar kelimeleri çıkarıp kelime skorlaması yap
        if not matched_results and isinstance(data, list):
            stop_words = {"nedir", "nelerdir", "hakkında", "bilgi", "bilgiler", "bilgileri", "bilgileriniz", "nasıl", "nerede", "mi", "mı", "mu", "mü", "ve", "ile", "bir", "bu"}
            # Kelimeleri ayır ve stop words temizle
            raw_words = re.findall(r'\w+', query_lower)
            keywords = [w for w in raw_words if len(w) > 2 and w not in stop_words]

            if keywords:
                best_item = None
                max_score = 0

                for item in data:
                    item_str = json.dumps(item, ensure_ascii=False).lower()
                    score = sum(1 for kw in keywords if kw in item_str)
                    if score > max_score:
                        max_score = score
                        best_item = item

                if best_item and max_score > 0:
                    matched_results.append(best_item)

        if matched_results:
            first_match = matched_results[0]
            if isinstance(first_match, dict):
                content = first_match.get("content") or first_match.get("text") or str(first_match)
                return clean_text(str(content))
            return clean_text(str(first_match))

        return f"Aramanızla ('{query}') ilgili BAÜN BİDB bilgi tabanında uygun bir içerik bulunamadı."

    except Exception as e:
        return f"Hata: {e}"

# Gemini API Şemaları (Frontend Widget Uyumlu)
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

    # Gemini'ye Gönderilecek Akıllı Prompt
    prompt = f"""
Sen Balıkesir Üniversitesi Bilgi İşlem Daire Başkanlığı (BAÜN BİDB) akıllı yardım asistanısın.
Aşağıda üniversitenin bilgi tabanı ve rehber metinleri yer almaktadır:

================ BİLGİ TABANI ================
{knowledge[:15000]}
===============================================

Kullanıcının Sorusu: "{user_question}"

Talimatlar:
1. Sadece yukarıda verilen bilgi tabanına dayanarak kibar, net ve açıklayıcı bir Türkçe yanıt ver.
2. Form isimleri, e-posta ayarları veya adımlar varsa liste halinde düzenli sun.
3. Bilgi tabanında bulunmayan bir konuysa kibarca BAÜN BİDB ile iletişime geçmelerini söyle.
"""

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
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