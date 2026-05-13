#!/usr/bin/env python3
"""
Samsung 产品图爬虫。
samsung.com 用 React SPA，需要 Playwright 渲染。
图片从 image-us.samsung.com CDN 加载。
"""
import hashlib, time, random
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "消费电子" / "samsung"

CATEGORIES = {
    "https://www.samsung.com/us/smartphones/all-smartphones/": ("手机", "智能手机"),
    "https://www.samsung.com/us/tablets/all-tablets/": ("平板", "平板电脑"),
    "https://www.samsung.com/us/watches/all-watches/": ("穿戴设备", "智能手表"),
    "https://www.samsung.com/us/buds/all-earbuds/": ("耳机", "真无线耳塞"),
    "https://www.samsung.com/us/monitors/all-monitors/": ("显示器", "显示器"),
    "https://www.samsung.com/us/televisions-home-theater/all-tvs/": ("电视", "电视"),
    "https://www.samsung.com/us/soundbars/all-soundbars/": ("条形音箱", "条形音箱"),
    "https://www.samsung.com/us/laptops/all-laptops/": ("笔记本", "笔记本电脑"),
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
    folder_counters = {}
    total = 0

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

            captured = []
            page = browser.new_page()

            def handle_response(response):
                url = response.url
                if (('samsung.com' in url or 'samsungcdn' in url)
                    and any(ext in url.lower() for ext in ['.png', '.jpg', '.jpeg', '.webp'])
                    and response.status == 200
                    and 'icon' not in url.lower() and 'logo' not in url.lower()
                    and 'banner' not in url.lower() and 'badge' not in url.lower()):
                    try:
                        ct = response.headers.get('content-type', '')
                        if 'image' in ct:
                            body = response.body()
                            if len(body) > 5000:
                                captured.append((url, body))
                    except Exception:
                        pass

            page.on('response', handle_response)

            try:
                page.goto(cat_url, timeout=45000, wait_until='domcontentloaded')
                page.wait_for_timeout(6000)

                # Scroll extensively to load all products
                for _ in range(40):
                    page.evaluate('window.scrollBy(0, window.innerHeight)')
                    page.wait_for_timeout(600)

                # Try clicking "load more" if available
                for _ in range(5):
                    try:
                        btn = page.locator('button:has-text("more"), a:has-text("more")')
                        if btn.count() > 0:
                            btn.first.click()
                            page.wait_for_timeout(3000)
                    except Exception:
                        break

                page.wait_for_timeout(3000)
            except Exception as e:
                print(f'  错误: {e}', flush=True)
                page.close()
                time.sleep(3)
                continue

            print(f'  拦截 {len(captured)} 图片', flush=True)

            saved = 0
            for url, body in captured:
                md5 = hashlib.md5(body).hexdigest()
                if md5 in seen_hashes:
                    continue
                seen_hashes.add(md5)
                folder_counters[fk] = folder_counters.get(fk, 0) + 1
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

    print(f'\n[samsung] 完成: {total} 张', flush=True)


if __name__ == '__main__':
    scrape()
