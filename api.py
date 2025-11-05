from flask import Flask, request
import os
import requests
from bs4 import BeautifulSoup
import chardet  # ✅ 新增：自动检测网页编码

app = Flask(__name__)

# 从 Vercel 环境变量读取
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = os.environ.get("REPO")

print("🔹 Debug Info:")
print("BOT_TOKEN:", BOT_TOKEN)
print("REPO:", REPO)

def fetch_page_info(link):
    """可靠的网页抓取函数，防乱码（自动检测编码）"""
    try:
        res = requests.get(link, timeout=10)
        # 直接检测原始字节流编码
        raw_data = res.content
        detected = chardet.detect(raw_data)
        encoding = detected.get("encoding", "utf-8")

        # 特例：常见中文网站一律强制 GBK 优先
        if any(domain in link for domain in ["sina.com.cn", "163.com", "qq.com", "ifeng.com", "sohu.com", "people.com.cn"]):
            encoding = "gbk"

        text = raw_data.decode(encoding, errors="ignore")
        soup = BeautifulSoup(text, "html.parser")

        title = soup.title.string.strip() if soup.title else "No Title"
        paragraphs = " ".join(p.get_text() for p in soup.find_all("p"))
        summary = paragraphs[:200] + "..." if len(paragraphs) > 200 else paragraphs

        return title, summary

    except Exception as e:
        return "No Title", f"Failed to fetch: {e}"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    print("🔹 Received data:", data)

    message = data.get("message", {})
    text = message.get("text", "")

    if text.startswith("http"):
        link = text
        title, summary = fetch_page_info(link)

        # 创建 GitHub Issue
        url = f"https://api.github.com/repos/{REPO}/issues"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        data_issue = {"title": title, "body": f"{summary}\n\n[阅读原文]({link})"}
        r = requests.post(url, json=data_issue, headers=headers)

        if r.status_code == 201:
            print("✅ Issue created:", title)
        else:
            print("❌ Failed to create issue:", r.text)

        # 回复 Telegram
        chat_id = message["chat"]["id"]
        reply = f"📰 已保存到 GitHub：{title}" if r.status_code == 201 else f"❌ 创建失败：{r.text}"
        requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            params={"chat_id": chat_id, "text": reply}
        )

    return "ok"

@app.route("/")
def index():
    return "Telegram News Bot is running ✅"

if __name__ == "__main__":
    app.run()
