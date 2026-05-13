#!/usr/bin/env python3
"""
Foscarini 定制爬虫 — 从分类页直接提取产品图片（wp-content/uploads）。
产品名从图片文件名提取，用 _classify_all_lighting 分类。
每产品1张图。严格限速防反爬。
"""
import hashlib, re, requests, time, random, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import _classify_all_lighting

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "灯具" / "foscarini"

CATEGORY_PAGES = {
    "sospensione-en": "pendant lamp suspension",
    "terra-en":       "floor lamp",
    "parete-en":      "wall lamp",
    "soffitto-en":    "ceiling lamp",
    "tavolo-en":      "table lamp",
    "outdoor-en":     "outdoor lamp",
}

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Referer': 'https://www.foscarini.com/',
})


def save_as_jpeg(img, dest):
    if img.mode in ('RGBA', 'LA', 'PA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        background.save(dest, 'JPEG', quality=95)
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=95)


def extract_product_name(filename):
    """Extract product name from foscarini image filename.
    e.g. 'allegretto-assai_s_gold_22_786x865-3.jpg' → 'allegretto assai'
    """
    # Remove extension
    name = re.sub(r'\.\w+$', '', filename)
    # Remove size suffix like _786x865-3
    name = re.sub(r'_\d+x\d+[-_]\d+$', '', name)
    # Remove color/variant suffixes like _s_gold_22
    name = re.sub(r'_[a-z]_[a-z]+_\d+$', '', name)
    # Take the product name part (before first underscore or use whole thing)
    name = name.replace('-', ' ').replace('_', ' ').strip()
    # Clean up: take first 2-3 meaningful words
    words = name.split()
    return ' '.join(words[:3]) if words else name


def scrape():
    seen_hashes = set()
    seen_products = set()  # dedup by product name
    folder_counters = {}
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for cat_slug, context_kw in CATEGORY_PAGES.items():
            cat_url = f"https://www.foscarini.com/en/product-category/funzione-en/{cat_slug}/"
            print(f'[{cat_slug}]', flush=True)

            try:
                page.goto(cat_url, timeout=25000, wait_until='domcontentloaded')
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f'  跳过: {e}', flush=True)
                time.sleep(5)
                continue

            for _ in range(8):
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(500)

            # Get product images (only .jpg, skip color swatch PNGs)
            img_urls = page.evaluate('''() => {
                return [...new Set(Array.from(document.querySelectorAll('img[src*="wp-content/uploads"]'))
                    .map(i => i.src)
                    .filter(s => s.endsWith('.jpg') || s.includes('.jpg?'))
                )]
            }''')

            print(f'  {len(img_urls)} product images', flush=True)

            for img_url in img_urls:
                filename = img_url.split('/')[-1].split('?')[0]
                product_name = extract_product_name(filename)

                if not product_name or product_name in seen_products:
                    continue
                seen_products.add(product_name)

                classify_name = f"{product_name} {context_kw}"
                sub_cat = _classify_all_lighting(classify_name)

                dest_dir = BASE / sub_cat
                dest_dir.mkdir(parents=True, exist_ok=True)
                folder_key = str(dest_dir)
                if folder_key not in folder_counters:
                    folder_counters[folder_key] = len([f for f in dest_dir.iterdir()
                                                        if f.suffix.lower() in ('.jpg', '.jpeg')])

                time.sleep(random.uniform(0.3, 0.8))

                try:
                    r = s.get(img_url, timeout=15)
                    if r.status_code != 200 or len(r.content) < 5000:
                        continue

                    md5 = hashlib.md5(r.content).hexdigest()
                    if md5 in seen_hashes:
                        continue

                    img = Image.open(BytesIO(r.content))
                    if max(img.size) < 400:
                        continue

                    seen_hashes.add(md5)
                    folder_counters[folder_key] += 1
                    dest = dest_dir / f"{folder_counters[folder_key]:02d}.jpg"
                    save_as_jpeg(img, dest)
                    total += 1
                    print(f'    {product_name} -> {sub_cat} ({img.size[0]}x{img.size[1]})', flush=True)

                except Exception:
                    continue

            time.sleep(random.uniform(3, 5))

        browser.close()

    print(f'\n[foscarini] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
