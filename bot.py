import json
import os
import subprocess
import sys

try:
  import requests
  from bs4 import BeautifulSoup
except ImportError:
  subprocess.run(
      [sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4"],
      check=True,
  )
  import requests
  from bs4 import BeautifulSoup

TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = "https://www.bim.com.tr/Categories/680/afisler.aspx"
CACHE_FILE = "sent_links.json"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9",
}


def telegram_foto_gonder(foto_url, caption):
  if not TOKEN or not CHAT_ID:
    print("BOT_TOKEN veya CHAT_ID eksik!")
    return
  api_url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"

  try:
    # Afiş görselini indir
    img_resp = requests.get(foto_url, headers=headers, timeout=15)
    if img_resp.status_code != 200:
      print(f"Resim indirilemedi: {foto_url}")
      return

    # Telegram'a doğrudan fotoğraf olarak gönder
    files = {"photo": ("afis.jpg", img_resp.content, "image/jpeg")}
    data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"}

    resp = requests.post(api_url, data=data, files=files, timeout=30)
    if not resp.ok:
      print(f"Telegram fotoğraf gönderim hatası: {resp.text}")
  except Exception as e:
    print(f"Telegram mesajı gönderilemedi: {e}")


# Daha önce gönderilen afişlerin hafızasını yükle
sent_links = []
if os.path.exists(CACHE_FILE):
  try:
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
      sent_links = json.load(f)
  except Exception:
    sent_links = []

try:
  print(f"BİM afiş sayfasına bağlanılıyor: {URL}")
  r = requests.get(URL, headers=headers, timeout=15)
  if r.status_code != 200:
    print(f"Hata: HTTP {r.status_code}")
    sys.exit(1)

  soup = BeautifulSoup(r.text, "html.parser")
  bulunan_resimler = []

  # Sayfadaki tüm resim etiketlerini tara
  for img in soup.find_all("img"):
    src = img.get("src") or img.get("data-src")
    if not src:
      continue

    # Mutlak URL oluştur
    if src.startswith("/"):
      img_url = "https://www.bim.com.tr" + src
    elif src.startswith("http"):
      img_url = src
    else:
      continue

    # Site logosu, ikon veya reklam görsellerini ele
    lower_url = img_url.lower()
    if any(
        kelime in lower_url
        for kelime in [
            "logo",
            "icon",
            "footer",
            "sosyal",
            "spacer",
            "banner",
            "header",
        ]
    ):
      continue

    alt_text = img.get("alt", "").strip()

    if img_url not in [item["url"] for item in bulunan_resimler]:
      bulunan_resimler.append({
          "url": img_url,
          "alt": alt_text if alt_text else "BİM Aktüel Afiş",
      })

  # Sadece daha önce gönderilmemiş yeni afişleri seç
  yeni_resimler = [
      item for item in bulunan_resimler if item["url"] not in sent_links
  ]

  if not yeni_resimler:
    print("Yeni afiş fotoğrafı bulunamadı.")
    sys.exit(0)

  print(f"{len(yeni_resimler)} adet yeni afiş bulundu, gönderiliyor...")

  for item in yeni_resimler:
    caption = f"🛒 <b>BİM Yeni Afiş / Katalog</b>\n📌 {item['alt']}"
    telegram_foto_gonder(item["url"], caption)

    # Gönderilen resmi hafızaya ekle
    if item["url"] not in sent_links:
      sent_links.append(item["url"])

  # Hafıza dosyasını güncelle
  with open(CACHE_FILE, "w", encoding="utf-8") as f:
    json.dump(sent_links, f, ensure_ascii=False, indent=2)

  print("Tüm afişler başarıyla gönderildi ve hafızaya kaydedildi.")

except Exception as e:
  print(f"Kritik Hata: {e}")
  sys.exit(1)
