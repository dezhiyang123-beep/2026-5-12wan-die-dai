#!/usr/bin/env python3
"""
音箱品牌通用爬虫 — 支持 marshall, sonos, jbl, harman_kardon, devialet。
每个品牌从产品列表页提取产品图。
"""
import hashlib, re, requests, time, random, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "音箱"

# Brand → list of category page URLs
BRANDS = {
    "marshall": [
        "https://www.marshall.com/us/en/speakers/bluetooth/portable",
        "https://www.marshall.com/us/en/speakers/bluetooth/home",
        "https://www.marshall.com/us/en/speakers/tv-sound",
        "https://www.marshall.com/us/en/speakers/party",
        "https://www.marshall.com/us/en/headphones",
    ],
    "sonos": [
        "https://www.sonos.com/en-us/shop/speakers",
        "https://www.sonos.com/en-us/shop/home-theater",
        "https://www.sonos.com/en-us/shop/headphones",
    ],
    "jbl": [
        "https://www.jbl.com/bluetooth-speakers/",
        "https://www.jbl.com/home-audio/",
        "https://www.jbl.com/headphones/",
        "https://www.jbl.com/earbuds/",
    ],
    "harman_kardon": [
        "https://www.harmankardon.com/speakers/",
        "https://www.harmankardon.com/soundbars/",
        "https://www.harmankardon.com/headphones/",
    ],
    "devialet": [
        "https://www.devialet.com/en-us/phantom/",
        "https://www.devialet.com/en-us/dione/",
        "https://www.devialet.com/en-us/mania/",
        "https://www.devialet.com/en-us/gemini/",
    ],
}

s = requests.Session()
s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


def save_as_jpeg(img, dest):
    if img.mode in ('RGBA', 'LA', 'PA'):
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        bg.save(dest, 'JPEG', quality=95)
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=95)


def classify_audio(product_name, page_url):
    """Simple audio product classification from name/URL."""
    name = (product_name + ' ' + page_url).lower()
    if any(kw in name for kw in ['soundbar', 'tv-sound', 'dione', 'heston']):
        return '条形音箱'
    if any(kw in name for kw in ['headphone', 'head phone', 'over-ear', 'on-ear']):
        return '头戴耳机'
    if any(kw in name for kw in ['earbud', 'earphone', 'in-ear', 'gemini', 'true wireless']):
        return '真无线耳塞'
    if any(kw in name for kw in ['subwoofer', 'sub ', 'bass']):
        return '低音炮'
    if any(kw in name for kw in ['portable', 'bluetooth', 'outdoor', 'party', 'mania', 'flip', 'charge', 'clip']):
        return '便携音箱'
    if any(kw in name for kw in ['home', 'bookshelf', 'phantom', 'acton', 'stanmore', 'woburn', 'one', 'era']):
        return '家用音箱'
    return '音箱'


def scrape_brand(browser, brand_name, urls):
    """Scrape a single brand."""
    seen_hashes = set()
    seen_imgs = set()
    folder_counters = {}
    total = 0

    page = browser.new_page()

    for cat_url in urls:
        print(f'  [{cat_url.split("/")[-1] or cat_url.split("/")[-2]}]', end='', flush=True)

        try:
            page.goto(cat_url, timeout=25000, wait_until='domcontentloaded')
            page.wait_for_timeout(8000)
        except Exception:
            print(' 跳过', flush=True)
            time.sleep(3)
            continue

        for _ in range(20):
            page.evaluate('window.scrollBy(0, window.innerHeight)')
            page.wait_for_timeout(400)

        # Get all product images (generic selector)
        imgs = page.evaluate('''() => {
            const results = [];
            const seen = new Set();
            document.querySelectorAll('img').forEach(img => {
                const src = img.src || '';
                if (img.naturalWidth < 150 || src.includes('svg') || src.includes('logo')
                    || src.includes('icon') || src.includes('flag')) return;
                const base = src.split('/').pop().split('?')[0];
                if (seen.has(base)) return;
                seen.add(base);
                results.push({src, alt: (img.alt || '').substring(0, 60)});
            });
            return results;
        }''')

        print(f' {len(imgs)} imgs', flush=True)

        for img_data in imgs:
            img_url = img_data['src']
            if img_url in seen_imgs:
                continue
            seen_imgs.add(img_url)

            sub_cat = classify_audio(img_data['alt'], cat_url)
            dest_dir = BASE / brand_name / sub_cat
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
            except Exception:
                continue

        time.sleep(random.uniform(2, 4))

    page.close()
    return total


def scrape():
    grand_total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for brand_name, urls in BRANDS.items():
            print(f'\n[{brand_name}]', flush=True)
            count = scrape_brand(browser, brand_name, urls)
            grand_total += count
            print(f'  → {brand_name}: {count} 张', flush=True)

        browser.close()

    print(f'\n[speakers] 完成: {grand_total} 张', flush=True)


if __name__ == '__main__':
    scrape()
