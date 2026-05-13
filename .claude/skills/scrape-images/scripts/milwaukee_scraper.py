#!/usr/bin/env python3
"""
Milwaukee bare tool / tool only 单品产品图爬虫。
从 milwaukeetool.com 抓取 bare tool 产品主图（白底单品图），跳过套装图。
保存到 ~/Desktop/设计素材库/01_品类标杆库/电动工具/milwaukee_baretool/
命名：milwaukee_baretool_{品类}_{序号:03d}.jpg
"""
import hashlib
import re
import time
import random
import sys
import os
from pathlib import Path
from io import BytesIO

try:
    import requests
    from PIL import Image
except ImportError:
    print("[ERROR] 缺少依赖，请先运行: pip install requests pillow")
    sys.exit(1)

SAVE_DIR = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "电动工具" / "milwaukee_baretool"
MIN_LONG_EDGE = 1000
REQUEST_DELAY = (2.0, 3.0)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.milwaukeetool.com/",
}

# 品类 URL → 品类标签
CATEGORY_URLS = {
    "drill-driver": "https://www.milwaukeetool.com/products/power-tools/drilling/drill-drivers",
    "hammer-drill": "https://www.milwaukeetool.com/products/power-tools/drilling/hammer-drills",
    "impact-driver": "https://www.milwaukeetool.com/products/power-tools/fastening/impact-drivers",
    "impact-wrench": "https://www.milwaukeetool.com/products/power-tools/fastening/impact-wrenches",
    "circular-saw": "https://www.milwaukeetool.com/products/power-tools/woodworking/circular-saws",
    "jig-saw": "https://www.milwaukeetool.com/products/power-tools/woodworking/jig-saws",
    "grinder": "https://www.milwaukeetool.com/products/power-tools/metalworking/grinders",
    "reciprocating-saw": "https://www.milwaukeetool.com/products/power-tools/sawzall-reciprocating-saws/sawzalls",
    "rotary-hammer": "https://www.milwaukeetool.com/products/power-tools/concrete/rotary-hammers",
    "oscillating-tool": "https://www.milwaukeetool.com/products/power-tools/woodworking/oscillating-multi-tool",
}

# 套装识别关键词（命中则跳过）
KIT_KEYWORDS = re.compile(
    r"\b(kit|combo|set|bundle|pc\.?|piece|\d+-tool|\bwith\b.*battery|\bwith\b.*charger)\b",
    re.IGNORECASE,
)

# bare tool 识别关键词（命中才保留）
BARE_TOOL_KEYWORDS = re.compile(
    r"\b(bare\s*tool|tool\s*only|skin\s*only|body\s*only)\b",
    re.IGNORECASE,
)

# 用于回退：标题里无包含 battery/charger 等词也视为可能是单品
BUNDLE_SIGNALS = re.compile(
    r"\b(battery|charger|case|bag|batteries|chargers)\b",
    re.IGNORECASE,
)


def is_bare_tool(title: str) -> bool:
    """判断产品是否为 bare tool 单品。"""
    if KIT_KEYWORDS.search(title):
        return False
    if BARE_TOOL_KEYWORDS.search(title):
        return True
    # 没有明确 bare tool 标识，但也没有套装/附件信号 → 保留（单品概率高）
    if not BUNDLE_SIGNALS.search(title):
        return True
    return False


def fetch_category_products(session: requests.Session, category: str, url: str) -> list[dict]:
    """通过官网搜索 API 获取某品类的产品列表。"""
    products = []
    try:
        # Milwaukee 官网使用 Elasticsearch 风格的分页 API
        api_url = (
            "https://www.milwaukeetool.com/api/search/v3/listings"
            f"?url={url.replace('https://www.milwaukeetool.com', '')}"
            "&start=0&count=100"
        )
        resp = session.get(api_url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        raw_products = data.get("listings", {}).get("products", [])
        products = [p for p in raw_products if p.get("type") == "PRODUCT"]
        print(f"  [{category}] API返回 {len(raw_products)} 条，PRODUCT类型 {len(products)} 条")
    except requests.exceptions.HTTPError as e:
        print(f"  [{category}] HTTP错误: {e} — 尝试直接解析页面失败，跳过")
    except requests.exceptions.ConnectionError as e:
        print(f"  [{category}] 连接错误: {e}")
    except requests.exceptions.Timeout:
        print(f"  [{category}] 请求超时，跳过")
    except ValueError as e:
        print(f"  [{category}] JSON解析失败: {e}，该品类可能有反爬保护")
    except Exception as e:
        print(f"  [{category}] 未知错误: {e}")
    return products


def download_image(session: requests.Session, img_url: str) -> Image.Image | None:
    """下载图片并返回 PIL Image，失败返回 None。"""
    try:
        resp = session.get(img_url, timeout=20)
        resp.raise_for_status()
        if len(resp.content) < 5000:
            return None
        img = Image.open(BytesIO(resp.content))
        img.load()
        return img
    except Exception:
        return None


def save_jpeg(img: Image.Image, dest: Path) -> None:
    """保存为 JPEG，处理透明通道。"""
    if img.mode in ("RGBA", "LA", "PA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        bg.save(dest, "JPEG", quality=95)
    else:
        img.convert("RGB").save(dest, "JPEG", quality=95)


def build_image_url(raw_url: str) -> str:
    """将相对路径补全为绝对 URL，并尝试请求高分辨率版本。"""
    if raw_url.startswith("//"):
        raw_url = "https:" + raw_url
    elif raw_url.startswith("/"):
        raw_url = "https://www.milwaukeetool.com" + raw_url

    # 尝试去掉尺寸参数拿原图（Milwaukee CDN 常见模式）
    raw_url = re.sub(r"[?&](width|w|size|format)=[^&]+", "", raw_url)
    return raw_url


def scrape():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    seen_hashes: set[str] = set()
    counters: dict[str, int] = {}
    total_saved = 0
    total_skipped_kit = 0
    total_skipped_size = 0

    for category, url in CATEGORY_URLS.items():
        print(f"\n{'='*50}")
        print(f"品类: {category}")
        products = fetch_category_products(session, category, url)

        if not products:
            print(f"  [{category}] 无产品数据，跳过")
            time.sleep(random.uniform(*REQUEST_DELAY))
            continue

        for prod in products:
            title = prod.get("title", "").strip()
            if not title:
                continue

            if not is_bare_tool(title):
                total_skipped_kit += 1
                print(f"  跳过套装: {title[:60]}")
                continue

            # 提取图片 URL
            img_info = prod.get("image", {})
            img_url = img_info.get("url", "") or img_info.get("src", "")
            if not img_url:
                continue
            img_url = build_image_url(img_url)

            time.sleep(random.uniform(*REQUEST_DELAY))

            img = download_image(session, img_url)
            if img is None:
                print(f"  下载失败: {title[:50]}")
                continue

            # 分辨率过滤
            long_edge = max(img.size)
            if long_edge < MIN_LONG_EDGE:
                total_skipped_size += 1
                print(f"  跳过低分辨率({img.size[0]}x{img.size[1]}): {title[:50]}")
                continue

            # 去重
            md5 = hashlib.md5(img.tobytes()).hexdigest()
            if md5 in seen_hashes:
                continue
            seen_hashes.add(md5)

            # 命名并保存
            counters[category] = counters.get(category, 0) + 1
            filename = f"milwaukee_baretool_{category}_{counters[category]:03d}.jpg"
            dest = SAVE_DIR / filename
            try:
                save_jpeg(img, dest)
                total_saved += 1
                print(f"  保存: {filename}  ({img.size[0]}x{img.size[1]})  {title[:50]}")
            except Exception as e:
                print(f"  保存失败: {e}")

        time.sleep(random.uniform(*REQUEST_DELAY))

    print(f"\n{'='*50}")
    print(f"完成。保存: {total_saved} 张 | 跳过套装: {total_skipped_kit} | 跳过低分辨率: {total_skipped_size}")
    print(f"保存路径: {SAVE_DIR}")


if __name__ == "__main__":
    scrape()
