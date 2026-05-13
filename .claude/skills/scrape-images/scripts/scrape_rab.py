#!/usr/bin/env python3
"""
RAB Lighting 定制爬虫 — 策略：
1. 一次遍历所有分类页，收集全站 feature 链接并去重
2. 根据 feature 链接所在的分类页判断大类/小类（跟 bega 一样用 URL 分类）
3. 每个 feature 页只取第1张 /images/product/photo/ 图
4. 替换为 /images/product/largePhoto/ 高清版
5. 严格限速
"""
import hashlib, re, requests, time, random, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "灯具" / "rab_lighting"

# URL path → (大类, 小类)
CATEGORIES = {
    "outdoor/AREALIGHTS":           ("户外灯", "场地灯"),
    "outdoor/CANOPYLIGHTS":         ("户外灯", "雨棚灯"),
    "outdoor/FLOOD":                ("户外灯", "泛光灯"),
    "outdoor/GARAGELIGHTS":         ("户外灯", "车库灯"),
    "outdoor/LANDSCAPE":            ("户外灯", "景观灯"),
    "outdoor/WALLPACKS":            ("户外灯", "壁灯"),
    "outdoor/WALL_SCONCES":         ("户外灯", "壁挂灯"),
    "indoor/COMMERCIAL_DOWNLIGHTS": ("室内灯", "商用筒灯"),
    "indoor/PANELS_TROFFERS":       ("室内灯", "面板灯"),
    "indoor/HIBAY":                 ("室内灯", "高棚灯"),
    "indoor/STRIPS_AND_WRAPS":      ("室内灯", "条形灯"),
    "indoor/SURFACEFLUSHMOUNTS":    ("室内灯", "吸顶灯"),
    "indoor/TRACK_LIGHTING":        ("室内灯", "轨道灯"),
}

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.rablighting.com/',
})


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

    # Phase 1: collect feature links per category (one Playwright session)
    print("Phase 1: 收集 feature 链接...", flush=True)
    feature_to_category = {}  # feature_url → (大类, 小类)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for cat_path, (da_lei, xiao_lei) in CATEGORIES.items():
            cat_url = f"https://www.rablighting.com/{cat_path}"
            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(5000)
            except Exception:
                time.sleep(3)
                continue

            for _ in range(10):
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(500)

            # Get feature links that are WITHIN the category content area (not nav)
            # Use majorGroup images as anchors - their parent <a> links to feature pages
            features = page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                document.querySelectorAll('img[src*="/images/menu/majorGroup/"]').forEach(img => {
                    const link = img.closest('a');
                    if (!link) return;
                    const href = link.href.split('?')[0].split('#')[0];
                    if (!href.includes('/feature/') || seen.has(href)) return;
                    const alt = img.alt || '';
                    if (alt.includes('ACCESSORIES') || img.src.includes('noimageavailable')) return;
                    seen.add(href);
                    results.push(href);
                });
                return results;
            }''')

            for feat_url in features:
                if feat_url not in feature_to_category:
                    feature_to_category[feat_url] = (da_lei, xiao_lei)

            print(f'  {da_lei}/{xiao_lei}: {len(features)} features', flush=True)
            time.sleep(random.uniform(2, 3))

        browser.close()

    unique_features = list(feature_to_category.keys())
    print(f"\n去重后: {len(unique_features)} 个 feature 页\n", flush=True)

    # Phase 2: visit each feature page once, get hero product photo
    print("Phase 2: 逐页抓取产品图...", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for feat_url in unique_features:
            da_lei, xiao_lei = feature_to_category[feat_url]

            try:
                page.goto(feat_url, timeout=25000, wait_until='domcontentloaded')
                page.wait_for_timeout(3000)
            except Exception:
                time.sleep(2)
                continue

            # Get FIRST product photo only (hero shot, not accessories)
            photo_url = page.evaluate('''() => {
                const imgs = document.querySelectorAll('img[src*="/images/product/photo/"]');
                return imgs.length > 0 ? imgs[0].src.split('?')[0] : '';
            }''')

            if not photo_url:
                time.sleep(random.uniform(1, 2))
                continue

            # Get product name from page title
            title = page.evaluate('() => document.title || ""')
            product_name = re.sub(r'\s*[-|].*$', '', title).strip()

            # Download largePhoto version
            large_url = photo_url.replace('/photo/', '/largePhoto/')

            dest_dir = BASE / da_lei / xiao_lei
            dest_dir.mkdir(parents=True, exist_ok=True)
            folder_key = str(dest_dir)
            if folder_key not in folder_counters:
                folder_counters[folder_key] = len([f for f in dest_dir.iterdir()
                                                    if f.suffix.lower() in ('.jpg', '.jpeg')])

            time.sleep(random.uniform(0.5, 1))

            try:
                r = s.get(large_url, timeout=15)
                if r.status_code != 200 or len(r.content) < 5000:
                    r = s.get(photo_url, timeout=15)
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
                print(f'  {product_name[:40]} -> {da_lei}/{xiao_lei} ({img.size[0]}x{img.size[1]})', flush=True)

            except Exception:
                continue

            time.sleep(random.uniform(2, 4))

        browser.close()

    print(f'\n[rab] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
