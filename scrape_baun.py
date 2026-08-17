import os
import re
import sys
import time
import json
import requests
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Disable SSL warnings for subdomains with self-signed or issuer cert issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Target base URL and domain restriction
BASE_URL = "https://www.balikesir.edu.tr/"
ALLOWED_DOMAIN = "balikesir.edu.tr"

# File output paths
SCRATCH_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_TXT_PATH = os.path.join(SCRATCH_DIR, "baun_knowledge_base.txt")
OUTPUT_JSON_PATH = os.path.join(SCRATCH_DIR, "baun_knowledge_base.json")

# Keywords of important sections to prioritize
PRIORITY_KEYWORDS = [
    "duyuru", "akademik", "takvim", "ogrenci", "fakulte",
    "enstitu", "yuksekokul", "yemek", "baskanlik", "iletisim",
    "senato", "yonetmelik", "burs", "harc", "kayit", "staj"
]

visited_urls = set()
scraped_data = []

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
}

def clean_html_content(soup):
    """Removes navigation, headers, footers, scripts, and styles to extract pure content."""
    for element in soup(["script", "style", "nav", "footer", "header", "form", "iframe", "noscript"]):
        element.extract()
    
    target = soup.body or soup

    text = target.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Filter short repetitive lines
    cleaned_lines = []
    for line in lines:
        if len(line) > 3 and not line.startswith("http"):
            cleaned_lines.append(line)
            
    return "\n".join(cleaned_lines)

def is_valid_url(url):
    """Check if URL belongs to balikesir.edu.tr and is an HTML web page."""
    parsed = urlparse(url)
    if ALLOWED_DOMAIN not in parsed.netloc:
        return False
    # Exclude non-document files except pdfs (which can be handled separately)
    excluded_exts = [".jpg", ".png", ".gif", ".css", ".js", ".mp4", ".zip", ".rar", ".exe", ".doc", ".docx"]
    if any(parsed.path.lower().endswith(ext) for ext in excluded_exts):
        return False
    return True

def scrape_url(url, depth=1, max_depth=2, max_pages=50):
    if len(visited_urls) >= max_pages:
        return
    if url in visited_urls or depth > max_depth:
        return

    visited_urls.add(url)
    print(f"[{len(visited_urls)}/{max_pages}] [Derinlik: {depth}] Taranıyor: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=12, verify=False)
        if response.status_code != 200:
            return
        
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type:
            return

        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else url
        cleaned_text = clean_html_content(soup)

        if len(cleaned_text) > 100:  # Only save pages with meaningful content
            item = {
                "title": title,
                "url": url,
                "depth": depth,
                "content": cleaned_text
            }
            scraped_data.append(item)

        # Collect internal links
        if depth < max_depth and len(visited_urls) < max_pages:
            links = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                full_url = urljoin(url, href)
                
                # Strip fragments
                full_url = full_url.split("#")[0]
                
                if is_valid_url(full_url) and full_url not in visited_urls:
                    # Prioritize links matching priority keywords
                    is_priority = any(kw in full_url.lower() for kw in PRIORITY_KEYWORDS)
                    links.append((is_priority, full_url))
            
            # Sort priority links first
            links.sort(key=lambda x: x[0], reverse=True)
            
            for _, link_url in links:
                if len(visited_urls) >= max_pages:
                    break
                scrape_url(link_url, depth + 1, max_depth, max_pages)
                time.sleep(0.3)  # Gentle crawling speed

    except Exception as e:
        print(f"Hata oluştu ({url}): {e}")

def save_results():
    print(f"\n--- Tarama Bitti: Toplam {len(scraped_data)} sayfa çekildi ---")
    
    # Save as JSON
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=2)
    print(f"JSON verisi kaydedildi: {OUTPUT_JSON_PATH}")

    # Save as Text Knowledge Base for LibreChat RAG Upload
    with open(OUTPUT_TXT_PATH, "w", encoding="utf-8") as f:
        f.write("====================================================\n")
        f.write("BALIKESİR ÜNİVERSİTESİ (BAÜN) KAPSAMLI BİLGİ BANKASI\n")
        f.write("====================================================\n\n")
        
        for idx, item in enumerate(scraped_data, 1):
            f.write(f"--- DOKÜMAN #{idx} ---\n")
            f.write(f"BAŞLIK: {item['title']}\n")
            f.write(f"KAYNAK URL: {item['url']}\n")
            f.write("İÇERİK:\n")
            f.write(item['content'])
            f.write("\n\n" + "="*50 + "\n\n")

    print(f"TXT Bilgi Bankası kaydedildi: {OUTPUT_TXT_PATH}")

if __name__ == "__main__":
    print("Balıkesir Üniversitesi Web Kazıma İşlemi Başlatılıyor...")
    scrape_url(BASE_URL, depth=1, max_depth=2, max_pages=35)
    save_results()
