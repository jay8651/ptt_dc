import os, json, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ----------- 自訂參數 -----------------
URLS = [
    "https://www.ptt.cc/bbs/HardwareSale/search?q=SSD",
    "https://www.ptt.cc/bbs/HardwareSale/search?q=筆電",
]
COOKIE         = {"over18": "1"}
THRESHOLD_DATE = datetime.date(2025, 7, 28)          # 只抓 7/28(含) 之後
SENT_FILE      = Path(__file__).with_name("sent.json")

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# SOCKS5 代理（需 pip install requests[socks]）
proxy_user = os.getenv("NORD_USER")
proxy_pass = os.getenv("NORD_PASS")
PROXIES = {
    "http":  f"socks5h://{proxy_user}:{proxy_pass}@nl.socks.nordhold.net:1080",
    "https": f"socks5h://{proxy_user}:{proxy_pass}@nl.socks.nordhold.net:1080",
}
# --------------------------------------

# 讀取已提醒連結
if SENT_FILE.exists():
    sent_links = set(json.loads(SENT_FILE.read_text(encoding="utf-8")))
else:
    sent_links = set()

new_links = []

def parse_page(url: str):
    """抓取單一搜尋頁面並 yield (post_date, title, link)"""
    res = requests.get(url, cookies=COOKIE, proxies=PROXIES, timeout=15)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")

    for ent in soup.select(".r-ent"):
        date_txt = ent.select_one(".date").text.strip()     # 例如 7/28
        try:
            m, d = map(int, date_txt.split("/"))
            post_date = datetime.date(datetime.datetime.now().year, m, d)
        except Exception:
            continue
        if post_date < THRESHOLD_DATE:
            continue

        a_tag = ent.select_one(".title a")
        if not a_tag:
            continue
        title = a_tag.text.strip()
        link = f"https://www.ptt.cc{a_tag['href']}"
        yield post_date, title, link

for url in URLS:
    for post_date, title, link in parse_page(url):
        if link in sent_links:
            continue

        # 發送 Discord 通知
        message = f"{title}\n👉 {link}"
        requests.post(DISCORD_WEBHOOK, json={"content": message},
                      proxies=PROXIES, timeout=10)
        new_links.append(link)

# 更新 sent.json
if new_links:
    sent_links.update(new_links)
    SENT_FILE.write_text(json.dumps(list(sent_links), ensure_ascii=False, indent=2),
                         encoding="utf-8")
