#!/usr/bin/env python3
"""
Direct brand scraper — bypasses sitemap discovery entirely.
For each brand, visits specific product catalog URLs with Playwright,
extracts all product images, downloads with classification into Chinese 2-level folders.
"""
import os, sys, re, time, random, hashlib
from pathlib import Path
from urllib.parse import urlparse, urljoin
from PIL import Image
from io import BytesIO
import requests

# Import shared utilities from main scraper
sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import (
    universal_extract_images, render_pages_batch, UNIVERSAL_SKIP, HEADERS,
    download_image, is_valid_image, convert_webp_to_jpg, is_product_shot, log,
    _classify_brand_product
)

BASE = Path(os.environ.get("SCRAPE_BASE", str(Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库")))

# ── URL → Chinese category mapping ────────────────────────────────────
# Each URL maps to (大类, 小类) based on its path segment.
# The scraper uses this to organize images into brand/大类/小类/NN.jpg

_URL_CATEGORY_MAP = {
    # ── artemide ──────────────────────────────────────────────────────
    "/subfamily/table": ("台灯", "台灯"),
    "/subfamily/floor": ("落地灯", "落地灯"),
    "/subfamily/suspension": ("吊灯", "吊灯"),
    "/subfamily/wall-ceiling": ("壁灯", "壁灯"),
    "/subfamily/outdoor": ("户外灯", "户外灯"),
    # ── foscarini ─────────────────────────────────────────────────────
    "/products/suspension": ("吊灯", "吊灯"),
    "/products/table": ("台灯", "台灯"),
    "/products/floor": ("落地灯", "落地灯"),
    "/products/wall": ("壁灯", "壁灯"),
    # ── louis_poulsen ─────────────────────────────────────────────────
    "/private/pendants": ("吊灯", "吊灯"),
    "/private/table-lamps": ("台灯", "台灯"),
    "/private/floor-lamps": ("落地灯", "落地灯"),
    "/private/wall-lamps": ("壁灯", "壁灯"),
    "/professional/outdoor": ("户外灯", "户外灯"),
    # ── nitecore ──────────────────────────────────────────────────────
    "/category/flashlights": ("手电筒", "手电筒"),
    "/category/headlamps": ("手电筒", "头灯"),
    "/category/lanterns": ("手电筒", "营地灯"),
    # ── biolite ───────────────────────────────────────────────────────
    "/collections/outdoor-lighting": ("户外灯", "户外灯"),
    "/collections/charge": ("充电设备", "充电设备"),
    "/collections/cook": ("户外炊具", "户外炊具"),
    # ── bega ──────────────────────────────────────────────────────────
    "/products/outdoor-luminaires": ("户外灯", "户外灯"),
    "/products/indoor-luminaires": ("室内灯", "室内灯"),
    # ── philips_lighting ──────────────────────────────────────────────
    "/led-bulbs": ("LED灯", "LED灯泡"),
    "/led-tubes": ("LED灯", "LED灯管"),
    "/led-lights": ("LED灯", "LED灯"),
    # ── rab_lighting ──────────────────────────────────────────────────
    "/products/area-site": ("户外灯", "场地灯"),
    "/products/flood": ("户外灯", "泛光灯"),
    "/products/wall": ("壁灯", "壁灯"),
    "/products/bollard-landscape": ("户外灯", "庭院灯"),
    "/products/parking-garage": ("户外灯", "车库灯"),
    # ── wac_lighting ──────────────────────────────────────────────────
    "/products/outdoor-lighting": ("户外灯", "户外灯"),
    "/products/track-lighting": ("轨道灯", "轨道灯"),
    "/products/recessed-lighting": ("筒灯", "筒灯"),
    "/products/pendant-lighting": ("吊灯", "吊灯"),
    # ── garmin ────────────────────────────────────────────────────────
    "/c/wearables-smartwatches": ("运动手表", "智能手表"),
    "/c/outdoor-recreation": ("户外设备", "户外设备"),
    "/c/marine": ("户外电子", "船用设备"),
    "/c/fitness-running": ("运动手表", "健身设备"),
    # ── omron ─────────────────────────────────────────────────────────
    "/blood-pressure": ("健康监测", "血压计"),
    "/pain-therapy": ("健康监测", "理疗仪"),
    "/respiratory": ("健康监测", "呼吸设备"),
    # ── dyson ─────────────────────────────────────────────────────────
    "/vacuum-cleaners": ("吸尘器", "吸尘器"),
    "/hair-care": ("美发工具", "美发工具"),
    "/air-treatment": ("空气净化器", "空气净化器"),
    "/lighting": ("台灯", "台灯"),
    "/headphones": ("耳机", "耳机"),
    # ── sony ──────────────────────────────────────────────────────────
    "/electronics/headphones": ("耳机", "头戴耳机"),
    "/electronics/wireless-speakers": ("蓝牙音箱", "便携音箱"),
    "/electronics/cameras": ("摄像头", "相机"),
    "/electronics/televisions": ("电视", "电视"),
    "/electronics/gaming-consoles": ("游戏设备", "游戏主机"),
    # ── yeti ──────────────────────────────────────────────────────────
    "/drinkware": ("保温容器", "保温杯"),
    "/coolers": ("保温容器", "保温箱"),
    "/bags": ("户外包袋", "户外包袋"),
    # ── bose ──────────────────────────────────────────────────────────
    "/c/speakers": ("蓝牙音箱", "便携音箱"),
    "/c/headphones": ("耳机", "头戴耳机"),
    "/c/earbuds": ("耳机", "真无线耳机"),
    "/c/soundbars": ("条形音箱", "条形音箱"),
    # ── shark ─────────────────────────────────────────────────────────
    "/vacuum-cleaners": ("吸尘器", "吸尘器"),
    "/robot-vacuums": ("吸尘器", "扫地机器人"),
    "/steam-mops": ("清洁机", "蒸汽拖把"),
    # ── olight ────────────────────────────────────────────────────────
    "/flashlights": ("手电筒", "手电筒"),
    "/headlamps": ("手电筒", "头灯"),
    "/camping-lanterns": ("手电筒", "营地灯"),
    # ── bosch_professional ────────────────────────────────────────────
    "/drills-background": ("电钻", "电钻"),
    "/circular-saws-background": ("电锯", "圆锯"),
    "/grinders-background": ("角磨机", "角磨机"),
    "/sanders-background": ("砂光机", "砂光机"),
    "/routers-background": ("铣", "修边机"),
    # ── logitech ──────────────────────────────────────────────────────
    "/products/mice": ("鼠标", "办公鼠标"),
    "/products/keyboards": ("键盘", "办公键盘"),
    "/products/combos": ("键鼠套装", "键鼠套装"),
    "/products/webcams": ("摄像头", "网络摄像头"),
    "/products/headsets": ("耳机", "办公耳机"),
    "/products/speakers": ("音箱", "桌面音箱"),
    "/products/gaming-mice": ("鼠标", "游戏鼠标"),
    "/products/gaming-keyboards": ("键盘", "游戏键盘"),
    "/products/gaming-audio": ("耳机", "游戏耳机"),
}


def _classify_url(page_url):
    """Match page URL against _URL_CATEGORY_MAP. Returns (大类, 小类) or None."""
    path = urlparse(page_url).path.rstrip("/").lower()
    # Try longest match first
    candidates = sorted(_URL_CATEGORY_MAP.keys(), key=len, reverse=True)
    for pattern in candidates:
        if pattern.lower() in path:
            return _URL_CATEGORY_MAP[pattern]
    return None


# ── Brand catalog URLs (manually curated, working URLs) ─────────────────
BRANDS = {
    # (base_output_folder, [list of catalog page URLs to visit])
    "artemide": (BASE / "灯具" / "artemide", [
        "https://www.artemide.com/en/subfamily/table",
        "https://www.artemide.com/en/subfamily/floor",
        "https://www.artemide.com/en/subfamily/suspension",
        "https://www.artemide.com/en/subfamily/wall-ceiling",
        "https://www.artemide.com/en/subfamily/outdoor",
    ]),
    "foscarini": (BASE / "灯具" / "foscarini", [
        "https://www.foscarini.com/en/products/suspension/",
        "https://www.foscarini.com/en/products/table/",
        "https://www.foscarini.com/en/products/floor/",
        "https://www.foscarini.com/en/products/wall/",
    ]),
    "louis_poulsen": (BASE / "灯具" / "louis_poulsen", [
        "https://www.louispoulsen.com/en-us/private/pendants",
        "https://www.louispoulsen.com/en-us/private/table-lamps",
        "https://www.louispoulsen.com/en-us/private/floor-lamps",
        "https://www.louispoulsen.com/en-us/private/wall-lamps",
        "https://www.louispoulsen.com/en-us/professional/outdoor",
    ]),
    "nitecore": (BASE / "灯具" / "nitecore", [
        "https://www.nitecore.com/category/flashlights",
        "https://www.nitecore.com/category/headlamps",
        "https://www.nitecore.com/category/lanterns-and-signal-lights",
    ]),
    "biolite": (BASE / "灯具" / "biolite", [
        "https://www.bioliteenergy.com/collections/outdoor-lighting",
        "https://www.bioliteenergy.com/collections/charge",
        "https://www.bioliteenergy.com/collections/cook",
    ]),
    "bega": (BASE / "灯具" / "bega", [
        "https://www.bega.com/en/products/outdoor-luminaires/",
        "https://www.bega.com/en/products/indoor-luminaires/",
    ]),
    "philips_lighting": (BASE / "灯具" / "philips_lighting", [
        "https://www.lighting.philips.com/consumer/led-lights/led-bulbs",
        "https://www.lighting.philips.com/consumer/led-lights/led-tubes",
        "https://www.usa.lighting.philips.com/consumer/led-lights",
    ]),
    "rab_lighting": (BASE / "灯具" / "rab_lighting", [
        "https://www.rablighting.com/products/area-site",
        "https://www.rablighting.com/products/flood",
        "https://www.rablighting.com/products/wall",
        "https://www.rablighting.com/products/bollard-landscape",
        "https://www.rablighting.com/products/parking-garage",
    ]),
    "wac_lighting": (BASE / "灯具" / "wac_lighting", [
        "https://www.waclighting.com/products/outdoor-lighting",
        "https://www.waclighting.com/products/track-lighting",
        "https://www.waclighting.com/products/recessed-lighting",
        "https://www.waclighting.com/products/pendant-lighting",
    ]),
    "garmin": (BASE / "户外装备" / "garmin", [
        "https://www.garmin.com/en-US/c/wearables-smartwatches/",
        "https://www.garmin.com/en-US/c/outdoor-recreation/",
        "https://www.garmin.com/en-US/c/marine/",
        "https://www.garmin.com/en-US/c/fitness-running/",
    ]),
    "omron": (BASE / "医疗设备" / "omron", [
        "https://www.omronhealthcare.com/blood-pressure",
        "https://www.omronhealthcare.com/pain-therapy",
        "https://www.omronhealthcare.com/respiratory",
    ]),
    "dyson": (BASE / "小家电" / "dyson", [
        "https://www.dyson.com/en/vacuum-cleaners",
        "https://www.dyson.com/en/hair-care",
        "https://www.dyson.com/en/air-treatment",
        "https://www.dyson.com/en/lighting",
        "https://www.dyson.com/en/headphones",
    ]),
    "sony": (BASE / "消费电子" / "sony", [
        "https://www.sony.com/en/electronics/headphones",
        "https://www.sony.com/en/electronics/wireless-speakers",
        "https://www.sony.com/en/electronics/cameras",
        "https://www.sony.com/en/electronics/televisions",
        "https://www.sony.com/en/electronics/gaming-consoles-accessories",
    ]),
    "yeti": (BASE / "户外装备" / "yeti", [
        "https://www.yeti.com/drinkware",
        "https://www.yeti.com/coolers",
        "https://www.yeti.com/bags",
    ]),
    "bose": (BASE / "音箱" / "bose", [
        "https://www.bose.com/c/speakers",
        "https://www.bose.com/c/headphones",
        "https://www.bose.com/c/earbuds",
        "https://www.bose.com/c/soundbars",
    ]),
    "shark": (BASE / "小家电" / "shark", [
        "https://www.sharkclean.com/vacuum-cleaners/",
        "https://www.sharkclean.com/robot-vacuums/",
        "https://www.sharkclean.com/steam-mops/",
    ]),
    "olight": (BASE / "户外装备" / "olight", [
        "https://www.olightstore.com/flashlights.html",
        "https://www.olightstore.com/headlamps.html",
        "https://www.olightstore.com/camping-lanterns.html",
    ]),
    "bosch_professional": (BASE / "电动工具" / "bosch_professional", [
        "https://www.boschtools.com/us/en/boschtools-ocs/drills-background-297056-c/",
        "https://www.boschtools.com/us/en/boschtools-ocs/circular-saws-background-297113-c/",
        "https://www.boschtools.com/us/en/boschtools-ocs/grinders-background-297138-c/",
        "https://www.boschtools.com/us/en/boschtools-ocs/sanders-background-297090-c/",
        "https://www.boschtools.com/us/en/boschtools-ocs/routers-background-297078-c/",
    ]),
    "logitech": (BASE / "消费电子" / "logitech", [
        "https://www.logitech.com/en-us/products/mice.html",
        "https://www.logitech.com/en-us/products/keyboards.html",
        "https://www.logitech.com/en-us/products/combos.html",
        "https://www.logitech.com/en-us/products/webcams.html",
        "https://www.logitech.com/en-us/products/headsets.html",
        "https://www.logitech.com/en-us/products/speakers.html",
        "https://www.logitechg.com/en-us/products/gaming-mice.html",
        "https://www.logitechg.com/en-us/products/gaming-keyboards.html",
        "https://www.logitechg.com/en-us/products/gaming-audio.html",
    ]),
}


def scrape_brand_direct(name, output_dir, urls, session, timeout=45):
    """Visit each URL with Playwright, extract and download product images into classified folders."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    seen_urls = set()
    seen_hashes = set()
    # Track per-subfolder counters: {subfolder_path: current_count}
    folder_counters = {}
    saved = 0

    def _get_next_path(folder):
        """Get next sequential filename in a classified subfolder."""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        if folder not in folder_counters:
            # Count existing files to continue numbering
            existing = [f for f in folder.iterdir() if f.suffix.lower() in ('.jpg', '.png')]
            folder_counters[folder] = len(existing)
        folder_counters[folder] += 1
        return folder / f"{folder_counters[folder]:02d}.jpg"

    def _on_page(page_url, html, intercepted):
        nonlocal saved

        # Determine category from URL — skip if no valid classification
        cat = _classify_url(page_url)
        if not cat:
            return  # No "其他" fallback — discard unclassifiable pages
        major, minor = cat
        dest_folder = output_dir / major / minor

        images = universal_extract_images(html, page_url, intercepted=intercepted)

        for img_url in images:
            if img_url in seen_urls or UNIVERSAL_SKIP.search(img_url):
                continue
            seen_urls.add(img_url)

            dest = _get_next_path(dest_folder)
            if not download_image(img_url, dest, session):
                dest.unlink(missing_ok=True)
                folder_counters[dest.parent] -= 1
                continue

            dest = Path(convert_webp_to_jpg(dest))

            if not is_valid_image(dest, min_px=400):
                dest.unlink(missing_ok=True)
                folder_counters[dest.parent] -= 1
                continue

            # Content hash dedup
            try:
                h = hashlib.md5(dest.read_bytes()).hexdigest()
                if h in seen_hashes:
                    dest.unlink(missing_ok=True)
                    folder_counters[dest.parent] -= 1
                    continue
                seen_hashes.add(h)
            except Exception:
                pass

            saved += 1

    log(f"\n[{name}] {len(urls)} 个目录页")
    render_pages_batch(urls, timeout, True, _on_page, delay=2.0)
    log(f"[{name}] 完成: {saved} 张图片 → {output_dir}")
    return saved


def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    # Allow running specific brands: python scrape_brands_direct.py dyson sony
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(BRANDS.keys())

    total = 0
    for name in targets:
        if name not in BRANDS:
            log(f"[跳过] 未知品牌: {name}")
            continue
        output_dir, urls = BRANDS[name]
        count = scrape_brand_direct(name, output_dir, urls, session)
        total += count

    log(f"\n[汇总] {len(targets)} 个品牌, {total} 张图片")


if __name__ == "__main__":
    main()
