#!/usr/bin/env python3
"""
Makita 定制爬虫 — 遍历工具子分类页，提取产品图片。
用产品名做 _classify_brand_product 分类。
CDN 图片升级到 width=800。每产品1张图。
"""
import hashlib, re, requests, time, random, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import _classify_brand_product

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "电动工具" / "makita"

# Subcategory URLs (18V LXT is the main platform with most products)
SUBCATEGORY_URLS = [
    "https://makitatools.com/products/tools/cordless/18v-lxt/drills-and-fastening/impact-drivers",
    "https://makitatools.com/products/tools/cordless/18v-lxt/drills-and-fastening/driver-drills-and-hammer-drivers",
    "https://makitatools.com/products/tools/cordless/18v-lxt/drills-and-fastening/rotary-hammers",
    "https://makitatools.com/products/tools/cordless/18v-lxt/drills-and-fastening/screwdrivers",
    "https://makitatools.com/products/tools/cordless/18v-lxt/drills-and-fastening/impact-wrenches",
    "https://makitatools.com/products/tools/cordless/18v-lxt/drills-and-fastening/nailers",
    "https://makitatools.com/products/tools/cordless/18v-lxt/saws/circular-saws",
    "https://makitatools.com/products/tools/cordless/18v-lxt/saws/reciprocating-saws",
    "https://makitatools.com/products/tools/cordless/18v-lxt/saws/jig-saws",
    "https://makitatools.com/products/tools/cordless/18v-lxt/saws/miter-saws",
    "https://makitatools.com/products/tools/cordless/18v-lxt/saws/band-saws",
    "https://makitatools.com/products/tools/cordless/18v-lxt/grinding-sanding-and-polishing/grinders",
    "https://makitatools.com/products/tools/cordless/18v-lxt/grinding-sanding-and-polishing/sanders",
    "https://makitatools.com/products/tools/cordless/18v-lxt/wood-surfacing-and-fine-finishing/routers",
    "https://makitatools.com/products/tools/cordless/18v-lxt/wood-surfacing-and-fine-finishing/planers",
    "https://makitatools.com/products/tools/cordless/18v-lxt/oscillating-multi-tools",
    "https://makitatools.com/products/tools/cordless/18v-lxt/concrete-and-masonry-tools",
    "https://makitatools.com/products/tools/cordless/18v-lxt/dust-extraction",
    # XGT (40V) additional products
    "https://makitatools.com/products/tools/cordless/40v-xgt/drills-and-fastening",
    "https://makitatools.com/products/tools/cordless/40v-xgt/saws",
    "https://makitatools.com/products/tools/cordless/40v-xgt/grinding-sanding-and-polishing",
]

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://makitatools.com/',
})


def save_as_jpeg(img, dest):
    if img.mode in ('RGBA', 'LA', 'PA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        background.save(dest, 'JPEG', quality=95)
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=95)


def upgrade_makita_url(url):
    """Upgrade Makita CDN URL to 800px."""
    return re.sub(r'width=\d+&height=\d+', 'width=800&height=800', url)


def scrape():
    seen_hashes = set()
    seen_alts = set()  # dedup by product name
    folder_counters = {}
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for cat_url in SUBCATEGORY_URLS:
            cat_label = cat_url.split('/')[-1]
            print(f'[{cat_label}]', flush=True)

            try:
                page.goto(cat_url, timeout=30000, wait_until='networkidle')
                page.wait_for_timeout(5000)
            except Exception as e:
                print(f'  跳过: {e}', flush=True)
                time.sleep(3)
                continue

            for _ in range(15):
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(400)

            # Get product images
            products = page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                document.querySelectorAll('img[src*="cdn.makitatools.com"]').forEach(img => {
                    const src = img.src || '';
                    if (img.naturalWidth < 100 || src.includes('navigation') || src.includes('login')
                        || src.includes('logo') || src.includes('CategoryLanding/Tools/')
                        || src.includes('CategoryLanding/icons')) return;
                    const base = src.split('/').pop().split('?')[0];
                    if (seen.has(base)) return;
                    seen.add(base);
                    results.push({src: src, alt: (img.alt || '').substring(0, 80)});
                });
                return results;
            }''')

            print(f'  {len(products)} products', flush=True)

            for prod in products:
                alt = prod['alt']
                if not alt or alt in seen_alts:
                    continue
                # Skip combo kits (multiple tools, not a single product)
                if 'combo kit' in alt.lower() and 'pc' in alt.lower():
                    continue
                seen_alts.add(alt)

                # Classify
                classification = _classify_brand_product(alt, [], 'makita')
                if not classification:
                    classification = _classify_brand_product(f"{alt} {cat_label}", [], 'makita')
                if not classification:
                    continue

                major, minor = classification
                dest_dir = BASE / major / minor if minor else BASE / major
                dest_dir.mkdir(parents=True, exist_ok=True)
                folder_key = str(dest_dir)
                if folder_key not in folder_counters:
                    folder_counters[folder_key] = len([f for f in dest_dir.iterdir()
                                                        if f.suffix.lower() in ('.jpg', '.jpeg')])

                img_url = upgrade_makita_url(prod['src'])

                try:
                    # Download via Playwright (CDN blocks direct requests)
                    img_bytes = page.evaluate('''(url) => {
                        return fetch(url).then(r => r.arrayBuffer()).then(buf => {
                            return Array.from(new Uint8Array(buf));
                        });
                    }''', img_url)

                    content = bytes(img_bytes)
                    if len(content) < 3000:
                        continue

                    md5 = hashlib.md5(content).hexdigest()
                    if md5 in seen_hashes:
                        continue

                    img = Image.open(BytesIO(content))
                    if max(img.size) < 200:
                        continue

                    seen_hashes.add(md5)
                    folder_counters[folder_key] += 1
                    dest = dest_dir / f"{folder_counters[folder_key]:02d}.jpg"
                    save_as_jpeg(img, dest)
                    total += 1
                    print(f'    {alt[:40]} -> {major}/{minor} ({img.size[0]}x{img.size[1]})', flush=True)

                except Exception:
                    continue

            time.sleep(random.uniform(3, 5))

        browser.close()

    print(f'\n[makita] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
