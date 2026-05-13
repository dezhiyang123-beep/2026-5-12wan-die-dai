#!/usr/bin/env python3
"""
Louis Poulsen 定制爬虫 — SPA 站点。
1. 从分类页获取产品链接
2. 进入每个产品详情页获取高分辨率 DAM 图片（height=2600）
3. RGBA 图片先填充白色背景再转 JPEG
4. 用产品名 + 分类上下文做分类
"""
import hashlib, re, requests, time, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import _classify_all_lighting

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "灯具" / "louis_poulsen"

CATEGORY_PAGES = {
    "pendants":  "pendant lamp suspension",
    "floor":     "floor lamp",
    "table":     "table lamp",
    "wall":      "wall sconce lamp",
    "outdoor":   "outdoor lamp",
    "portable":  "portable lamp rechargeable",
}

MAX_IMGS_PER_PRODUCT = 2

s = requests.Session()
s.headers['User-Agent'] = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/125.0.0.0 Safari/537.36')


def save_as_jpeg(img, dest):
    """Convert image to JPEG with white background (handles RGBA transparency)."""
    if img.mode in ('RGBA', 'LA', 'PA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])  # use alpha as mask
        background.save(dest, 'JPEG', quality=95)
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=95)


def upgrade_dam_url(url):
    """Upgrade DAM URL to high resolution."""
    # Extract the base assetstream URL and add high-res params
    m = re.search(r'(https://dam\.louispoulsen\.dk/DigizuiteCore/LegacyService/api/assetstream/\d+/\d+\.webp)', url)
    if m:
        base = m.group(1)
        # Request 2600px - DAM will return the largest available
        return f"{base}?height=2600&width=2600"
    return url


def scrape():
    seen_hashes = set()
    seen_slugs = set()
    folder_counters = {}
    total = 0
    cookie_dismissed = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for cat_slug, context_kw in CATEGORY_PAGES.items():
            cat_url = f"https://www.louispoulsen.com/en-us/catalog/private/{cat_slug}"
            print(f'[{cat_slug}]', flush=True)

            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(5000)
            except Exception as e:
                print(f'  跳过: {e}', flush=True)
                continue

            # Dismiss cookie dialog once
            if not cookie_dismissed:
                try:
                    for sel in ['button:has-text("Allow all")', '#onetrust-accept-btn-handler']:
                        btn = page.query_selector(sel)
                        if btn:
                            btn.click()
                            page.wait_for_timeout(2000)
                            cookie_dismissed = True
                            break
                except Exception:
                    pass

            # Scroll to load all products
            for _ in range(15):
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(600)

            # Get product links
            product_links = page.evaluate('''(catSlug) => {
                return [...new Set(Array.from(document.querySelectorAll('a[href]'))
                    .map(a => a.href.split('?')[0])
                    .filter(h => h.includes('/catalog/private/' + catSlug + '/') && h.split('/').length >= 8)
                )]
            }''', cat_slug)

            print(f'  {len(product_links)} products', flush=True)

            # Visit each product page for high-res images
            for prod_url in product_links:
                slug = prod_url.rstrip('/').split('/')[-1]
                if slug in seen_slugs:
                    continue
                seen_slugs.add(slug)

                product_name = slug.replace('-', ' ')
                classify_name = f"{product_name} {context_kw}"
                sub_cat = _classify_all_lighting(classify_name)

                dest_dir = BASE / sub_cat
                dest_dir.mkdir(parents=True, exist_ok=True)
                folder_key = str(dest_dir)
                if folder_key not in folder_counters:
                    folder_counters[folder_key] = len([f for f in dest_dir.iterdir()
                                                        if f.suffix.lower() in ('.jpg', '.jpeg')])

                try:
                    page.goto(prod_url, timeout=25000, wait_until='domcontentloaded')
                    page.wait_for_timeout(4000)
                except Exception:
                    continue

                # Get high-res DAM images from product page (height=2600 versions)
                img_urls = page.evaluate('''() => {
                    const urls = [];
                    const seen = new Set();
                    document.querySelectorAll('img[src*="dam.louispoulsen"]').forEach(img => {
                        const src = img.src || '';
                        // Extract asset ID to dedup across sizes
                        const m = src.match(/assetstream\\/(\d+)/);
                        if (!m) return;
                        const assetId = m[1];
                        if (seen.has(assetId)) return;
                        seen.add(assetId);
                        // Only get images that are rendered large (product gallery, not thumbnails)
                        if ((img.naturalWidth || 0) >= 400) {
                            urls.push(src);
                        }
                    });
                    return urls;
                }''')

                saved = 0
                for img_url in img_urls[:MAX_IMGS_PER_PRODUCT]:
                    hires_url = upgrade_dam_url(img_url)

                    try:
                        r = s.get(hires_url, timeout=15)
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
                        saved += 1

                    except Exception:
                        continue

                if saved:
                    print(f'    {product_name} -> {sub_cat} ({saved})', flush=True)

            time.sleep(1)

        browser.close()

    print(f'\n[louis_poulsen] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
