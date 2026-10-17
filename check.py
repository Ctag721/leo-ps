#!/usr/bin/env python3
"""
PS5 Pro 补货检查（多家澳洲零售商）—— GitHub Actions 版

- JB Hi-Fi：用 Shopify 的 JSON 接口，能准确判断有没有货。
- 其他网站：没有公开接口，所以检查网页里出现了哪些库存相关的字样
  （比如 "add to cart" / "sold out" / "available to purchase in"），
  一旦和上次检查的结果不一样就推送，让你自己点进去看。

上次检查的结果存在 state.json 里，由 workflow 用 actions/cache 在每次运行之间保留。
"""

import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
STATE_FILE = "state.json"
MELB = timezone(timedelta(hours=11))

JB_URL = "https://www.jbhifi.com.au/products/ps5-playstation-5-pro-console"

# 其他零售商：名字 → 商品页
OTHER_STORES = {
    "EB Games": "https://www.ebgames.com.au/product/ps5/313202-playstation-5-pro-console",
    "Kmart": "https://www.kmart.com.au/product/playstation-5-pro-console-white-110012215/",
    "Big W": "https://www.bigw.com.au/product/playstation-5-pro-console/p/104141",
}

# 网页里出现这些字样，就认为可能有货
IN_STOCK_WORDS = ["add to cart", "add to bag", "add to trolley", "buy now", '"instock"', "in stock"]
# 用来判断页面状态有没有变化的所有字样
STATUS_WORDS = IN_STOCK_WORDS + [
    "out of stock", "sold out", "currently unavailable", "unavailable",
    "notify me", "coming soon", "available to purchase in", "pre-order", "preorder",
    '"outofstock"',
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-AU,en;q=0.9",
}


def log(msg):
    print(f"[{datetime.now(MELB):%Y-%m-%d %H:%M}] {msg}", flush=True)


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def push(title, message, click, priority="urgent"):
    if not NTFY_TOPIC:
        log("NTFY_TOPIC not set, skip push")
        return
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title, "Priority": priority, "Click": click, "Tags": "video_game"},
    )
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        log(f"push failed: {e}")


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def check_jb():
    """返回 (有货?, 价格)。JSON 失败时退回网页关键词。"""
    try:
        data = json.loads(fetch(JB_URL + ".js"))
        price = data.get("price")
        price_str = f"${price / 100:,.2f}" if isinstance(price, (int, float)) else "?"
        return bool(data.get("available")), price_str
    except Exception as e:
        log(f"JB JSON failed ({e}), trying HTML")
    html = fetch(JB_URL).lower()
    if any(w in html for w in ["sold out", "out of stock", "currently unavailable"]):
        return False, "?"
    if any(w in html for w in ["add to cart", "buy now"]):
        return True, "?"
    raise RuntimeError("can't tell JB stock status")


def page_signature(url):
    """返回网页里出现的库存相关字样（排序后的列表）。"""
    html = fetch(url).lower()
    return sorted(w for w in STATUS_WORDS if w in html)


def main():
    state = load_state()
    first_run = not state

    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        push("PS5 Pro watch", "测试推送：手机通知设置成功 ✅", JB_URL, priority="default")

    # ---- JB Hi-Fi ----
    try:
        available, price = check_jb()
        log(f"JB Hi-Fi: {'IN STOCK ' + price if available else 'out of stock'}")
        if available:
            push("PS5 Pro in stock at JB Hi-Fi!", f"JB Hi-Fi 现在有货 {price}，赶紧去下单！", JB_URL)
        state["JB Hi-Fi"] = {"available": available}
    except Exception as e:
        log(f"JB Hi-Fi check failed: {e}")

    # ---- 其他零售商 ----
    for name, url in OTHER_STORES.items():
        try:
            sig = page_signature(url)
        except Exception as e:
            log(f"{name}: check failed ({e})")
            continue

        prev = state.get(name, {}).get("signature")
        log(f"{name}: {sig or '(no status words found)'}")

        if prev is not None and sig != prev:
            looks_in_stock = any(w in sig for w in IN_STOCK_WORDS) and not any(
                w in sig for w in ["out of stock", "sold out", '"outofstock"']
            )
            title = f"PS5 Pro: {name} page changed"
            msg = (
                f"{name} 的 PS5 Pro 页面状态变了，可能补货了，快点进去看看！"
                if looks_in_stock
                else f"{name} 的 PS5 Pro 页面有变化，点进去确认一下。"
            )
            push(title, f"{msg}\n之前: {prev}\n现在: {sig}", url,
                 priority="urgent" if looks_in_stock else "high")

        state[name] = {"signature": sig}

    if first_run:
        log("First run: saved baseline, will alert on future changes")
    save_state(state)


if __name__ == "__main__":
    main()
