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
        raw_data = res.content

        # 优先从页面内容自动识别编码构建 soup，支持无 lxml 环境
        soup = None
        for parser in ("lxml", "html.parser"):
            try:
                soup = BeautifulSoup(raw_data, parser)
                break
            except Exception:
                continue
        if soup is None:
            raise RuntimeError("No HTML parser available")

        # 若标题缺失，再回退按多编码解码后重建 soup
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        else:
            detected = chardet.detect(raw_data)
            enc_candidates = [
                res.encoding,
                detected.get("encoding"),
                getattr(res, "apparent_encoding", None),
                "utf-8",
                "gb18030",
            ]
            seen = set()
            text = None
            for enc in [e for e in enc_candidates if e and not (e in seen or seen.add(e))]:
                try:
                    text = raw_data.decode(enc)
                    break
                except Exception:
                    continue
            text = text or raw_data.decode("utf-8", errors="ignore")

            for parser in ("lxml", "html.parser"):
                try:
                    soup = BeautifulSoup(text, parser)
                    break
                except Exception:
                    continue
            title = soup.title.string.strip() if soup and soup.title else "No Title"

        paragraphs = " ".join(p.get_text() for p in soup.find_all("p")) if soup else ""
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
