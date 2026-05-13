#!/usr/bin/env python3
"""
Shopify 品牌通用爬虫 — 使用 /collections/{name}/products.json API。
适用于 Leatherman, Goal Zero 等 Shopify 站点。
"""
import hashlib, time, random, requests, re
from pathlib import Path
from PIL import Image
from io import BytesIO

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库"

s = requests.Session()
s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

BRANDS = {
    "leatherman": {
        "base_url": "https://www.leatherman.com",
        "output": BASE / "户外装备" / "leatherman",
        "collections": {
            "multi-tools": ("多功能工具", "多功能钳"),
            "knives": ("刀具", "折叠刀"),
            "accessories": ("配件", "配件"),
        },
    },
    "goalzero": {
        "base_url": "https://www.goalzero.com",
        "output": BASE / "户外装备" / "goal_zero",
        "collections": {
            "portable-power-stations": ("便携电源", "电源站"),
            "solar-panels": ("便携电源", "太阳能板"),
            "lights": ("户外灯", "露营灯"),
            "power-banks": ("便携电源", "充电宝"),
            "alta-electric-coolers-portable-refrigerators-freezers": ("户外电器", "电动冷藏箱"),
        },
    },
}


def save_as_jpeg(data, dest):
    img = Image.open(BytesIO(data))
    if max(img.size) < 200:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if img.mode in ('RGBA', 'LA', 'PA'):
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        bg.save(dest, 'JPEG', quality=95)
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=95)
    return True


def fetch_shopify_products(base_url, collection):
    """Fetch all products from a Shopify collection via JSON API."""
    products = []
    page = 1
    while True:
        url = f"{base_url}/collections/{collection}/products.json?limit=250&page={page}"
        try:
            r = s.get(url, timeout=20)
            if r.status_code != 200:
                break
            data = r.json()
            batch = data.get('products', [])
            if not batch:
                break
            products.extend(batch)
            page += 1
            time.sleep(random.uniform(1, 2))
        except Exception as e:
            print(f'    API error: {e}', flush=True)
            break
    return products


def scrape_brand(brand_name, config):
    """Scrape a single Shopify brand."""
    seen_hashes = set()
    folder_counters = {}
    total = 0

    base_url = config['base_url']
    output = config['output']
    output.mkdir(parents=True, exist_ok=True)

    for collection, (major, minor) in config['collections'].items():
        dest_dir = output / major / minor
        dest_dir.mkdir(parents=True, exist_ok=True)
        fk = str(dest_dir)
        if fk not in folder_counters:
            folder_counters[fk] = len([f for f in dest_dir.iterdir()
                                       if f.suffix.lower() in ('.jpg', '.jpeg')])

        print(f'  [{collection}]', end='', flush=True)
        products = fetch_shopify_products(base_url, collection)
        print(f' {len(products)} products', flush=True)

        saved = 0
        for product in products:
            images = product.get('images', [])
            if not images:
                continue
            # Take the first (main) image
            img_url = images[0].get('src', '')
            if not img_url:
                continue

            # Request high resolution
            img_url = re.sub(r'\?v=\d+', '', img_url)
            if '?' not in img_url:
                img_url += '?width=1200'
            else:
                img_url += '&width=1200'

            time.sleep(random.uniform(0.3, 0.8))
            try:
                r = s.get(img_url, timeout=15)
                if r.status_code != 200 or len(r.content) < 3000:
                    continue
                md5 = hashlib.md5(r.content).hexdigest()
                if md5 in seen_hashes:
                    continue
                seen_hashes.add(md5)
                folder_counters[fk] += 1
                dest = dest_dir / f"{folder_counters[fk]:02d}.jpg"
                if save_as_jpeg(r.content, dest):
                    saved += 1
                    total += 1
                else:
                    dest.unlink(missing_ok=True)
                    folder_counters[fk] -= 1
            except Exception:
                continue

        print(f'    → {saved} 张', flush=True)
        time.sleep(random.uniform(2, 4))

    return total


def main():
    import sys
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(BRANDS.keys())

    grand_total = 0
    for name in targets:
        if name not in BRANDS:
            print(f'未知品牌: {name}', flush=True)
            continue
        print(f'\n[{name}]', flush=True)
        count = scrape_brand(name, BRANDS[name])
        grand_total += count
        print(f'  → {name}: {count} 张', flush=True)

    print(f'\n[shopify] 完成: {grand_total} 张', flush=True)


if __name__ == '__main__':
    main()
