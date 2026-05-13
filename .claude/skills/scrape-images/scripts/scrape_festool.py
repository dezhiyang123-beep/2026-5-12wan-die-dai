#!/usr/bin/env python3
"""
Festool 定制爬虫 — 从子分类页取产品图(>=500px)。
分类从 URL 路径提取(如 /products/saws/jigsaws → 电锯/曲线锯)。
过滤配件小图和产品型号页。
"""
import hashlib, re, requests, time, random, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import _classify_brand_product

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "电动工具" / "festool"

# Subcategory slug → (大类, 小类)
SLUG_MAP = {
    "plunge-saws": ("电锯", "轨道锯"),
    "circular-saws": ("电锯", "圆锯"),
    "carpentry-circular-saws": ("电锯", "圆锯"),
    "cordless-portable-circular-saws": ("电锯", "圆锯"),
    "jigsaws": ("电锯", "曲线锯"),
    "cordless-pendulum-jigsaws": ("电锯", "曲线锯"),
    "sliding-compound-mitre-saws": ("电锯", "斜切锯"),
    "mitre-saws": ("电锯", "斜切锯"),
    "cordless-mitre-saw": ("电锯", "斜切锯"),
    "cordless-sliding-compound-mitre-saw": ("电锯", "斜切锯"),
    "circular-table-saws": ("电锯", "台锯"),
    "cordless-table-saw": ("电锯", "台锯"),
    "insulation-saws": ("电锯", "绝缘锯"),
    "cordless-insulating-material-saw": ("电锯", "绝缘锯"),
    "reciprocating-saws": ("电锯", "往复锯"),
    "cordless-reciprocating-saw": ("电锯", "往复锯"),
    "sword-saws": ("电锯", "剑锯"),
    "cordless-plunge-cut-saw": ("电锯", "轨道锯"),
    "random-orbital-sanders": ("砂光机", "轨道砂光机"),
    "orbital-sanders": ("砂光机", "轨道砂光机"),
    "cordless-sander": ("砂光机", None),
    "belt-sanders": ("砂光机", "砂带机"),
    "long-reach-sanders": ("砂光机", "长臂砂光机"),
    "delta-sanders": ("砂光机", "三角砂光机"),
    "pneumatic-sanders": ("砂光机", "气动砂光机"),
    "gear-drive-eccentric-sanders": ("砂光机", "偏心砂光机"),
    "gear-drive-eccentric-sander-rotex": ("砂光机", "偏心砂光机"),
    "edge-sanders": ("砂光机", "边缘砂光机"),
    "renovation-grinders": ("角磨机", "翻新磨"),
    "concrete-grinders": ("角磨机", "混凝土磨"),
    "angle-grinders": ("角磨机", None),
    "cordless-angle-grinder": ("角磨机", None),
    "routers": ("铣", "修边机"),
    "edge-routers": ("铣", "封边修边机"),
    "cordless-edge-router": ("铣", "封边修边机"),
    "module-routers": ("铣", "修边机"),
    "cordless-drills": ("电钻", "充电电钻"),
    "cordless-impact-drivers": ("电钻", "冲击起子"),
    "cordless-hammer-drills": ("电钻", "锤钻"),
    "cordless-percussion-drills": ("电钻", "锤钻"),
    "cordless-rotary-hammer-drills": ("电钻", "锤钻"),
    "cordless-drywall-screwdrivers": ("电钻", "螺丝刀"),
    "planers": ("刨", "电刨"),
    "cordless-planer": ("刨", "电刨"),
    "one-handed-planers": ("刨", "电刨"),
    "oscillators": ("多功能工具", "摆动工具"),
    "oscillating-multi-tools": ("多功能工具", "摆动工具"),
    "cordless-oscillator": ("多功能工具", "摆动工具"),
    "domino-jointers": ("木工工具", "榫接机"),
    "jointing-machines": ("木工工具", "榫接机"),
    "cordless-joining-machine": ("木工工具", "榫接机"),
    "systainer-dust-extractors": ("吸尘设备", "除尘器"),
    "construction-site-dust-extractors": ("吸尘设备", "除尘器"),
    "compact-dust-extractors": ("吸尘设备", "除尘器"),
    "mobile-dust-extractors": ("吸尘设备", "除尘器"),
    "cordless-dust-extractors": ("吸尘设备", "除尘器"),
}

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.festool.com/',
})


def save_as_jpeg(img, dest):
    if img.mode in ('RGBA', 'LA', 'PA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        background.save(dest, 'JPEG', quality=95)
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=95)


def get_category_from_url(url):
    """Extract category from URL by finding a known slug in the path."""
    parts = url.rstrip('/').split('/')
    for part in reversed(parts):
        if part in SLUG_MAP:
            return SLUG_MAP[part]
    return None


def scrape():
    seen_hashes = set()
    seen_imgs = set()
    folder_counters = {}
    total = 0

    # Direct subcategory URLs to visit (curated, not auto-discovered)
    SUBCATEGORY_URLS = [
        f"https://www.festool.com/products/saws/{slug}"
        for slug in ["plunge-saws", "circular-saws", "jigsaws", "sliding-compound-mitre-saws",
                      "circular-table-saws", "insulation-saws", "reciprocating-saws", "sword-saws", "mitre-saws"]
    ] + [
        f"https://www.festool.com/products/sanders-and-grinders/{slug}"
        for slug in ["random-orbital-sanders", "orbital-sanders", "belt-sanders", "long-reach-sanders",
                      "delta-sanders", "pneumatic-sanders", "gear-drive-eccentric-sanders",
                      "renovation-grinders", "edge-sanders"]
    ] + [
        f"https://www.festool.com/products/routing/{slug}"
        for slug in ["routers", "edge-routers"]
    ] + [
        "https://www.festool.com/products/drilling-and-screwdriving/cordless-drills",
        "https://www.festool.com/products/drilling-and-screwdriving/cordless-impact-drivers",
        "https://www.festool.com/products/drilling-and-screwdriving/cordless-hammer-drills",
        "https://www.festool.com/products/drilling-and-screwdriving/cordless-drywall-screwdrivers",
        "https://www.festool.com/products/planers",
        "https://www.festool.com/products/oscillators",
        "https://www.festool.com/products/domino-jointing-system",
        "https://www.festool.com/products/dust-extractors/systainer-dust-extractors",
        "https://www.festool.com/products/dust-extractors/construction-site-dust-extractors",
        "https://www.festool.com/products/dust-extractors/mobile-dust-extractors",
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for sub_url in SUBCATEGORY_URLS:
            cat = get_category_from_url(sub_url)
            if not cat:
                continue

            major, minor = cat
            slug = sub_url.rstrip('/').split('/')[-1]
            print(f'[{slug}]', end='', flush=True)

            try:
                page.goto(sub_url, timeout=25000, wait_until='domcontentloaded')
                page.wait_for_timeout(5000)
            except Exception:
                print(' 跳过', flush=True)
                time.sleep(3)
                continue

            for _ in range(10):
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(400)

            imgs = page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                document.querySelectorAll('img[src*="media.cdn.festool.io"]').forEach(img => {
                    const src = img.src || '';
                    // Skip small accessory thumbnails by URL pattern (400x267)
                    if (src.includes('_400_267')) return;
                    const id = src.match(/([a-f0-9-]{36})/);
                    const key = id ? id[1] : src;
                    if (seen.has(key)) return;
                    seen.add(key);
                    results.push(src);
                });
                return results;
            }''')

            dest_dir = BASE / major / minor if minor else BASE / major
            dest_dir.mkdir(parents=True, exist_ok=True)
            folder_key = str(dest_dir)
            if folder_key not in folder_counters:
                folder_counters[folder_key] = len([f for f in dest_dir.iterdir()
                                                    if f.suffix.lower() in ('.jpg', '.jpeg')])

            count = 0
            for img_src in imgs:
                if img_src in seen_imgs:
                    continue
                seen_imgs.add(img_src)

                hires = re.sub(r'_\d+_\d+\.webp', '_800_600.webp', img_src)
                try:
                    r = s.get(hires, timeout=15)
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
                    count += 1
                except Exception:
                    continue

            print(f' -> {major}/{minor} ({count})', flush=True)
            time.sleep(random.uniform(2, 4))

        browser.close()

    print(f'\n[festool] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
