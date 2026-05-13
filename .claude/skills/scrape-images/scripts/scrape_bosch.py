#!/usr/bin/env python3
"""
Bosch Professional 定制爬虫 — 从工具分类页提取产品图片。
用产品名（从 URL/alt 提取）+ _classify_brand_product 分类。
图片从 ocsmedia CDN 获取 740x740 版本。
严格限速。
"""
import hashlib, re, requests, time, random, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import _classify_brand_product

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "电动工具" / "bosch_professional"

# Tool category pages
CATEGORY_URLS = [
    "https://www.boschtools.com/us/en/drills-hammer-drills-impact-drivers-23409-ocs-c/",
    "https://www.boschtools.com/us/en/circular-saws-36763-ocs-c/",
    "https://www.boschtools.com/us/en/band-saws-36762-ocs-c/",
    "https://www.boschtools.com/us/en/jig-saws-36764-ocs-c/",
    "https://www.boschtools.com/us/en/reciprocating-saws-36761-ocs-c/",
    "https://www.boschtools.com/us/en/saws-23418-ocs-c/",
    "https://www.boschtools.com/us/en/grinders-metalworking-23412-ocs-c/",
    "https://www.boschtools.com/us/en/sanders-23416-ocs-c/",
    "https://www.boschtools.com/us/en/routers-router-tables-23415-ocs-c/",
    "https://www.boschtools.com/us/en/planers-23417-ocs-c/",
    "https://www.boschtools.com/us/en/hammers-rotary-demolition-23411-ocs-c/",
    "https://www.boschtools.com/us/en/oscillating-multi-tools-23414-ocs-c/",
    "https://www.boschtools.com/us/en/nailers-staplers-41742-ocs-c/",
    "https://www.boschtools.com/us/en/dust-extraction-collection-23421-ocs-c/",
    "https://www.boschtools.com/us/en/measuring-layout-tools-23413-ocs-c/",
    "https://www.boschtools.com/us/en/benchtop-tools-25311-ocs-c/",
    "https://www.boschtools.com/us/en/batteries-chargers-starter-kits-23419-ocs-c/",
]

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Referer': 'https://www.boschtools.com/',
})


def save_as_jpeg(img, dest):
    if img.mode in ('RGBA', 'LA', 'PA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        background.save(dest, 'JPEG', quality=95)
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=95)


def upgrade_bosch_url(url):
    """Upgrade Bosch CDN URL to 740x740 resolution."""
    # Pattern 1: /product-image/265x265/ → /product-image/740x740/
    upgraded = re.sub(r'/product-image/\d+x\d+/', '/product-image/740x740/', url)
    if upgraded != url:
        return upgraded
    # Pattern 2: /optimized/166x164/ → /optimized/740x740/
    upgraded = re.sub(r'/optimized/\d+x\d+/', '/optimized/740x740/', url)
    return upgraded


def extract_product_name(url, alt_text):
    """Extract product name from Bosch image URL or alt text."""
    if alt_text and len(alt_text) > 5:
        return alt_text
    # From URL: cordless-drill-drivers-ps21-2a-060199291g.png
    m = re.search(r'/([a-z][\w-]+)\.png', url, re.I)
    if m:
        return m.group(1).replace('-', ' ')
    return ""


def scrape():
    seen_hashes = set()
    seen_urls = set()
    folder_counters = {}
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for cat_url in CATEGORY_URLS:
            cat_name = re.search(r'/en/([\w-]+)-\d+-ocs-c/', cat_url)
            cat_label = cat_name.group(1).replace('-', ' ') if cat_name else cat_url[-40:]
            print(f'[{cat_label}]', flush=True)

            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(8000)
            except Exception as e:
                print(f'  跳过: {e}', flush=True)
                time.sleep(5)
                continue

            # Heavy scroll to load all product tiles
            for _ in range(20):
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(400)

            # Get product images
            products = page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                document.querySelectorAll('img').forEach(img => {
                    const src = img.src || '';
                    if (img.naturalWidth < 100) return;
                    if (src.includes('logo') || src.includes('.svg') || src.includes('263x155')) return;
                    if (!src.includes('ocsmedia') && !src.includes('boschtools.com/binary')) return;

                    // Dedup by base filename
                    const base = src.split('/').pop().split('.')[0];
                    if (seen.has(base)) return;
                    seen.add(base);

                    const link = img.closest('a');
                    results.push({
                        src: src,
                        alt: (img.alt || '').substring(0, 80),
                        href: link ? link.href : ''
                    });
                });
                return results;
            }''')

            print(f'  {len(products)} product images', flush=True)

            for prod in products:
                img_url = prod['src']
                if img_url in seen_urls:
                    continue
                seen_urls.add(img_url)

                # Get product name and classify
                name = extract_product_name(img_url, prod['alt'])
                if not name:
                    continue

                classification = _classify_brand_product(name, [], 'bosch_professional')
                if not classification:
                    # Fallback: use category URL as context
                    classification = _classify_brand_product(f"{name} {cat_label}", [], 'bosch_professional')
                if not classification:
                    continue

                major, minor = classification
                dest_dir = BASE / major / minor if minor else BASE / major
                dest_dir.mkdir(parents=True, exist_ok=True)
                folder_key = str(dest_dir)
                if folder_key not in folder_counters:
                    folder_counters[folder_key] = len([f for f in dest_dir.iterdir()
                                                        if f.suffix.lower() in ('.jpg', '.jpeg')])

                # Download high-res version
                hires_url = upgrade_bosch_url(img_url)
                time.sleep(random.uniform(0.3, 0.8))

                try:
                    r = s.get(hires_url, timeout=15, allow_redirects=True)
                    if r.status_code != 200 or len(r.content) < 3000:
                        r = s.get(img_url, timeout=15, allow_redirects=True)
                        if r.status_code != 200 or len(r.content) < 3000:
                            continue

                    md5 = hashlib.md5(r.content).hexdigest()
                    if md5 in seen_hashes:
                        continue

                    img = Image.open(BytesIO(r.content))
                    if max(img.size) < 150:
                        continue

                    seen_hashes.add(md5)
                    folder_counters[folder_key] += 1
                    dest = dest_dir / f"{folder_counters[folder_key]:02d}.jpg"
                    save_as_jpeg(img, dest)
                    total += 1
                    print(f'    {name[:40]} -> {major}/{minor} ({img.size[0]}x{img.size[1]})', flush=True)

                except Exception:
                    continue

            time.sleep(random.uniform(3, 5))

        browser.close()

    print(f'\n[bosch] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
