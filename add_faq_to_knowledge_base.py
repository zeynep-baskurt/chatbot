import os
import json
import re
from collections import defaultdict

SCRATCH_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(SCRATCH_DIR, "baun_knowledge_base.json")
TXT_PATH = os.path.join(SCRATCH_DIR, "baun_knowledge_base.txt")
MARKDOWN_PATH = os.path.join(SCRATCH_DIR, "baun_librechat_rag.md")

TRANSCRIPT_PATH = r"C:\Users\elifs\.gemini\antigravity\brain\84ab5117-ceb1-4fa7-9b40-aa36b687cc71\.system_generated\logs\transcript_full.jsonl"

def slugify(text):
    text = text.lower()
    replacements = {
        'ç': 'c', 'ğ': 'g', 'ı': 'i', 'i': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
        'Ç': 'c', 'Ğ': 'g', 'İ': 'i', 'I': 'i', 'Ö': 'o', 'Ş': 's', 'Ü': 'u',
        ' ': '-', '_': '-'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r'[^a-z0-9\-]', '', text)
    text = re.sub(r'\-+', '-', text).strip('-')
    return text

def main():
    print("[1/5] Transcript dosyasından SSS verisi çekiliyor...")
    faq_raw = ""
    if os.path.exists(TRANSCRIPT_PATH):
        with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if data.get("type") == "USER_INPUT":
                    content = data.get("content", "")
                    if "Altınoluk Meslek Yüksekokulu" in content and "Birim\tSoru\tCevap" in content:
                        faq_raw = content
                        break

    if not faq_raw:
        print("[HATA] Transcript içinde SSS verisi bulunamadı!")
        return

    items_by_birim = defaultdict(list)
    lines = faq_raw.splitlines()
    total_parsed = 0

    for line in lines:
        parts = line.split("\t")
        if len(parts) >= 3:
            birim, soru, cevap = parts[0].strip(), parts[1].strip(), parts[2].strip()
            if birim == "Birim" and soru == "Soru":
                continue
            if birim and soru and cevap:
                items_by_birim[birim].append({"soru": soru, "cevap": cevap})
                total_parsed += 1

    print(f"[OK] Toplam {total_parsed} soru-cevap çifti, {len(items_by_birim)} birim için ayrıştırıldı.")

    # 2. Load existing baun_knowledge_base.json
    print("[2/5] Mevcut baun_knowledge_base.json yükleniyor...")
    kb_data = []
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            kb_data = json.load(f)

    # Filter out old SSS entries if re-running
    web_pages = [item for item in kb_data if not item.get("title", "").startswith("SSS -")]
    print(f"[INFO] {len(web_pages)} adet web sayfası korundu.")

    # 3. Add FAQ items grouped by unit
    faq_json_items = []

    for birim, qas in items_by_birim.items():
        title = f"SSS - {birim} Sıkça Sorulan Sorular"
        url = f"https://www.balikesir.edu.tr/sss/{slugify(birim)}"
        
        content_lines = [f"Birim: {birim}\n"]
        for idx, qa in enumerate(qas, 1):
            content_lines.append(f"Soru {idx}: {qa['soru']}")
            content_lines.append(f"Cevap: {qa['cevap']}\n")
        
        content_str = "\n".join(content_lines)

        faq_json_items.append({
            "title": title,
            "url": url,
            "depth": 2,
            "content": content_str
        })

    # Combine web pages + faq entries
    updated_kb = web_pages + faq_json_items

    print(f"[3/5] Toplam {len(updated_kb)} öge oluşturuldu ({len(web_pages)} Web Sayfası + {len(faq_json_items)} Birim SSS).")

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(updated_kb, f, ensure_ascii=False, indent=2)
    print(f"[OK] {JSON_PATH} güncellendi.")

    # 4. Generate baun_knowledge_base.txt
    print("[4/5] baun_knowledge_base.txt oluşturuluyor...")
    with open(TXT_PATH, "w", encoding="utf-8") as f:
        for item in updated_kb:
            f.write(f"=== {item['title']} ({item['url']}) ===\n")
            f.write(f"{item['content']}\n\n")
            f.write("=" * 60 + "\n\n")
    print(f"[OK] {TXT_PATH} güncellendi.")

    # 5. Generate baun_librechat_rag.md
    print("[5/5] baun_librechat_rag.md oluşturuluyor...")
    with open(MARKDOWN_PATH, "w", encoding="utf-8") as f:
        f.write("# BALIKESİR ÜNİVERSİTESİ (BAÜN) KURUMSAL BİLGİ VE SSS DOKÜMANI\n\n")
        f.write("> Bu doküman `https://balikesir.edu.tr/` resmi web sitesinden çekilen güncel web sayfalarını ve Üniversite Birimlerine ait Sıkça Sorulan Sorular (SSS) verilerini içerir. LibreChat RAG / Agent altyapısı için özel hazırlanmıştır.\n\n")
        f.write(f"- **Toplam Kaynak Sayısı:** {len(updated_kb)}\n")
        f.write(f"- **Web Sayfası Sayısı:** {len(web_pages)}\n")
        f.write(f"- **Birim SSS Sayısı:** {len(faq_json_items)} ({total_parsed} Soru-Cevap)\n\n")
        f.write("---\n\n")

        # Section 1: Web Pages
        f.write("# BÖLÜM 1: WEB SAYFALARI BİLGİ BANKASI\n\n")
        for idx, item in enumerate(web_pages, 1):
            f.write(f"## {idx}. {item['title']}\n")
            f.write(f"**Kaynak URL:** [{item['url']}]({item['url']})\n\n")
            f.write("### Sayfa İçeriği:\n")
            paragraphs = item['content'].split('\n')
            for p in paragraphs:
                if len(p.strip()) > 0:
                    f.write(f"{p.strip()}\n\n")
            f.write("---\n\n")

        # Section 2: Unit FAQs
        f.write("# BÖLÜM 2: BİRİMLERE GÖRE SIKÇA SORULAN SORULAR (SSS)\n\n")
        for idx, item in enumerate(faq_json_items, 1):
            f.write(f"## SSS {idx}. {item['title']}\n")
            f.write(f"**Kaynak URL:** [{item['url']}]({item['url']})\n\n")
            f.write("### Soru ve Cevaplar:\n\n")
            paragraphs = item['content'].split('\n')
            for p in paragraphs:
                if len(p.strip()) > 0:
                    f.write(f"{p.strip()}\n\n")
            f.write("---\n\n")

    print(f"[OK] {MARKDOWN_PATH} oluşturuldu.")
    print("\n[BAŞARILI] Tüm SSS verileri bilgi bankasına eklendi ve LibreChat RAG dokümanı güncellendi!")

if __name__ == "__main__":
    main()
