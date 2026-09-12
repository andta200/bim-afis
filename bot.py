import json
import os
import subprocess
import sys

try:
  import requests
  from bs4 import BeautifulSoup
  from playwright.sync_api import sync_playwright
except ImportError:
  subprocess.run(
      [
          sys.executable,
          "-m",
          "pip",
          "install",
          "requests",
          "beautifulsoup4",
          "playwright",
      ],
      check=True,
  )
  subprocess.run(
      [sys.executable, "-m", "playwright", "install", "chromium"], check=True
  )
  import requests
  from bs4 import BeautifulSoup
  from playwright.sync_api import sync_playwright

TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = "https://www.bim.com.tr/Categories/680/afisler.aspx"
CACHE_FILE = "sent_links.json"


def telegram_foto_gonder(foto_url, caption):
  if not TOKEN or not CHAT_ID:
    print("BOT_TOKEN veya CHAT_ID eksik!")
    return
  api_url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }
  try:
    img_resp = requests.get(foto_url, headers=headers, timeout=20)
    if img_resp.status_code != 200:
      print(f"Resim indirilemedi: {foto_url}")
      return

    files = {"photo": ("afis.jpg", img_resp.content, "image/jpeg")}
    data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"}

    resp = requests.post(api_url, data=data, files=files, timeout=30)
    if not resp.ok:
      print(f"Telegram fotoğraf gönderim hatası: {resp.text}")
  except Exception as e:
    print(f"Telegram mesajı gönderilemedi: {e}")


sent_links = []
if os.path.exists(CACHE_FILE):
  try:
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
      sent_links = json.load(f)
  except Exception:
    sent_links = []

try:
  print("Playwright ile tüm sekmeler taranıyor...")
  with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
        ],
    )
    page = browser.new_page(
        viewport={"width": 1920, "height": 1080},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )

    page.goto(URL, timeout=60000, wait_until="networkidle")
    page.wait_for_timeout(3000)

    try:
      tabs = page.locator("xpath=//*[contains(@class, 'tab') or contains(@class, 'category') or self::a]")
      count = tabs.count()
      for i in range(min(count, 50)):
        try:
          t = tabs.nth(i)
          if t.is_visible():
            t.click(timeout=1000)
            page.wait_for_timeout(1000)
        except Exception:
          pass
    except Exception:
      pass

    html_content = page.content()
    browser.close()

  soup = BeautifulSoup(html_content, "html.parser")
  bulunan_resimler = []

  for img in soup.find_all("img"):
    src = img.get("src") or img.get("data-src") or img.get("data-original")
    if not src:
      continue

    if src.startswith("/"):
      img_url = "https://www.bim.com.tr" + src
    elif src.startswith("http"):
      img_url = src
    else:
      continue

    lower_url = img_url.lower()
    if any(
        k in lower_url
        for k in ["logo", "icon", "footer", "sosyal", "spacer", "banner"]
    ):
      continue

    if "Uploads" in img_url or "katalog" in lower_url or "afis" in lower_url:
      high_res_url = (
          img_url.replace("_thumb", "")
          .replace("small_", "")
          .replace("/s/", "/l/")
      )

      parent_text = ""
      try:
        parent = img.find_parent(class_=["tab", "content", "section", "div"])
        if parent:
          parent_text = parent.get_text(" ", strip=True)[:30]
      except Exception:
        pass

      alt_text = img.get("alt", "").strip()
      baslik_detay = alt_text if alt_text else parent_text

      if high_res_url not in [item["url"] for item in bulunan_resimler]:
        bulunan_resimler.append({
            "url": high_res_url,
            "title": baslik_detay if baslik_detay else "Aktüel Ürünler",
        })

  if len(bulunan_resimler) < 2:
    for img in soup.find_all("img"):
      src = img.get("src") or img.get("data-src")
      if src and ("Uploads" in src or "Files" in src):
        full_url = (
            ("https://www.bim.com.tr" + src) if src.startswith("/") else src
        )
        if full_url not in [i["url"] for i in bulunan_resimler]:
          bulunan_resimler.append({"url": full_url, "title": "BİM Afiş"})

  yeni_resimler = [
      item for item in bulunan_resimler if item["url"] not in sent_links
  ]

  if not yeni_resimler:
    print("Yeni afiş bulunamadı.")
    sys.exit(0)

  print(f"{len(yeni_resimler)} yeni yüksek kaliteli afiş işleniyor...")

  for idx, item in enumerate(yeni_resimler, 1):
    caption = f"BİM | Afiş | {item['title']} ({idx}/{len(yeni_resimler)})"
    telegram_foto_gonder(item["url"], caption)

    if item["url"] not in sent_links:
      sent_links.append(item["url"])

  with open(CACHE_FILE, "w", encoding="utf-8") as f:
    json.dump(sent_links, f, ensure_ascii=False, indent=2)

  print("Tüm afişler yüksek kalitede gönderildi.")

except Exception as e:
  print(f"Kritik Hata: {e}")
  sys.exit(1)
