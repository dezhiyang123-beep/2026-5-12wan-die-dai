#!/usr/bin/env python3
"""
Philips Hue 定制爬虫 — 从分类页获取产品链接+名称。
用产品名 + 分类上下文做 _classify_all_lighting 分类。
每产品最多2张图。
"""
import hashlib, re, requests, time, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import _classify_all_lighting

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "灯具" / "philips_lighting"

# Category URL → context keyword
CATEGORY_PAGES = {
    "https://www.philips-hue.com/en-us/products/smart-table-lamps":     "table lamp",
    "https://www.philips-hue.com/en-us/products/smart-floor-lamps":     "floor lamp",
    "https://www.philips-hue.com/en-us/products/smart-ceiling-lights":  "ceiling lamp",
    "https://www.philips-hue.com/en-us/products/smart-pendant-lights":  "pendant lamp",
    "https://www.philips-hue.com/en-us/products/smart-wall-lights":     "wall lamp",
    "https://www.philips-hue.com/en-us/products/smart-light-bulbs":     "smart LED bulb",
    "https://www.philips-hue.com/en-us/products/smart-light-strips":    "LED light strip smart",
}

MAX_IMGS_PER_PRODUCT = 2

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

        for cat_url, context_kw in CATEGORY_PAGES.items():
            print(f'[{context_kw}]', flush=True)

            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f'  跳过: {e}', flush=True)
                continue

            for _ in range(10):
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(500)

            # Get product links with names
            products = page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                document.querySelectorAll('a[href*="/p/"]').forEach(a => {
                    const href = a.href.split('?')[0];
                    if (seen.has(href)) return;
                    seen.add(href);
                    // Extract product name from URL slug
                    const parts = href.split('/');
                    const pPart = parts.indexOf('p');
                    if (pPart < 0) return;
                    const slug = parts.slice(pPart + 1).join('/').replace(/-/g, ' ');
                    results.push({href, slug});
                });
                return results;
            }''')

            print(f'  {len(products)} products', flush=True)

            for prod in products:
                slug_key = prod['href'].split('?')[0]
                if slug_key in seen_slugs:
                    continue
                seen_slugs.add(slug_key)

                product_name = prod['slug']
                classify_name = f"{product_name} {context_kw}"
                sub_cat = _classify_all_lighting(classify_name)

                dest_dir = BASE / sub_cat
                dest_dir.mkdir(parents=True, exist_ok=True)
                folder_key = str(dest_dir)
                if folder_key not in folder_counters:
                    folder_counters[folder_key] = len([f for f in dest_dir.iterdir()
                                                        if f.suffix.lower() in ('.jpg', '.jpeg')])

                # Visit product page, get images
                try:
                    page.goto(prod['href'], timeout=20000, wait_until='domcontentloaded')
                    page.wait_for_timeout(2000)
                except Exception:
                    continue

                img_urls = page.evaluate('''() => {
                    const urls = [];
                    // og:image
                    const og = document.querySelector('meta[property="og:image"]');
                    if (og && og.content) urls.push(og.content);
                    // Signify CDN images
                    document.querySelectorAll('img[src*="signify"]').forEach(img => {
                        const src = img.src || '';
                        if (src && !src.includes('icon') && !src.includes('logo') &&
                            !src.includes('svg') && !src.includes('flag') &&
                            !urls.includes(src)) {
                            urls.push(src);
                        }
                    });
                    return urls;
                }''')

                saved = 0
                for img_url in img_urls[:MAX_IMGS_PER_PRODUCT]:
                    hires = img_url.split('?')[0] + '?wid=1200&hei=1200&qlt=85'
                    try:
                        r = s.get(hires, timeout=10)
                        if r.status_code != 200 or len(r.content) < 5000:
                            r = s.get(img_url, timeout=10)
                            if r.status_code != 200 or len(r.content) < 5000:
                                continue

                        md5 = hashlib.md5(r.content).hexdigest()
                        if md5 in seen_hashes:
                            continue

                        img = Image.open(BytesIO(r.content))
                        if max(img.size) < 300:
                            continue

                        seen_hashes.add(md5)
                        folder_counters[folder_key] += 1
                        dest = dest_dir / f"{folder_counters[folder_key]:02d}.jpg"
                        img.convert('RGB').save(dest, 'JPEG', quality=95)
                        total += 1
                        saved += 1

                    except Exception:
                        continue

                if saved:
                    print(f'    {product_name[:40]} -> {sub_cat} ({saved})', flush=True)

            time.sleep(1)

        browser.close()

    print(f'\n[philips] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
