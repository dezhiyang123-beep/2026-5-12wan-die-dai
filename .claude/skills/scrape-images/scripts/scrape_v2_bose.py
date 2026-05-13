#!/usr/bin/env python3
"""
Bose V2 — 列表页取bosecreative CDN URL → requests下载高清图。
"""
import sys, hashlib, time, random, re, shutil, requests
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "音箱" / "bose"

CATEGORIES = {
    "https://www.bose.com/c/speakers": "便携音箱",
    "https://www.bose.com/c/headphones": "头戴耳机",
    "https://www.bose.com/c/earbuds": "真无线耳机",
    "https://www.bose.com/c/soundbars": "条形音箱",
    "https://www.bose.com/c/portable-home-speakers": "家用音箱",
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
    seen_urls = set()
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for cat_url, cat_name in CATEGORIES.items():
            dest_dir = BASE / cat_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            counter = 0

            print(f'\n[{cat_name}]', flush=True)

            page = browser.new_page()
            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(6000)
                for _ in range(20):
                    page.evaluate('window.scrollBy(0, window.innerHeight)')
                    page.wait_for_timeout(400)

                # 取所有bosecreative产品图URL（过滤Nav-Flyout导航图）
                img_urls = page.evaluate('''() => {
                    const urls = [];
                    document.querySelectorAll('img').forEach(img => {
                        const src = img.currentSrc || img.src || '';
                        if (src.includes('bosecreative.com') && img.naturalWidth >= 300
                            && !src.includes('Nav-Flyout') && !src.includes('Nav_Flyout')
                            && !src.includes('logo') && !src.includes('icon')
                            && !src.includes('BrandAnthem'))
                            urls.push(src);
                    });
                    return [...new Set(urls)];
                }''')
                print(f'  {len(img_urls)} 个产品图URL', flush=True)
            except Exception as e:
                print(f'  错误: {e}', flush=True)
                img_urls = []
            finally:
                page.close()

            # requests下载
            saved = 0
            for img_url in img_urls:
                # 去URL参数后的base作为去重key
                base_url = img_url.split('?')[0]
                if base_url in seen_urls:
                    continue
                seen_urls.add(base_url)

                # 改参数拿1200px
                if '?' in img_url:
                    hires = re.sub(r'width:\d+', 'width:1200', img_url)
                    hires = re.sub(r'height:\d+', 'height:1200', hires)
                else:
                    hires = img_url + '?io=width:1200,height:1200,transform:fill'

                time.sleep(random.uniform(0.3, 0.8))
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

            print(f'  保存 {saved} 张', flush=True)
            time.sleep(random.uniform(3, 5))

        browser.close()

    print(f'\n[bose] 完成: {total} 张', flush=True)


if __name__ == '__main__':
    scrape()
