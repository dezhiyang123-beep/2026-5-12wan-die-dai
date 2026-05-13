#!/usr/bin/env python3
"""
Bose 定制爬虫 — 从分类页提取产品卡片。
用产品名做分类（便携音箱/家庭影院/耳机/耳塞等）。
CDN: assets.bosecreative.com，通过 ?io=width:1200 获取高清。
每产品1张图。
"""
import hashlib, re, requests, time, random, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "音箱" / "bose"

# Category pages → (大类, 小类)
CATEGORY_PAGES = {
    "https://www.bose.com/c/speakers/portable":     ("音箱", "便携音箱"),
    "https://www.bose.com/c/speakers/home-speakers": ("音箱", "家用音箱"),
    "https://www.bose.com/c/speakers/outdoors":      ("音箱", "户外音箱"),
    "https://www.bose.com/c/home-theater/soundbars":  ("家庭影院", "条形音箱"),
    "https://www.bose.com/c/home-theater/bass-modules": ("家庭影院", "低音炮"),
    "https://www.bose.com/c/home-theater/surround-speakers": ("家庭影院", "环绕音箱"),
    "https://www.bose.com/c/headphones":              ("耳机", "头戴耳机"),
    "https://www.bose.com/c/earbuds":                 ("耳机", "真无线耳塞"),
    "https://www.bose.com/c/portable-pa":             ("专业音响", "便携PA"),
}

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.bose.com/',
})


def save_as_jpeg(img, dest):
    if img.mode in ('RGBA', 'LA', 'PA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        background.save(dest, 'JPEG', quality=95)
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=95)


def upgrade_bose_url(url):
    """Upgrade Bose CDN URL to 1200px."""
    # Remove existing io params and add high-res
    base = re.sub(r'\?.*$', '', url)
    return f"{base}?io=width:1200,height:1200"


def scrape():
    seen_hashes = set()
    seen_slugs = set()
    folder_counters = {}
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for cat_url, (da_lei, xiao_lei) in CATEGORY_PAGES.items():
            print(f'[{xiao_lei}]', flush=True)

            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(5000)
            except Exception as e:
                print(f'  跳过: {e}', flush=True)
                time.sleep(3)
                continue

            for _ in range(15):
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(400)

            # Get product cards with images
            products = page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                document.querySelectorAll('a[href*="/p/"]').forEach(a => {
                    const href = a.href.split('?')[0];
                    if (seen.has(href)) return;
                    seen.add(href);
                    const img = a.querySelector('img[src*="bosecreative"], img[src*="bose"]');
                    if (!img) return;
                    const src = img.src || '';
                    if (!src || src.includes('svg')) return;
                    results.push({
                        slug: href.split('/').pop(),
                        name: (img.alt || '').substring(0, 60),
                        img: src
                    });
                });
                return results;
            }''')

            print(f'  {len(products)} products', flush=True)

            dest_dir = BASE / da_lei / xiao_lei
            dest_dir.mkdir(parents=True, exist_ok=True)
            folder_key = str(dest_dir)
            if folder_key not in folder_counters:
                folder_counters[folder_key] = len([f for f in dest_dir.iterdir()
                                                    if f.suffix.lower() in ('.jpg', '.jpeg')])

            for prod in products:
                if prod['slug'] in seen_slugs:
                    continue
                seen_slugs.add(prod['slug'])

                img_url = upgrade_bose_url(prod['img'])
                time.sleep(random.uniform(0.3, 0.8))

                try:
                    r = s.get(img_url, timeout=15)
                    if r.status_code != 200 or len(r.content) < 3000:
                        r = s.get(prod['img'], timeout=15)
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
                    print(f'    {prod["name"][:40]} ({img.size[0]}x{img.size[1]})', flush=True)

                except Exception:
                    continue

            time.sleep(random.uniform(2, 4))

        browser.close()

    print(f'\n[bose] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
