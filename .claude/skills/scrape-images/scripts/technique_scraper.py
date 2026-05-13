"""
从Google Images抓取产品图，按12种设计手法(H01-H12)分类保存。
用法: python technique_scraper.py --keywords H01 H02 --count 20 --save_path ./output
"""

import os
import time
import hashlib
import argparse
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse
from PIL import Image
from io import BytesIO

TECHNIQUE_KEYWORDS = {
    "H01": "product design cutout hollow perforated",
    "H02": "product design over-mold rubber grip soft-touch",
    "H03": "product design parting line two-tone color block",
    "H04": "product design parametric gradient voronoi",
    "H05": "product design modular swappable interchangeable",
    "H06": "product design biomimicry organic bone structure",
    "H07": "product design unibody monolithic seamless",
    "H08": "product design contrast accent highlight focal point",
    "H09": "product design hidden concealed flush recessed",
    "H10": "product design material texture finish tactile",
    "H11": "product design transparent visible exposed mechanism",
    "H12": "product design interface button knob ergonomic",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

MIN_LONG_EDGE = 1000


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
    }


def search_google_images(query, count=20):
    """从Google Images搜索并提取图片URL列表。"""
    params = {
        "q": query,
        "tbm": "isch",
        "ijn": "0",
        "tbs": "isz:l",  # 倾向大图
    }
    url = "https://www.google.com/search?" + urlencode(params)
    try:
        resp = requests.get(url, headers=get_headers(), timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ERROR] 请求失败: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    img_urls = []

    # Google Images在data-src或src属性里存缩略图，实际大图在data-iurl或JS里
    # 提取img标签的src（base64小图跳过）和data属性里的URL
    for img in soup.find_all("img"):
        for attr in ("data-iurl", "data-src", "src"):
            url_candidate = img.get(attr, "")
            if url_candidate.startswith("http") and not url_candidate.startswith("data:"):
                img_urls.append(url_candidate)
                break

    # 同时从页面脚本里抽取高分辨率URL（Google Images常见模式）
    for script in soup.find_all("script"):
        text = script.string or ""
        for part in text.split('"'):
            if part.startswith("http") and any(ext in part for ext in (".jpg", ".jpeg", ".png", ".webp")):
                img_urls.append(part)

    # 去重（基于URL），取前N个候选
    seen = set()
    unique_urls = []
    for u in img_urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)
        if len(unique_urls) >= count * 3:  # 多抓一些，过滤低分辨率后仍有足够数量
            break

    return unique_urls


def check_image_size(img_bytes):
    """检查图片长边是否 >= MIN_LONG_EDGE。"""
    try:
        img = Image.open(BytesIO(img_bytes))
        return max(img.size) >= MIN_LONG_EDGE
    except Exception:
        return False


def download_image(url, save_path, filename):
    """下载单张图片，返回是否成功。"""
    try:
        resp = requests.get(url, headers=get_headers(), timeout=20, stream=True)
        resp.raise_for_status()
        content = resp.content
        if not check_image_size(content):
            return False
        os.makedirs(save_path, exist_ok=True)
        with open(os.path.join(save_path, filename), "wb") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"  [SKIP] 下载失败 {url[:60]}... : {e}")
        return False


def scrape_technique(technique_id, category, count, base_save_path):
    """抓取单个手法的产品图。"""
    if technique_id not in TECHNIQUE_KEYWORDS:
        print(f"[ERROR] 未知手法编号: {technique_id}")
        return

    query = TECHNIQUE_KEYWORDS[technique_id]
    save_path = os.path.join(base_save_path, technique_id)
    print(f"\n[{technique_id}] 搜索: {query}")
    print(f"  目标数量: {count}  保存路径: {save_path}")

    img_urls = search_google_images(query, count)
    print(f"  找到候选URL: {len(img_urls)}")

    downloaded = 0
    seen_urls = set()

    for url in img_urls:
        if downloaded >= count:
            break
        if url in seen_urls:
            continue
        seen_urls.add(url)

        idx = downloaded + 1
        filename = f"{technique_id}_{category}_{idx:03d}.jpg"
        success = download_image(url, save_path, filename)
        if success:
            downloaded += 1
            print(f"  [{downloaded}/{count}] 已保存: {filename}")

        delay = random.uniform(2.0, 3.0)
        time.sleep(delay)

    print(f"  完成: 成功下载 {downloaded} 张")
    return downloaded


def main():
    parser = argparse.ArgumentParser(description="按设计手法抓取产品图")
    parser.add_argument(
        "--techniques",
        nargs="+",
        default=list(TECHNIQUE_KEYWORDS.keys()),
        help="手法编号列表，如 H01 H02（默认全部12种）",
    )
    parser.add_argument("--category", default="产品", help="品类名称，用于文件命名")
    parser.add_argument("--count", type=int, default=20, help="每种手法目标下载数量")
    parser.add_argument(
        "--save_path",
        default=os.path.expanduser("~/Desktop/设计素材库/03_设计手法库"),
        help="保存根目录（默认: ~/Desktop/设计素材库/03_设计手法库）",
    )
    args = parser.parse_args()

    print("=== 手法库爬虫启动 ===")
    print(f"手法: {args.techniques}")
    print(f"品类: {args.category}")
    print(f"每种数量: {args.count}")
    print(f"保存路径: {args.save_path}")

    total = 0
    for tech_id in args.techniques:
        n = scrape_technique(tech_id, args.category, args.count, args.save_path)
        if n:
            total += n

    print(f"\n=== 完成 | 总计下载 {total} 张 ===")


if __name__ == "__main__":
    main()
