import requests
from bs4 import BeautifulSoup
import json
import os

# Çekilecek BAÜN BİDB Sayfaları ve Kılavuz URL'leri
URLS = [
    "https://bid.balikesir.edu.tr/",
]

def scrape_bidb():
    print("🔍 BAÜN BİDB Web Verileri Çekiliyor...")
    knowledge_base = []
    
    for url in URLS:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Sayfa başlığını al
                title = soup.title.string.strip() if soup.title else url
                
                # Sayfadaki metinleri, başlıkları ve maddeleri topla
                elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li'])
                texts = [el.get_text().strip() for el in elements if len(el.get_text().strip()) > 10]
                content = "\n".join(texts)
                
                knowledge_base.append({
                    "url": url,
                    "title": title,
                    "content": content
                })
                print(f"✅ Başarıyla Çekildi: {url}")
            else:
                print(f"❌ Hata koda sahip ({response.status_code}): {url}")
        except Exception as e:
            print(f"⚠️ Bağlantı hatası ({url}): {e}")

    # data klasörüne JSON formatında kaydet
    os.makedirs("data", exist_ok=True)
    with open("data/bidb_knowledge.json", "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f, ensure_ascii=False, indent=4)
        
    print("\n🎉 Veriler 'data/bidb_knowledge.json' dosyasına kaydedildi!")

if __name__ == "__main__":
    scrape_bidb()
    