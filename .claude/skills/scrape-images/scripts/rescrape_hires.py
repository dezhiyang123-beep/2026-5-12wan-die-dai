#!/usr/bin/env python3
"""
重爬低分辨率品牌的高清图。
策略：清除<500px的缩略图，用Playwright重新抓取高清版本。

Logitech: 产品详情页有1900px大图，列表页只有416px缩略图
Bose: bosecreative CDN支持尺寸参数
Petzl: 清除<5KB垃圾文件，保留DOM抓的大图
Shark: 产品详情页有更大的图
"""
import sys, hashlib, time, random, re
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库"


def save_as_jpeg(data, dest):
    img = Image.open(BytesIO(data))
    if max(img.size) < 500:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if img.mode in ('RGBA', 'LA', 'PA'):
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        bg.save(dest, 'JPEG', quality=95)
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=95)
    return True


def remove_small_images(brand_path, min_px=500, min_bytes=5000):
    """删除小于阈值的图片，返回删除数量。"""
    removed = 0
    for f in list(brand_path.rglob('*.jpg')) + list(brand_path.rglob('*.jpeg')):
        try:
            if f.stat().st_size < min_bytes:
                f.unlink()
                removed += 1
                continue
            img = Image.open(f)
            if max(img.size) < min_px:
                f.unlink()
                removed += 1
        except Exception:
            pass
    return removed


def get_folder_counter(dest_dir):
    dest_dir.mkdir(parents=True, exist_ok=True)
    return len([f for f in dest_dir.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg')])


# ── Logitech: 进入每个产品详情页抓1900px大图 ──────────────────────

def rescrape_logitech():
    brand_path = BASE / "消费电子" / "logitech"
    removed = remove_small_images(brand_path)
    print(f"[logitech] 删除 {removed} 张小图")

    # 收集现有hash防重复
    seen_hashes = set()
    for f in brand_path.rglob('*.jpg'):
        try:
            seen_hashes.add(hashlib.md5(f.read_bytes()).hexdigest())
        except:
            pass

    PAGES = {
        "https://www.logitech.com/en-us/products/mice.html": ("鼠标", "办公鼠标"),
        "https://www.logitech.com/en-us/products/keyboards.html": ("键盘", "办公键盘"),
        "https://www.logitech.com/en-us/products/combos.html": ("键鼠套装", None),
        "https://www.logitech.com/en-us/products/webcams.html": ("摄像头", "网络摄像头"),
        "https://www.logitech.com/en-us/products/headsets.html": ("耳机", "办公耳机"),
        "https://www.logitech.com/en-us/products/speakers.html": ("音箱", "桌面音箱"),
    }

    folder_counters = {}
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for cat_url, (major, minor) in PAGES.items():
            dest_dir = brand_path / major / minor if minor else brand_path / major
            dest_dir.mkdir(parents=True, exist_ok=True)
            fk = str(dest_dir)
            if fk not in folder_counters:
                folder_counters[fk] = get_folder_counter(dest_dir)

            cat_name = minor or major
            print(f"  [{cat_name}] 抓产品链接...", flush=True)

            page = browser.new_page()
            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(5000)
                # Scroll to load all
                for _ in range(20):
                    page.evaluate('window.scrollBy(0, window.innerHeight)')
                    page.wait_for_timeout(400)

                # Extract product detail page URLs
                product_urls = page.evaluate('''() => {
                    const urls = [];
                    document.querySelectorAll('a[href*="/products/"]').forEach(a => {
                        const href = a.href;
                        // Product detail pages have pattern like /products/xxx/yyy.html
                        if (href.match(/\/products\/[^/]+\/[^/]+\.html/) && !urls.includes(href))
                            urls.push(href);
                    });
                    return [...new Set(urls)].slice(0, 40);
                }''')
                print(f"    {len(product_urls)} 个产品页", flush=True)
            except Exception as e:
                print(f"    错误: {e}", flush=True)
                page.close()
                continue

            page.close()

            # Visit each product page and grab the gallery images
            saved = 0
            for prod_url in product_urls:
                page = browser.new_page()
                captured = []

                def handle_resp(response):
                    url = response.url
                    if (('logitech.com' in url)
                        and any(ext in url.lower() for ext in ['.png', '.jpg', '.jpeg'])
                        and 'gallery' in url.lower()
                        and response.status == 200):
                        try:
                            body = response.body()
                            if len(body) > 10000:
                                captured.append((url, body))
                        except:
                            pass

                page.on('response', handle_resp)

                try:
                    page.goto(prod_url, timeout=20000, wait_until='domcontentloaded')
                    page.wait_for_timeout(3000)
                except:
                    page.close()
                    time.sleep(1)
                    continue

                # Take only first (main) gallery image per product
                if captured:
                    url, body = captured[0]
                    md5 = hashlib.md5(body).hexdigest()
                    if md5 not in seen_hashes:
                        seen_hashes.add(md5)
                        folder_counters[fk] = folder_counters.get(fk, 0) + 1
                        dest = dest_dir / f"{folder_counters[fk]:02d}.jpg"
                        if save_as_jpeg(body, dest):
                            saved += 1
                            total += 1
                        else:
                            dest.unlink(missing_ok=True)
                            folder_counters[fk] -= 1

                page.close()
                time.sleep(random.uniform(1.5, 3))

            print(f"    保存 {saved} 张高清图", flush=True)
            time.sleep(random.uniform(2, 4))

        browser.close()

    print(f"[logitech] 完成: +{total} 张高清图\n")


# ── Bose: 用响应拦截重抓 ──────────────────────────────────────────

def rescrape_bose():
    brand_path = BASE / "音箱" / "bose"
    removed = remove_small_images(brand_path)
    print(f"[bose] 删除 {removed} 张小图")

    seen_hashes = set()
    for f in brand_path.rglob('*.jpg'):
        try:
            seen_hashes.add(hashlib.md5(f.read_bytes()).hexdigest())
        except:
            pass

    PAGES = {
        "https://www.bose.com/c/speakers": ("音箱", "便携音箱"),
        "https://www.bose.com/c/headphones": ("音箱", "头戴耳机"),
        "https://www.bose.com/c/earbuds": ("音箱", "真无线耳机"),
        "https://www.bose.com/c/soundbars": ("音箱", "条形音箱"),
    }

    folder_counters = {}
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for cat_url, (_, minor) in PAGES.items():
            dest_dir = brand_path / minor
            dest_dir.mkdir(parents=True, exist_ok=True)
            fk = str(dest_dir)
            if fk not in folder_counters:
                folder_counters[fk] = get_folder_counter(dest_dir)

            print(f"  [{minor}]", flush=True)

            captured = []
            page = browser.new_page()

            def handle_resp(response):
                url = response.url
                if (('bose.com' in url or 'bosecreative' in url or 'cloudinary' in url)
                    and any(ext in url.lower() for ext in ['.png', '.jpg', '.jpeg', '.webp'])
                    and response.status == 200
                    and 'icon' not in url.lower() and 'logo' not in url.lower()):
                    try:
                        body = response.body()
                        if len(body) > 10000:
                            captured.append((url, body))
                    except:
                        pass

            page.on('response', handle_resp)

            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(6000)
                for _ in range(25):
                    page.evaluate('window.scrollBy(0, window.innerHeight)')
                    page.wait_for_timeout(500)
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"    错误: {e}", flush=True)
                page.close()
                time.sleep(3)
                continue

            # Also try DOM fetch for larger images
            dom_imgs = page.evaluate('''() => {
                const results = [];
                document.querySelectorAll('img').forEach(img => {
                    let src = img.currentSrc || img.src || '';
                    // Try to get higher resolution by modifying URL
                    if (src.includes('w_') || src.includes('h_')) {
                        src = src.replace(/w_\d+/g, 'w_1200').replace(/h_\d+/g, 'h_1200');
                    }
                    if (img.naturalWidth >= 100 && src.length > 10
                        && !src.includes('svg') && !src.includes('logo')
                        && !src.includes('icon') && !src.includes('data:'))
                        results.push(src);
                });
                return [...new Set(results)];
            }''')

            print(f"    拦截 {len(captured)} + DOM {len(dom_imgs)}", flush=True)

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

            for img_url in dom_imgs:
                try:
                    body = page.evaluate('''async (url) => {
                        const r = await fetch(url);
                        const buf = await r.arrayBuffer();
                        return Array.from(new Uint8Array(buf));
                    }''', img_url)
                    body = bytes(body)
                    if len(body) < 10000:
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
                except:
                    continue

            print(f"    保存 {saved} 张", flush=True)
            page.close()
            time.sleep(random.uniform(3, 5))

        browser.close()

    print(f"[bose] 完成: +{total} 张\n")


# ── Petzl: 清理垃圾，已有大图够用 ──────────────────────────────────

def clean_petzl():
    brand_path = BASE / "户外装备" / "petzl"
    removed = remove_small_images(brand_path, min_px=500, min_bytes=5000)
    print(f"[petzl] 删除 {removed} 张小图/垃圾文件\n")


# ── Shark: 清理小图 ──────────────────────────────────────────────

def clean_shark():
    brand_path = BASE / "小家电" / "shark"
    removed = remove_small_images(brand_path, min_px=500)
    print(f"[shark] 删除 {removed} 张小图\n")


# ── IF Award: 删除<500px缩略图(源文件限制无法改善) ────────────────

def clean_if_award():
    total_removed = 0
    for cat in ['小家电', '消费电子', '音箱', '电动工具']:
        d = BASE / cat / 'if_award'
        if not d.exists():
            continue
        removed = remove_small_images(d, min_px=500)
        if removed:
            print(f"[IF {cat}] 删除 {removed} 张<500px缩略图")
            total_removed += removed
    print(f"[IF Award] 总计删除 {total_removed} 张\n")


if __name__ == '__main__':
    # 先清理不需要重爬的
    print("=" * 50)
    print("阶段1: 清理垃圾图片")
    print("=" * 50)
    clean_petzl()
    clean_shark()
    clean_if_award()

    print("=" * 50)
    print("阶段2: 重爬高清图")
    print("=" * 50)
    rescrape_logitech()
    rescrape_bose()

    print("全部完成")
