import os
import json

SCRATCH_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(SCRATCH_DIR, "baun_knowledge_base.json")
MARKDOWN_PATH = os.path.join(SCRATCH_DIR, "baun_librechat_rag.md")

def generate_librechat_markdown():
    if not os.path.exists(JSON_PATH):
        print(f"Hata: {JSON_PATH} bulunamadı. Önce scrape_baun.py dosyasını çalıştırın.")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(MARKDOWN_PATH, "w", encoding="utf-8") as f:
        f.write("# BALIKESİR ÜNİVERSİTESİ (BAÜN) KURUMSAL BİLGİ DOKÜMANI\n\n")
        f.write("> Bu doküman `https://balikesir.edu.tr/` resmi web sitesinden çekilen güncel bilgileri içerir ve LibreChat RAG / Agent altyapısı için özel hazırlanmıştır.\n\n")

        for idx, item in enumerate(data, 1):
            f.write(f"## {idx}. {item['title']}\n")
            f.write(f"**Kaynak URL:** [{item['url']}]({item['url']})\n\n")
            f.write("### Sayfa İçeriği:\n")
            
            # Clean content into paragraph blocks
            paragraphs = item['content'].split('\n')
            for p in paragraphs:
                if len(p.strip()) > 0:
                    f.write(f"{p.strip()}\n\n")
            
            f.write("---\n\n")

    print(f"[OK] LibreChat icin Markdown Dokumani Olusturuldu: {MARKDOWN_PATH}")
    print(f"[INFO] Bu .md dosyasini LibreChat arayuzunde olusturdugunuz BAUN Agent'ina dosya olarak yukleyebilirsiniz.")

if __name__ == "__main__":
    generate_librechat_markdown()
