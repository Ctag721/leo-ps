#!/usr/bin/env python3
"""
PS5 Pro 补货检查（JB Hi-Fi Australia）—— GitHub Actions 版

每次运行只检查一次，由 GitHub Actions 定时触发。
有货时通过 ntfy 推送到手机。ntfy 的 topic 从环境变量 NTFY_TOPIC 读取
（在 repo 的 Settings → Secrets and variables → Actions 里设置）。
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

PRODUCT_URL = "https://www.jbhifi.com.au/products/ps5-playstation-5-pro-console"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-AU,en;q=0.9",
}

OUT_OF_STOCK_WORDS = ["sold out", "out of stock", "currently unavailable", "coming soon"]
IN_STOCK_WORDS = ["add to cart", "add to bag", "buy now"]

MELB = timezone(timedelta(hours=11))


def log(msg):
    print(f"[{datetime.now(MELB):%Y-%m-%d %H:%M} 墨尔本] {msg}", flush=True)


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def check_via_json():
    data = json.loads(fetch(PRODUCT_URL.rstrip("/") + ".js"))
    price = data.get("price")
    price_str = f"${price / 100:,.2f}" if isinstance(price, (int, float)) else "?"
    return bool(data.get("available")), price_str


def check_via_html():
    html = fetch(PRODUCT_URL).lower()
    if any(w in html for w in OUT_OF_STOCK_WORDS):
        return False, "?"
    if any(w in html for w in IN_STOCK_WORDS):
        return True, "?"
    return None, "?"


def push(title, message, priority="urgent"):
    if not NTFY_TOPIC:
        log("没有设置 NTFY_TOPIC，跳过推送")
        return
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,  # HTTP header 只能用英文，中文放在正文里
            "Priority": priority,
            "Click": PRODUCT_URL,
            "Tags": "video_game",
        },
    )
    urllib.request.urlopen(req, timeout=15)


def main():
    # 手动运行（workflow_dispatch）时发一条测试推送，确认手机能收到
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        push("PS5 Pro watch", "测试推送：手机通知设置成功 ✅", priority="default")
        log("已发送测试推送")

    try:
        available, price = check_via_json()
        method = "json"
    except Exception as e:
        log(f"JSON 检查失败（{e}），改用网页检查")
        try:
            available, price = check_via_html()
            method = "html"
        except Exception as e2:
            log(f"网页检查也失败了: {e2}")
            sys.exit(1)  # 让 Actions 显示红色失败，方便发现被拦截之类的问题

    if available is None:
        log("页面状态判断不出来，可能 JB 改版了")
        sys.exit(1)
    if available:
        log(f"✅ 有货！价格 {price}（{method}）")
        push("PS5 Pro in stock!", f"JB Hi-Fi 现在有货 {price}，赶紧去下单！")
    else:
        log(f"无货（{method}）")


if __name__ == "__main__":
    main()
