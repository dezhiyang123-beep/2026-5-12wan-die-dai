#!/usr/bin/env python3
"""
Milwaukee 定制爬虫 — 通过拦截 /api/search/v3/listings API 获取产品数据。
用 Playwright 访问分类页触发 API，拦截 JSON 响应获取产品名+图片+分类。
每产品1张图。用 _classify_brand_product 分类。
"""
import hashlib, re, requests, time, random, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import _classify_brand_product

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "电动工具" / "milwaukee"

# Tool category URLs to crawl
CATEGORY_URLS = [
    "https://www.milwaukeetool.com/products/power-tools/drilling/drill-drivers",
    "https://www.milwaukeetool.com/products/power-tools/drilling/hammer-drills",
    "https://www.milwaukeetool.com/products/power-tools/drilling/right-angle-drills",
    "https://www.milwaukeetool.com/products/power-tools/fastening/impact-drivers",
    "https://www.milwaukeetool.com/products/power-tools/fastening/impact-wrenches",
    "https://www.milwaukeetool.com/products/power-tools/fastening/ratchets",
    "https://www.milwaukeetool.com/products/power-tools/fastening/screwdrivers",
    "https://www.milwaukeetool.com/products/power-tools/woodworking/circular-saws",
    "https://www.milwaukeetool.com/products/power-tools/woodworking/jig-saws",
    "https://www.milwaukeetool.com/products/power-tools/woodworking/miter-saws",
    "https://www.milwaukeetool.com/products/power-tools/woodworking/routers",
    "https://www.milwaukeetool.com/products/power-tools/woodworking/sanders",
    "https://www.milwaukeetool.com/products/power-tools/woodworking/planers",
    "https://www.milwaukeetool.com/products/power-tools/woodworking/oscillating-multi-tool",
    "https://www.milwaukeetool.com/products/power-tools/sawzall-reciprocating-saws/sawzalls",
    "https://www.milwaukeetool.com/products/power-tools/metalworking/grinders",
    "https://www.milwaukeetool.com/products/power-tools/metalworking/band-saws",
    "https://www.milwaukeetool.com/products/power-tools/metalworking/sanders-and-polishers",
    "https://www.milwaukeetool.com/products/power-tools/metalworking/shears-and-nibblers",
    "https://www.milwaukeetool.com/products/power-tools/concrete/rotary-hammers",
    "https://www.milwaukeetool.com/products/power-tools/concrete/concrete-vibrators",
    "https://www.milwaukeetool.com/products/power-tools/woodworking/nailers-and-staplers",
]

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Referer': 'https://www.milwaukeetool.com/',
})


def save_as_jpeg(img, dest):
    if img.mode in ('RGBA', 'LA', 'PA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        background.save(dest, 'JPEG', quality=95)
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=95)


def scrape():
    seen_hashes = set()
    seen_skus = set()
    folder_counters = {}
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()

        for cat_url in CATEGORY_URLS:
            cat_label = cat_url.split('/')[-1]
            print(f'[{cat_label}]', flush=True)

            api_data = {}

            def handle_response(response):
                if 'api/search/v3/listings' in response.url:
                    try:
                        api_data['body'] = response.json()
                    except Exception:
                        pass

            page = ctx.new_page()
            page.on('response', handle_response)

            try:
                page.goto(cat_url, timeout=30000, wait_until='networkidle')
                page.wait_for_timeout(8000)
            except Exception as e:
                print(f'  跳过: {e}', flush=True)
                page.close()
                time.sleep(3)
                continue

            page.close()

            if 'body' not in api_data:
                print('  无 API 数据', flush=True)
                time.sleep(3)
                continue

            products = api_data['body'].get('listings', {}).get('products', [])
            print(f'  {len(products)} products', flush=True)

            for prod in products:
                if prod.get('type') != 'PRODUCT':
                    continue

                sku = prod.get('subtitle', '') or prod.get('meta', {}).get('sku', '')
                if sku in seen_skus:
                    continue
                seen_skus.add(sku)

                title = prod.get('title', '')
                img_info = prod.get('image', {})
                img_url = img_info.get('url', '')
                if not img_url or not title:
                    continue

                # Build full image URL
                if img_url.startswith('/'):
                    img_url = f"https://www.milwaukeetool.com{img_url}"

                # Classify using product title
                classification = _classify_brand_product(title, [], 'milwaukee')
                if not classification:
                    classification = _classify_brand_product(f"{title} {cat_label}", [], 'milwaukee')
                if not classification:
                    continue

                major, minor = classification
                dest_dir = BASE / major / minor if minor else BASE / major
                dest_dir.mkdir(parents=True, exist_ok=True)
                folder_key = str(dest_dir)
                if folder_key not in folder_counters:
                    folder_counters[folder_key] = len([f for f in dest_dir.iterdir()
                                                        if f.suffix.lower() in ('.jpg', '.jpeg')])

                time.sleep(random.uniform(0.3, 0.8))

                try:
                    r = s.get(img_url, timeout=15)
                    if r.status_code != 200 or len(r.content) < 3000:
                        continue

                    md5 = hashlib.md5(r.content).hexdigest()
                    if md5 in seen_hashes:
                        continue

                    img = Image.open(BytesIO(r.content))
                    if max(img.size) < 200:
                        continue

                    seen_hashes.add(md5)
                    folder_counters[folder_key] += 1
                    dest = dest_dir / f"{folder_counters[folder_key]:02d}.jpg"
                    save_as_jpeg(img, dest)
                    total += 1
                    print(f'    {title[:40]} -> {major}/{minor} ({img.size[0]}x{img.size[1]})', flush=True)

                except Exception:
                    continue

            time.sleep(random.uniform(3, 5))

        browser.close()

    print(f'\n[milwaukee] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
