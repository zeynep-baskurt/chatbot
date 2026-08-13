import json
import re
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(
    title="BAÜN BİDB Chatbot Backend (Gemini API Compatible)",
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


def clean_text(text: str) -> str:
    """Metindeki fazla \\n karakterlerini ve gereksiz boşlukları temizler."""
    if not text:
        return ""
    # Arka arkaya gelen \n ve boşlukları tek bir satır başı veya boşluğa indirger
    cleaned = re.sub(r'[\r\n]+', '\n', text)
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    return cleaned.strip()


def search_in_knowledge_base(query: str) -> str:
    """bidb_knowledge.json dosyasından arama yapar ve temizlenmiş metin döner."""
    if not JSON_FILE_PATH.exists():
        return "Bilgi tabanı dosyası (bidb_knowledge.json) bulunamadı."

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
        return f"Bilgi tabanı okunurken hata oluştu: {str(e)}"


# --- Gemini API Şemaları ---

class Part(BaseModel):
    text: str

class Content(BaseModel):
    role: Optional[str] = "user"
    parts: List[Part]

class GeminiRequest(BaseModel):
    contents: List[Content]


@app.get("/")
def home():
    return {"status": "Gemini uyumlu Backend sunucusu ve Data entegrasyonu aktif!"}


@app.post("/v1beta/models/gemini-pro:generateContent")
@app.post("/v1/chat/completions")
def generate_content(request: GeminiRequest):
    try:
        user_text = request.contents[-1].parts[0].text
    except (IndexError, AttributeError):
        user_text = ""

    bot_response_text = search_in_knowledge_base(user_text)

    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": bot_response_text
                        }
                    ],
                    "role": "model"
                },
                "finishReason": "STOP",
                "index": 0
            }
        ]
    }