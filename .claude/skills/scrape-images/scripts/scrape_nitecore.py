#!/usr/bin/env python3
"""
Nitecore 定制爬虫 — 从 nitecore.cn 分类页发现产品，提取产品型号名。
用型号前缀做功能分类（NU→通用头灯, UT→越野跑头灯, EDC→EDC手电等）。
每产品最多2张图（og:image + 第一张 album 图）。
"""
import hashlib, re, requests, time, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import _classify_all_lighting

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "灯具" / "nitecore"

# Nitecore product series → (context keyword for _classify_all_lighting)
# The series prefix from the URL determines the product type
# Nitecore-specific subcategory mapping (not using _classify_all_lighting
# because it's too coarse for a flashlight specialist brand)
HEADLAMP_SERIES = {
    "nu": "头灯/通用头灯",
    "ut": "头灯/越野跑头灯",
    "ha": "头灯/电池头灯",
    "hc": "头灯/高显色头灯",
    "hu": "头灯/通用头灯",
    "nr": "头灯/充电头灯",
}

FLASHLIGHT_SERIES = {
    "edc": "手电筒/EDC手电",
    "p":   "手电筒/战术手电",
    "e":   "手电筒/便携手电",
    "mh":  "手电筒/充电搜索手电",
    "mt":  "手电筒/多功能手电",
    "t":   "手电筒/迷你手电",
    "tm":  "手电筒/高亮搜索手电",
    "srt": "手电筒/战术手电",
    "npl": "手电筒/枪灯",
    "nwl": "手电筒/武器灯",
    "cl":  "营地灯/营地灯",
    "l":   "手电筒/工作灯",
    "lr":  "手电筒/工作灯",
}

# Category URLs to crawl
CATEGORIES = [
    "flashlight/edc",
    "flashlight/pseries",
    "flashlight/eseries",
    "flashlight/mh",
    "flashlight/mt",
    "flashlight/npl",
    "flashlight/tseries",
    "flashlight/srt",
    "flashlight/tm",
    "flashlight/nwl",
    "flashlight/cl",
    "flashlight/lseries",
    "headlamp",
]

MAX_IMGS_PER_PRODUCT = 2

s = requests.Session()
s.headers['User-Agent'] = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/125.0.0.0 Safari/537.36')


def get_subcategory(product_slug, category_path):
    """Determine 大类/小类 folder from product slug and category."""
    slug_lower = product_slug.lower()

    # Headlamps: classify by series prefix
    if 'headlamp' in category_path:
        for prefix, subcat in HEADLAMP_SERIES.items():
            if slug_lower.startswith(prefix):
                return subcat
        return "头灯/通用头灯"

    # Flashlights: classify by series from category path
    cat_series = category_path.split('/')[-1]  # e.g. 'edc', 'pseries', 'cl'
    # Map category path to series key
    cat_to_key = {
        'edc': 'edc', 'pseries': 'p', 'eseries': 'e', 'mh': 'mh',
        'mt': 'mt', 'npl': 'npl', 'tseries': 't', 'srt': 'srt',
        'tm': 'tm', 'nwl': 'nwl', 'cl': 'cl', 'lseries': 'l',
    }
    key = cat_to_key.get(cat_series, '')
    if key in FLASHLIGHT_SERIES:
        return FLASHLIGHT_SERIES[key]
    return "手电筒/其他手电"


def scrape():
    seen_hashes = set()
    seen_slugs = set()
    folder_counters = {}
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for cat_path in CATEGORIES:
            cat_url = f"https://www.nitecore.cn/category/{cat_path}"
            print(f'[{cat_path}]', flush=True)

            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f'  跳过: {e}', flush=True)
                continue

            for _ in range(10):
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(500)

            product_urls = page.evaluate('''() => {
                return [...new Set(Array.from(document.querySelectorAll('a[href*="/product/"]'))
                    .map(a => a.href.split('?')[0])
                    .filter(h => h.includes('nitecore.cn/product/'))
                )]
            }''')

            print(f'  {len(product_urls)} products', flush=True)

            for prod_url in product_urls:
                slug = prod_url.rstrip('/').split('/')[-1]
                if slug in seen_slugs:
                    continue
                seen_slugs.add(slug)

                # Classify using brand-specific mapping
                sub_cat_path = get_subcategory(slug, cat_path)

                dest_dir = BASE / sub_cat_path
                dest_dir.mkdir(parents=True, exist_ok=True)
                folder_key = str(dest_dir)
                if folder_key not in folder_counters:
                    folder_counters[folder_key] = len([f for f in dest_dir.iterdir()
                                                        if f.suffix.lower() in ('.jpg', '.jpeg')])

                # Visit product page, get max 2 images
                try:
                    page.goto(prod_url, timeout=25000, wait_until='domcontentloaded')
                    page.wait_for_timeout(2000)
                except Exception:
                    continue

                img_urls = page.evaluate('''() => {
                    const urls = [];
                    // og:image first (hero shot)
                    const og = document.querySelector('meta[property="og:image"]');
                    if (og && og.content) urls.push(og.content);
                    // First album/product image
                    const albumImgs = document.querySelectorAll('img[src*="album"], img.content-small-img');
                    albumImgs.forEach(img => {
                        let src = img.src || '';
                        src = src.replace(/_s(\\.[a-z]+)$/i, '$1');  // remove _s suffix for full size
                        if (src.startsWith('http') && !urls.includes(src)) urls.push(src);
                    });
                    return urls;
                }''')

                saved = 0
                for img_url in img_urls[:MAX_IMGS_PER_PRODUCT]:
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
                        img.convert('RGB').save(dest, 'JPEG', quality=95)
                        total += 1
                        saved += 1

                    except Exception:
                        continue

                if saved:
                    print(f'    {slug} -> {sub_cat_path} ({saved} imgs)', flush=True)

            time.sleep(1)

        browser.close()

    print(f'\n[nitecore] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
