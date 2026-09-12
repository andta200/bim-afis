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


def telegram_gonder(metin):
  if not TOKEN or not CHAT_ID:
    print("BOT_TOKEN veya CHAT_ID eksik!")
    return
  api_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
  if len(metin) > 4000:
    metin = metin[:4000] + "\n...(Karakter sınırından dolayı kesildi)"

  try:
    requests.post(
        api_url,
        json={"chat_id": CHAT_ID, "text": metin, "parse_mode": "HTML"},
        timeout=10,
    )
  except Exception as e:
    print(f"Telegram mesajı gönderilemedi: {e}")


# Daha önce gönderilen linklerin hafızasını yükle
sent_links = []
if os.path.exists(CACHE_FILE):
  try:
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
      sent_links = json.load(f)
  except Exception:
    sent_links = []

try:
  print(f"BİM afişleri kontrol ediliyor: {URL}")
  r = requests.get(URL, headers=headers, timeout=15)
  if r.status_code != 200:
    print(f"Hata: HTTP {r.status_code}")
    sys.exit(1)

  soup = BeautifulSoup(r.text, "html.parser")

  ogeler = []
  for a in soup.find_all("a", href=True):
    href = a["href"]
    text = a.get_text(strip=True)
    if (
        "AktuelUrunler" in href
        or "afis" in href.lower()
        or "katalog" in href.lower()
        or len(text) > 5
    ):
      if href.startswith("/"):
        href = "https://www.bim.com.tr" + href
      elif not href.startswith("http"):
        continue
      if text and text not in [o["text"] for o in ogeler]:
        ogeler.append({"text": text, "href": href})

  if not ogeler:
    for a in soup.find_all("a", href=True):
      if "Details" in a["href"] or "Category" in a["href"]:
        text = a.get_text(strip=True)
        if text:
          href = a["href"]
          if href.startswith("/"):
            href = "https://www.bim.com.tr" + href
          ogeler.append({"text": text, "href": href})

  # Sadece daha önce gönderilmemiş yeni linkleri filtrele
  yeni_ogeler = [item for item in ogeler if item["href"] not in sent_links]

  if not yeni_ogeler:
    print("Yeni içerik bulunamadı, bildirim gönderilmeyecek.")
    sys.exit(0)

  # Yeni bulunanları mesaj yap ve gönder
  mesaj_satirlari = [
      f"• {item['text']} -> {item['href']}" for item in yeni_ogeler[:20]
  ]
  rapor = (
      "🛒 <b>BİM Yeni Afiş / Katalog Eklendi!</b>\n\n"
      + "\n".join(mesaj_satirlari)
  )
  telegram_gonder(rapor)

  # Yeni gönderilenleri hafızaya ekle ve dosyayı kaydet
  for item in yeni_ogeler:
    if item["href"] not in sent_links:
      sent_links.append(item["href"])

  with open(CACHE_FILE, "w", encoding="utf-8") as f:
    json.dump(sent_links, f, ensure_ascii=False, indent=2)

  print(f"{len(yeni_ogeler)} yeni öğe gönderildi ve hafızaya kaydedildi.")

except Exception as e:
  print(f"Kritik Hata: {e}")
  sys.exit(1)
