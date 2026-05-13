#!/usr/bin/env python3
"""
Olight 定制爬虫 — 从 all-products 页获取产品卡片。
用产品名做 _classify_all_lighting 分类（手电筒品牌）。
CDN 图片升级到 @1200w_1200h_90q。
每产品1张图。过滤非灯具产品（热成像、瞄准镜等）。
"""
import hashlib, re, requests, time, random, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import _classify_all_lighting

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "灯具" / "olight"

# Skip non-lighting products
SKIP_PRODUCT = re.compile(
    r'(thermal|monocular|osight|red.?dot|sight|scope|optic|holster|mount|battery'
    r'|charger|case|pouch|filter|diffuser|clip$|strap|lanyard|pocket.?clip)',
    re.I
)

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.olight.com/',
})


def upgrade_olight_url(url):
    """Upgrade Olight CDN URL to 1200px resolution."""
    # Remove existing size suffix and add 1200
    base = re.sub(r'@\d+w.*$', '', url)
    # Remove .webp if present in base
    base = re.sub(r'\.webp$', '', base)
    if base.endswith('.gif'):
        return base  # GIFs can't be resized
    return f"{base}@1200w_1200h_90q.webp"


def save_as_jpeg(img, dest):
    if img.mode in ('RGBA', 'LA', 'PA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        background.save(dest, 'JPEG', quality=95)
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=95)


def scrape():
    seen_hashes = set()
    folder_counters = {}
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print('[all-products]', flush=True)

        try:
            page.goto('https://www.olight.com/all-products', timeout=30000, wait_until='domcontentloaded')
            page.wait_for_timeout(8000)
        except Exception as e:
            print(f'  跳过: {e}', flush=True)
            browser.close()
            return

        # Scroll to load all products
        for _ in range(30):
            page.evaluate('window.scrollBy(0, window.innerHeight)')
            page.wait_for_timeout(400)

        # Get product cards
        products = page.evaluate('''() => {
            const results = [];
            const seen = new Set();
            document.querySelectorAll('a[href*="/store/"]').forEach(a => {
                const href = a.href.split('?')[0];
                if (seen.has(href) || !href.includes('olight.com/store/')) return;
                seen.add(href);
                const img = a.querySelector('img');
                if (!img) return;
                const src = img.src || img.dataset.src || '';
                if (!src || src.includes('svg')) return;
                const alt = img.alt || '';
                results.push({href, name: alt.substring(0, 80), img: src});
            });
            return results;
        }''')

        print(f'  {len(products)} products found', flush=True)

        for prod in products:
            name = prod['name']

            # Skip non-lighting products
            if SKIP_PRODUCT.search(name):
                continue
            if not name:
                continue

            # Classify - add "flashlight" context since most olight products are flashlights
            # Determine context from product name
            context = "flashlight"
            if re.search(r'head.?lamp|headlight', name, re.I):
                context = "headlamp"
            elif re.search(r'lantern|camp', name, re.I):
                context = "camping lantern"
            elif re.search(r'weapon|pistol|gun|rail|pl[- ]', name, re.I):
                context = "weapon light tactical"

            classify_name = f"{name} {context}"
            sub_cat = _classify_all_lighting(classify_name)

            dest_dir = BASE / sub_cat
            dest_dir.mkdir(parents=True, exist_ok=True)
            folder_key = str(dest_dir)
            if folder_key not in folder_counters:
                folder_counters[folder_key] = len([f for f in dest_dir.iterdir()
                                                    if f.suffix.lower() in ('.jpg', '.jpeg')])

            # Download high-res image
            img_url = upgrade_olight_url(prod['img'])
            time.sleep(random.uniform(0.3, 0.8))

            try:
                r = s.get(img_url, timeout=15)
                if r.status_code != 200 or len(r.content) < 3000:
                    # Fallback to original URL
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
                print(f'  {name[:40]} -> {sub_cat} ({img.size[0]}x{img.size[1]})', flush=True)

            except Exception:
                continue

        browser.close()

    print(f'\n[olight] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
