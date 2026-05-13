#!/usr/bin/env python3
"""
Flos 定制爬虫 — 从分类页提取产品链接+名称+hero图。
用产品名 + 分类页上下文做 _classify_all_lighting 分类。
每产品取1张 hero 图（分类页上的 packshot）。
"""
import hashlib, re, requests, time, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import _classify_all_lighting

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "灯具" / "flos"

# Category page URL → context keyword for classification
CATEGORY_PAGES = {
    "table-lamps":       "table lamp",
    "floor-lamps":       "floor lamp",
    "suspension-lamps":  "pendant lamp suspension",
    "ceiling-lamps":     "ceiling lamp",
    "wall-lamps":        "wall lamp",
    "portable-lamps":    "portable lamp rechargeable",
    "outdoor-lamps":     "outdoor lamp",
}

s = requests.Session()
s.headers['User-Agent'] = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/125.0.0.0 Safari/537.36')


def scrape():
    seen_hashes = set()
    seen_slugs = set()
    folder_counters = {}
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for slug, context_kw in CATEGORY_PAGES.items():
            cat_url = f"https://flos.com/en/us/shop-products/{slug}/"
            print(f'[{slug}]', flush=True)

            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f'  跳过: {e}', flush=True)
                continue

            # Scroll to load all products
            for _ in range(15):
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(500)

            # Try load more button
            try:
                while True:
                    btn = page.query_selector('button:has-text("Load More"), button:has-text("Show More")')
                    if btn and btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(2000)
                    else:
                        break
            except Exception:
                pass

            for _ in range(5):
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(400)

            # Extract products: name from URL slug, hero image from FLOS-master packshot
            products = page.evaluate('''() => {
                const results = [];
                const seen = new Set();

                // Find product links with FLOS-master images
                document.querySelectorAll('a[href*=".html"]').forEach(a => {
                    const href = a.href.split('?')[0];
                    if (!href.includes('/en/us/') || href.includes('shop-products') ||
                        href.includes('shop-by-room') || href.includes('privacy')) return;

                    // Extract slug (product name)
                    const parts = href.split('/');
                    let productSlug = '';
                    for (const part of parts) {
                        if (part && !['en','us','https:','','flos.com'].includes(part) &&
                            !part.includes('.html') && !part.startsWith('M-')) {
                            productSlug = part;
                            break;
                        }
                    }
                    if (!productSlug || productSlug.length < 3 || seen.has(productSlug)) return;
                    seen.add(productSlug);

                    // Find hero image (FLOS-master packshot)
                    const img = a.querySelector('img[src*="FLOS-master"]');
                    if (!img) return;

                    results.push({
                        slug: productSlug,
                        name: productSlug.replace(/-/g, ' '),
                        imgSrc: img.src
                    });
                });
                return results;
            }''')

            print(f'  {len(products)} products', flush=True)

            for prod in products:
                if prod['slug'] in seen_slugs:
                    continue
                seen_slugs.add(prod['slug'])

                # Classify using product name + category context
                classify_name = f"{prod['name']} {context_kw}"
                sub_cat = _classify_all_lighting(classify_name)

                dest_dir = BASE / sub_cat
                dest_dir.mkdir(parents=True, exist_ok=True)
                folder_key = str(dest_dir)
                if folder_key not in folder_counters:
                    folder_counters[folder_key] = len([f for f in dest_dir.iterdir()
                                                        if f.suffix.lower() in ('.jpg', '.jpeg')])

                # Download hero image (high-res)
                img_url = prod['imgSrc'].split('?')[0] + '?sw=1200&sh=1200'

                try:
                    r = s.get(img_url, timeout=15)
                    if r.status_code != 200 or len(r.content) < 5000:
                        r = s.get(prod['imgSrc'], timeout=15)
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
                    img.convert('RGB').save(dest, 'JPEG', quality=95)
                    total += 1
                    print(f'    {prod["name"]} -> {sub_cat}', flush=True)

                except Exception:
                    continue

            time.sleep(1)

        browser.close()

    print(f'\n[flos] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
