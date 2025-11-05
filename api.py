from flask import Flask, request
import os
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# 从 Vercel 环境变量读取
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = os.environ.get("REPO")  # 例如 "yiranzhimo/news_collector"

print("🔹 Debug Info:")
print("BOT_TOKEN:", BOT_TOKEN)
print("REPO:", REPO)

def fetch_page_info(link):
    """自动识别编码、提取网页标题与摘要（防乱码版）"""
    try:
        res = requests.get(link, timeout=10)
        encoding = res.encoding.lower() if res.encoding else ""

        # 如果编码缺失或是默认的 ISO-8859-1，则重新检测
        if encoding in ["iso-8859-1", "", None]:
            detected = requests.utils.get_encodings_from_content(res.text)
            if detected:
                res.encoding = detected[0]
            else:
                res.encoding = res.apparent_encoding  # 使用 requests 自动猜测
        
        # 针对常见中文网站，强制使用 gbk 避免乱码
        chinese_domains = ["sina.com.cn", "163.com", "qq.com", "ifeng.com", "sohu.com", "people.com.cn"]
        if any(domain in link for domain in chinese_domains):
            res.encoding = "gbk"

        soup = BeautifulSoup(res.text, "html.parser")
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
