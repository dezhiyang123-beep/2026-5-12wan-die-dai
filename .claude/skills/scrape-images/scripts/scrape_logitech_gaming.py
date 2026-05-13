#!/usr/bin/env python3
"""
Logitech Gaming (logitechg.com) 专用爬虫。
CDN 拒绝 requests，使用 Playwright 响应拦截捕获产品图。
"""
import hashlib, time, random, sys
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "消费电子" / "logitech"

CATEGORIES = {
    "https://www.logitechg.com/en-us/products/gaming-mice.html": ("鼠标", "游戏鼠标"),
    "https://www.logitechg.com/en-us/products/gaming-keyboards.html": ("键盘", "游戏键盘"),
    "https://www.logitechg.com/en-us/products/gaming-audio.html": ("耳机", "游戏耳机"),
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


def scrape():
    seen_hashes = set()
    total = 0

    # Count existing files per folder
    folder_counters = {}
    for d in BASE.rglob('*'):
        if d.is_dir():
            folder_counters[str(d)] = len([f for f in d.iterdir()
                                           if f.suffix.lower() in ('.jpg', '.jpeg')])

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for cat_url, (major, minor) in CATEGORIES.items():
            dest_dir = BASE / major / minor
            dest_dir.mkdir(parents=True, exist_ok=True)
            fk = str(dest_dir)
            if fk not in folder_counters:
                folder_counters[fk] = len([f for f in dest_dir.iterdir()
                                           if f.suffix.lower() in ('.jpg', '.jpeg')])

            print(f'\n[{minor}] {cat_url}', flush=True)

            # Collect CDN images via response interception
            captured = []

            page = browser.new_page()

            def handle_response(response):
                url = response.url
                # Logitech Gaming CDN pattern: resource.logitechg.com or content/dam/gaming
                if (('resource.logitechg.com' in url or 'content/dam/gaming' in url
                     or 'content/dam/logitech' in url or 'content/dam/astro' in url)
                    and any(ext in url.lower() for ext in ['.png', '.jpg', '.jpeg', '.webp'])
                    and 'gallery' in url.lower()
                    and response.status == 200):
                    try:
                        body = response.body()
                        if len(body) > 5000:
                            captured.append((url, body))
                    except Exception:
                        pass

            page.on('response', handle_response)

            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(5000)

                # Scroll to trigger lazy loading
                for _ in range(30):
                    page.evaluate('window.scrollBy(0, window.innerHeight)')
                    page.wait_for_timeout(500)

                # Wait for more images to load
                page.wait_for_timeout(3000)

            except Exception as e:
                print(f'  错误: {e}', flush=True)
                page.close()
                time.sleep(3)
                continue

            print(f'  捕获 {len(captured)} 个CDN响应', flush=True)

            saved = 0
            for url, body in captured:
                md5 = hashlib.md5(body).hexdigest()
                if md5 in seen_hashes:
                    continue
                seen_hashes.add(md5)

                folder_counters[fk] += 1
                dest = dest_dir / f"{folder_counters[fk]:02d}.jpg"
                if save_as_jpeg(body, dest):
                    saved += 1
                    total += 1
                else:
                    dest.unlink(missing_ok=True)
                    folder_counters[fk] -= 1

            print(f'  保存 {saved} 张', flush=True)
            page.close()
            time.sleep(random.uniform(3, 5))

        browser.close()

    print(f'\n[logitechg] 完成: {total} 张游戏产品图', flush=True)


if __name__ == '__main__':
    scrape()
