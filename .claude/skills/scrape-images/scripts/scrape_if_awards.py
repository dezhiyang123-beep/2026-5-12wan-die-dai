#!/usr/bin/env python3
"""
IF Design Award 通用爬虫 — 按品类 ID 抓取获奖产品。
每产品最多2张图，按品类存储到对应的 if_award 文件夹。
"""
import hashlib, re, requests, time, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import download_image, is_valid_image, convert_webp_to_jpg

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库"

IF_API_BASE = "https://ifdesign.com/api/search/entry"
IF_AWARD_IDS = [2]  # iF DESIGN AWARD

# Category ID → (品类文件夹, IF品类名)
CATEGORIES = {
    "233": ("电动工具", "工具·工业设备"),
    "542": ("小家电", "家用电器"),
    "772": ("小家电", "厨房电器"),
    "56":  ("音箱", "音频设备"),
    "93":  ("消费电子", "电脑·平板"),
    "82":  ("消费电子", "通讯设备"),
}

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
})


def save_as_jpeg(img, dest):
    if img.mode in ('RGBA', 'LA', 'PA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        background.save(dest, 'JPEG', quality=95)
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=95)


def scrape():
    total = 0

    for cat_id, (base_cat, cat_name) in CATEGORIES.items():
        dest_dir = BASE / base_cat / "if_award" / cat_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        counter = len([f for f in dest_dir.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg')])

        print(f'[IF {cat_id}: {cat_name}]', flush=True)

        api_headers = {
            "Content-Type": "application/json",
            "Origin": "https://ifdesign.com",
            "Referer": "https://ifdesign.com/en/winner-ranking/winner-overview/",
        }

        # Fetch winners from API
        all_items = []
        for award_id in IF_AWARD_IDS:
            offset = 0
            batch = 100
            while True:
                payload = {
                    "award": award_id, "countries": [], "range": 5, "seed": "",
                    "count": batch, "find": "", "disciplines": [],
                    "categories": [int(cat_id)],
                    "isGoldAward": False, "isBestOfYear": False,
                    "isSupportedByIF": False, "profileId": 0,
                }
                try:
                    resp = s.post(
                        f"{IF_API_BASE}/{offset}/{batch}?order=random&language=en",
                        headers=api_headers, json=payload, timeout=30
                    )
                    data = resp.json()
                except Exception as e:
                    print(f'  API error: {e}', flush=True)
                    break
                items = data.get("items", [])
                total_count = data.get("count", 0)
                all_items.extend(items)
                offset += len(items)
                if offset >= total_count or not items:
                    break
                time.sleep(0.5)

        print(f'  {len(all_items)} winners', flush=True)

        seen_imgs = set()
        cat_count = 0
        for item in all_items[:200]:  # Limit to 200 per category
            name = item.get("name", "")
            if not name:
                continue

            # Get images
            imgs = []
            for key in ("primaryMedia", "secondaryMedia"):
                url = item.get(key)
                if url and url not in seen_imgs and "ifdalivestorage" in url:
                    seen_imgs.add(url)
                    imgs.append(url)

            imgs = imgs[:2]  # Max 2 per product

            for img_url in imgs:
                time.sleep(0.3)
                try:
                    r = s.get(img_url, timeout=15)
                    if r.status_code != 200 or len(r.content) < 3000:
                        continue

                    md5 = hashlib.md5(r.content).hexdigest()
                    img = Image.open(BytesIO(r.content))
                    if max(img.size) < 300:
                        continue

                    counter += 1
                    dest = dest_dir / f"{counter:02d}.jpg"
                    save_as_jpeg(img, dest)
                    total += 1
                    cat_count += 1

                except Exception:
                    continue

        print(f'  → {cat_count} images saved', flush=True)
        time.sleep(1)

    print(f'\n[if_awards] 完成: {total} 张', flush=True)


if __name__ == '__main__':
    scrape()
