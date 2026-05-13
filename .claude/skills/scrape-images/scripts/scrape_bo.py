#!/usr/bin/env python3
"""
Bang & Olufsen 产品图爬虫。
使用 Playwright 响应拦截从 CDN 捕获产品图。
"""
import hashlib, time, random
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "消费电子" / "bang_olufsen"

CATEGORIES = {
    "https://www.bang-olufsen.com/en/us/speakers": ("音箱", "家用音箱"),
    "https://www.bang-olufsen.com/en/us/portable-speakers": ("音箱", "便携音箱"),
    "https://www.bang-olufsen.com/en/us/headphones": ("耳机", "头戴耳机"),
    "https://www.bang-olufsen.com/en/us/earphones": ("耳机", "真无线耳塞"),
    "https://www.bang-olufsen.com/en/us/soundbars": ("条形音箱", "条形音箱"),
    "https://www.bang-olufsen.com/en/us/televisions": ("电视", "电视"),
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
                if (('bang-olufsen' in url or 'cloudinary' in url or 'imgix' in url
                     or 'contentful' in url)
                    and any(ext in url.lower() for ext in ['.png', '.jpg', '.jpeg', '.webp'])
                    and response.status == 200
                    and 'icon' not in url.lower() and 'logo' not in url.lower()):
                    try:
                        body = response.body()
                        if len(body) > 5000:
                            captured.append((url, body))
                    except Exception:
                        pass

            page.on('response', handle_response)

            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(6000)

                for _ in range(20):
                    page.evaluate('window.scrollBy(0, window.innerHeight)')
                    page.wait_for_timeout(500)

                page.wait_for_timeout(3000)
            except Exception as e:
                print(f'  错误: {e}', flush=True)
                page.close()
                time.sleep(3)
                continue

            # Also try DOM extraction
            dom_imgs = page.evaluate('''() => {
                const results = [];
                document.querySelectorAll('img').forEach(img => {
                    const src = img.currentSrc || img.src || '';
                    if (img.naturalWidth >= 200 && src.length > 10
                        && !src.includes('svg') && !src.includes('logo')
                        && !src.includes('icon') && !src.includes('data:'))
                        results.push(src);
                });
                return [...new Set(results)];
            }''')

            print(f'  拦截 {len(captured)} + DOM {len(dom_imgs)}', flush=True)

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

            # DOM images via fetch
            for img_url in dom_imgs:
                try:
                    body = page.evaluate('''async (url) => {
                        const r = await fetch(url);
                        const buf = await r.arrayBuffer();
                        return Array.from(new Uint8Array(buf));
                    }''', img_url)
                    body = bytes(body)
                    if len(body) < 5000:
                        continue
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
                except Exception:
                    continue

            print(f'  保存 {saved} 张', flush=True)
            page.close()
            time.sleep(random.uniform(3, 5))

        browser.close()

    print(f'\n[B&O] 完成: {total} 张', flush=True)


if __name__ == '__main__':
    scrape()
