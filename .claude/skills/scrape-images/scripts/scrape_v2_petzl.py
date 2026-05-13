#!/usr/bin/env python3
"""
Petzl V2 爬虫 — 进产品详情页取高清产品图。
V1问题：1/3是181px缩略图。V2进详情页取大图。
"""
import sys, hashlib, time, random
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "户外装备" / "petzl"

CATEGORIES = {
    "https://www.petzl.com/US/en/Sport/Headlamps": "头灯",
    "https://www.petzl.com/US/en/Professional/Headlamps": "专业头灯",
    "https://www.petzl.com/US/en/Sport/Harnesses": "安全带",
    "https://www.petzl.com/US/en/Sport/Helmets": "头盔",
    "https://www.petzl.com/US/en/Sport/Carabiners-And-Quickdraws": "锁扣",
    "https://www.petzl.com/US/en/Sport/Ice-Axes": "冰镐",
    "https://www.petzl.com/US/en/Sport/Crampons": "冰爪",
}

SKIP = ['logo', 'icon', 'sprite', 'svg', 'analytics', 'facebook', 'pixel']


def save_as_jpeg(data, dest):
    img = Image.open(BytesIO(data))
    w, h = img.size
    if max(w, h) < 300:
        return False
    if max(w, h) / max(min(w, h), 1) > 2.5:
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
    import shutil
    if BASE.exists():
        shutil.rmtree(str(BASE))
    BASE.mkdir(parents=True)

    seen_hashes = set()
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for cat_url, cat_name in CATEGORIES.items():
            dest_dir = BASE / cat_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            counter = 0

            print(f'\n[{cat_name}] {cat_url}', flush=True)

            # Step 1: 列表页获取产品链接
            page = browser.new_page()
            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(5000)
                for _ in range(15):
                    page.evaluate('window.scrollBy(0, window.innerHeight)')
                    page.wait_for_timeout(400)

                product_links = page.evaluate('''() => {
                    const links = [];
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.href;
                        if (href.includes('petzl.com') && href.includes('/US/en/')
                            && (href.includes('/Sport/') || href.includes('/Professional/'))
                            && !href.includes('/How-to-choose')
                            && href.split('/').length > 7
                            && !links.includes(href))
                            links.push(href);
                    });
                    return [...new Set(links)];
                }''')
                print(f'  {len(product_links)} 个产品页', flush=True)
            except Exception as e:
                print(f'  错误: {e}', flush=True)
                page.close()
                continue
            page.close()

            # Step 2: 进详情页取图
            saved = 0
            for prod_url in product_links:
                page = browser.new_page()
                captured = []

                def on_response(response):
                    url = response.url.lower()
                    if any(skip in url for skip in SKIP):
                        return
                    if (('petzl' in url)
                        and any(ext in url for ext in ['.png', '.jpg', '.jpeg', '.webp'])
                        and response.status == 200):
                        try:
                            body = response.body()
                            if len(body) > 10000:
                                captured.append(body)
                        except:
                            pass

                page.on('response', on_response)

                try:
                    page.goto(prod_url, timeout=20000, wait_until='domcontentloaded')
                    page.wait_for_timeout(4000)
                except:
                    page.close()
                    time.sleep(1)
                    continue

                # 取前2张大图
                for body in captured[:2]:
                    md5 = hashlib.md5(body).hexdigest()
                    if md5 not in seen_hashes:
                        seen_hashes.add(md5)
                        counter += 1
                        dest = dest_dir / f"{counter:02d}.jpg"
                        if save_as_jpeg(body, dest):
                            saved += 1
                            total += 1
                        else:
                            dest.unlink(missing_ok=True)
                            counter -= 1

                page.close()
                time.sleep(random.uniform(1.5, 3))

            print(f'  保存 {saved} 张', flush=True)
            time.sleep(random.uniform(3, 5))

        browser.close()

    print(f'\n[petzl] 完成: {total} 张', flush=True)


if __name__ == '__main__':
    scrape()
