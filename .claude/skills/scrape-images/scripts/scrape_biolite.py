#!/usr/bin/env python3
"""
BioLite 定制爬虫 — 通过 Shopify JSON API 获取产品数据。
用产品名 + collection 上下文做 _classify_all_lighting 分类。
每产品最多2张图。
"""
import hashlib, re, requests, time, sys
from pathlib import Path
from PIL import Image
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import _classify_all_lighting

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "灯具" / "biolite"

# Collection → context keyword (appended to product name for classification)
COLLECTIONS = {
    "headlamps":                    "headlamp",
    "rechargeable-lanterns":        "portable lantern",
    "rechargeable-solar-lanterns":  "solar lantern",
    "area-string-lights":           "outdoor string light",
    "solarhome-solar-lighting-kits":"solar lighting kit",
}

SKIP_PRODUCT = re.compile(
    r'(carry-bag|toolkit|firemat|firepoker|grill|fast.?charger|cable'
    r'|crew.?kit|safety.?kit|series.?kit|4.?pack|multipack|variety.?pack'
    r'|essentials.?kit|cook.?kit|complete.?cook|ecozoom|campstove'
    r'|firepit|goal.?zero|power.?station|charge.?\d|solar.?panel'
    r'|charger|go.?bag)',
    re.I
)

MAX_IMGS_PER_PRODUCT = 2

s = requests.Session()
s.headers['User-Agent'] = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/125.0.0.0 Safari/537.36')


def scrape():
    seen_hashes = set()
    seen_products = set()  # dedup across collections
    folder_counters = {}
    total = 0

    for collection, context_kw in COLLECTIONS.items():
        print(f'[{collection}]', flush=True)

        # Fetch products via Shopify JSON API
        all_products = []
        page_num = 1
        while True:
            url = f"https://www.bioliteenergy.com/collections/{collection}/products.json?limit=250&page={page_num}"
            try:
                r = s.get(url, timeout=15)
                if r.status_code != 200:
                    break
                products = r.json().get('products', [])
                if not products:
                    break
                all_products.extend(products)
                page_num += 1
                time.sleep(0.5)
            except Exception:
                break

        # Filter accessories
        products = [p for p in all_products
                    if not SKIP_PRODUCT.search(p.get('title', ''))
                    and p.get('id') not in seen_products]

        print(f'  {len(products)} products', flush=True)

        for product in products:
            pid = product.get('id')
            if pid in seen_products:
                continue
            seen_products.add(pid)

            title = product.get('title', '')
            # Classify using product name + collection context
            classify_name = f"{title} {context_kw}"
            sub_cat = _classify_all_lighting(classify_name)

            dest_dir = BASE / sub_cat
            dest_dir.mkdir(parents=True, exist_ok=True)
            folder_key = str(dest_dir)
            if folder_key not in folder_counters:
                folder_counters[folder_key] = len([f for f in dest_dir.iterdir()
                                                    if f.suffix.lower() in ('.jpg', '.jpeg')])

            images = product.get('images', [])[:MAX_IMGS_PER_PRODUCT]

            for img_info in images:
                img_url = img_info.get('src', '')
                if not img_url:
                    continue

                # High-res Shopify URL
                img_url = re.sub(r'\?.*$', '', img_url) + '?width=1200&height=1200'

                try:
                    r = s.get(img_url, timeout=15)
                    if r.status_code != 200 or len(r.content) < 3000:
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

                except Exception:
                    continue

            print(f'  {title} -> {sub_cat}', flush=True)

    print(f'\n[biolite] 完成: {total} 张产品图', flush=True)


if __name__ == '__main__':
    scrape()
