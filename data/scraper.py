import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import urljoin, urlparse

BASE_URL = "https://bid.balikesir.edu.tr/"

# BAÜN BİDB Ana Hizmet Sayfaları ve Kılavuz Linkleri
URLS = [
    "https://bid.balikesir.edu.tr/",
    "https://bid.balikesir.edu.tr/sayfa/eduroam-kablosuz-ag-kurulumu",
    "https://bid.balikesir.edu.tr/sayfa/akilli-kart-islemleri",
    "https://bid.balikesir.edu.tr/sayfa/e-posta-islemleri",
    "https://bid.balikesir.edu.tr/sayfa/formlar-ve-dilekceler",
    "https://bid.balikesir.edu.tr/sayfa/sikca-sorulan-sorular",
    "https://bid.balikesir.edu.tr/sayfa/yazilim-ve-lisans-islemleri",
    "https://bid.balikesir.edu.tr/sayfa/iletisim"
]

def scrape_bidb():
    print(" BAÜN BİDB Tüm Alt Sayfa ve Hizmet Verileri Çekiliyor...")
    knowledge_base = []
    visited_urls = set()
    
    # Ana sayfadaki diğer tüm dahili alt linkleri de otomatik bul
    try:
        res = requests.get(BASE_URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, 'html.parser')
            for a in soup.find_all('a', href=True):
                full_url = urljoin(BASE_URL, a['href'])
                if urlparse(full_url).netloc == urlparse(BASE_URL).netloc:
                    if full_url not in URLS and not full_url.endswith(('.pdf', '.doc', '.docx', '.png', '.jpg')):
                        URLS.append(full_url)
    except Exception as e:
        print(f"Link tarama uyarısı: {e}")

    for url in URLS:
        if url in visited_urls:
            continue
        visited_urls.add(url)
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                title = soup.title.string.strip() if soup.title else url
                
                # Sayfadaki tüm metin, başlık, tablo ve maddeleri topla
                elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li', 'td'])
                texts = [el.get_text().strip() for el in elements if len(el.get_text().strip()) > 5]
                content = "\n".join(texts)
                
                if len(content) > 30:
                    knowledge_base.append({
                        "url": url,
                        "title": title,
                        "content": content
                    })
                    print(f" Çekildi: {title[:40]}... ({url})")
            else:
                print(f" Hata ({response.status_code}): {url}")
        except Exception as e:
            print(f" Bağlantı hatası ({url}): {e}")
            
    # Şablon ve tekrar eden menü/footer satırlarını temizle
    from collections import Counter
    line_counts = Counter()
    for item in knowledge_base:
        content = item.get("content", "")
        unique_lines = set(line.strip() for line in content.split('\n') if line.strip())
        for line in unique_lines:
            line_counts[line] += 1
            
    num_pages = len(knowledge_base)
    boilerplate_lines = {line for line, count in line_counts.items() if count > num_pages * 0.3}
    
    for item in knowledge_base:
        content = item.get("content", "")
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        cleaned_lines = [line for line in lines if line not in boilerplate_lines]
        item["content"] = "\n".join(cleaned_lines)

    os.makedirs("data", exist_ok=True)
    with open("data/bidb_knowledge.json", "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f, ensure_ascii=False, indent=4)
        
    print(f"\n Toplam {len(knowledge_base)} sayfa başarıyla temizlenip 'data/bidb_knowledge.json' dosyasına kaydedildi!")

if __name__ == "__main__":
    scrape_bidb()