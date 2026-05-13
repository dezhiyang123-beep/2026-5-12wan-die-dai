#!/usr/bin/env python3
"""
升级现有低分辨率图片：
- Logitech: Cloudinary CDN URL参数 w_416 → w_1200
- IF Award: 源文件限制，删除<500px
- Petzl/Shark: 清理小图
- Bose: 用DOM抓到的图已经是最大的了
"""
import sys, hashlib, re, time, random, requests
from pathlib import Path
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库"
s = requests.Session()
s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


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


# ── Logitech: 用Playwright获取所有CDN URL，替换尺寸参数重新下载 ──

def upgrade_logitech():
    brand_path = BASE / "消费电子" / "logitech"
    print("[logitech] 升级分辨率", flush=True)

    PAGES = {
        "https://www.logitech.com/en-us/products/mice.html": ("鼠标", "办公鼠标"),
        "https://www.logitech.com/en-us/products/keyboards.html": ("键盘", "办公键盘"),
        "https://www.logitech.com/en-us/products/combos.html": ("键鼠套装", None),
        "https://www.logitech.com/en-us/products/webcams.html": ("摄像头", "网络摄像头"),
        "https://www.logitech.com/en-us/products/headsets.html": ("耳机", "办公耳机"),
        "https://www.logitech.com/en-us/products/speakers.html": ("音箱", "桌面音箱"),
    }

    seen_hashes = set()
    total_upgraded = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for cat_url, (major, minor) in PAGES.items():
            dest_dir = brand_path / major / minor if minor else brand_path / major
            dest_dir.mkdir(parents=True, exist_ok=True)

            cat_name = minor or major
            print(f"  [{cat_name}]", end='', flush=True)

            page = browser.new_page()
            try:
                page.goto(cat_url, timeout=30000, wait_until='domcontentloaded')
                page.wait_for_timeout(5000)
                for _ in range(20):
                    page.evaluate('window.scrollBy(0, window.innerHeight)')
                    page.wait_for_timeout(400)

                # Get all product image URLs from DOM
                img_urls = page.evaluate('''() => {
                    const results = [];
                    document.querySelectorAll('img').forEach(img => {
                        const src = img.currentSrc || img.src || '';
                        if (src.includes('resource.logitech.com') && src.includes('content/dam'))
                            results.push(src);
                    });
                    return [...new Set(results)];
                }''')
                print(f" {len(img_urls)} CDN URLs", flush=True)
            except Exception as e:
                print(f" 错误: {e}", flush=True)
                page.close()
                continue
            page.close()

            # Delete existing small images in this folder
            for f in list(dest_dir.rglob('*.jpg')):
                try:
                    img = Image.open(f)
                    if max(img.size) < 500:
                        f.unlink()
                except:
                    pass

            counter = len([f for f in dest_dir.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg')])

            # Re-download with high resolution
            saved = 0
            for url in img_urls:
                # Replace Cloudinary size params: w_416,h_312 → w_1200,h_900
                hires_url = re.sub(r'w_\d+', 'w_1200', url)
                hires_url = re.sub(r'h_\d+', 'h_900', hires_url)
                hires_url = re.sub(r'dpr_[\d.]+', 'dpr_2.0', hires_url)

                time.sleep(random.uniform(0.3, 0.8))
                try:
                    r = s.get(hires_url, timeout=15)
                    if r.status_code != 200 or len(r.content) < 5000:
                        continue
                    md5 = hashlib.md5(r.content).hexdigest()
                    if md5 in seen_hashes:
                        continue
                    seen_hashes.add(md5)

                    counter += 1
                    dest = dest_dir / f"{counter:02d}.jpg"
                    if save_as_jpeg(r.content, dest):
                        saved += 1
                        total_upgraded += 1
                    else:
                        dest.unlink(missing_ok=True)
                        counter -= 1
                except Exception:
                    continue

            print(f"    +{saved} 张高清", flush=True)
            time.sleep(random.uniform(2, 4))

        browser.close()

    print(f"[logitech] 升级完成: +{total_upgraded} 张\n")


# ── IF Award: 删除源文件限制的小图 ────────────────────────────────

def clean_if_award():
    total = 0
    for cat in ['小家电', '消费电子', '音箱', '电动工具']:
        d = BASE / cat / 'if_award'
        if not d.exists():
            continue
        removed = remove_small_images(d, min_px=500)
        if removed:
            print(f"[IF {cat}] 删除 {removed} 张<500px")
            total += removed
    print(f"[IF Award] 共删 {total} 张\n")


# ── Petzl: 清理 ──────────────────────────────────────────────────

def clean_petzl():
    removed = remove_small_images(BASE / "户外装备" / "petzl", min_px=500, min_bytes=5000)
    print(f"[petzl] 删除 {removed} 张\n")


# ── Shark: 清理 ──────────────────────────────────────────────────

def clean_shark():
    removed = remove_small_images(BASE / "小家电" / "shark", min_px=500)
    print(f"[shark] 删除 {removed} 张\n")


if __name__ == '__main__':
    print("=" * 50)
    print("分辨率升级")
    print("=" * 50)
    clean_petzl()
    clean_shark()
    clean_if_award()
    upgrade_logitech()
    print("全部完成")
