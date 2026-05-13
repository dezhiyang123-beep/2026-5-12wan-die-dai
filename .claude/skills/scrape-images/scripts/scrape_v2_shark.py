#!/usr/bin/env python3
"""
Shark V2 — 列表页取产品链接 → 详情页取Cloudinary高清图 → requests下载。
"""
import sys, hashlib, time, random, re, shutil, requests
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "小家电" / "shark"

CATEGORIES = {
    "https://www.sharkclean.com/vacuum-cleaners/": "立式吸尘器",
    "https://www.sharkclean.com/cordless-vacuums/": "手持吸尘器",
    "https://www.sharkclean.com/robot-vacuums/": "扫地机器人",
    "https://www.sharkclean.com/steam-mops/": "蒸汽拖把",
    "https://www.sharkclean.com/air-purifiers/": "空气净化器",
}

session = requests.Session()
session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


def save_as_jpeg(data, dest):
    img = Image.open(BytesIO(data))
    w, h = img.size
    if max(w, h) < 400:
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

            print(f'\n[{cat_name}]', flush=True)

            # Step 1: 列表页取产品链接
            page = browser.new_page()
            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(8000)
                for _ in range(20):
                    page.evaluate('window.scrollBy(0, window.innerHeight)')
                    page.wait_for_timeout(500)

                product_links = page.evaluate('''() => {
                    const links = [];
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.href;
                        if (href.includes('sharkninja.com/shark-') && href.endsWith('.html')
                            && !href.includes('ninja-') && !links.includes(href))
                            links.push(href);
                    });
                    return [...new Set(links)];
                }''')
                print(f'  {len(product_links)} 个产品链接', flush=True)
            except Exception as e:
                print(f'  错误: {e}', flush=True)
                product_links = []
            finally:
                page.close()

            # Step 2: 进每个详情页取Cloudinary图片URL
            saved = 0
            for prod_url in product_links:
                page = browser.new_page()
                try:
                    page.goto(prod_url, timeout=25000, wait_until='domcontentloaded')
                    page.wait_for_timeout(5000)

                    # 从DOM取Cloudinary产品图
                    img_urls = page.evaluate('''() => {
                        const urls = [];
                        document.querySelectorAll('img').forEach(img => {
                            const src = img.currentSrc || img.src || '';
                            if (src.includes('cloudinary.com') && src.includes('image/upload')
                                && !src.includes('spinner') && !src.includes('logo')
                                && img.naturalWidth >= 300)
                                urls.push(src);
                        });
                        return urls.slice(0, 1);
                    }''')

                    for img_url in img_urls:
                        # 改Cloudinary参数拿高清
                        hires = re.sub(r'h_\d+', 'h_1200', img_url)
                        hires = re.sub(r'w_\d+', 'w_1200', hires)

                        time.sleep(random.uniform(0.3, 0.6))
                        try:
                            r = session.get(hires, timeout=15)
                            if r.status_code != 200 or len(r.content) < 10000:
                                continue
                            md5 = hashlib.md5(r.content).hexdigest()
                            if md5 in seen_hashes:
                                continue
                            seen_hashes.add(md5)
                            counter += 1
                            dest = dest_dir / f"{counter:02d}.jpg"
                            if save_as_jpeg(r.content, dest):
                                saved += 1
                                total += 1
                            else:
                                dest.unlink(missing_ok=True)
                                counter -= 1
                        except:
                            pass
                except:
                    pass
                finally:
                    page.close()
                    time.sleep(random.uniform(1, 2))

            print(f'  保存 {saved} 张', flush=True)
            time.sleep(random.uniform(3, 5))

        browser.close()

    print(f'\n[shark] 完成: {total} 张', flush=True)


if __name__ == '__main__':
    scrape()
