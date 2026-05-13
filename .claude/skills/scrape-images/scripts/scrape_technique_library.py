#!/usr/bin/env python3
"""
设计手法库爬虫 — 从品牌官网产品页取高清图，填充 03_设计手法库/H01-H12。

每种手法精选 3-4 个品牌，每个品牌抓 3 张，共约 9-12 张/手法。
图片来源：品牌官网产品列表/详情页，有白底产品图的品牌优先。

用法：
  python scrape_technique_library.py                      # 爬全部12种手法
  python scrape_technique_library.py --techniques H01 H07 # 只爬指定手法
  python scrape_technique_library.py --per-brand 3        # 每个品牌最多几张（默认3）
"""
import sys, hashlib, time, random, argparse
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from PIL import Image
from io import BytesIO
import requests
from playwright.sync_api import sync_playwright

BASE = Path.home() / "Desktop" / "设计素材库" / "03_设计手法库"

# 每种手法：文件夹名 + 品牌来源列表
# 格式：(品牌名, 品类, 产品列表页URL)
# 优先选有白底/浅灰背景产品图的品牌官网
TECHNIQUES = {
    "H01": {
        "folder": "H01_减法设计",
        "sources": [
            ("Herman_Miller", "furniture",
             "https://www.hermanmiller.com/products/seating/office-chairs/aeron-chairs/"),
            ("Vitra", "furniture",
             "https://www.vitra.com/en-gb/office/category/seating"),
            ("Muuto", "furniture",
             "https://www.muuto.com/en/lighting"),
            ("IKEA_PS", "furniture",
             "https://www.ikea.com/us/en/cat/ps-series-22860/"),
        ],
    },
    "H02": {
        "folder": "H02_包覆设计",
        "sources": [
            ("OXO", "kitchen",
             "https://www.oxo.com/categories/cooking-and-baking/tools-gadgets"),
            ("Leica", "camera",
             "https://www.leica-camera.com/en-US/Photography/Leica-Q"),
            ("Panasonic_Lumix", "camera",
             "https://www.panasonic.com/uk/consumer/cameras-camcorders/lumix-cameras.html"),
            ("Bosch_Tools", "tools",
             "https://www.boschtools.com/us/en/boschtools-ocs/cordless-drills-and-drivers-36246-c/"),
        ],
    },
    "H03": {
        "folder": "H03_分件线设计",
        "sources": [
            ("Beats", "audio",
             "https://www.beatsbydre.com/headphones/over-ear"),
            ("Smeg", "appliance",
             "https://www.smeg.com/en/toasters/"),
            ("Nikon", "camera",
             "https://www.nikonusa.com/cameras/mirrorless-cameras/"),
            ("BangOlufsen_Headphones", "audio",
             "https://www.bang-olufsen.com/en/us/headphones"),
        ],
    },
    "H04": {
        "folder": "H04_参数化渐变",
        "sources": [
            ("NervousSystem", "design-objects",
             "https://n-e-r-v-o-u-s.com/shop/product.php?code=509"),
            ("OnRunning", "footwear",
             "https://www.on-running.com/en-us/shop/shoes"),
            ("Zellerfeld", "footwear",
             "https://zellerfeld.com/shop"),
            ("Formlabs", "industrial",
             "https://formlabs.com/blog/parametric-design/"),
        ],
    },
    "H05": {
        "folder": "H05_模块化设计",
        "sources": [
            ("Vitsoe", "furniture",
             "https://www.vitsoe.com/gb/606"),
            ("USM", "furniture",
             "https://www.usm.com/en/products/usm-haller/tables/"),
            ("Flos_Systems", "lighting",
             "https://www.flos.com/en/systems"),
            ("Agrafka", "furniture",
             "https://www.muuto.com/en/shelving"),
        ],
    },
    "H06": {
        "folder": "H06_仿生设计",
        "sources": [
            ("Humanscale", "furniture",
             "https://www.humanscale.com/products/seating/"),
            ("Thule", "outdoor",
             "https://www.thule.com/en-us/backpacks/hiking-backpacks"),
            ("Molo_Kids", "furniture",
             "https://www.molodesign.com/shop/"),
            ("Kartell", "furniture",
             "https://www.kartell.com/en/chairs"),
        ],
    },
    "H07": {
        "folder": "H07_极简整合",
        "sources": [
            ("BangOlufsen", "audio",
             "https://www.bang-olufsen.com/en/us/speakers"),
            ("Smeg_Fridge", "appliance",
             "https://www.smeg.com/en/refrigerators/"),
            ("Vitsoe_Chair", "furniture",
             "https://www.vitsoe.com/gb/620"),
            ("Kartell", "furniture",
             "https://www.kartell.com/en/chairs"),
        ],
    },
    "H08": {
        "folder": "H08_对比强调",
        "sources": [
            ("Smeg_Kettle", "appliance",
             "https://www.smeg.com/en/kettles/"),
            ("Smeg_Toaster", "appliance",
             "https://www.smeg.com/en/toasters/"),
            ("BangOlufsen_Color", "audio",
             "https://www.bang-olufsen.com/en/us/headphones"),
            ("Kartell_Color", "furniture",
             "https://www.kartell.com/en/lamps"),
        ],
    },
    "H09": {
        "folder": "H09_隐藏工程",
        "sources": [
            ("Blum", "hardware",
             "https://www.blum.com/us/en/products/liftingsystems/aventos/aventoshf/"),
            ("Elica", "appliance",
             "https://www.elica.com/en/products/cooker-hoods/built-in"),
            ("Vitsoe_606", "furniture",
             "https://www.vitsoe.com/gb/606"),
            ("Agape", "bathroom",
             "https://www.agapedesign.it/en/products/washbasins"),
        ],
    },
    "H10": {
        "folder": "H10_材料表达",
        "sources": [
            ("FermLiving", "furniture",
             "https://www.fermliving.com/collections/chairs"),
            ("String_Furniture", "furniture",
             "https://string.se/en-gb/products/shelving-systems/string-system/"),
            ("WOUD", "furniture",
             "https://woud.dk/en/furniture/chairs"),
            ("Menu_Design", "furniture",
             "https://www.menudesignshop.com/collections/furniture"),
        ],
    },
    "H11": {
        "folder": "H11_功能外显",
        "sources": [
            ("Flos_Infra", "lighting",
             "https://www.flos.com/en/table"),
            ("Moooi", "lighting",
             "https://www.moooi.com/en/lighting"),
            ("Artemide", "lighting",
             "https://www.artemide.com/en/subfamily/table-lamps"),
            ("Muuto_Lamp", "lighting",
             "https://www.muuto.com/en/lighting"),
        ],
    },
    "H12": {
        "folder": "H12_人机界面强化",
        "sources": [
            ("Humanscale_Input", "office",
             "https://www.humanscale.com/products/keyboard-and-mouse/"),
            ("Fiskars", "tools",
             "https://www.fiskars.com/en-us/gardening-and-yard-care/products/pruning"),
            ("Ergotron", "office",
             "https://www.ergotron.com/en-us/products/product-type/monitor-arms"),
            ("Caran_Ache", "stationery",
             "https://www.carandache.com/en/pens"),
        ],
    },
}

SKIP_KEYWORDS = [
    'logo', 'icon', 'badge', 'sprite', 'avatar', 'author',
    'facebook', 'twitter', 'instagram', 'nav', 'header', 'footer',
    'thumbnail-xs', 'placeholder', 'loading', 'blank', 'pixel',
]

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
})


def url_ok(url: str) -> bool:
    u = url.lower()
    if not u.startswith('http'):
        return False
    return not any(k in u for k in SKIP_KEYWORDS)


def save_jpeg(data: bytes, dest: Path) -> bool:
    try:
        img = Image.open(BytesIO(data))
    except Exception:
        return False
    w, h = img.size
    if max(w, h) < 800:
        return False
    if max(w, h) / max(min(w, h), 1) > 3.5:  # 跳过极端横幅
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if img.mode in ('RGBA', 'LA', 'P', 'PA'):
        bg = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode in ('RGBA', 'PA'):
            bg.paste(img, mask=img.split()[-1])
        else:
            bg.paste(img)
        bg.save(dest, 'JPEG', quality=92)
    else:
        img.convert('RGB').save(dest, 'JPEG', quality=92)
    return True


def extract_best_image_urls(page, max_results: int = 12) -> list:
    """从当前页面提取产品图URL（优先srcset最大版本，按尺寸/面积降序）。"""
    return page.evaluate('''(maxResults) => {
        function parseSrcset(srcset) {
            return srcset.split(',').map(s => {
                const parts = s.trim().split(/\\s+/);
                return {url: parts[0] || '', w: parseInt(parts[1]) || 0};
            }).filter(x => x.url && x.url.startsWith('http'));
        }
        function getBestUrl(img) {
            const srcset = img.srcset || img.getAttribute('data-srcset') || '';
            if (srcset) {
                const entries = parseSrcset(srcset).sort((a, b) => b.w - a.w);
                if (entries.length > 0) return {url: entries[0].url, w: entries[0].w};
            }
            const src = img.getAttribute('data-src') || img.getAttribute('data-lazy-src')
                || img.currentSrc || img.src || '';
            return {url: src, w: img.offsetWidth || img.width || 0};
        }

        const results = [];
        const seen = new Set();
        document.querySelectorAll('img').forEach(img => {
            const {url, w} = getBestUrl(img);
            if (!url || url.startsWith('data:') || seen.has(url)) return;
            if (w < 200 && img.offsetWidth < 200) return;
            seen.add(url);
            const h = img.naturalHeight || img.offsetHeight || img.height || 0;
            results.push({url, w: w || img.offsetWidth, h, area: (w || img.offsetWidth) * h});
        });
        results.sort((a, b) => b.area - a.area);
        return results.slice(0, maxResults).map(x => x.url);
    }''', max_results)


def scrape_brand_page(page, brand: str, category: str, url: str,
                      wanted: int, seen_hashes: set,
                      dest_dir: Path, code: str, seq_start: int) -> int:
    """抓一个品牌产品页，返回实际保存数量。"""
    print(f"  [{brand}] {url[:70]}...", flush=True)
    try:
        page.goto(url, timeout=25000, wait_until='domcontentloaded')
        page.wait_for_timeout(3000)
        # 滚动加载懒加载图
        for _ in range(10):
            page.evaluate('window.scrollBy(0, window.innerHeight)')
            page.wait_for_timeout(300)
    except Exception as e:
        print(f"  [跳过] 加载失败: {e}", flush=True)
        return 0

    img_urls = extract_best_image_urls(page, max_results=20)
    saved = 0
    seq = seq_start

    for img_url in img_urls:
        if saved >= wanted:
            break
        if not url_ok(img_url):
            continue
        try:
            resp = session.get(img_url, timeout=20, allow_redirects=True)
            if resp.status_code != 200:
                continue
            data = resp.content
            img_hash = hashlib.md5(data).hexdigest()
            if img_hash in seen_hashes:
                continue
            dest = dest_dir / f"{code}_{category}_{seq:03d}.jpg"
            if save_jpeg(data, dest):
                seen_hashes.add(img_hash)
                try:
                    check = Image.open(BytesIO(data))
                    dims = f"{check.size[0]}×{check.size[1]}"
                except Exception:
                    dims = "?"
                print(f"    ✓ {dest.name} ({dims})", flush=True)
                seq += 1
                saved += 1
        except Exception:
            continue
        time.sleep(random.uniform(0.3, 0.8))

    return saved


def scrape_technique(browser, code: str, info: dict, per_brand: int) -> int:
    dest_dir = BASE / info["folder"]
    dest_dir.mkdir(parents=True, exist_ok=True)

    existing = list(dest_dir.glob("*.jpg")) + list(dest_dir.glob("*.jpeg"))
    existing_count = len(existing)
    target = per_brand * len(info["sources"])

    if existing_count >= target:
        print(f"\n[{code}] {info['folder']} 已有 {existing_count} 张，跳过。", flush=True)
        return existing_count

    print(f"\n[{code}] {info['folder']} — 已有 {existing_count} 张，目标 {target} 张", flush=True)

    seen_hashes = set()
    for f in existing:
        try:
            seen_hashes.add(hashlib.md5(f.read_bytes()).hexdigest())
        except Exception:
            pass

    page = browser.new_page()
    seq = existing_count + 1
    total_saved = 0

    try:
        for brand, category, url in info["sources"]:
            already = existing_count + total_saved
            if already >= target:
                break
            n = scrape_brand_page(page, brand, category, url,
                                   per_brand, seen_hashes,
                                   dest_dir, code, seq + total_saved)
            total_saved += n
            time.sleep(random.uniform(1.0, 2.0))
    finally:
        page.close()

    final = existing_count + total_saved
    status = "✓" if total_saved >= per_brand else f"⚠ 仅得 {total_saved} 张"
    print(f"  [{code}] 完成：{final} 张 {status}", flush=True)
    return final


def main():
    parser = argparse.ArgumentParser(description="设计手法库爬虫（品牌官网版）")
    parser.add_argument("--techniques", nargs="+",
                        help="指定手法编号，如 H01 H07。默认全部12种。")
    parser.add_argument("--per-brand", type=int, default=3,
                        help="每个品牌最多下载张数（默认3）")
    args = parser.parse_args()

    targets = {}
    if args.techniques:
        for code in args.techniques:
            code = code.upper()
            if code in TECHNIQUES:
                targets[code] = TECHNIQUES[code]
            else:
                print(f"未知编号: {code}，可用: {list(TECHNIQUES.keys())}")
    else:
        targets = TECHNIQUES

    print(f"目标: {BASE}")
    print(f"手法: {list(targets.keys())}，每品牌 {args.per_brand} 张")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        results = {}
        try:
            for code, info in targets.items():
                results[code] = scrape_technique(browser, code, info, args.per_brand)
        finally:
            browser.close()

    print("\n=== 汇总 ===")
    for code, count in results.items():
        folder = TECHNIQUES[code]["folder"]
        target = args.per_brand * len(TECHNIQUES[code]["sources"])
        status = "✓" if count >= target else f"⚠ ({count}/{target})"
        print(f"  {folder}: {count} 张 {status}")
    print(f"\n合计: {sum(results.values())} 张")


if __name__ == "__main__":
    main()
