#!/usr/bin/env python3
"""
Artemide 定制爬虫 — 从设计系列/室内/室外分类页提取产品图片。
产品名从图片文件名或 alt 提取，用 _classify_all_lighting 分类。
取 /contents/immagini/family/ 路径的产品图，每产品1张。
"""
import hashlib, re, requests, time, random, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import _classify_all_lighting

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "灯具" / "artemide"

CATEGORY_PAGES = {
    "https://www.artemide.com/en/products/design": "lamp",
    "https://www.artemide.com/en/products/indoor": "architectural indoor lamp",
    "https://www.artemide.com/en/products/outdoor": "outdoor lamp",
}

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.artemide.com/',
})


def save_as_jpeg(img, dest):
    if img.mode in ('RGBA', 'LA', 'PA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        background.save(dest, 'JPEG', quality=95)
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=95)


def extract_name_from_url(url):
    """Extract product name from artemide image filename."""
    fname = url.split('/')[-1].split('_480')[0].split('_960')[0]
    # Clean: small-960x960_ojpg → remove prefixes
    fname = re.sub(r'^(small|tall|wide)[-_]?\d*x?\d*[-_]?', '', fname)
    fname = re.sub(r'_?\d+$', '', fname)  # remove trailing numbers
    fname = fname.replace('_', ' ').replace('-', ' ').strip()
    return fname if len(fname) > 2 else ""


def scrape():
    seen_hashes = set()
    seen_imgs = set()
    folder_counters = {}
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for cat_url, context_kw in CATEGORY_PAGES.items():
            cat_label = cat_url.split('/')[-1]
            print(f'[{cat_label}]', flush=True)

            try:
                page.goto(cat_url, timeout=30000, wait_until='networkidle')
                page.wait_for_timeout(8000)
            except Exception as e:
                print(f'  跳过: {e}', flush=True)
                time.sleep(3)
                continue

            # Heavy scroll to load all products
            for _ in range(40):
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(400)

            # Get product images from /contents/immagini/family/
            imgs = page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                document.querySelectorAll('img[src*="/contents/immagini/family/"]').forEach(img => {
                    const src = img.src || '';
                    // Dedup by asset ID (the hash-like part of filename)
                    const match = src.match(/([a-f0-9]{10,})/);
                    const key = match ? match[1] : src;
                    if (seen.has(key)) return;
                    seen.add(key);
                    results.push({src, alt: img.alt || ''});
                });
                return results;
            }''')

            print(f'  {len(imgs)} product images', flush=True)

            for img_data in imgs:
                img_url = img_data['src']
                if img_url in seen_imgs:
                    continue
                seen_imgs.add(img_url)

                # Get product name
                name = img_data['alt'] or extract_name_from_url(img_url)
                if not name:
                    continue

                # Classify
                classify_name = f"{name} {context_kw}"
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
                    print(f'    {name[:30]} -> {sub_cat} ({img.size[0]}x{img.size[1]})', flush=True)

                except Exception:
                    continue

            time.sleep(random.uniform(3, 5))

        browser.close()

    print(f'\n[artemide] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
