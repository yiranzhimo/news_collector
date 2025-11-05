from flask import Flask, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# ========== 配置信息 ==========
GITHUB_TOKEN = "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"
REPO = "yiranzhimo/news_collector/"  # 例如 "li-qian/news-collector"
BOT_TOKEN = "8317115528:AAG7PP3H1wqPNzdHO1u4Lyt_nWZYmZxt-wY"
# ==============================

def create_issue(title, body):
    url = f"https://api.github.com/repos/{REPO}/issues"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    data = {"title": title, "body": body}
    r = requests.post(url, json=data, headers=headers)
    if r.status_code == 201:
        print("✅ Issue created:", title)
    else:
        print("❌ Failed:", r.text)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    message = data.get("message", {})
    text = message.get("text", "")

    if text.startswith("http"):
        link = text
        res = requests.get(link, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        title = soup.title.string.strip() if soup.title else "No Title"
        paragraphs = " ".join(p.get_text() for p in soup.find_all("p"))
        summary = paragraphs[:200] + "..." if len(paragraphs) > 200 else paragraphs
        create_issue(title, f"{summary}\n\n[阅读原文]({link})")

        chat_id = message["chat"]["id"]
        reply = f"📰 已保存到 GitHub：{title}"
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                     params={"chat_id": chat_id, "text": reply})
    return "ok"

if __name__ == "__main__":
    app.run()
