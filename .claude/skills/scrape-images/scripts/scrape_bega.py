#!/usr/bin/env python3
"""
BEGA 定制爬虫 — 策略：
1. 用 Playwright 访问每个分类页（带延迟防封）
2. 提取产品卡片（282x282 大缩略图 + 产品链接），每产品只取1张 hero 图
3. 通过 Contentful CDN 下载高分辨率版本
4. 分类来自 URL 路径（outdoor/indoor + subcategory）

bega URL 结构本身就是正确的二级分类：
  outdoor-luminaires/wall-luminaires → 户外灯/壁灯
"""
import hashlib, re, requests, time, random
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "灯具" / "bega"

# URL subcategory → (大类, 小类)
CATEGORIES = {
    # ── 户外灯 ──
    "outdoor-luminaires/recessed-wall-luminaires":    ("户外灯", "嵌入式壁灯"),
    "outdoor-luminaires/wall-luminaires":             ("户外灯", "壁灯"),
    "outdoor-luminaires/recessed-ceiling-luminaires":  ("户外灯", "嵌入式吸顶灯"),
    "outdoor-luminaires/ceiling-luminaires":           ("户外灯", "吸顶灯"),
    "outdoor-luminaires/pendant-luminaires":           ("户外灯", "吊灯"),
    "outdoor-luminaires/in-ground-luminaires":         ("户外灯", "地埋灯"),
    "outdoor-luminaires/underwater-luminaires":        ("户外灯", "水下灯"),
    "outdoor-luminaires/floodlights":                  ("户外灯", "泛光灯"),
    "outdoor-luminaires/garden-luminaires":             ("户外灯", "庭院灯"),
    "outdoor-luminaires/light-design-elements":        ("户外灯", "光设计元素"),
    "outdoor-luminaires/bollards":                      ("户外灯", "路桩灯"),
    "outdoor-luminaires/light-building-elements":      ("户外灯", "建筑照明元素"),
    "outdoor-luminaires/pole-top-luminaires":           ("户外灯", "柱顶灯"),
    # ── 室内灯 ──
    "indoor-luminaires/recessed-wall-luminaires":      ("室内灯", "嵌入式壁灯"),
    "indoor-luminaires/wall-luminaires":               ("室内灯", "壁灯"),
    "indoor-luminaires/recessed-ceiling-luminaires":    ("室内灯", "嵌入式吸顶灯"),
    "indoor-luminaires/ceiling-luminaires":             ("室内灯", "吸顶灯"),
    "indoor-luminaires/track-spotlights":               ("室内灯", "轨道射灯"),
    "indoor-luminaires/pendant-luminaires":             ("室内灯", "吊灯"),
    "indoor-luminaires/table-and-floor-luminaires":     ("室内灯", "台灯·落地灯"),
}

s = requests.Session()
s.headers['User-Agent'] = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/125.0.0.0 Safari/537.36')


def upgrade_to_hires(url, width=1200):
    """Extract raw Contentful URL and request high-res version."""
    m = re.search(r'(https://images\.ctfassets\.net/[^?\s&]+)', url)
    if m:
        raw = m.group(1)
        if raw.endswith('.svg'):
            return None
        return f"{raw}?fit=fill&w={width}&q=90"
    return None


def scrape():
    seen_hashes = set()
    seen_slugs = set()  # 1 image per product series
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = ctx.new_page()

        for url_path, (da_lei, xiao_lei) in CATEGORIES.items():
            cat_url = f"https://www.bega.com/en/products/{url_path}/"
            dest_dir = BASE / da_lei / xiao_lei
            dest_dir.mkdir(parents=True, exist_ok=True)
            counter = len([f for f in dest_dir.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg')])

            print(f'[{da_lei}/{xiao_lei}]', end='', flush=True)

            try:
                page.goto(cat_url, timeout=40000, wait_until='domcontentloaded')
                page.wait_for_timeout(3000)
            except Exception:
                time.sleep(5)
                try:
                    page.goto(cat_url, timeout=40000, wait_until='domcontentloaded')
                    page.wait_for_timeout(3000)
                except Exception:
                    print(' 跳过', flush=True)
                    continue

            # Scroll to load all product cards
            for _ in range(5):
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(800)

            # Extract product cards: each has a link (with slug) + hero image (282x282)
            products = page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                document.querySelectorAll('a[href*="/products/"]').forEach(a => {
                    const href = a.href.split('?')[0].replace(/\\/+$/, '');
                    const parts = href.split('/');
                    if (parts.length < 8) return;
                    const slug = parts[parts.length - 1];
                    if (seen.has(slug)) return;
                    seen.add(slug);
                    // Get the hero image (>200px wide)
                    const img = a.querySelector('img');
                    if (!img) return;
                    const src = img.src || '';
                    const w = img.naturalWidth || 0;
                    if (w < 200 || !src.includes('ctfassets')) return;
                    results.push({slug: slug, imgSrc: src});
                });
                return results;
            }''')

            # Filter to only products in THIS subcategory (not nav links to other categories)
            cat_segment = url_path.split('/')[1]  # e.g. 'wall-luminaires'
            products = [p for p in products if cat_segment in p['slug'] or
                       p['slug'].startswith(cat_segment.split('-')[0])]

            print(f' {len(products)} products', flush=True)

            cat_count = 0
            for prod in products:
                slug = prod['slug']
                if slug in seen_slugs:
                    continue
                seen_slugs.add(slug)

                hires_url = upgrade_to_hires(prod['imgSrc'])
                if not hires_url:
                    continue

                try:
                    r = s.get(hires_url, timeout=15)
                    if r.status_code != 200 or len(r.content) < 3000:
                        continue

                    md5 = hashlib.md5(r.content).hexdigest()
                    if md5 in seen_hashes:
                        continue

                    img = Image.open(BytesIO(r.content))
                    if max(img.size) < 300:
                        continue

                    seen_hashes.add(md5)
                    counter += 1
                    dest = dest_dir / f"{counter:02d}.jpg"
                    img.convert('RGB').save(dest, 'JPEG', quality=95)
                    total += 1
                    cat_count += 1

                except Exception:
                    continue

            print(f'  → +{cat_count} ({counter} total)', flush=True)
            time.sleep(random.uniform(2, 4))

        browser.close()

    print(f'\n[bega] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
