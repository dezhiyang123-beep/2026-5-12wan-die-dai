#!/usr/bin/env python3
"""
Samsung V2 爬虫 — 进产品详情页取高清白底产品图。
补全所有品类：手机/平板/手表/耳机/显示器/电视/笔记本/条形音箱。
"""
import sys, hashlib, time, random, re
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库" / "消费电子" / "samsung"

CATEGORIES = {
    "https://www.samsung.com/us/smartphones/all-smartphones/": "智能手机",
    "https://www.samsung.com/us/tablets/all-tablets/": "平板电脑",
    "https://www.samsung.com/us/watches/all-watches/": "智能手表",
    "https://www.samsung.com/us/mobile-audio/all-mobile-audio/": "耳机",
    "https://www.samsung.com/us/computing/monitors/all-monitors/": "显示器",
    "https://www.samsung.com/us/televisions-home-theater/all-tvs/": "电视",
    "https://www.samsung.com/us/computing/laptops/all-laptops/": "笔记本电脑",
    "https://www.samsung.com/us/televisions-home-theater/all-soundbars/": "条形音箱",
}

SKIP = ['logo', 'icon', 'badge', 'banner', 'sprite', 'svg', 'pixel', 'analytics',
        'facebook', 'google', 'twitter', 'pinterest']


def save_as_jpeg(data, dest):
    try:
        img = Image.open(BytesIO(data))
    except Exception:
        return False
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
                page.goto(cat_url, timeout=45000, wait_until='domcontentloaded')
                page.wait_for_timeout(6000)
                for _ in range(30):
                    page.evaluate('window.scrollBy(0, window.innerHeight)')
                    page.wait_for_timeout(500)
                # 点"load more"
                for _ in range(3):
                    try:
                        btn = page.locator('button:has-text("more"), a:has-text("more")')
                        if btn.count() > 0:
                            btn.first.click()
                            page.wait_for_timeout(3000)
                    except:
                        break

                product_links = page.evaluate('''() => {
                    const links = [];
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.href;
                        if (href.includes('samsung.com/us/') && href.includes('/buy/')
                            && !links.includes(href))
                            links.push(href);
                    });
                    // 也尝试产品卡片链接
                    document.querySelectorAll('a[href*="/smartphones/"], a[href*="/tablets/"], a[href*="/watches/"], a[href*="/monitors/"], a[href*="/laptops/"], a[href*="/tvs/"], a[href*="/soundbars/"]').forEach(a => {
                        const href = a.href;
                        if (href.includes('samsung.com') && !href.includes('/all-')
                            && !links.includes(href))
                            links.push(href);
                    });
                    return [...new Set(links)].slice(0, 50);
                }''')
                print(f'  {len(product_links)} 个产品链接', flush=True)
            except Exception as e:
                print(f'  列表页错误: {e}', flush=True)
                page.close()
                continue
            page.close()

            # Step 2: 进详情页取图
            saved = 0
            for prod_url in product_links[:30]:  # 限制每品类30个产品
                page = browser.new_page()
                captured = []

                def on_response(response):
                    url = response.url.lower()
                    if any(skip in url for skip in SKIP):
                        return
                    if (('samsung.com' in url or 'samsungcdn' in url)
                        and any(ext in url for ext in ['.png', '.jpg', '.jpeg', '.webp'])
                        and 'gallery' in url or 'product' in url
                        and response.status == 200):
                        try:
                            body = response.body()
                            if len(body) > 20000:
                                captured.append(body)
                        except:
                            pass

                page.on('response', on_response)

                try:
                    page.goto(prod_url, timeout=25000, wait_until='domcontentloaded')
                    page.wait_for_timeout(4000)
                except:
                    page.close()
                    time.sleep(1)
                    continue

                # 取第一张大图
                if captured:
                    body = captured[0]
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
                time.sleep(random.uniform(2, 4))

            print(f'  保存 {saved} 张', flush=True)
            time.sleep(random.uniform(3, 5))

        browser.close()

    print(f'\n[samsung] 完成: {total} 张', flush=True)


if __name__ == '__main__':
    scrape()
