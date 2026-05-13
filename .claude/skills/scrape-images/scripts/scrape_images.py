"""
Multi-site image scraper.
Supports: RAB Lighting, Red Dot Design Award (32 categories), iF Design Award, any website.
No LLM API key required.  VPN required for Red Dot / iF Design (blocked in mainland China).

Usage examples:
  # Red Dot — lighting category, 5 sub-types, deduplicated
  python scrape_images.py "https://www.red-dot.org/project-search/?cat=lighting&q=pendant" \\
      --site reddot --category lighting --download ~/Desktop/reddot_lighting --limit 20

  # iF Design — lighting category (ID 129)
  python scrape_images.py "https://ifdesign.com/en/winner-ranking/show/product-design/0?categoryId=129" \\
      --site ifdesign --download ~/Desktop/if_lighting --limit 100

  # Any brand website
  python scrape_images.py --brand "Flos" --download ~/Desktop/flos --limit 20

Key options:
  --site {rab,reddot,ifdesign,auto}   Force scraper mode (default: auto-detect)
  --brand BRAND                        Brand name — auto-searches for official product page
  --download DIR                       Root folder; subfolders created per product/type
  --limit INT                          Max products to scrape (default: 5)
  --timeout INT                        Page timeout in seconds (default: 30)
  --category CATEGORY                  Red Dot category slug (32 options, see --help)
  --years YEAR [...]                   Red Dot year filter, e.g. --years 2023 2024 2025
  --max-per-product N                  Images per product cap (default: 2)
  --classify                           Post-process into 8 super-categories + report
  --bear-mode                          Taobao + XHS bear-product color research mode
  --no-headless                        Show browser window (debug)
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse, parse_qs

import requests
import urllib3
from bs4 import BeautifulSoup

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ── RAB filter patterns ────────────────────────────────────────────────────

RAB_SKIP = re.compile(
    r"(backgr(?:ou|uo)n?d|[-_]bg[-_.]|[-_]bg$"
    r"|mobile"                                          # all mobile-variant images
    r"|logo|loader|spinner|placeholder"
    r"|[-_]icons?[-_.\d]|icon\d*\."                     # icon patterns
    r"|cta.button|learn.more|play.button"               # buttons (covers learn-more-btn)
    r"|[-_]btn[-_.]"                                    # button images
    r"|app[-_]icon"                                     # app icon sets
    r"|dlc[-_]|dlc\d|ip\d\d|\d\dip"                    # IP rating badges (65IP etc.)
    r"|\d+v[-_]icon|\d+v_\d"
    r"|\d+k(?:hours)?[-_.\d]"
    r"|no_comp|yrs?_no|[-_]\dg[-_]"                     # 3G/4G vibration badges
    r"|warranty|line_\d"
    r"|livechat|email_icon|lightingdesign"
    r"|wheretobuy|lightcloud|RAB-logo"
    r"|mobile_hero|section.hero"
    r"|versatile|everyday.use|mounting.options"
    r"|quality.performence|quality.bg|stay.in.control"
    r"|recycle|ship\.|cube\.|wind\.|books|dvds|shells"
    r"|less.material|section_1_0|footnote"
    r"|lcb.phone|lcb_phone"
    r"|haz.location|location.dark"
    r"|feature\d*[-_]?asset"                            # spec feature assets
    r"|[-_]PC\."                                        # parameter charts
    r"|field.adjustable.w.cct"
    # ── Marketing / badge images (glazed_builder_images) ──────────────────
    r"|glazed_builder_images"                           # ALL badge/icon/marketing images
    # ── System combo diagrams ─────────────────────────────────────────────
    r"|[-_]components\b|components\.jpg|components\.png"  # Driver+Controller+product combos
    r"|selectable.beam|selectable.photocell"
    r"|ground.breaking|most.flexible|smaller.size"
    r"|hero.backup|\.backup\."
    r"|section[-_]\d|[-_]sec\d[-_.]"                    # section illustrations
    r"|[-_]mage\."
    r"|[-_]lens[-_.]"
    r"|x22fp.hero"
    r"|fxled.most|fxled.footnote"
    # ── Spec / dimension drawings ──────────────────────────────────────────
    r"|dimension|[-_]dims?\."                           # dimension/dims drawings
    r"|diagram"                                         # diagrams
    r"|callout|call.out"                                # callout diagrams
    # ── Spec infographic / icons ───────────────────────────────────────────
    r"|dimmable"                                        # dimmable% spec graphics
    r"|90cri"                                           # CRI spec graphics
    r"|high.efficac|efficac"                            # 175 lm/W bubbles
    r"|multiple.power|power.package"                    # wattage selection grids
    r"|perf.data"                                       # performance data charts
    r"|voltage.icon"                                    # voltage icon sets
    r"|highperformance.icon|high.performance.icon"
    r"|builttough"                                      # built-tough icon sets
    r"|smkpanel|circadian"
    # ── Certification / warranty badges ───────────────────────────────────
    r"|5yr|5-yr|yr_nc|_nc_2x"                          # warranty badges
    r"|energy.star|title24|ul[-_]wm|ccea"               # certification badges
    # ── Dimmer / control photos ────────────────────────────────────────────
    r"|dimmer\.|dimming\."                              # dimmer switch photos
    # ── LightCloud icons ───────────────────────────────────────────────────
    r"|[/_]lc\.png|lc[-_]sensor"                        # lc.png / LC_Sensors.png
    # ── Scene / marketing images ───────────────────────────────────────────
    r"|parking.lot"                                     # parking lot scenes
    r"|adjustabilit"                                    # adjustability diagrams
    r"|anywhere.wafer"
    # ── Accessory / variant images ─────────────────────────────────────────
    r"|wafer[-_]color|color.trim|mounting.plate|emergency.driver"
    r"|[-_]accessories|accessory"                       # accessory group images
    r"|twistlock|slipfitter.kit|pole.mount.kit"         # specific accessories
    r"|house.side|joiner.bracket"
    r"|remote_\d"                                       # remote controls
    # ── Mounting diagrams ──────────────────────────────────────────────────
    r"|mountimage|mounting.image"
    # ── Generic / blank images ─────────────────────────────────────────────
    r"|thumbnail"                                       # generic thumbnails
    r"|[/_]line\.png"                                   # blank separator line
    # ── Trim / accessory variant photos ───────────────────────────────────
    r"|wfrl.trim|dltrim|dlplate|extcbl"                 # wafer trim variants
    r"|[-_]cct\."                                       # CCT selection icons
    r"|[-_]voltage\."                                   # voltage spec icons
    r"|smooth_\d|baffle_\d"                             # numbered finish swatches
    r"|\d+k"                                            # spec lifetime badges (50K hours)
    # ── Cockpit media (all marketing/junk, no clean product shots) ─────────
    r"|cockpit/storage/media"
    # ── Tape light accessories / drivers / channels ───────────────────────
    r"|/t[io]d[-_]\d"                                   # tape drivers: tid-60, tod-96
    r"|/tap\d{2}"                                       # tape connectors: tap12, tap15
    r"|/tsg[.\-_]|/tsg$"                               # tape sealant gel
    r"|/tbb\d|/tb\d{2}\."                              # tape backing board
    r"|/tnd[_.\-]"                                     # tape driver variant
    r"|/lcblv"                                         # LightCloud Blue device
    r"|channel|extrusion"                              # aluminum channels
    # ── Scene / lifestyle hero images ────────────────────────────────────
    r"|features/hero_images/"                          # RAB lifestyle hero shots
    r"|[-_]hero[-_.]desktop"                           # hero desktop variants
    r"|[-_]hero[-_.]mobile)",
    re.IGNORECASE,
)

RAB_HIRES = re.compile(
    r"/sites/default/files/features/hero_images/"
    r"|/images/product/photo/",
    re.IGNORECASE,
)

RAB_SKIP_PAGES = re.compile(
    r"(sustainability|ez.layout|ezlayout|lighting.design|lightingdesign"
    r"|case.stud|about|careers|affiliat|certif|dlc|taa|rebate"
    r"|lightcloud|digikits|electric.vehicle|ev.charger)",
    re.IGNORECASE,
)

# Known image file extensions (used to reject e.g. .php)
_IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}

# ── Red Dot filter patterns ────────────────────────────────────────────────

REDDOT_SKIP = re.compile(
    r"(logo|icon|badge|avatar|flag|social|award.seal|rd.seal"
    r"|navigation|menu|footer|header|banner.bg"
    r"|_[A-Z]{2}_RD_"               # award badges: 2025_DC_RD_xxx, 2025_BC_RD_xxx
    r"|_[A-Z]{2}_BoB_"              # Best of Best badges
    r"|csm_20\d\d_[A-Z]{2}_"       # any year/category badge: csm_2025_DC_...
    r"|rd_logo|reddot.logo)",
    re.IGNORECASE,
)

# ── Universal noise filter (applies to all sites) ─────────────────────────

UNIVERSAL_SKIP = re.compile(
    r"(logo|favicon|sprite|icon\d*\.|[-_]icon[-_.]"
    r"|loader|spinner|placeholder|blank\.gif|pixel\.gif|spacer"
    r"|[-_]bg[-_.]|background"
    r"|social[-_]|share[-_]|twitter|facebook|instagram|linkedin|youtube"
    r"|avatar|gravatar|profile[-_]pic"
    r"|banner[-_]ad|ad[-_]banner|advertisement"
    r"|tracking|analytics|beacon"
    r"|\.svg$)",                    # SVG icons/logos
    re.IGNORECASE,
)

# ── Universal URL upgrade patterns ────────────────────────────────────────
# Each is (compiled_regex, replacement). Applied in order, first match wins.

URL_UPGRADE_PATTERNS = [
    # RAB specific
    (re.compile(r"/product/photo/", re.I),          "/product/largePhoto/"),
    # WordPress thumbnail: image-300x200.jpg → image.jpg
    (re.compile(r"-\d+x\d+(\.\w{2,5})(\?.*)?$"),   r"\1"),
    # Shopify: product_100x100.jpg → product_2048x2048.jpg (request high-res)
    (re.compile(r"_\d+x\d*(\.\w{2,5})(\?.*)?$"),   r"_2048x2048\1"),
    # Shopify CDN: /files/...?width=300 → ?width=2048
    (re.compile(r"(cdn\.shopify\.com.*[?&]width=)\d+", re.I), r"\g<1>2048"),
    # Generic size suffix in filename: _sm _xs _s _thumb _small _med _medium _m _preview _mini
    (re.compile(r"[_-](xs|sm|s|thumb|thumbnail|small|med|medium|m|mini|preview|tiny|lite)(\.\w{2,5})$", re.I), r"\2"),
    # Cloudinary / imgix: w_300,h_200 → w_1200,h_1200
    (re.compile(r"\bw_\d+\b"),                      "w_1200"),
    # imgix: ?w=300 → ?w=1200  (keep other params)
    (re.compile(r"([?&]w=)\d+"),                    r"\g<1>1200"),
    (re.compile(r"([?&]width=)\d+", re.I),          r"\g<1>1200"),
    # Size path segment: /300x200/ or /resize/300/200/
    (re.compile(r"/\d+x\d+/"),                      "/"),
    (re.compile(r"/resize/\d+/\d+/", re.I),         "/"),
    # /thumb/ or /thumbnail/ → /
    (re.compile(r"/(thumb|thumbnail)s?/", re.I),     "/"),
    # /small/ /medium/ → /large/
    (re.compile(r"/small/", re.I),                  "/large/"),
    (re.compile(r"/medium/", re.I),                 "/large/"),
    # @2x suffix already present — nothing to upgrade
]

# data-* attributes that commonly hold full-size image URLs
HIRES_DATA_ATTRS = [
    "data-zoom-image", "data-zoom", "data-large", "data-full",
    "data-full-url", "data-hires", "data-hi-res", "data-big",
    "data-original", "data-original-src", "data-zoom-src",
    "data-lazy-src", "data-src",
]

# ══════════════════════════════════════════════════════════════════════════
# RED DOT — 32 official categories + 8 super-category classifier
# ══════════════════════════════════════════════════════════════════════════

REDDOT_CATEGORIES = {
    "living-rooms-bedrooms": "客厅与卧室",
    "kitchen-household": "厨房与家居",
    "tableware-cooking": "餐具与烹饪",
    "bath-sanitary": "浴室与卫浴",
    "interior-design": "室内设计",
    "furniture": "家具",
    "lighting": "照明",
    "garden": "花园与户外",
    "heating-air-conditioning": "暖通空调",
    "consumer-electronics": "消费电子",
    "computers-information-technology": "计算机与信息技术",
    "smartphones-tablets": "智能手机与平板",
    "audio": "音频设备",
    "cameras": "相机与摄影",
    "wearables-fitness": "可穿戴与健身",
    "sports-outdoor": "运动与户外",
    "baby-child": "母婴与儿童",
    "fashion-accessories": "时尚与配饰",
    "watches-jewellery": "手表与珠宝",
    "medical-rehabilitation": "医疗与康复",
    "life-science": "生命科学",
    "tools": "工具",
    "industry-crafts-trade": "工业与手工艺",
    "automotive": "汽车",
    "bicycles-e-mobility": "自行车与电动出行",
    "urban-public-design": "城市与公共设计",
    "office": "办公用品",
    "communication-design": "传播设计",
    "packaging": "包装设计",
    "material-surface": "材料与表面",
    "technology": "技术与创新",
    "robots": "机器人",
}

# Keywords used to filter sitemap URLs for each category
REDDOT_CATEGORY_KEYWORDS = {
    "lighting":               ["light", "lamp", "luminaire", "luminaria", "leuchte", "licht",
                               "bulb", "lantern", "chandelier", "sconce", "pendant", "spotlight",
                               "downlight", "floodlight", "streetlight", "nightlight", "luminar",
                               "illumin", "fixture", "torch", "torchiere", "candle"],
    "furniture":              ["chair", "sofa", "table", "desk", "shelf", "cabinet", "bench",
                               "stool", "couch", "wardrobe", "dresser", "sideboard", "ottoman"],
    "automotive":             ["car", "vehicle", "auto", "drive", "electric-vehicle", "concept",
                               "sedan", "suv", "truck", "motorcycle", "cockpit", "interior"],
    "audio":                  ["speaker", "headphone", "earphone", "audio", "sound", "music",
                               "amplifier", "subwoofer", "earbuds", "headset"],
    "cameras":                ["camera", "lens", "photo", "tripod", "drone", "gimbal"],
    "smartphones-tablets":    ["phone", "smartphone", "tablet", "ipad", "mobile", "handset"],
    "computers-information-technology": ["laptop", "computer", "monitor", "keyboard", "mouse",
                                          "pc", "workstation", "notebook"],
    "wearables-fitness":      ["watch", "fitness", "tracker", "wearable", "band", "smartwatch",
                               "bracelet"],
    "watches-jewellery":      ["watch", "clock", "ring", "necklace", "jewel", "bracelet",
                               "timepiece"],
    "sports-outdoor":         ["sport", "bike", "ski", "helmet", "gym", "fitness", "running",
                               "outdoor", "camp", "hiking"],
    "baby-child":             ["baby", "child", "stroller", "pram", "toy", "kids", "infant",
                               "nursery"],
    "medical-rehabilitation": ["medical", "wheelchair", "prosthetic", "rehab", "health",
                               "hospital", "therapy", "clinical"],
    "tools":                  ["tool", "drill", "saw", "grinder", "wrench", "power-tool",
                               "screwdriver", "hammer"],
    "robots":                 ["robot", "drone", "automation", "autonomous", "ai", "cobot"],
    "packaging":              ["packaging", "package", "box", "container", "bottle", "bag"],
    "kitchen-household":      ["kitchen", "kettle", "blender", "toaster", "coffee", "cookware",
                               "appliance", "household"],
    "bath-sanitary":          ["bath", "shower", "toilet", "faucet", "sanitary", "washbasin",
                               "spa", "sauna"],
    "garden":                 ["garden", "outdoor", "patio", "grill", "barbecue", "planter",
                               "irrigation"],
}
# Fallback: use the category slug itself as keyword for unspecified categories
REDDOT_YEAR_START = 2020
REDDOT_YEAR_END = 2026

REDDOT_SUPER_CATEGORIES = {
    "家居生活": ["living-rooms-bedrooms", "kitchen-household", "tableware-cooking",
                 "bath-sanitary", "interior-design", "furniture", "lighting", "garden",
                 "heating-air-conditioning"],
    "数码科技": ["consumer-electronics", "computers-information-technology",
                 "smartphones-tablets", "audio", "cameras", "wearables-fitness",
                 "technology", "robots"],
    "出行交通": ["automotive", "bicycles-e-mobility"],
    "运动户外": ["sports-outdoor"],
    "母婴儿童": ["baby-child"],
    "时尚配饰": ["fashion-accessories", "watches-jewellery"],
    "医疗健康": ["medical-rehabilitation", "life-science"],
    "商业办公": ["tools", "industry-crafts-trade", "office", "urban-public-design",
                 "communication-design", "packaging", "material-surface"],
}
_REDDOT_SUB_TO_SUPER = {
    sub: sup for sup, subs in REDDOT_SUPER_CATEGORIES.items() for sub in subs
}


def log(msg):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


# ══════════════════════════════════════════════════════════════════════════
# UNIVERSAL HIGH-RES IMAGE HELPERS
# ══════════════════════════════════════════════════════════════════════════

def parse_srcset_largest(srcset_val):
    """Parse srcset attribute and return the URL of the largest image."""
    if not srcset_val:
        return None
    best_url, best_w = None, 0
    for part in srcset_val.split(","):
        parts = part.strip().split()
        if not parts:
            continue
        url = parts[0]
        w = 0
        if len(parts) > 1:
            desc = parts[1]
            if desc.endswith("w"):
                try:
                    w = int(desc[:-1])
                except ValueError:
                    pass
            elif desc.endswith("x"):
                try:
                    w = int(float(desc[:-1]) * 1000)
                except ValueError:
                    pass
        if w >= best_w:
            best_w, best_url = w, url
    return best_url


def _extract_bynder_original(url):
    """For Next.js image proxy URLs, extract the original bynder CDN source URL."""
    if "/_next/image?" not in url:
        return None
    m = re.search(r'[?&]url=([^&]+)', url)
    if m:
        from urllib.parse import unquote
        raw = unquote(m.group(1))
        # Remove /thumbnail/ path to get full-size original
        raw = re.sub(r'/thumbnail/[^/]+$', '', raw)
        if 'bynder' in raw or raw.startswith('http'):
            return raw
    return None


def try_url_upgrade(url):
    """Apply common URL patterns to find a higher-resolution version."""
    # Next.js image proxy: extract the original source URL (e.g. bynder CDN)
    if "/_next/image?" in url or "/_next/image/" in url:
        original = _extract_bynder_original(url)
        return original if original else url
    for pattern, replacement in URL_UPGRADE_PATTERNS:
        new = pattern.sub(replacement, url)
        if new != url:
            return new
    return url


def universal_extract_images(html, page_url, intercepted=None, skip_pattern=None):
    """
    Universal high-res image extractor. Works on any website.

    Priority order:
      1. og:image meta tag       — best single product shot
      2. srcset largest          — browser-standard multi-res
      3. data-zoom/data-large    — lightbox/gallery attributes
      4. Network intercepted     — sorted by file size (largest first)
      5. Regular <img> src       — with URL upgrade attempted

    All candidate URLs are automatically upgraded via URL_UPGRADE_PATTERNS.
    Noise (logos, icons, social) filtered by UNIVERSAL_SKIP.
    """
    seen = set()
    result = []   # list of (priority, url)

    def add(raw_url, priority):
        if not raw_url or raw_url.startswith("data:"):
            return
        abs_url = raw_url if raw_url.startswith("http") else urljoin(page_url, raw_url)
        upgraded = try_url_upgrade(abs_url)
        for u in ([upgraded] if upgraded != abs_url else []) + [abs_url]:
            if u not in seen:
                seen.add(u)
                result.append((priority, u))

    soup = BeautifulSoup(html, "html.parser")

    # 1. og:image
    for meta in soup.find_all("meta"):
        prop = meta.get("property", "") or meta.get("name", "")
        if "og:image" in prop:
            add(meta.get("content", ""), 1)

    # Alt-text noise: skip obvious non-product images
    _ALT_SKIP = re.compile(
        r"(logo|icon|banner|background|pattern|texture|decoration"
        r"|arrow|button|badge|award|seal|ribbon|cart|menu|close|search"
        r"|thumbnail\.?s?$|placeholder)",
        re.IGNORECASE,
    )

    # 2-3. <img> tags
    for tag in soup.find_all("img"):
        alt = tag.get("alt", "")
        if alt and _ALT_SKIP.search(alt):
            continue
        # srcset → pick largest
        srcset = tag.get("srcset", "")
        if srcset:
            best = parse_srcset_largest(srcset)
            if best:
                add(best if best.startswith("http") else urljoin(page_url, best), 2)

        # data-* hires attributes
        for attr in HIRES_DATA_ATTRS:
            val = tag.get(attr, "")
            if val and not val.startswith("data:"):
                add(val if val.startswith("http") else urljoin(page_url, val), 3)

        # regular src
        src = tag.get("src", "")
        if src:
            add(src if src.startswith("http") else urljoin(page_url, src), 5)

    # 4. Network-intercepted images (sorted by content-length, largest first)
    if intercepted:
        for img_url, cl in sorted(intercepted.items(), key=lambda x: -x[1]):
            add(img_url, 4)

    # Sort by priority, apply skip filters, return
    result.sort(key=lambda x: x[0])
    final = []
    seen_final = set()
    for _, url in result:
        if url in seen_final:
            continue
        seen_final.add(url)
        if UNIVERSAL_SKIP.search(url):
            continue
        if skip_pattern and skip_pattern.search(url):
            continue
        final.append(url)

    return final


def render_page_intercept(url, timeout, headless):
    """Render page with Playwright, capturing all image network responses."""
    from playwright.sync_api import sync_playwright
    intercepted = {}   # url → content-length in bytes

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(extra_http_headers=HEADERS)

        def on_response(response):
            ct = response.headers.get("content-type", "")
            if "image" in ct:
                try:
                    cl = int(response.headers.get("content-length", 0))
                except ValueError:
                    cl = 0
                intercepted[response.url] = cl

        page.on("response", on_response)

        try:
            page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
        except Exception:
            try:
                page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)
            except Exception:
                pass

        # Scroll to trigger lazy-load images
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
        except Exception:
            pass

        html = page.content()
        browser.close()

    return html, intercepted


def render_pages_batch(urls, timeout, headless, callback, delay=1.5):
    """
    Render multiple pages using ONE browser instance (much faster than render_page_intercept per page).

    Args:
        urls: list of URLs to visit
        timeout: page load timeout in seconds
        headless: run headless
        callback: function(url, html, intercepted) called for each page
        delay: seconds between page loads (anti-bot)
    """
    from playwright.sync_api import sync_playwright
    import random

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(extra_http_headers=HEADERS)
        page = context.new_page()

        for i, url in enumerate(urls):
            intercepted = {}

            def on_response(response):
                ct = response.headers.get("content-type", "")
                if "image" in ct:
                    try:
                        cl = int(response.headers.get("content-length", 0))
                    except ValueError:
                        cl = 0
                    intercepted[response.url] = cl

            page.on("response", on_response)

            try:
                page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
            except Exception:
                try:
                    page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
                except Exception:
                    page.remove_listener("response", on_response)
                    continue

            html = page.content()
            page.remove_listener("response", on_response)

            try:
                callback(url, html, intercepted)
            except Exception as e:
                log(f"    [callback错误] {url}: {e}")

            # Anti-bot delay
            time.sleep(random.uniform(delay * 0.5, delay * 1.5))

            # Progress
            if (i + 1) % 50 == 0:
                log(f"  [进度] {i+1}/{len(urls)} 页面完成")

        browser.close()


def extract_product_name(html, site="rab"):
    """Extract a clean human-readable product name from page HTML."""
    soup = BeautifulSoup(html, "html.parser")

    if site == "rab":
        # RAB page title format: "X34 LED Field Adjustable Floodlight | RAB Lighting"
        title_tag = soup.find("title")
        if title_tag:
            raw = title_tag.get_text(strip=True)
            # Strip site suffix: "XL22 Floodlight | RAB Lighting" or "XL22 Floodlight - RAB Lighting"
            text = re.split(r"\s*[|\-]\s*RAB", raw)[0].strip()
            if not text:
                text = re.split(r"[|]", raw)[0].strip()
            if text and len(text) < 80:
                return text
        # Fallback: <h2> often has the model name on RAB feature pages
        for tag in soup.find_all(["h2", "h3"]):
            text = tag.get_text(strip=True)
            # Look for something that starts with a model code (letters+digits)
            if text and re.match(r"^[A-Z]{1,5}[\d]", text):
                return text

    elif site == "reddot":
        # Red Dot project pages: <h1> contains the clean product name
        h1 = soup.find("h1")
        if h1:
            name = h1.get_text(strip=True)
            if name and len(name) < 100:
                return name
        # Fallback: <title> before " | " or " - "
        title_tag = soup.find("title")
        if title_tag:
            text = re.split(r"[|\-]", title_tag.get_text(strip=True))[0].strip()
            if text:
                return text

    return None


def name_to_folder(name):
    """Convert product name to a clean folder name: 'X34® LED Floodlight' → 'X34_LED_Floodlight'"""
    # Replace special chars (®, ™, etc.) with space to avoid words merging
    name = re.sub(r"[^\w\s\-]", " ", name).strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name[:80]


def name_to_prefix(name):
    """Convert product name to image filename prefix."""
    return name_to_folder(name)


def extract_model_code(product_name):
    """
    Extract the short model code from a full product name.
    'NEOFLEX Tape Light'  → 'NEOFLEX'
    'MASI® Canopy Light'  → 'MASI'
    'T17 Field Adjustable'→ 'T17'
    'CR4'                 → 'CR4'
    Falls back to full cleaned name if no model code found.
    """
    # Remove special chars like ®, ™
    cleaned = re.sub(r"[^\w\s\-]", " ", product_name).strip()
    # First token that is all-caps (with optional digits/hyphens)
    m = re.match(r"^([A-Z][A-Z0-9\-]+)", cleaned)
    if m:
        return m.group(1).strip("-")
    return name_to_folder(cleaned)


# ── Browser helpers ────────────────────────────────────────────────────────

def render_page(url, timeout, headless, wait_for_selector=None):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(extra_http_headers=HEADERS)
        try:
            if wait_for_selector:
                # For JS-heavy pages: load DOM then wait for target element
                page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
                try:
                    page.wait_for_selector(wait_for_selector, timeout=20000)
                except Exception:
                    page.wait_for_timeout(8000)
            else:
                # Standard pages: try networkidle, fallback to domcontentloaded
                try:
                    page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
                except Exception:
                    page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
        except Exception:
            pass
        html = page.content()
        browser.close()
    return html


def render_and_download(url, dest, timeout, headless):
    """Use browser session to download a token-authenticated image."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(extra_http_headers=HEADERS)
        page = context.new_page()
        try:
            resp = page.goto(url, timeout=timeout * 1000)
            if resp and resp.status == 200:
                body = resp.body()
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "wb") as f:
                    f.write(body)
                browser.close()
                return True
        except Exception:
            pass
        browser.close()
    return False


# ── Download helper ────────────────────────────────────────────────────────

def download_image(img_url, dest, session, retries=3, backoff=2.0):
    for attempt in range(retries):
        try:
            resp = session.get(img_url, timeout=20, stream=True, verify=False)
            if resp.status_code == 429:
                wait = backoff ** (attempt + 1) * 5
                log(f"    [429] 限速，等待 {wait:.0f}s 后重试 ({attempt+1}/{retries})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(backoff ** attempt)
            else:
                log(f"    [X] {dest.name}: {e}")
    return False


def is_valid_image(path, min_px=600, max_white=0.98, max_ratio=3.5):
    """Return False for images that are too small, nearly blank/white, or banner-shaped."""
    try:
        from PIL import Image
        img = Image.open(path).convert("RGB")
        w, h = img.size
        if max(w, h) < min_px:  # Allow elongated images (tape lights, strip lights, etc.)
            return False
        # Both dimensions must be reasonable — skip ultra-wide banners
        if h > 0 and (w / h) > max_ratio:
            return False
        # Both dimensions must be reasonable — skip ultra-tall narrow banners
        if w > 0 and (h / w) > max_ratio:
            return False
        # Require minimum size on the short side (filters thumbnail icons that are tall)
        if min(w, h) < 200:
            return False
        pixels = list(img.getdata())
        white = sum(1 for r, g, b in pixels if r > 240 and g > 240 and b > 240)
        if white / len(pixels) > max_white:
            return False
        return True
    except Exception:
        return False  # PIL not available or unreadable — reject the file


def convert_webp_to_jpg(path):
    """Convert any non-JPEG image (png/webp/avif/etc.) to jpg. Returns new path (or original if already jpg)."""
    p = Path(path)
    if p.suffix.lower() in ('.jpg', '.jpeg'):
        return path
    try:
        from PIL import Image
        img = Image.open(p).convert("RGB")
        new_path = p.with_suffix('.jpg')
        img.save(new_path, "JPEG", quality=95)
        p.unlink()  # remove original
        return new_path
    except Exception:
        return path


def is_product_shot(path, edge_margin=0.05):
    """
    Heuristic to detect product shot (clean background) vs lifestyle/banner.

    Strategy: sample the 4 corners of the image. If at least 2 corners are
    uniformly-colored (low internal variance), it's likely a product shot.
    This works for white, black, grey, or any solid-color backgrounds.
    """
    try:
        from PIL import Image
        import statistics
        img = Image.open(path).convert("RGB")
        w, h = img.size
        cw = max(5, int(w * edge_margin))
        ch = max(5, int(h * edge_margin))

        # Sample 4 corner regions
        corners = [
            img.crop((0, 0, cw, ch)),            # top-left
            img.crop((w - cw, 0, w, ch)),         # top-right
            img.crop((0, h - ch, cw, h)),         # bottom-left
            img.crop((w - cw, h - ch, w, h)),     # bottom-right
        ]

        uniform_corners = 0
        for corner in corners:
            pixels = list(corner.getdata())
            if len(pixels) < 5:
                continue
            r_std = statistics.pstdev([p[0] for p in pixels])
            g_std = statistics.pstdev([p[1] for p in pixels])
            b_std = statistics.pstdev([p[2] for p in pixels])
            avg_std = (r_std + g_std + b_std) / 3
            if avg_std < 30:  # this corner is uniformly colored
                uniform_corners += 1

        # Product shot: at least 2 of 4 corners are uniform
        return uniform_corners >= 2
    except Exception:
        return True  # cannot analyse → keep by default


def safe_filename(url, index):
    path = urlparse(url).path
    name = unquote(Path(path).name)
    name = re.sub(r"[^\w.\-]", "_", name)
    if not name or name == "_":
        name = f"image_{index}"
    if "." not in name:
        name += ".jpg"
    return name[:120]


# ══════════════════════════════════════════════════════════════════════════
# CATEGORY EXTRACTION (A+B combined)
# ══════════════════════════════════════════════════════════════════════════

# Words to drop from category paths (noise)
_CAT_SKIP = re.compile(
    r"^(home|homepage|index|main|all|products?|shop|store|catalog|catalogue|page|www|\d+)$",
    re.IGNORECASE,
)


def _clean_cat_part(s):
    """Clean a single category string into a folder-safe token."""
    s = re.sub(r"[^\w\s\-]", " ", s).strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:40]


def extract_breadcrumbs(html, page_url):
    """
    Extract category breadcrumb from a product page.
    Returns a list of category strings, e.g. ['Indoor', 'Commercial_Downlights'].

    Priority:
      1. JSON-LD BreadcrumbList schema  (most reliable)
      2. Microdata schema.org/BreadcrumbList
      3. HTML <nav> / <ol class="breadcrumb"> elements
      4. URL path segments as fallback
    """
    soup = BeautifulSoup(html, "html.parser")

    def _filter(crumbs):
        """Remove home/brand/product-name noise, return up to 3 middle items."""
        cleaned = []
        for c in crumbs:
            c = c.strip()
            if not c or _CAT_SKIP.match(c):
                continue
            cleaned.append(_clean_cat_part(c))
        return cleaned[:3]

    # ── 1. JSON-LD BreadcrumbList ──────────────────────────────────────────
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            raw = script.string or ""
            data = json.loads(raw)
            # data may be a single object or a list
            nodes = data if isinstance(data, list) else [data]
            # Also handle @graph
            graph_nodes = []
            for n in nodes:
                if isinstance(n, dict) and "@graph" in n:
                    graph_nodes.extend(n["@graph"])
            nodes = nodes + graph_nodes
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                if node.get("@type") in ("BreadcrumbList", "http://schema.org/BreadcrumbList"):
                    items = node.get("itemListElement", [])
                    names = [
                        (item.get("item", {}) or {}).get("name") or item.get("name", "")
                        for item in items
                    ]
                    # Drop first (home) and last (product name)
                    mid = _filter(names[1:-1]) if len(names) > 2 else _filter(names[:-1])
                    if mid:
                        return mid
        except Exception:
            pass

    # ── 2. Microdata ──────────────────────────────────────────────────────
    bc_el = soup.find(attrs={"itemtype": re.compile(r"BreadcrumbList", re.I)})
    if bc_el:
        items = bc_el.find_all(attrs={"itemprop": "name"})
        names = [i.get_text(strip=True) for i in items]
        mid = _filter(names[1:-1]) if len(names) > 2 else _filter(names[:-1])
        if mid:
            return mid

    # ── 3. HTML breadcrumb elements ───────────────────────────────────────
    for sel in [
        'nav[aria-label*="breadcrumb" i] a',
        'ol.breadcrumb a', 'ul.breadcrumb a',
        '[class*="breadcrumb" i] a',
        '[class*="Breadcrumb"] a',
        'nav.breadcrumb a',
    ]:
        links = soup.select(sel)
        if links:
            names = [a.get_text(strip=True) for a in links]
            # RAB (and some sites) renders breadcrumb twice (desktop+mobile).
            # Deduplicate by taking only the first unique sequence.
            half = len(names) // 2
            if half >= 2 and names[:half] == names[half:]:
                names = names[:half]
            mid = _filter(names[1:-1]) if len(names) > 2 else _filter(names[:-1])
            if mid:
                return mid

    # ── 4. URL path fallback ──────────────────────────────────────────────
    path_parts = urlparse(page_url).path.strip("/").split("/")
    # Remove last segment (product slug) and clean
    candidates = [p.replace("-", " ").replace("_", " ").title() for p in path_parts[:-1]]
    return _filter(candidates)


def _dedup_cats(cats):
    """Remove consecutive duplicate category entries."""
    result = []
    for c in cats:
        if not result or c.lower() != result[-1].lower():
            result.append(c)
    return result


def build_category_folder(crumbs, nav_category=None):
    """
    Build category folder path (WITHOUT product name).
    Structure: Primary_Category / Sub_Category  (max 2 levels)
    e.g. Outdoor/Flexible_Linear  or  Indoor/Tape_Lighting
    """
    cats = _dedup_cats(crumbs[:3]) if crumbs else []
    cats = cats[:2]
    if not cats and nav_category:
        parts = [_clean_cat_part(p) for p in nav_category.replace("/", "_").split("_") if p]
        cats = _dedup_cats([p for p in parts if not _CAT_SKIP.match(p)])[:2]
    if not cats:
        cats = ["Uncategorized"]
    return Path(*cats)


def build_image_prefix(model_code):
    """
    Image filename prefix = just the model code.
    e.g. NEOFLEX_01.jpg  /  MASI_01.jpg
    The folder path already contains the category — no need to repeat it.
    """
    return model_code[:60]


# ══════════════════════════════════════════════════════════════════════════
# RAB LIGHTING
# ══════════════════════════════════════════════════════════════════════════

def rab_find_feature_links(html, base_url):
    """Find /feature/ product page links on a RAB category listing page."""
    soup = BeautifulSoup(html, "html.parser")
    base_netloc = urlparse(base_url).netloc
    links = {}
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "/feature/" not in href:
            continue
        abs_url = href if href.startswith("http") else urljoin(base_url, href)
        if urlparse(abs_url).netloc not in (base_netloc, "www." + base_netloc, base_netloc.replace("www.", "")):
            continue
        name = urlparse(abs_url).path.rstrip("/").split("/")[-1]
        if name and abs_url not in seen and not RAB_SKIP_PAGES.search(name):
            seen.add(abs_url)
            links[name] = abs_url
    return links


def rab_extract_product_images(html, page_url):
    """
    Extract ONLY product body images from a RAB feature page.
    Targets /images/product/photo/ URLs exclusively and upgrades each to largePhoto (900x900).
    Avoids the accessory/badge bleed that universal_extract_images can produce.
    RAB_SKIP is still applied as a final filter to catch accessory SKUs in that path.
    """
    base = "https://" + urlparse(page_url).netloc
    seen = set()
    result = []
    # Match filenames only — exclude template placeholders like {{image}}
    for fname in re.findall(r'/images/product/photo/([^"\'<>\s{}]+\.(?:jpg|jpeg|png|webp))', html, re.I):
        large_url = f"{base}/images/product/largePhoto/{fname}"
        if large_url not in seen and not RAB_SKIP.search(large_url):
            seen.add(large_url)
            result.append(large_url)
    return result


def scrape_rab(cat_url, cat_name, download_root, limit, timeout, headless, session):
    log(f"\n{'='*60}")
    log(f"[RAB 分类] {cat_name}  ->  {cat_url}")
    html = render_page(cat_url, timeout, headless)
    feature_links = rab_find_feature_links(html, cat_url)
    log(f"  发现 {len(feature_links)} 个产品页，抓取前 {min(limit, len(feature_links))} 个")

    # Build category hierarchy from cat_url path as breadcrumb fallback.
    # e.g. "https://rablighting.com/indoor/COMMERCIAL_DOWNLIGHTS"
    #   → ["Indoor", "Commercial_Downlights"]
    cat_path_parts = [p for p in urlparse(cat_url).path.strip("/").split("/") if p]
    url_crumbs = [_clean_cat_part(p.replace("_", " ").title()) for p in cat_path_parts]
    url_crumbs = [c for c in url_crumbs if c and not _CAT_SKIP.match(c)][:2]

    results = []
    for i, (slug, prod_url) in enumerate(list(feature_links.items())[:limit]):
        log(f"  [{i+1}/{min(limit, len(feature_links))}] {slug}")
        try:
            prod_html = render_page(prod_url, timeout, headless)

            real_name = extract_product_name(prod_html, "rab") or slug
            model_code = extract_model_code(real_name)
            log(f"    产品: {real_name}  →  型号: {model_code}")

            # Breadcrumb first; if missing or only 1 level, fall back to URL-derived hierarchy
            crumbs = extract_breadcrumbs(prod_html, prod_url)
            if not crumbs or len(crumbs) < 2:
                crumbs = url_crumbs or crumbs
            log(f"    分类: {crumbs}")

            cat_folder = build_category_folder(crumbs, nav_category=cat_name)
            prefix = build_image_prefix(model_code)

            # Use targeted extractor: only /images/product/largePhoto/ URLs (900×900 product shots)
            images = rab_extract_product_images(prod_html, prod_url)
            log(f"    找到 {len(images)} 张产品图")

            if download_root:
                folder = Path(download_root) / cat_folder / model_code
                folder.mkdir(parents=True, exist_ok=True)
                ok = 0
                for j, img_url in enumerate(images):
                    ext = Path(urlparse(img_url).path).suffix or ".png"
                    fname = f"{prefix}_{j+1:02d}{ext}"
                    dest = folder / fname
                    if download_image(img_url, dest, session):
                        if is_valid_image(dest):
                            ok += 1
                            log(f"    [OK] {fname}")
                        else:
                            dest.unlink(missing_ok=True)
                            log(f"    [过滤] {fname}")
                log(f"    下载 {ok}/{len(images)} 张 -> {folder}")
            results.append({"product": real_name, "url": prod_url, "images": images,
                            "category": crumbs or [cat_name]})
        except Exception as e:
            log(f"    [跳过] {e}")
        time.sleep(1)
    return results


# ══════════════════════════════════════════════════════════════════════════
# RED DOT DESIGN AWARD
# ══════════════════════════════════════════════════════════════════════════

def reddot_find_project_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    links = {}
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "/project/" not in href:
            continue
        abs_url = href if href.startswith("http") else urljoin(base_url, href)
        name = urlparse(abs_url).path.rstrip("/").split("/")[-1]
        if name and abs_url not in seen:
            seen.add(abs_url)
            text = a.get_text(strip=True) or name
            links[name] = {"url": abs_url, "title": text}
    return links


def _extract_jsonld_images(data):
    """Recursively extract image URLs from JSON-LD structured data."""
    urls = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key in ("image", "photo", "thumbnail"):
                if isinstance(value, str) and value.startswith("http"):
                    urls.append(value)
                elif isinstance(value, list):
                    for v in value:
                        if isinstance(v, str) and v.startswith("http"):
                            urls.append(v)
                        elif isinstance(v, dict) and "url" in v:
                            urls.append(v["url"])
            elif isinstance(value, (dict, list)):
                urls.extend(_extract_jsonld_images(value))
    elif isinstance(data, list):
        for item in data:
            urls.extend(_extract_jsonld_images(item))
    return urls


def reddot_extract_images(html, page_url):
    """
    Priority:
    1. Slider images via index.php?eID=tx_solr_image&size=large (1900px)
    2. fileadmin/user_upload/ originals (1710–3500px)
    3. JSON-LD structured data (schema.org image fields)

    _processed_ images are intentionally excluded: they are low-res (1240px)
    thumbnails that appear throughout the page including the "related projects"
    section at the bottom, pulling in images from completely unrelated products.
    """
    base = "https://" + urlparse(page_url).netloc
    seen = set()
    slider_imgs = []
    upload_imgs = []

    # Slider images (highest quality, token-based)
    for m in re.finditer(r'(https?://[^\s"\'<>]*index\.php\?[^\s"\'<>]*eID=tx_solr_image[^\s"\'<>]*size=large[^\s"\'<>]*)', html):
        url = m.group(1).replace("&amp;", "&")
        if url not in seen:
            seen.add(url)
            slider_imgs.append(url)

    # User upload originals
    for path in re.findall(r'["\'](/fileadmin/user_upload/[^"\'<>\s]+\.(?:jpg|jpeg|png|webp))["\']', html):
        url = base + path
        if url not in seen and not REDDOT_SKIP.search(path):
            seen.add(url)
            upload_imgs.append(url)

    # JSON-LD structured data (schema.org)
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                         html, re.DOTALL | re.IGNORECASE):
        try:
            data = json.loads(m.group(1))
            for img_url in _extract_jsonld_images(data):
                if img_url not in seen and not REDDOT_SKIP.search(img_url):
                    seen.add(img_url)
                    upload_imgs.append(img_url)
        except Exception:
            pass

    return slider_imgs + upload_imgs


def scrape_reddot(search_url, topic_name, download_root, limit, timeout, headless, session):
    log(f"\n{'='*60}")
    log(f"[Red Dot] {topic_name}  ->  {search_url}")
    html = render_page(search_url, timeout, headless, wait_for_selector='a[href*="/project/"]')
    projects = reddot_find_project_links(html, search_url)
    log(f"  发现 {len(projects)} 个作品，抓取前 {min(limit, len(projects))} 个")

    results = []
    seen_img_urls = set()  # Global dedup: skip images already saved by a previous project
    for i, (slug, proj_info) in enumerate(list(projects.items())[:limit]):
        proj_url = proj_info["url"]
        log(f"  [{i+1}/{min(limit, len(projects))}] {slug}")
        try:
            proj_html = render_page(proj_url, timeout, headless)

            real_name = extract_product_name(proj_html, "reddot") or slug
            model_code = extract_model_code(real_name)
            log(f"    产品: {real_name}  →  型号: {model_code}")

            crumbs = extract_breadcrumbs(proj_html, proj_url)
            log(f"    分类: {crumbs or topic_name}")

            cat_folder = build_category_folder(crumbs, nav_category=topic_name)
            prefix = build_image_prefix(model_code)

            raw_images = reddot_extract_images(proj_html, proj_url)
            images = [u for u in raw_images if u not in seen_img_urls]
            seen_img_urls.update(images)
            skipped = len(raw_images) - len(images)
            log(f"    找到 {len(images)} 张图" + (f"（跳过 {skipped} 张跨项目重复）" if skipped else ""))

            if download_root:
                folder = Path(download_root) / cat_folder / model_code
                folder.mkdir(parents=True, exist_ok=True)
                ok = 0
                for j, img_url in enumerate(images):
                    ext = ".jpg"
                    fname = f"{prefix}_{j+1:02d}{ext}"
                    dest = folder / fname
                    if "eID=tx_solr_image" in img_url:
                        if render_and_download(img_url, dest, timeout, headless):
                            ok += 1
                            log(f"    [OK] {fname} (1900px)")
                        else:
                            log(f"    [X]  {fname}")
                    else:
                        if download_image(img_url, dest, session):
                            ok += 1
                            log(f"    [OK] {fname}")
                log(f"    下载 {ok}/{len(images)} 张 -> {folder}")

            results.append({"product": real_name, "url": proj_url, "images": images,
                            "category": crumbs or [topic_name]})
        except Exception as e:
            log(f"    [跳过] {e}")
        time.sleep(1)
    return results


# ══════════════════════════════════════════════════════════════════════════
# iF DESIGN AWARD
# ══════════════════════════════════════════════════════════════════════════

IF_SKIP_PAGES = re.compile(
    r"(winner-overview|jury|profile|search|tag|magazine)",
    re.IGNORECASE,
)


def ifdesign_find_project_links(html, base_url):
    """Find /winner-ranking/project/ links on an iF Design Award category page."""
    soup = BeautifulSoup(html, "html.parser")
    links = {}
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "/winner-ranking/project/" not in href:
            continue
        abs_url = href if href.startswith("http") else urljoin(base_url, href)
        if abs_url in seen or IF_SKIP_PAGES.search(href):
            continue
        seen.add(abs_url)
        # key = slug-id  e.g. "via-lactea-chandelier-737549"
        parts = urlparse(abs_url).path.rstrip("/").split("/")
        entry_id = parts[-1] if parts[-1].isdigit() else ""
        slug = parts[-2] if entry_id else parts[-1]
        key = f"{slug}-{entry_id}" if entry_id else slug
        links[key] = abs_url
    return links


def ifdesign_extract_images(html, page_url, intercepted=None, max_images=2):
    """
    Extract product images from an iF Design Award project page.
    Images are on Azure Blob Storage (ifdalivestorage.blob.core.windows.net).

    V4.1 upgrade: now takes up to max_images (default 2) to match Red Dot quality.
    Originals preferred over mid-size. Scene/application shots filtered by heuristic.
    """
    seen = set()
    originals = []
    midsize = []

    def _add(url):
        if not url or url in seen or "ifdalivestorage" not in url:
            return
        seen.add(url)
        if "/mid-size/" in url:
            midsize.append(url)
        else:
            originals.append(url)

    # 1. HTML img tags in gallery order — hero product shot comes first
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img", src=True):
        _add(img["src"])

    # 2. Intercepted as supplemental fallback for any images not in HTML
    if intercepted:
        for img_url in intercepted:
            _add(img_url)

    # Take up to max_images originals (product shots first in gallery order)
    if originals:
        return originals[:max_images]
    return midsize[:max_images]


def scrape_ifdesign(cat_url, cat_name, download_root, limit, timeout, headless, session):
    log(f"\n{'='*60}")
    log(f"[iF Design] {cat_name}  ->  {cat_url}")
    # iF Design uses React/JS rendering — needs extra time after networkidle
    from playwright.sync_api import sync_playwright
    with sync_playwright() as _p:
        _browser = _p.chromium.launch(headless=headless)
        _page = _browser.new_page(extra_http_headers=HEADERS)
        try:
            _page.goto(cat_url, timeout=timeout * 1000, wait_until="networkidle")
        except Exception:
            _page.goto(cat_url, timeout=timeout * 1000, wait_until="domcontentloaded")
        _page.wait_for_timeout(4000)  # Allow React hydration + API fetch
        html = _page.content()
        _browser.close()
    project_links = ifdesign_find_project_links(html, cat_url)
    log(f"  发现 {len(project_links)} 个作品，抓取前 {min(limit, len(project_links))} 个")

    results = []
    seen_img_urls = set()  # Global dedup across projects
    for i, (slug, prod_url) in enumerate(list(project_links.items())[:limit]):
        log(f"  [{i+1}/{min(limit, len(project_links))}] {slug}")
        try:
            prod_html, intercepted = render_page_intercept(prod_url, timeout, headless)

            real_name = extract_product_name(prod_html, "reddot") or slug
            model_code = extract_model_code(real_name)
            log(f"    产品: {real_name}  →  型号: {model_code}")

            raw_images = ifdesign_extract_images(prod_html, prod_url, intercepted=intercepted)
            images = [u for u in raw_images if u not in seen_img_urls]
            seen_img_urls.update(images)
            skipped = len(raw_images) - len(images)
            log(f"    找到 {len(images)} 张图" + (f"（跳过 {skipped} 张重复）" if skipped else ""))

            if download_root and images:
                folder = Path(download_root) / model_code
                folder.mkdir(parents=True, exist_ok=True)
                ok = 0
                for j, img_url in enumerate(images):
                    ext = Path(urlparse(img_url).path).suffix.lower() or ".jpg"
                    if ext not in _IMG_EXTS:
                        ext = ".jpg"
                    fname = f"{j+1:02d}{ext}"
                    dest = folder / fname
                    if download_image(img_url, dest, session):
                        if is_valid_image(dest):
                            ok += 1
                            log(f"    [OK] {fname}")
                        else:
                            dest.unlink(missing_ok=True)
                            log(f"    [过滤] {fname}")
                log(f"    下载 {ok}/{len(images)} 张 -> {folder}")

            results.append({"product": real_name, "url": prod_url, "images": images,
                            "category": [cat_name]})
        except Exception as e:
            log(f"    [跳过] {e}")
        time.sleep(1)
    return results


# ══════════════════════════════════════════════════════════════════════════
# iF Design REST API scraper (bypasses Vue SPA rendering issues)
# ══════════════════════════════════════════════════════════════════════════

IF_API_BASE = "https://ifdesign.com/api/search/entry"
IF_AWARD_IDS = [2]  # Only iF DESIGN AWARD (main award); TALENT AWARD/SOCIAL PROJECTS use different category schemas

# Map iF Design designation text → Chinese lamp-type subfolder name
_IF_LAMP_TYPE_MAP = [
    (["pendant", "chandelier", "hanging", "suspension"], "吊灯"),
    (["wall", "sconce", "wall luminaire", "wall washer", "wall light"], "壁灯"),
    (["floor lamp", "floor light", "standing lamp", "torchiere", "uplight"], "落地灯"),
    (["ceiling", "downlight", "recessed", "flush mount", "overhead", "panel light"], "吸顶灯"),
    (["desk lamp", "table lamp", "study lamp", "reading lamp", "bedside"], "台灯"),
    (["spotlight", "track", "accent light", "directed"], "射灯"),
    (["outdoor", "bollard", "street", "floodlight", "garden", "landscape", "exterior", "facade"], "户外灯"),
    (["portable", "flashlight", "torch", "lantern", "camping", "emergency"], "便携灯"),
    (["strip", "linear", "tape", "ribbon", "neon"], "灯带"),
]

def _if_lamp_type(designation: str, product_name: str = "") -> str:
    """Map a product designation + name to a Chinese lamp-type folder name.
    V4.1: now uses both designation AND product name for classification,
    matching Red Dot's _classify_all_lighting() approach.
    """
    d = ((designation or "") + " " + (product_name or "")).lower()
    for keywords, folder in _IF_LAMP_TYPE_MAP:
        if any(kw in d for kw in keywords):
            return folder
    return "其他灯具"


# ── iF Design product verification (matches Red Dot's _verify_lighting) ──

_IF_NOT_FIXTURE_PATTERNS = [
    "vehicle", "car ", "automotive", "headlight", "taillight", "bike light",
    "camera", "webcam", "projector", "monitor", "display", "screen",
    "software", "app ", "interface", "packaging", "branding",
    "furniture", "chair", "table ", "desk ", "shelf", "cabinet",
    "kitchen", "oven", "fridge", "washing", "vacuum", "robot",
    "phone", "tablet", "laptop", "headphone", "speaker", "earbud",
    "watch", "wearable", "medical", "surgical", "dental",
]

def _verify_if_lighting(designation: str, product_name: str) -> tuple:
    """Check if an iF Design entry is an actual lighting fixture.
    Returns (True, '') to accept or (False, 'reason') to skip.
    Mirrors Red Dot's _verify_lighting() logic.
    """
    combined = ((designation or "") + " " + (product_name or "")).lower()

    # Hard reject: explicit non-fixture patterns
    for pattern in _IF_NOT_FIXTURE_PATTERNS:
        if pattern in combined:
            return False, f"非灯具产品（含'{pattern}'）"

    # Accept: designation contains lighting-related keywords
    if any(kw in combined for kws, _ in _IF_LAMP_TYPE_MAP for kw in kws):
        return True, ""

    # Accept: generic lighting keywords
    _generic_light_kws = ["light", "lamp", "luminaire", "luminaria", "leuchte",
                          "illumin", "candle", "fixture", "luminary", "lumen"]
    if any(kw in combined for kw in _generic_light_kws):
        return True, ""

    return False, "无法确认为灯具产品"

def scrape_ifdesign_api(category_id, cat_name, download_root, limit, timeout, session):
    """Scrape iF Design winners using the REST API.
    V4.1 upgrade: verification filter + richer classification + 2 images per product.
    """
    log(f"\n{'='*60}")
    log(f"[iF Design API] category={category_id} ({cat_name})")
    api_headers = {
        "Content-Type": "application/json",
        "Origin": "https://ifdesign.com",
        "Referer": "https://ifdesign.com/en/winner-ranking/winner-overview/",
    }
    all_items = []
    for award_id in IF_AWARD_IDS:
        offset = 0
        batch = 100
        while True:
            payload = {
                "award": award_id, "countries": [], "range": 5, "seed": "",
                "count": batch, "find": "", "disciplines": [],
                "categories": [category_id],
                "isGoldAward": False, "isBestOfYear": False,
                "isSupportedByIF": False, "profileId": 0,
            }
            try:
                resp = session.post(
                    f"{IF_API_BASE}/{offset}/{batch}?order=random&language=en",
                    headers=api_headers, json=payload, timeout=timeout
                )
                data = resp.json()
            except Exception as e:
                log(f"  [API error award={award_id} offset={offset}] {e}")
                break
            items = data.get("items", [])
            total = data.get("count", 0)
            log(f"  Award {award_id}: {offset}+{len(items)}/{total}")
            all_items.extend(items)
            offset += len(items)
            if offset >= total or not items:
                break
    log(f"  共 {len(all_items)} 条，下载前 {min(limit, len(all_items))} 条")
    results = []
    seen_imgs: set = set()
    skipped_verify = 0
    max_per_product = getattr(session, '_max_per_product', 2)
    for i, item in enumerate(all_items[:limit]):
        slug = item.get("slug", "")
        if not slug:
            continue
        parts = slug.rstrip("/").split("/")
        prod_name = parts[-2] if len(parts) >= 2 else parts[-1]
        display_name = item.get("name") or prod_name
        designation = item.get("designation") or ""

        # V4.1: Verify this is actually a lighting fixture (like Red Dot's _verify_lighting)
        ok, reason = _verify_if_lighting(designation, display_name)
        if not ok:
            skipped_verify += 1
            if skipped_verify <= 5:  # Only log first 5 skips to avoid spam
                log(f"  [跳过] {display_name} — {reason}")
            continue

        # V4.1: Use both designation AND product name for richer classification
        lamp_type = _if_lamp_type(designation, display_name)

        # V4.1: Detect award level (Gold / standard winner)
        is_gold = item.get("isGoldAward", False)
        award_level = "gold" if is_gold else "winner"

        proj_url = "https://ifdesign.com/en" + slug
        log(f"  [{i+1}/{min(limit, len(all_items))}] {display_name} [{lamp_type}] [{award_level}] ({designation})")

        # Collect images from API response
        imgs = []
        for key in ("primaryMedia", "secondaryMedia"):
            url = item.get(key)
            if url and url not in seen_imgs and "ifdalivestorage" in url:
                seen_imgs.add(url)
                imgs.append(url)

        # V4.1: Limit per product (default 2, matching Red Dot)
        imgs = imgs[:max_per_product]

        if not imgs:
            continue
        model_code = extract_model_code(display_name)
        if download_root and imgs:
            folder = Path(download_root) / lamp_type / model_code
            folder.mkdir(parents=True, exist_ok=True)
            ok_count = 0
            for j, img_url in enumerate(imgs):
                ext = Path(urlparse(img_url).path).suffix.lower() or ".jpg"
                if ext not in _IMG_EXTS:
                    ext = ".jpg"
                dest = folder / f"{j+1:02d}{ext}"
                if download_image(img_url, dest, session):
                    ok_count += 1
                    log(f"    [OK] {dest.name}")
            log(f"    下载 {ok_count}/{len(imgs)} 张 -> {folder}")
        results.append({"product": display_name, "url": proj_url,
                        "images": imgs, "category": [cat_name, lamp_type],
                        "designation": designation, "award_level": award_level})
    if skipped_verify > 5:
        log(f"  （另有 {skipped_verify - 5} 个非灯具产品被跳过）")
    log(f"  最终结果: {len(results)} 个灯具产品")
    return results


# ══════════════════════════════════════════════════════════════════════════
# Red Dot sitemap-based scraper (bypasses Vue SPA rendering issues)
# ══════════════════════════════════════════════════════════════════════════

REDDOT_SITEMAP_BASE = "https://www.red-dot.org/sitemap.xml"
REDDOT_SITEMAP_CHASH = "5076c78547ddcde5d47b73c8c9898f49"
REDDOT_SITEMAP_PAGES = 42
REDDOT_LIGHTING_KWS = [
    "light", "lamp", "luminaire", "luminaria", "leuchte", "licht",
    "bulb", "lantern", "torch", "chandelier", "sconce", "pendant",
    "spotlight", "downlight", "floodlight", "streetlight", "nightlight",
    "lumen", "luminous", "illumin", "candle", "fixture", "luminary",
]

def _reddot_award_level(html):
    """Detect award level from Red Dot project page HTML."""
    text = html.lower()
    if "best of the best" in text:
        return "best_of_the_best"
    if "honourable mention" in text or "honourable_mention" in text:
        return "honourable_mention"
    return "winner"


# ── Category-specific verify functions ────────────────────────────────────────
# Each returns (True, "") to accept or (False, "reason") to skip.

_LIGHT_KWS = [
    "light", "lights", "lamp", "luminaire", "luminaria",
    "leuchte", "licht", "luminar", "lantern", "chandelier",
    "sconce", "downlight", "spotlight", "floodlight",
    "streetlight", "torchiere", "bulb", "illumin",
    "leuchten", "beleucht", "luce", "verlichting", "lighting",
]

_NOT_FIXTURE_RE = re.compile(
    r"(?:packaging|branding|brand.identity|annual.report|trade.fair|exhibition.stand"
    r"|\bstand\b|poster|publication|\bbook\b|sculpture|art.installation|campaign"
    r"|redesign|corporate.design|marken.?auftritt|erleuchtet|analyse|grafisch"
    r"|\bwall\b.*\bcar\b|\bcar\b.*\blight|lightwall|light.wall"
    # Vehicle lighting — not architectural fixtures
    r"|\bheadlamp\b|\bheadlight\b|\bfoglight\b|\bfog.lamp\b"
    r"|\bbicycle.?(frame|light|lamp)\b|\bcycling\b|\be-bike\b|ebike|\bscooter\b"
    r"|\bautomotive\b|\bvehicle\b.*\blight|\bcar\b.*\bhead"
    r"|\bclamp\b"
    # Security cameras that happen to include a light
    r"|spotlight.?cam(?:era)?\b|floodlight.?cam(?:era)?\b"
    r"|security.?cam(?:era)?\b|surveillance.?cam(?:era)?\b"
    r"|\bcam.?(floodlight|spotlight)\b"
    r"|ring.?cam\b|nest.?cam\b|arlo.?cam\b|reli.?cam\b"
    # Software / mobile apps whose name contains "light"
    r"|\bluminar.?(ai|neo)\b|luminar.?ai\b|photo.?editing.?light\b"
    # Non-lamp consumer goods with "light" in name
    r"|\belectric.?bike\b|\bmotorcycle\b"
    r"|\btoothbrush\b|\bdental\b"
    r"|\bumbrella\b(?!.*lamp)|\bluggage\b|\bsuitcase\b|\bhandbag\b"
    r"|\bjacket\b(?!.*lamp)|\bclothing\b|\btextile\b"
    # Pure communication / graphic design entries
    r"|light.?book\b|\bbook.?of.?light\b|light.?impressions\b"
    r"|light.?magazine\b|annual.?light\b)",
    re.IGNORECASE,
)

# Breadcrumb patterns that indicate a NON-lighting category on Red Dot
_NON_LIGHTING_CRUMB_RE = re.compile(
    r'\b(communication.?design|automotive|vehicles?|computers?|information.?technology'
    r'|software|mobile.?apps?|cameras?|photography.?equipment|sports.?equipment'
    r'|fashion|textiles?|watches?|jewellery|packaging|bicycles?|e-mobility'
    r'|baby|child|medical(?!.*light)|rehabilitation|industry|crafts?'
    r'|trade|public.?design|urban.?design)\b',
    re.IGNORECASE,
)

# Breadcrumb patterns that CONFIRM a lighting product on Red Dot
_LIGHTING_CRUMB_RE = re.compile(
    r'\b(luminaires?|light.?installations?|lighting|leuchten|illumination'
    r'|lamps?|light.?fittings?|light.?fixtures?)\b',
    re.IGNORECASE,
)


def _verify_lighting(html, real_name, crumbs, slug):
    """Accept only actual lighting fixtures; reject non-fixture / communication design."""
    _crumb_text = " ".join(crumbs).lower()
    _name_lower = real_name.lower()
    _slug_and_name = (slug + " " + real_name).lower()

    # ── Extract Red Dot product type from <span class="subtitle"> ────────────
    # On Red Dot project pages the subtitle is the product category label, e.g.:
    #   "Lighting and lamps", "LED Table Lamp", "Suspended LED Luminaire"
    _sub_m = re.search(r'<span\s+class=["\']subtitle["\'][^>]*>(.*?)</span>',
                       html, re.IGNORECASE | re.DOTALL)
    _subtitle = re.sub(r'<[^>]+>', '', _sub_m.group(1)).strip().lower() if _sub_m else ""
    _subtitle_is_lighting = bool(
        _LIGHTING_CRUMB_RE.search(_subtitle) or
        any(re.search(r'\b' + re.escape(kw) + r'\b', _subtitle) for kw in _LIGHT_KWS)
    )

    # ── Hard reject: slug/name contains explicit non-fixture patterns ────────
    if _NOT_FIXTURE_RE.search(_slug_and_name):
        return False, "非灯具产品（通讯设计/车灯/摄像头/软件等）"

    # ── Accept: subtitle directly confirms lighting (most reliable signal) ────
    if _subtitle_is_lighting:
        return True, ""

    # ── Hard reject: breadcrumbs confirm a non-lighting Red Dot category ────
    if _NON_LIGHTING_CRUMB_RE.search(_crumb_text):
        if not _LIGHTING_CRUMB_RE.search(_crumb_text):
            return False, "面包屑指向非灯具类别"

    # ── Accept: breadcrumbs explicitly confirm lighting category ─────────────
    if _LIGHTING_CRUMB_RE.search(_crumb_text):
        return True, ""

    # ── Accept: product name / slug contains lighting keyword ────────────────
    is_lighting = (
        any(re.search(r'\b' + re.escape(kw) + r'\b', _crumb_text) for kw in _LIGHT_KWS)
        or any(re.search(r'\b' + re.escape(kw) + r'\b', _name_lower) for kw in _LIGHT_KWS)
        or bool(re.search(r'\blights?\b', _name_lower))
    )
    if not is_lighting:
        return False, "非灯具品类"

    return True, ""


# ── Lamp sub-type classification ──────────────────────────────────────────
# Maps main lamp category → [(keyword_list, 子品类名), ...], fallback name

_LAMP_SUBTYPE_RULES = {
    "pendant": (
        [
            (["linear", "slim", "strip", "bar", "tube", "line", "profile"], "线型吊灯"),
            (["chandelier", "crystal", "candle", "branch", "arm"], "枝形吊灯"),
            (["ring", "circle", "halo", "loop", "round"], "环形吊灯"),
        ],
        "创意吊灯",  # fallback
    ),
    "wall": (
        [
            (["outdoor", "solar", "garden", "exterior", "pir", "sensor", "security", "cam"], "户外壁灯"),
            (["bedside", "reading", "bed", "bedroom"], "床头壁灯"),
            (["mirror", "vanity", "bath", "bathroom"], "浴室壁灯"),
            (["shelf", "bracket", "panel"], "装饰壁灯"),
        ],
        "室内壁灯",
    ),
    "floor": (
        [
            (["reading", "task", "adjustable", "arm", "articulated"], "阅读落地灯"),
            (["arc", "arch", "overhanging"], "弧形落地灯"),
        ],
        "装饰落地灯",
    ),
    "table": (
        [
            (["desk", "study", "task", "work", "office"], "学习台灯"),
            (["portable", "rechargeable", "battery", "wireless", "cordless"], "便携台灯"),
            (["bedside", "night", "nightlight"], "床头灯"),
        ],
        "创意台灯",
    ),
    "downlight": (
        [
            (["downlight", "recessed", "ceiling", "embedded"], "筒灯"),
            (["spotlight", "spot", "track", "accent"], "射灯"),
            (["sensor", "motion", "pir"], "感应灯"),
            (["flood", "floodlight", "project"], "投光灯"),
        ],
        "射灯",
    ),
}


def _classify_lamp_subtype(product_name, main_hint):
    """Classify a lamp product into a Chinese sub-category name."""
    rules, fallback = _LAMP_SUBTYPE_RULES.get(main_hint, ([], "其他灯具"))
    name_lower = product_name.lower()
    for kws, sub_name in rules:
        if any(kw in name_lower for kw in kws):
            return sub_name
    return fallback


def _make_lamp_subtype_fn(main_hint):
    """Return a callable(product_name) -> sub-category folder name, or None."""
    if main_hint not in _LAMP_SUBTYPE_RULES:
        return None
    return lambda name, subtitle="": _classify_lamp_subtype(name, main_hint)


def _classify_all_lighting(product_name, subtitle=""):
    """Universal lighting sub-category classifier for full-category scans (20+ categories).
    Works on any lighting product name without needing a main_hint.
    Priority order from specific to generic to avoid misclassification.
    subtitle: Red Dot <span class="subtitle"> text (e.g. "Pendant Luminaire", "LED Floor Lamp")
              which is more reliable than the product name for classification.
    """
    # Use subtitle first (more reliable Red Dot category label), then product name
    n = (subtitle + " " + product_name).lower()

    # ════════════════════════════════════════════════════════════════════
    # 1. 摄影/视频补光灯 — photography / video fill lights
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(fill.?light|key.?light|video.?light|led.?panel|ring.?light'
                 r'|bi.?color.?light|studio.?light|photo.?light|cinematic.?light'
                 r'|godox|smallrig|elgato.?key|manfrotto.?pro.?light|hobolite)\b', n):
        return "摄影补光灯"

    # ════════════════════════════════════════════════════════════════════
    # 2. 路灯/市政灯 — street / urban lighting
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(street.?light|street.?lamp|road.?light|bollard|pole.?light'
                 r'|post.?light|urban.?light|city.?light|public.?light|traffic.?light'
                 r'|highway.?light|parkway)\b', n):
        return "路灯·市政灯"

    # ════════════════════════════════════════════════════════════════════
    # 3. 户外灯具 — outdoor architectural / landscape
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(outdoor|garden|landscape|solar|exterior|pir|floodlight'
                 r'|flood.?light|security.?light|path.?light|lawn.?light'
                 r'|flood.?lamp|motion.?light|sensor.?light)\b', n):
        if re.search(r'\b(wall|sconce|facade|mounted)\b', n):
            return "户外壁灯"
        return "户外灯具"

    # ════════════════════════════════════════════════════════════════════
    # 4. 营地灯/露营灯 — camping / portable outdoor lanterns
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(camping|camp.?light|camp.?lamp|lantern|outdoor.?lamp'
                 r'|portable.?lantern|emergency.?lantern|telescopic.?lantern'
                 r'|collapsible|hanging.?lamp|tent.?light)\b', n):
        return "营地灯·露营灯"

    # ════════════════════════════════════════════════════════════════════
    # 5. 手电筒/工作灯 — torches / work lights / inspection lights
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(torch|flashlight|work.?light|inspection.?light|task.?light'
                 r'|workshop.?light|mechanic.?light|utility.?light|head.?torch'
                 r'|headtorch|headlamp(?!.*headlamp)|handheld.?light|pocket.?light'
                 r'|led.?work|portable.?work|emergency.?light|explosion.?proof)\b', n):
        return "手电·工作灯"

    # ════════════════════════════════════════════════════════════════════
    # 6. 灯泡/光源模块 — bulbs, LED modules, light sources
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(bulb|led.?bulb|led.?lamp(?!.*floor|.*table|.*wall|.*pendant)'
                 r'|led.?module|light.?source|led.?candle|filament|oled.?panel'
                 r'|mr16|par\d+|br\d+|capsule.?lamp|corn.?lamp|globe.?bulb)\b', n):
        return "灯泡·光源"

    # ════════════════════════════════════════════════════════════════════
    # 7. 吊灯 — pendant / hanging / chandelier
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(pendant|chandelier|hanging|suspension|suspended|hung'
                 r'|suspension.?lamp|hanging.?lamp)\b', n):
        if re.search(r'\b(linear|slim|strip|bar|tube|line|profile|rail|led.?bar)\b', n):
            return "线型吊灯"
        if re.search(r'\b(chandelier|crystal|candle|branch|arm|multi.?arm'
                     r'|tree|forest|cloud)\b', n):
            return "枝形吊灯"
        if re.search(r'\b(ring|circle|halo|loop|round|circular|orb|disc|disk)\b', n):
            return "环形吊灯"
        if re.search(r'\b(modular|cluster|system|nest|cocoon|origami|woven|knit)\b', n):
            return "组合吊灯"
        return "创意吊灯"

    # ════════════════════════════════════════════════════════════════════
    # 8. 壁灯 — wall lamps / sconces
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(wall.?lamp|wall.?light|wall.?luminaire|sconce|wall.?fixture'
                 r'|wall.?mounted|bracket.?light|wall.?sconce|applique)\b', n):
        if re.search(r'\b(outdoor|garden|exterior|solar|pir)\b', n):
            return "户外壁灯"
        if re.search(r'\b(bedside|reading|bed|bedroom|headboard)\b', n):
            return "床头壁灯"
        if re.search(r'\b(mirror|vanity|bath|bathroom|powder)\b', n):
            return "浴室壁灯"
        return "室内壁灯"

    # ════════════════════════════════════════════════════════════════════
    # 9. 落地灯 — floor lamps / standing lamps
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(floor.?lamp|floor.?light|standing.?lamp|torchiere|uplight'
                 r'|uplighter|floor.?luminaire|stand.?lamp|floor.?fixture)\b', n):
        if re.search(r'\b(reading|task|adjustable|arm|articulated|architect)\b', n):
            return "阅读落地灯"
        if re.search(r'\b(arc|arch|overhanging|curve|bow)\b', n):
            return "弧形落地灯"
        return "装饰落地灯"

    # ════════════════════════════════════════════════════════════════════
    # 10. 吸顶灯 — ceiling / flush mount
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(ceiling.?lamp|ceiling.?light|ceiling.?luminaire|flush.?mount'
                 r'|surface.?mount|ceiling.?fixture|overhead.?light|oyster.?light'
                 r'|ceiling.?panel|panel.?light)\b', n):
        return "吸顶灯"

    # ════════════════════════════════════════════════════════════════════
    # 11. 筒灯/射灯/轨道灯 — downlights / spotlights / track lights
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(downlight|recessed.?light|recessed.?lamp|spotlight|spot.?light'
                 r'|track.?light|rail.?light|accent.?light|directional.?light)\b', n):
        if re.search(r'\b(downlight|recessed|embedded|ceiling.?spot)\b', n):
            return "筒灯"
        if re.search(r'\b(track|rail|gimbal|adjustable.?spot|beam.?angle)\b', n):
            return "轨道灯·射灯"
        return "射灯"

    # ════════════════════════════════════════════════════════════════════
    # 12. 台灯/桌灯 — table / desk lamps
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(table.?lamp|desk.?lamp|study.?lamp|task.?lamp|work.?lamp'
                 r'|reading.?lamp|bedside.?lamp|night.?light|nightlight|desk.?light'
                 r'|table.?light|led.?desk|portable.?lamp(?!.*camp))\b', n):
        if re.search(r'\b(desk|study|task|work|office|eye.?care|eye.?protect'
                     r'|teenager|student|professional)\b', n):
            return "学习台灯"
        if re.search(r'\b(portable|rechargeable|battery|wireless|cordless|usb)\b', n):
            return "便携台灯"
        if re.search(r'\b(bedside|night|nightlight|wake.?up|sunrise|sleep)\b', n):
            return "床头灯·起床灯"
        if re.search(r'\b(screen|monitor|bar|strip|computer|gaming|rgb)\b', n):
            return "屏幕灯·氛围灯"
        return "创意台灯"

    # ════════════════════════════════════════════════════════════════════
    # 13. 应急灯/安全灯 — emergency / exit / safety lights
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(emergency.?light|exit.?light|exit.?sign|escape.?light'
                 r'|safety.?light|warning.?light|signal.?light|hazard.?light'
                 r'|evacuation|uv.?germicidal|germicidal|disinfection.?lamp)\b', n):
        return "应急·安全灯"

    # ════════════════════════════════════════════════════════════════════
    # 14. 医疗/光疗灯 — medical / UV / therapy lights
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(surgical|operation.?light|shadowless|medical.?lamp|dental.?light'
                 r'|uv.?lamp|uv.?light|light.?therapy|therapy.?light|red.?light.?therapy'
                 r'|led.?mask|face.?mask.?light|phototherapy|newborn.?light|bili.?light)\b', n):
        return "医疗·光疗灯"

    # ════════════════════════════════════════════════════════════════════
    # 15. 氛围灯/智能灯 — smart / ambient / decorative LED
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(smart.?lamp|smart.?light|ambient.?light|mood.?light'
                 r'|rgb.?light|color.?light|philips.?hue|govee|yeelight|xiaomi'
                 r'|gradient.?light|lightguide|light.?strip(?!.*floor)|led.?strip'
                 r'|neon.?light|pixel.?light|gaming.?light)\b', n):
        return "智能灯·氛围灯"

    # ════════════════════════════════════════════════════════════════════
    # 16. 蜡烛灯/烛台 — candles / candleholders
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(candle(?!.*lamp)|candlelight|candleholder|tealight|tea.?light'
                 r'|flame.?effect|lovinflame|wax)\b', n):
        return "蜡烛灯·烛台"

    # ════════════════════════════════════════════════════════════════════
    # 17. 投光灯/建筑照明 — architectural / flood / project lights
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(flood.?light|floodlight|project.?light|projection.?light'
                 r'|architectural.?light|facade.?light|wash.?light|linear.?light'
                 r'|led.?linear|media.?facade|light.?installation)\b', n):
        return "投光灯·建筑照明"

    # ════════════════════════════════════════════════════════════════════
    # 宽词回退 — single-keyword fallback
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\bpendant\b|\bchandelier\b|\bhanging\b', n):
        return "创意吊灯"
    if re.search(r'\bwall\b', n):
        return "室内壁灯"
    if re.search(r'\bfloor\b', n):
        return "装饰落地灯"
    if re.search(r'\b(table|desk|bedside|nightstand)\b', n):
        return "创意台灯"
    if re.search(r'\b(downlight|spotlight|spot|recessed)\b', n):
        return "射灯"
    if re.search(r'\bceiling\b', n):
        return "吸顶灯"
    if re.search(r'\b(sconce|bracket)\b', n):
        return "室内壁灯"
    if re.search(r'\b(torch|flashlight|handheld|portable)\b', n):
        return "手电·工作灯"
    if re.search(r'\b(lantern|camping|camp)\b', n):
        return "营地灯·露营灯"
    if re.search(r'\b(solar|outdoor|garden)\b', n):
        return "户外灯具"
    if re.search(r'\b(ring|panel|studio|fill)\b', n):
        return "摄影补光灯"
    if re.search(r'\b(bulb|source|module)\b', n):
        return "灯泡·光源"
    if re.search(r'\b(smart|rgb|ambient|govee|hue|yeelight)\b', n):
        return "智能灯·氛围灯"

    # ════════════════════════════════════════════════════════════════════
    # 宽词回退2 — Red Dot subtitle "luminaire" compound terms
    # These come from the Red Dot <span class="subtitle"> field
    # ════════════════════════════════════════════════════════════════════
    if re.search(r'\b(pendant|suspension|suspended|hanging)\b', n):
        return "创意吊灯"
    if re.search(r'\b(wall|sconce|applique)\b', n):
        return "室内壁灯"
    if re.search(r'\b(floor|standing|stand.up|uplight|torchiere)\b', n):
        return "装饰落地灯"
    if re.search(r'\b(table|desk|bedside|nightstand|night.?light)\b', n):
        return "创意台灯"
    if re.search(r'\b(ceiling|flush|surface.mount|overhead)\b', n):
        return "吸顶灯"
    if re.search(r'\b(recessed|downlight|embedded)\b', n):
        return "筒灯"
    if re.search(r'\b(spot|track|rail|accent)\b', n):
        return "射灯"
    if re.search(r'\b(linear|strip|bar|tube.?light|profile)\b', n):
        return "线型吊灯"
    if re.search(r'\b(outdoor|exterior|garden|solar|street|road|bollard|post.light)\b', n):
        return "户外灯具"
    if re.search(r'\b(portable|rechargeable|battery|wireless|cordless|usb.charge)\b', n):
        return "创意台灯"
    if re.search(r'\b(emergency|exit|safety|evacuation)\b', n):
        return "应急·安全灯"

    return "其他灯具"


def scrape_reddot_sitemap(keywords, topic_name, download_root, limit, timeout, session,
                          years=None, sub_keywords=None, verify_fn=None,
                          subtype_fn=None):
    """Scrape Red Dot winners using sitemap + keyword filter — no Playwright needed.

    Args:
        keywords:      List of English keywords to match against sitemap URL slugs.
        topic_name:    Folder name / label for this run.
        years:         Optional list of ints, e.g. [2022, 2023]. Filters by year
                       extracted from the product page content. None = no filter.
        sub_keywords:  Optional secondary filter — keeps only URLs whose slug contains
                       at least one of these strings (case-insensitive). Used to
                       de-overlap sub-category runs that all share the same top-level
                       lighting keyword list.
        verify_fn:     Optional callable(html, product_name, crumbs, slug) -> (bool, reason).
                       If provided, each product is passed to this function after page fetch;
                       return (False, "reason") to skip it. Used for category-specific
                       validation (e.g. lighting fixture check). None = accept all products.
        subtype_fn:    Optional callable(product_name) -> str. Returns a sub-category
                       folder name (e.g. "线型吊灯", "学习台灯"). Products are grouped by
                       sub-category instead of individual product folders. None = flat
                       (images go directly into download_root with sequential numbering).
    """
    log(f"\n{'='*60}")
    log(f"[Red Dot Sitemap] keywords={keywords[:5]}… scanning {REDDOT_SITEMAP_PAGES} pages"
        + (f"  years={years}" if years else ""))
    # Fetch sitemap index to get real sub-sitemap URLs (handles cHash correctly)
    try:
        idx_r = session.get(REDDOT_SITEMAP_BASE, timeout=timeout)
        sitemap_urls = re.findall(
            r"<loc>([^<]*sitemap=project[^<]*)</loc>", idx_r.text.replace("&amp;", "&"))
        # Remove duplicates (index lists both no-page and page=1-41)
        sitemap_urls = list(dict.fromkeys(sitemap_urls))
        log(f"  从 sitemap index 获得 {len(sitemap_urls)} 个子 sitemap")
    except Exception as e:
        log(f"  sitemap index 获取失败 ({e})，使用默认分页")
        sitemap_urls = [
            f"{REDDOT_SITEMAP_BASE}?page={p}&sitemap=project&cHash={REDDOT_SITEMAP_CHASH}"
            for p in range(1, REDDOT_SITEMAP_PAGES + 1)
        ]
    candidate_urls = []
    seen_urls: set = set()
    for page_num, sub_url in enumerate(sitemap_urls, 1):
        # Add cache-buster so VPN proxy doesn't return stale cached page
        bust_url = sub_url + f"&_t={int(time.time()) + page_num * 97}"
        try:
            r = session.get(bust_url, timeout=timeout)
            page_urls = re.findall(
                r"<loc>(https://www\.red-dot\.org/project/[^<]+)</loc>", r.text)
            new_urls = [u for u in page_urls if u not in seen_urls]
            seen_urls.update(new_urls)
            # Use word-boundary matching so "lamp" doesn't match "clamp" or "headlamp"
            matched = [u for u in new_urls
                       if any(re.search(r'\b' + re.escape(kw) + r'\b', u.lower())
                              for kw in keywords)]
            candidate_urls.extend(matched)
            total = len(sitemap_urls)
            if page_num % 10 == 0 or page_num == total:
                log(f"  Sitemap {page_num}/{total}: {len(candidate_urls)} matches so far")
        except Exception as e:
            log(f"  Sitemap page {page_num} error: {e}")
    if sub_keywords:
        # Word-boundary matching: "floor" matches "floor-lamp" but not "flooring"
        candidate_urls = [u for u in candidate_urls
                          if any(re.search(r'\b' + re.escape(kw) + r'\b', u.lower())
                                 for kw in sub_keywords)]
        log(f"  sub_keywords={sub_keywords} → {len(candidate_urls)} 个精细候选")
    log(f"  共找到 {len(candidate_urls)} 个候选项目，抓取前 {min(limit, len(candidate_urls))} 个")
    results = []
    seen_imgs: set = set()
    _folder_counters: dict = {}   # sequential numbering per folder path
    for i, proj_url in enumerate(candidate_urls[:limit]):
        slug = proj_url.rstrip("/").split("/")[-1]
        log(f"  [{i+1}/{min(limit, len(candidate_urls))}] {slug}")
        try:
            html = session.get(proj_url, timeout=timeout).text
            raw_images = reddot_extract_images(html, proj_url)
            images = [u for u in raw_images if u not in seen_imgs]
            seen_imgs.update(images)
            if not images:
                log("    (无图，跳过)")
                continue
            real_name = extract_product_name(html, "reddot") or slug
            model_code = extract_model_code(real_name)
            crumbs = extract_breadcrumbs(html, proj_url)
            # Category-specific product validation (e.g. lighting fixture check).
            # verify_fn is injected by the caller; None means accept every product.
            if verify_fn is not None:
                ok, reason = verify_fn(html, real_name, crumbs, slug)
                if not ok:
                    log(f"    ({reason}，跳过) {real_name}")
                    continue
            # Year filtering — look for award year in JSON-LD datePublished or
            # a "Red Dot Award YYYY" badge, not just any year in the HTML.
            if years:
                year_match = (
                    re.search(r'"datePublished"\s*:\s*"(20[12]\d)', html)
                    or re.search(r'red.dot(?:\s+award)?[^0-9]{0,20}(20[12]\d)', html, re.IGNORECASE)
                    or re.search(r'award.year[^0-9]{0,10}(20[12]\d)', html, re.IGNORECASE)
                )
                page_year = int(year_match.group(1)) if year_match else None
                if page_year and page_year not in years:
                    log(f"    (年份 {page_year} 不在筛选范围，跳过)")
                    continue

            award = _reddot_award_level(html)
            # Limit images per product to avoid duplicate shots (lit/unlit, accessories, etc.)
            max_imgs = getattr(session, '_max_per_product', 2)
            images = images[:max_imgs]
            # Extract subtitle for better sub-category classification
            _sub_m2 = re.search(
                r'<span\s+class=["\']subtitle["\'][^>]*>(.*?)</span>',
                html, re.IGNORECASE | re.DOTALL)
            _subtitle2 = re.sub(r'<[^>]+>', '', _sub_m2.group(1)).strip() if _sub_m2 else ""
            # Determine output folder: sub-category if subtype_fn provided, else flat
            sub_cat = subtype_fn(real_name, _subtitle2) if subtype_fn else None
            log(f"    产品: {real_name}  奖项: {award}  子类: {sub_cat or '-'}  图: {len(images)}")
            if download_root:
                if sub_cat:
                    folder = Path(download_root) / sub_cat
                else:
                    folder = Path(download_root)
                folder.mkdir(parents=True, exist_ok=True)
                folder_key = str(folder)
                counter = _folder_counters.get(folder_key, 0)
                ok = 0
                for j, img_url in enumerate(images):
                    ext = Path(urlparse(img_url).path).suffix.lower() or ".jpg"
                    if ext not in _IMG_EXTS:
                        ext = ".jpg"
                    counter += 1
                    dest = folder / f"{counter:02d}{ext}"
                    if download_image(img_url, dest, session):
                        ok += 1
                _folder_counters[folder_key] = counter
                log(f"    下载 {ok}/{len(images)} 张 -> {folder}")
            results.append({"product": real_name, "url": proj_url,
                            "images": images, "category": crumbs or [topic_name],
                            "award_level": award})
        except Exception as e:
            log(f"    [跳过] {e}")
        time.sleep(0.3)
    return results


def scrape_reddot_full_lighting_scan(download_root, limit, timeout, session,
                                     years=None, verify_fn=None, subtype_fn=None,
                                     workers=15):
    """Full lighting scan: check ALL Red Dot project URLs via breadcrumbs.

    Unlike scrape_reddot_sitemap (which filters by URL slug keywords and misses
    products whose names don't contain obvious lighting words), this function
    visits EVERY project page and uses server-rendered breadcrumbs to confirm
    whether the product is a lighting fixture.

    Process:
      Phase 1 — Collect all ~42,000 sitemap URLs (XML parsing, fast)
      Phase 2 — Parallel HTTP check of each URL for lighting breadcrumb
      Phase 3 — Download images from confirmed lighting URLs (up to limit)

    Estimated wall time: ~30 min for Phase 2 (42k URLs × 0.6s ÷ 15 workers).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    log(f"\n{'='*60}")
    log(f"[Red Dot 全量扫描] 不靠关键词 — 面包屑识别全部灯具（42,000+ URL）")
    log(f"  workers={workers}  limit={limit}  预计耗时约 25-35 分钟")

    # ── Phase 1: Collect ALL project URLs from sitemap ─────────────────────
    log("  [Phase 1] 收集 sitemap 全量 URL …")
    try:
        idx_r = session.get(REDDOT_SITEMAP_BASE, timeout=timeout)
        sitemap_urls = re.findall(
            r"<loc>([^<]*sitemap=project[^<]*)</loc>", idx_r.text.replace("&amp;", "&"))
        sitemap_urls = list(dict.fromkeys(sitemap_urls))
    except Exception as e:
        log(f"  sitemap index 获取失败 ({e})，使用默认分页")
        sitemap_urls = [
            f"{REDDOT_SITEMAP_BASE}?page={p}&sitemap=project&cHash={REDDOT_SITEMAP_CHASH}"
            for p in range(1, REDDOT_SITEMAP_PAGES + 1)
        ]

    all_project_urls = []
    seen_p1: set = set()
    for page_num, sub_url in enumerate(sitemap_urls, 1):
        bust_url = sub_url + f"&_t={int(time.time()) + page_num * 97}"
        try:
            r = session.get(bust_url, timeout=timeout)
            page_urls = re.findall(
                r"<loc>(https://www\.red-dot\.org/project/[^<]+)</loc>", r.text)
            new_urls = [u for u in page_urls if u not in seen_p1]
            seen_p1.update(new_urls)
            all_project_urls.extend(new_urls)
            total = len(sitemap_urls)
            if page_num % 10 == 0 or page_num == total:
                log(f"  Sitemap {page_num}/{total}: 共 {len(all_project_urls)} 个 URL")
        except Exception as e:
            log(f"  Sitemap {page_num} 错误: {e}")

    log(f"  [Phase 1 完成] 共 {len(all_project_urls)} 个项目 URL")

    # ── Phase 2: Parallel breadcrumb + metadata extraction ─────────────────
    log(f"  [Phase 2] {workers} 线程并发检查面包屑，识别灯具产品 …")

    max_imgs_per = getattr(session, '_max_per_product', 2)

    def _check_one(url):
        """Fetch URL, check breadcrumbs, extract image URLs. Return None if not lighting."""
        try:
            html = session.get(url, timeout=timeout).text
            slug = url.rstrip("/").split("/")[-1]
            real_name = extract_product_name(html, "reddot") or slug
            crumbs = extract_breadcrumbs(html, url)

            ok, reason = (verify_fn(html, real_name, crumbs, slug)
                          if verify_fn else (True, ""))
            if not ok:
                return None

            if years:
                ym = (re.search(r'"datePublished"\s*:\s*"(20[12]\d)', html)
                      or re.search(r'red.dot(?:\s+award)?[^0-9]{0,20}(20[12]\d)',
                                   html, re.IGNORECASE))
                page_year = int(ym.group(1)) if ym else None
                if page_year and page_year not in years:
                    return None

            images = reddot_extract_images(html, url)[:max_imgs_per]
            award = _reddot_award_level(html)
            # Extract subtitle for better sub-category classification
            _sub_m = re.search(
                r'<span\s+class=["\']subtitle["\'][^>]*>(.*?)</span>',
                html, re.IGNORECASE | re.DOTALL)
            _subtitle = re.sub(r'<[^>]+>', '', _sub_m.group(1)).strip() if _sub_m else ""
            sub_cat = subtype_fn(real_name, _subtitle) if subtype_fn else None

            return {
                "url": url, "slug": slug, "real_name": real_name,
                "crumbs": crumbs, "images": images,
                "award": award, "sub_cat": sub_cat,
            }
        except Exception:
            return None

    lighting_products = []
    checked = [0]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_check_one, u): u for u in all_project_urls}
        for future in as_completed(futures):
            result = future.result()
            checked[0] += 1
            if result:
                lighting_products.append(result)
            if checked[0] % 1000 == 0:
                log(f"  已检查 {checked[0]}/{len(all_project_urls)}，"
                    f"已确认灯具 {len(lighting_products)} 个")

    log(f"  [Phase 2 完成] 灯具产品 {len(lighting_products)} / 总项目 {len(all_project_urls)}")

    # Sort by URL (roughly chronological) so sequential numbering makes sense
    lighting_products.sort(key=lambda x: x["url"])

    # ── Phase 3: Download images ───────────────────────────────────────────
    actual = min(limit, len(lighting_products))
    log(f"  [Phase 3] 下载图片，处理前 {actual} 个产品 …")

    results = []
    seen_imgs: set = set()
    _folder_counters: dict = {}

    for i, prod in enumerate(lighting_products[:limit]):
        images = [u for u in prod["images"] if u not in seen_imgs]
        seen_imgs.update(images)
        if not images:
            continue

        sub_cat = prod["sub_cat"]
        log(f"  [{i+1}/{actual}] {prod['real_name']}  奖项: {prod['award']}  "
            f"子类: {sub_cat or '-'}  图: {len(images)}")

        if download_root:
            folder = Path(download_root) / sub_cat if sub_cat else Path(download_root)
            folder.mkdir(parents=True, exist_ok=True)
            folder_key = str(folder)
            counter = _folder_counters.get(folder_key, 0)
            ok_count = 0
            for img_url in images:
                ext = Path(urlparse(img_url).path).suffix.lower() or ".jpg"
                if ext not in _IMG_EXTS:
                    ext = ".jpg"
                counter += 1
                dest = folder / f"{counter:02d}{ext}"
                if download_image(img_url, dest, session):
                    ok_count += 1
            _folder_counters[folder_key] = counter
            log(f"    下载 {ok_count}/{len(images)} 张 -> {folder}")

        results.append({
            "product": prod["real_name"],
            "url": prod["url"],
            "images": prod["images"],
            "category": prod["crumbs"] or ["lighting"],
            "award_level": prod["award"],
        })
        time.sleep(0.05)

    log(f"  [Phase 3 完成] 下载 {len(results)} 个产品的图片")
    return results


# ══════════════════════════════════════════════════════════════════════════
# BEAR ANALYSIS — Taobao + Xiaohongshu multi-keyword color research
# ══════════════════════════════════════════════════════════════════════════

BEAR_KEYWORDS = [
    "小熊夜灯", "熊猫夜灯", "卡通熊夜灯", "泰迪熊小夜灯", "熊夜灯",
    "泰迪熊", "小熊玩偶", "熊猫公仔", "毛绒小熊", "小熊玩具",
    "小熊台灯", "熊形摆件", "北极熊玩偶", "棕熊玩偶", "小熊音乐盒",
]

BEAR_PRICE_BANDS = [
    ("100-200", 100, 200),
    ("200-300", 200, 300),
    ("300-500", 300, 500),
]

# Profile dir persisted across runs so login sessions are saved
BEAR_TB_PROFILE  = str(Path.home() / "AppData" / "Local" / "Temp" / "bear_tb_profile")
BEAR_XHS_PROFILE = str(Path.home() / "AppData" / "Local" / "Temp" / "bear_xhs_profile")
_CDP_PORT_TB  = 9222
_CDP_PORT_XHS = 9223

_CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def _find_chrome():
    for p in _CHROME_PATHS:
        if os.path.exists(p):
            return p
    return None


def _start_chrome_cdp(profile_dir, port):
    """Launch real Chrome.exe with remote-debugging on *port*, using *profile_dir*.
    Returns (proc, ws_url) — ws_url is the websocket endpoint for Playwright CDP.
    """
    import subprocess, urllib.request

    chrome = _find_chrome()
    if not chrome:
        raise FileNotFoundError("Chrome not found at known paths")
    Path(profile_dir).mkdir(parents=True, exist_ok=True)

    # Kill any stale Chrome on this port
    proc = subprocess.Popen(
        [
            chrome,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1280,900",
        ],
    )

    # Wait until Chrome's debugging port is ready (up to 15s)
    for _ in range(30):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=2) as resp:
                if resp.status == 200:
                    return proc
        except Exception:
            pass
    raise RuntimeError(f"Chrome did not open CDP on port {port} in time")


# Taobao image URL: strip size suffix to get larger image
_TB_SIZE_RE = re.compile(r"_\d+x\d+\.(jpg|jpeg|png|webp)", re.I)


def _taobao_upgrade(url):
    return _TB_SIZE_RE.sub(r".\1", url)


def _taobao_extract_imgs(html):
    seen = set()
    result = []
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-original"):
            raw = img.get(attr, "")
            if not raw or raw.startswith("data:"):
                continue
            if raw.startswith("//"):
                raw = "https:" + raw
            if not any(d in raw for d in ("alicdn.com", "taobaocdn.com", "tbcdn.cn")):
                continue
            if any(x in raw.lower() for x in ("logo", "icon", "banner", "sprite", "loading")):
                continue
            upgraded = _taobao_upgrade(raw)
            u = upgraded if upgraded != raw else raw
            if u not in seen:
                seen.add(u)
                result.append(u)
            break
    return result


_TB_LOGIN_PATTERNS = re.compile(
    r"(passport\.taobao|login\.taobao|login\.tmall|login\.alibaba"
    r"|/member/login|TB_token_|tb\.com/member/login)",
    re.IGNORECASE,
)


def _is_taobao_login_page(url, html):
    """Return True if the page is a Taobao login/auth wall."""
    if _TB_LOGIN_PATTERNS.search(url):
        return True
    # Also check for login form in HTML
    if 'id="J_Form"' in html or 'name="TPL_username"' in html:
        return True
    return False


def _scrape_taobao_page(ctx, url, timeout):
    """Navigate to *url* in a new page inside *ctx*, scroll, return (html, is_login).
    If a login wall is detected, returns ("", True) so caller can pause.
    """
    page = ctx.new_page()
    try:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        except Exception:
            pass
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            page.wait_for_timeout(5000)
        for js in [
            "window.scrollTo(0, document.body.scrollHeight/2)",
            "window.scrollTo(0, document.body.scrollHeight)",
        ]:
            try:
                page.evaluate(js)
                page.wait_for_timeout(1500)
            except Exception:
                pass
        final_url = page.url
        html = ""
        for _ in range(3):
            try:
                html = page.content()
                break
            except Exception:
                page.wait_for_timeout(2000)
        if _is_taobao_login_page(final_url, html):
            return "", True
        return html, False
    finally:
        try:
            page.close()
        except Exception:
            pass


def _taobao_wait_relogin(ctx):
    """Print a prompt and wait for the user to re-login, then press Enter."""
    print("\n" + "!"*60)
    print("[淘宝] 检测到登录拦截！请在浏览器里重新登录淘宝，")
    print("       登录完成后回到此窗口按 Enter 继续...")
    print("!"*60)
    try:
        input()
    except EOFError:
        time.sleep(30)


def _tb_js_click_text(page, text, exact=True):
    """Click an element whose trimmed textContent matches *text* via JS.
    Returns True if clicked, False if not found.
    """
    js = f"""
        () => {{
            const all = [...document.querySelectorAll('a, span, div, li, button')];
            for (const el of all) {{
                const t = el.textContent.trim();
                if ({'t === ' + repr(text) if exact else repr(text) + ' in t (t === ' + repr(text) + ' || t.startsWith(' + repr(text) + '))'}) {{
                    el.click();
                    return true;
                }}
            }}
            return false;
        }}
    """
    # Simpler inline JS to avoid f-string nesting issues
    if exact:
        return page.evaluate(
            "(t) => { const all=[...document.querySelectorAll('a,span,div,li,button')];"
            " for(const el of all){if(el.textContent.trim()===t){el.click();return true;}}"
            " return false; }",
            text
        )
    else:
        return page.evaluate(
            "(t) => { const all=[...document.querySelectorAll('a,span,div,li,button')];"
            " for(const el of all){if(el.textContent.trim().startsWith(t)){el.click();return true;}}"
            " return false; }",
            text
        )


def _tb_mouse_click_text(page, text, exact=True):
    """Find an element by text via JS, then use page.mouse.click() at its center.
    This produces isTrusted=true events — required for Taobao's React event system.
    Returns True on success, False if element not found or click failed.
    """
    js = """([text, exact]) => {
        const all = [...document.querySelectorAll('a,span,div,li,button')];
        for (const el of all) {
            const t = (el.innerText || el.textContent || '').trim();
            const match = exact ? t === text : t.includes(text);
            if (match) {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0)
                    return {x: r.left + r.width/2, y: r.top + r.height/2};
            }
        }
        return null;
    }"""
    try:
        rect = page.evaluate(js, [text, exact])
        if rect:
            page.mouse.move(rect['x'], rect['y'])
            page.wait_for_timeout(80)
            page.mouse.click(rect['x'], rect['y'])
            return True
    except Exception:
        pass
    return False


def _tb_click_queding(page, near_y=None):
    """Click the 确定 button inside the 区间 price dropdown.

    Taobao class "confirmButton--<hash>" is the price-range confirm button.
    The pagination bar also has a "确定" (class next-pagination-jump-go) far down the
    page — we must NOT hit that one.

    Strategy order:
      1. JS el.click() on [class*="confirmButton"]  — same mechanism as 销量/区间
      2. JS el.click() on [class*="buttonWrapper"] child that contains only 确定
      3. page.mouse.click() at confirmButton coordinates
    """
    # ── 1. Direct JS click on the confirmButton element ───────────────────
    hit = page.evaluate("""() => {
        const el = document.querySelector('[class*="confirmButton"]');
        if (!el) return 'not-found';
        el.click();
        return 'clicked';
    }""")
    if hit == 'clicked':
        return 'JS-confirmButton'

    # ── 2. JS click on child div of buttonWrapper that contains only 确定 ─
    hit2 = page.evaluate("""() => {
        const wrapper = document.querySelector('[class*="buttonWrapper"]');
        if (!wrapper) return 'no-wrapper';
        const divs = [...wrapper.querySelectorAll('div,span,button')];
        for (const el of divs) {
            if ((el.innerText || el.textContent || '').trim() === '确定') {
                el.click();
                return 'clicked';
            }
        }
        return 'no-child';
    }""")
    if hit2 == 'clicked':
        return 'JS-buttonWrapper'

    # ── 3. Mouse click at confirmButton coordinates ────────────────────────
    rect = page.evaluate("""() => {
        const el = document.querySelector('[class*="confirmButton"]');
        if (!el) return null;
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) return {x: r.left + r.width/2, y: r.top + r.height/2};
        return null;
    }""")
    if rect:
        try:
            page.mouse.move(rect['x'], rect['y'])
            page.wait_for_timeout(100)
            page.mouse.click(rect['x'], rect['y'])
            return 'mouse-confirmButton'
        except Exception:
            pass

    # Strategy K: Enter key on price input (form submit)
    pressed = page.evaluate("""
        () => {
            const inputs = [...document.querySelectorAll('input')].filter(i => {
                const ph = i.placeholder || '';
                return ph.includes('最低') || ph.includes('最高') ||
                       ph.includes('低价') || ph.includes('高价');
            });
            if (!inputs.length) return false;
            const last = inputs[inputs.length - 1];
            last.focus();
            last.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',keyCode:13,which:13,bubbles:true}));
            last.dispatchEvent(new KeyboardEvent('keyup',{key:'Enter',keyCode:13,which:13,bubbles:true}));
            return true;
        }
    """)
    if pressed:
        return 'K'

    return False


def _taobao_apply_ui_filters(page, price_min, price_max):
    """Apply sales sort and price range via the Taobao sort bar + 区间 dropdown.

    UI flow observed:
      综合 | 销量 | 价格 | 区间▾ | 品牌 | 新品 ...
      Click 销量 → sort by sales
      Click 区间 → price dropdown opens showing ¥最低价 / ¥最高价 inputs + 确定 button
    """

    # ── Step 1: Click 销量 ────────────────────────────────────────────────
    ok1 = _tb_js_click_text(page, "销量")
    log(f"      [UI] ① 销量 点击: {'✓' if ok1 else '✗ 未找到，请手动点'}")
    page.wait_for_timeout(1500)

    # ── Step 2: Click 区间 to open price dropdown ─────────────────────────
    ok2 = _tb_js_click_text(page, "区间", exact=False)
    log(f"      [UI] ② 区间 点击: {'✓' if ok2 else '✗ 未找到，请手动点'}")

    # Wait up to 4s for the price inputs to actually appear in the dropdown
    input_sel = 'input[placeholder*="最低"], input[placeholder*="最高"], input[placeholder*="低价"], input[placeholder*="高价"]'
    try:
        page.wait_for_selector(input_sel, timeout=4000)
        log("      [UI] 区间下拉已展开，输入框可见")
    except Exception:
        log("      [UI] ⚠ 等待区间输入框超时，尝试继续...")
    page.wait_for_timeout(300)

    # ── Step 3: Fill 最低价 / 最高价 inputs and get their coordinates ─────
    input_coords = page.evaluate(
        """([lo, hi]) => {
            const inputs = [...document.querySelectorAll('input')].filter(i => {
                const ph = i.placeholder || '';
                return ph.includes('最低') || ph.includes('最高') ||
                       ph.includes('低价') || ph.includes('高价');
            });
            if (inputs.length < 2) return null;
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value').set;
            setter.call(inputs[0], lo);
            inputs[0].dispatchEvent(new Event('input', {bubbles:true}));
            inputs[0].dispatchEvent(new Event('change', {bubbles:true}));
            setter.call(inputs[1], hi);
            inputs[1].dispatchEvent(new Event('input', {bubbles:true}));
            inputs[1].dispatchEvent(new Event('change', {bubbles:true}));
            // Return the bounding rect of the SECOND input so we know where the dropdown is
            const r = inputs[1].getBoundingClientRect();
            return {x: r.left + r.width/2, y: r.top + r.height/2, inputY: r.bottom};
        }""",
        [str(price_min), str(price_max)]
    )
    filled = input_coords is not None
    log(f"      [UI] ③ 价格输入 {price_min}-{price_max}: {'✓' if filled else '✗ 未找到输入框，请手动填'}")
    page.wait_for_timeout(300)

    # ── Step 4: Click 确定 ────────────────────────────────────────────────
    ok4 = False
    if filled:
        ok4 = _tb_click_queding(page, near_y=input_coords['inputY'])

    log(f"      [UI] ④ 确定 点击: {'✓ (策略' + str(ok4) + ')' if ok4 else '✗ 未找到，请手动点'}")
    page.wait_for_timeout(2000)


def _taobao_open_preview(ctx, keyword, price_min, price_max, timeout):
    """Open a preview page, apply UI filters, keep it open for user to inspect.
    Returns (page, url) — caller must close the page after user confirmation.
    """
    from urllib.parse import quote

    base_url = (
        f"https://s.taobao.com/search?q={quote(keyword)}"
        f"&sort=sale-desc"
        f"&startprice={price_min}&endprice={price_max}"
    )

    page = ctx.new_page()
    try:
        page.goto(base_url, wait_until="domcontentloaded", timeout=timeout * 1000)
        page.wait_for_timeout(3000)
        _taobao_apply_ui_filters(page, price_min, price_max)
        page.wait_for_timeout(2000)
        final_url = page.url
    except Exception:
        final_url = base_url

    # Page stays open — caller is responsible for closing it
    return page, final_url


def scrape_taobao_band(keyword, price_min, price_max, band_label,
                       download_root, pages, timeout, session, seen_global, ctx,
                       confirmed_base_url=None):
    """Scrape one keyword × one price band.
    For each keyword: open one persistent page, apply UI filters (销量+区间+价格+确定),
    then scrape all pages within that same tab (avoids re-login / filter reset).
    """
    from urllib.parse import quote

    folder = Path(download_root) / "Taobao" / band_label
    folder.mkdir(parents=True, exist_ok=True)
    safe_kw = re.sub(r"[^\w]", "_", keyword)

    search_url = f"https://s.taobao.com/search?q={quote(keyword)}&sort=sale-desc"
    log(f"    [淘宝] {keyword}  价格¥{price_min}-{price_max}  排序:销量↓")

    page = ctx.new_page()
    ok_total = 0
    try:
        # ── Navigate and apply UI filters ─────────────────────────────────
        for _attempt in range(2):
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=timeout * 1000)
            except Exception:
                pass
            page.wait_for_timeout(3000)

            # Check for login wall
            cur_url = page.url
            html_check = ""
            try:
                html_check = page.content()
            except Exception:
                pass
            if _is_taobao_login_page(cur_url, html_check):
                _taobao_wait_relogin(ctx)
                continue
            break

        # Apply UI filters on this page
        _taobao_apply_ui_filters(page, price_min, price_max)

        # Wait for results to refresh after filters applied
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            page.wait_for_timeout(3000)

        # ── Scrape pages ──────────────────────────────────────────────────
        for pg in range(pages):
            log(f"      第{pg+1}页")

            if pg > 0:
                # Click the 下一页 button — keeps filters, looks human, avoids anti-bot
                clicked_next = page.evaluate("""() => {
                    // Try common next-page selectors
                    const selectors = [
                        'a.next-pagination-item.next',
                        'button.next-pagination-item.next',
                        '[class*="next-pagination"] [class*="next"]:not([disabled])',
                        'a[aria-label="下一页"]',
                        'button[aria-label="下一页"]',
                    ];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el) { el.click(); return sel; }
                    }
                    // Text-based fallback: find 下一页 link
                    for (const el of document.querySelectorAll('a,button,span')) {
                        const t = (el.innerText || el.textContent || '').trim();
                        if (t === '下一页' || t === '›' || t === '>') {
                            el.click(); return 'text:' + t;
                        }
                    }
                    return null;
                }""")
                if clicked_next:
                    log(f"        → 下一页 via {clicked_next}")
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=timeout * 1000)
                    except Exception:
                        pass
                    page.wait_for_timeout(2500)
                else:
                    log("        ⚠ 未找到下一页按钮，跳过后续页")
                    break

            # Scroll to trigger lazy load
            for js in ["window.scrollTo(0,document.body.scrollHeight/2)",
                       "window.scrollTo(0,document.body.scrollHeight)"]:
                try:
                    page.evaluate(js)
                    page.wait_for_timeout(1200)
                except Exception:
                    pass

            html = ""
            for _ in range(3):
                try:
                    html = page.content()
                    break
                except Exception:
                    page.wait_for_timeout(1500)

            imgs = _taobao_extract_imgs(html)
            new_imgs = [u for u in imgs if u not in seen_global]
            seen_global.update(new_imgs)
            log(f"        找到 {len(new_imgs)} 张新图（页面共 {len(imgs)} 张）")

            ok = 0
            for j, img_url in enumerate(new_imgs):
                ext = Path(urlparse(img_url).path).suffix.lower() or ".jpg"
                if ext not in _IMG_EXTS:
                    ext = ".jpg"
                fname = f"{safe_kw}_p{pg+1}_{j+1:03d}{ext}"
                dest = folder / fname
                if download_image(img_url, dest, session):
                    if is_valid_image(dest, min_px=200):
                        ok += 1
                    else:
                        dest.unlink(missing_ok=True)
            ok_total += ok
            log(f"        下载 {ok} 张有效图 -> {folder}")
            time.sleep(2)

    finally:
        try:
            page.close()
        except Exception:
            pass

    return ok_total


def scrape_taobao_bear(download_root, pages_per_band, timeout, headless, session, start_band=None):
    """Scrape all bear keywords × price bands from Taobao.
    Non-headless: pops up real Chrome so user can log in; session saved for next run.
    """
    from playwright.sync_api import sync_playwright

    log(f"\n{'='*60}")
    log(f"[淘宝熊] 关键词×{len(BEAR_KEYWORDS)}  价格带×{len(BEAR_PRICE_BANDS)}  每带{pages_per_band}页")

    chrome_proc = None
    with sync_playwright() as pw:
        if not headless:
            chrome = _find_chrome()
            if not chrome:
                log("[淘宝] 未找到 Chrome，请手动安装后重试")
                return 0
            log(f"[淘宝] 正在启动 Chrome（端口 {_CDP_PORT_TB}）…")
            chrome_proc = _start_chrome_cdp(BEAR_TB_PROFILE, _CDP_PORT_TB)
            try:
                browser = pw.chromium.connect_over_cdp(f"http://localhost:{_CDP_PORT_TB}")
            except Exception as e:
                log(f"[淘宝] 连接 Chrome 失败: {e}")
                if chrome_proc:
                    chrome_proc.terminate()
                return 0

            # Use the first context Chrome created (its default window)
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()

            # Navigate to Taobao so user can log in
            try:
                intro_page = ctx.new_page()
                intro_page.goto("https://www.taobao.com/", wait_until="domcontentloaded",
                                timeout=30000)
                intro_page.wait_for_timeout(2000)
                intro_page.close()
            except Exception:
                pass

            print("\n" + "="*60)
            print("[淘宝] 浏览器已弹出。")
            print("请在浏览器中完成淘宝登录，登录完成后回到此终端按 Enter 继续...")
            print("="*60)
            try:
                input()
            except EOFError:
                time.sleep(20)  # non-interactive fallback
        else:
            log("[淘宝] 无头模式（可能被淘宝拦截，建议改用 --no-headless）")
            b = pw.chromium.launch(headless=True)
            ctx = b.new_context(extra_http_headers=HEADERS)

        seen_global = set()
        grand_total = 0
        skip = bool(start_band)
        for band_label, price_min, price_max in BEAR_PRICE_BANDS:
            if skip:
                if band_label == start_band:
                    skip = False
                else:
                    log(f"\n  ── [跳过] 价格带 ¥{price_min}-{price_max} ──")
                    continue

            print("\n" + "="*60)
            print(f"  即将开始：价格段 ¥{price_min}-{price_max}  |  排序：销量从高到低")
            print(f"  关键词共 {len(BEAR_KEYWORDS)} 个，每词抓 {pages_per_band} 页")
            print()
            print("  → 浏览器将打开第一个关键词预览页，请确认：")
            print("    1. 页面顶部「销量」按钮已高亮选中")
            print(f"    2. 价格筛选框显示 {price_min} - {price_max}")
            print("  确认无误后回到此窗口按 Enter 开始批量抓取")
            print("  （如需手动调整筛选，调好后再按 Enter）")
            print("="*60)

            # Open preview page (stays open for user to inspect)
            preview_page, confirmed_url = _taobao_open_preview(
                ctx, BEAR_KEYWORDS[0], price_min, price_max, timeout
            )

            try:
                input()
            except EOFError:
                time.sleep(15)

            # Now close the preview page before bulk scraping
            try:
                preview_page.close()
            except Exception:
                pass

            log(f"\n  ── 价格带 ¥{price_min}-{price_max}  排序:销量↓  开始抓取 ──")
            band_total = 0
            for kw in BEAR_KEYWORDS:
                n = scrape_taobao_band(kw, price_min, price_max, band_label,
                                       download_root, pages_per_band, timeout,
                                       session, seen_global, ctx,
                                       confirmed_base_url=confirmed_url)
                band_total += n
            log(f"  价格带 ¥{price_min}-{price_max} 合计: {band_total} 张")
            grand_total += band_total

        log(f"\n[淘宝熊汇总] {grand_total} 张图片")

    if chrome_proc:
        try:
            chrome_proc.terminate()
        except Exception:
            pass

    return grand_total


# ── Xiaohongshu helpers ───────────────────────────────────────────────────

_XHS_DOMAINS = ("xhscdn.com", "ci.xiaohongshu.com", "sns-img")


def _xhs_extract_imgs(html):
    seen = set()
    result = []

    for pattern in [
        r'"url"\s*:\s*"(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
        r'"imageUrl"\s*:\s*"(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
        r'"cover"\s*:\s*"(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
        r'"fileid"\s*:\s*"([^"]+)"',   # XHS uses file IDs; keep if CDN domain found nearby
    ]:
        for m in re.finditer(pattern, html, re.I):
            raw = m.group(1).replace("\\u002F", "/").replace("\\/", "/")
            if any(d in raw for d in _XHS_DOMAINS) and raw not in seen:
                seen.add(raw)
                result.append(raw)

    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        for attr in ("src", "data-src"):
            raw = img.get(attr, "")
            if raw and any(d in raw for d in _XHS_DOMAINS) and raw not in seen:
                seen.add(raw)
                result.append(raw)

    return result


def scrape_xhs_keyword(keyword, download_root, timeout, session, seen_global, ctx):
    """Scrape one XHS keyword using existing browser context *ctx*."""
    from urllib.parse import quote

    safe_kw = re.sub(r"[^\w]", "_", keyword)
    folder = Path(download_root) / "Xiaohongshu" / safe_kw
    folder.mkdir(parents=True, exist_ok=True)

    url = (f"https://www.xiaohongshu.com/search_result"
           f"?keyword={quote(keyword)}&source=web_explore_feed")
    log(f"    [小红书] {keyword}")

    page = ctx.new_page()
    html = ""
    try:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        except Exception:
            pass
        page.wait_for_timeout(5000)
        for _ in range(3):
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
            except Exception:
                break
        html = page.content()
    except Exception as e:
        log(f"      [跳过] 渲染失败: {e}")
    finally:
        try:
            page.close()
        except Exception:
            pass

    imgs = _xhs_extract_imgs(html)
    new_imgs = [u for u in imgs if u not in seen_global]
    seen_global.update(new_imgs)
    log(f"      找到 {len(new_imgs)} 张新图")

    ok = 0
    for j, img_url in enumerate(new_imgs):
        ext = Path(urlparse(img_url).path).suffix
        if not ext or len(ext) > 5:
            ext = ".jpg"
        fname = f"{safe_kw}_{j+1:03d}{ext}"
        dest = folder / fname
        if download_image(img_url, dest, session):
            if is_valid_image(dest, min_px=150):
                ok += 1
            else:
                dest.unlink(missing_ok=True)
    log(f"      下载 {ok} 张有效图 -> {folder}")
    time.sleep(2)
    return ok


def scrape_xhs_bear(download_root, timeout, headless, session):
    """Scrape all bear keywords from Xiaohongshu.
    Non-headless: connects to a real Chrome instance with a persistent profile
    (same mechanism as Taobao) so login is saved across runs.
    """
    from playwright.sync_api import sync_playwright

    log(f"\n{'='*60}")
    log(f"[小红书熊] 关键词×{len(BEAR_KEYWORDS)}")

    chrome_proc = None
    with sync_playwright() as pw:
        if not headless:
            chrome = _find_chrome()
            if not chrome:
                log("[小红书] 未找到 Chrome，请手动安装后重试")
                return 0
            log(f"[小红书] 正在启动 Chrome（端口 {_CDP_PORT_XHS}）…")
            chrome_proc = _start_chrome_cdp(BEAR_XHS_PROFILE, _CDP_PORT_XHS)
            try:
                browser = pw.chromium.connect_over_cdp(f"http://localhost:{_CDP_PORT_XHS}")
            except Exception as e:
                log(f"[小红书] 连接 Chrome 失败: {e}")
                if chrome_proc:
                    chrome_proc.terminate()
                return 0

            ctx = browser.contexts[0] if browser.contexts else browser.new_context()

            # Navigate to XHS so user can log in — keep page open so Chrome doesn't exit
            try:
                intro = ctx.new_page()
                intro.goto("https://www.xiaohongshu.com/", wait_until="domcontentloaded",
                           timeout=30000)
                intro.wait_for_timeout(2000)
                # Do NOT close intro — Chrome auto-exits when last tab closes
            except Exception:
                pass

            print("\n" + "="*60)
            print("[小红书] 浏览器已弹出。")
            print("请在浏览器中完成小红书登录，登录完成后回到此终端按 Enter 继续...")
            print("（登录状态已保存，下次运行无需重新登录）")
            print("="*60)
            try:
                input()
            except EOFError:
                time.sleep(20)
        else:
            log("[小红书] 无头模式（可能被拦截，建议改用 --no-headless）")
            b = pw.chromium.launch(headless=True)
            ctx = b.new_context(extra_http_headers={
                **HEADERS,
                "Referer": "https://www.xiaohongshu.com/",
            })

        seen_global = set()
        total = 0
        for kw in BEAR_KEYWORDS:
            n = scrape_xhs_keyword(kw, download_root, timeout, session, seen_global, ctx)
            total += n

        log(f"\n[小红书熊汇总] {total} 张图片")

    if chrome_proc:
        try:
            chrome_proc.terminate()
        except Exception:
            pass

    return total


# ══════════════════════════════════════════════════════════════════════════
# BRAND SEARCH — find official website from brand name
# ══════════════════════════════════════════════════════════════════════════

# Path segments that suggest a product catalog page
CATALOG_HINTS = re.compile(
    r"/(products?|catalog|catalogue|collection|shop|range|lighting|luminaires?|portfolio|items?)(/|$)",
    re.IGNORECASE,
)

def search_brand_url(brand_name, timeout=30, headless=True):
    """
    Search DuckDuckGo for the brand's official product page.
    Returns (homepage_url, product_catalog_url).
    Falls back to Playwright-rendered search if instant API returns nothing useful.
    """
    from urllib.parse import quote_plus
    from playwright.sync_api import sync_playwright

    query = f"{brand_name} official site products lighting"
    log(f"  [搜索] DuckDuckGo: {query}")

    # ── Step 1: DuckDuckGo Instant Answer API (fast, no JS needed) ──────────
    try:
        api_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_redirect=1&no_html=1"
        resp = requests.get(api_url, timeout=15, headers=HEADERS)
        data = resp.json()

        candidates = []
        # AbstractURL = recognized official site
        if data.get("AbstractURL"):
            candidates.append(data["AbstractURL"])
        # Results list
        for r in data.get("Results", []):
            if r.get("FirstURL"):
                candidates.append(r["FirstURL"])
        # RelatedTopics
        for r in data.get("RelatedTopics", []):
            if r.get("FirstURL"):
                candidates.append(r["FirstURL"])

        if candidates:
            homepage = candidates[0]
            log(f"  [找到] {homepage}")
            return homepage
    except Exception as e:
        log(f"  [API失败] {e}，切换到浏览器搜索")

    # ── Step 2: Playwright search on DuckDuckGo ──────────────────────────────
    log("  [浏览器搜索] 启动...")
    found_url = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(extra_http_headers=HEADERS)
        try:
            search_url = f"https://duckduckgo.com/?q={quote_plus(query)}&ia=web"
            page.goto(search_url, wait_until="networkidle", timeout=timeout * 1000)
            page.wait_for_timeout(2000)

            # Extract first organic result links
            results = page.eval_on_selector_all(
                'a[data-testid="result-title-a"], h2 a, .result__title a',
                'els => els.map(e => e.href).filter(h => h.startsWith("http"))'
            )
            # Filter out DuckDuckGo internal links
            organic = [u for u in results if "duckduckgo.com" not in u and "bing.com" not in u]
            if organic:
                found_url = organic[0]
                log(f"  [找到] {found_url}")
        except Exception as e:
            log(f"  [搜索失败] {e}")
        browser.close()

    return found_url


def find_catalog_page(homepage_url, timeout=30, headless=True):
    """
    Given a brand homepage, try to find the product catalog/listing page.
    Returns the best catalog URL, or homepage if none found.
    """
    log(f"  [查找产品页] {homepage_url}")
    try:
        html = render_page(homepage_url, timeout, headless)
        soup = BeautifulSoup(html, "html.parser")
        base_netloc = urlparse(homepage_url).netloc

        best = None
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            abs_url = href if href.startswith("http") else urljoin(homepage_url, href)
            if urlparse(abs_url).netloc not in (base_netloc, "www." + base_netloc, base_netloc.replace("www.", "")):
                continue
            if CATALOG_HINTS.search(abs_url):
                best = abs_url
                break

        if best:
            log(f"  [产品页] {best}")
            return best
    except Exception as e:
        log(f"  [查找失败] {e}")

    return homepage_url


# ══════════════════════════════════════════════════════════════════════════
# PRODUCT URL DISCOVERY — sitemap + pagination crawl
# ══════════════════════════════════════════════════════════════════════════

# Matches product pages from sitemaps. Two-tier approach:
# Tier 1 (high confidence): URLs with clear product path indicators
# Tier 2 (fallback): URLs with ≥3 path segments that aren't obviously non-product
_PRODUCT_URL_TIER1 = re.compile(
    r"("
    r"/product/[^/]+/[^/]+"           # /product/{sku}/{slug} (DeWalt)
    r"|/products/details/[^/]+"        # /products/details/{slug} (Milwaukee)
    r"|/products/[^/]+/products/[^/]+" # Shopify: /collections/{cat}/products/{slug}
    r"|/item/[^/]+"                    # /item/{id}
    r"|/detail/[^/]+"                  # /detail/{slug}
    r"|/p/[^/?#]+"                     # /p/{slug}
    r"|/pd/[^/?#]+"                    # /pd/{id}
    r"|/shop/product/[^/]+"            # /shop/product/{code} (Apple)
    r"|/collections/[^/]+/products/[^/]+" # Shopify generic
    r")",
    re.IGNORECASE,
)

# Pages to EXCLUDE from sitemap product discovery (non-product pages)
_SITEMAP_URL_SKIP = re.compile(
    r"(/blog|/news|/press|/about|/contact|/careers|/legal|/privacy|/terms"
    r"|/faq|/help|/support|/warranty|/recall|/login|/account|/cart|/checkout"
    r"|/search|/store-locator|/dealer|/where-to-buy|/events|/webinar"
    r"|/case-stud|/white-paper|/download|/software|/driver|/firmware"
    r"|/sitemap\.xml|/feed|/rss|\.(pdf|zip|doc|xls)$"
    r"|/tag/|/category/[^/]*$|/archive|/author/)",
    re.IGNORECASE,
)

def _is_product_url(url):
    """Check if a sitemap URL is likely a product page."""
    path = urlparse(url).path
    # Tier 1: high confidence patterns
    if _PRODUCT_URL_TIER1.search(path):
        return True
    # Tier 2: URL has ≥3 path segments and isn't obviously non-product
    segments = [s for s in path.strip("/").split("/") if s]
    if len(segments) >= 3 and not _SITEMAP_URL_SKIP.search(path):
        return True
    return False

# Keep old name for backward compatibility
_PRODUCT_URL_RE = _PRODUCT_URL_TIER1

# Sub-sitemaps to skip during product URL discovery (listing pages, articles, etc.)
_SITEMAP_SKIP_RE = re.compile(
    r"(listing_page|article|page|campaign|event|dealer|collection/sitemap|system/sitemap)",
    re.IGNORECASE,
)
_NEXT_PAGE_RE = re.compile(
    r"(next|page=\d|[?&]p=\d|/page/\d|\?pg=\d)",
    re.IGNORECASE,
)

def _is_product_url_crawl(url, base_netloc):
    """Used by discover_product_urls_by_crawl — checks domain + product path."""
    p = urlparse(url)
    if p.netloc and p.netloc.replace("www.", "") != base_netloc.replace("www.", ""):
        return False
    return bool(_PRODUCT_URL_RE.search(p.path))

def _find_next_page(soup, current_url):
    """Return the next-page URL from a pagination bar, or None."""
    # <link rel="next"> is most reliable
    link_next = soup.find("link", rel="next")
    if link_next and link_next.get("href"):
        return urljoin(current_url, link_next["href"])
    # <a rel="next"> or aria-label="Next"
    for a in soup.find_all("a", href=True):
        rel = (a.get("rel") or [])
        label = (a.get("aria-label") or "").lower()
        text = a.get_text(strip=True).lower()
        if "next" in rel or "next" in label or text in ("next", "→", ">", "»", "next page"):
            href = a["href"]
            if href and not href.startswith("#") and not href.startswith("javascript"):
                return urljoin(current_url, href)
    return None

def discover_product_urls_from_sitemap(origin, session, timeout=20):
    """
    Try sitemap.xml / sitemap_index.xml to get all product URLs.
    Handles three sitemap formats:
      1. Standard <sitemapindex> — sub-sitemaps in <sitemap><loc>
      2. Non-standard <urlset> listing sub-sitemap URLs (e.g. DeWalt)
      3. Regular <urlset> with product page URLs
    """
    import xml.etree.ElementTree as ET
    product_urls = []
    visited_sitemaps = set()
    sitemap_queue = []   # list of (url, xml_text)

    for path in ["/sitemap.xml", "/sitemap_index.xml", "/en/sitemap.xml",
                 "/sitemap_products_1.xml", "/sitemap/sitemap.xml"]:
        sm_url = origin + path
        try:
            r = session.get(sm_url, timeout=timeout)
            if r.status_code == 200 and ("<url>" in r.text or "<sitemap>" in r.text):
                sitemap_queue.append((sm_url, r.text))
                visited_sitemaps.add(sm_url)
                log(f"  [sitemap] 找到 {sm_url}")
                break
        except Exception:
            pass

    def _fetch_sitemap(url):
        if url in visited_sitemaps:
            return None
        visited_sitemaps.add(url)
        try:
            r = session.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        return None

    while sitemap_queue:
        sm_url, xml_text = sitemap_queue.pop(0)
        try:
            root_el = ET.fromstring(xml_text)
            ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Format 1: standard <sitemapindex>
            for sm in root_el.findall(".//s:sitemap/s:loc", ns):
                child_url = (sm.text or "").strip()
                if child_url:
                    content = _fetch_sitemap(child_url)
                    if content:
                        sitemap_queue.append((child_url, content))

            # Format 2 & 3: <urlset><url><loc>
            for loc in root_el.findall(".//s:url/s:loc", ns):
                url = (loc.text or "").strip()
                if not url:
                    continue
                # Non-standard: entry is itself a sub-sitemap (e.g. DeWalt)
                if url.endswith(".xml") and "sitemap" in url.lower():
                    # Skip non-product sub-sitemaps (listing pages, articles, etc.)
                    if _SITEMAP_SKIP_RE.search(url):
                        continue
                    content = _fetch_sitemap(url)
                    if content:
                        sitemap_queue.append((url, content))
                # Regular product page
                elif _is_product_url(url):
                    product_urls.append(url)
        except Exception:
            pass

    log(f"  [sitemap] 共发现 {len(product_urls)} 个产品URL")
    return product_urls


def discover_product_urls_by_crawl(start_url, timeout, headless, session, max_catalog_pages=50):
    """
    Crawl a brand's catalog pages (following pagination) to discover all product URLs.
    Does NOT visit individual product pages here — just collects their URLs.
    """
    base_netloc = urlparse(start_url).netloc
    catalog_visited = set()
    catalog_queue = [start_url]
    product_urls = []
    seen_products = set()

    NAV_SKIP = re.compile(
        r"(#|javascript:|mailto:|tel:"
        r"|/cart|/checkout|/account|/login|/register|/search"
        r"|/privacy|/terms|/legal|/about|/contact|/blog|/news|/faq"
        r"|/cdn-cgi|/wp-admin|/wp-login"
        r"|\.(pdf|zip|doc|xls|csv)$)",
        re.IGNORECASE,
    )

    while catalog_queue and len(catalog_visited) < max_catalog_pages:
        page_url = catalog_queue.pop(0)
        if page_url in catalog_visited:
            continue
        catalog_visited.add(page_url)
        log(f"  [crawl] 目录页 {len(catalog_visited)}/{max_catalog_pages}: {page_url}")

        try:
            html, _ = render_page_intercept(page_url, timeout, headless)
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            log(f"  [crawl] 跳过 {e}")
            continue

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or NAV_SKIP.search(href):
                continue
            abs_url = href if href.startswith("http") else urljoin(page_url, href)
            p = urlparse(abs_url)
            if p.netloc.replace("www.", "") != base_netloc.replace("www.", ""):
                continue
            if _is_product_url_crawl(abs_url, base_netloc):
                clean = abs_url.split("?")[0].split("#")[0]
                if clean not in seen_products:
                    seen_products.add(clean)
                    product_urls.append(abs_url)

        # Follow pagination
        next_pg = _find_next_page(soup, page_url)
        if next_pg and next_pg not in catalog_visited:
            catalog_queue.insert(0, next_pg)   # depth-first pagination

    log(f"  [crawl] 共发现 {len(product_urls)} 个产品URL（浏览了{len(catalog_visited)}个目录页）")
    return product_urls


# ══════════════════════════════════════════════════════════════════════════
# UNIVERSAL SCRAPER (any website)
# ══════════════════════════════════════════════════════════════════════════

def scrape_universal(start_url, topic, download_root, limit, timeout, headless, session):
    """
    Generic scraper for any website.
    Strategy:
      1. Load the start URL and collect product/item links (anchor tags with meaningful paths)
      2. For each linked page, use universal_extract_images to find hi-res images
      3. If no sub-links found, treat the start URL itself as the single product page
    """
    log(f"\n{'='*60}")
    log(f"[通用模式] {start_url}")

    # Step 1: load start page, discover product links
    start_html, start_intercepted = render_page_intercept(start_url, timeout, headless)
    soup = BeautifulSoup(start_html, "html.parser")
    base_netloc = urlparse(start_url).netloc

    # Collect candidate product links (same domain, not nav/utility pages)
    NAV_SKIP = re.compile(
        r"(#|javascript:|mailto:|tel:"
        r"|/cart|/checkout|/account|/login|/register|/search"
        r"|/privacy|/terms|/legal|/about|/contact|/blog|/news|/faq"
        r"|/cdn-cgi|/wp-admin|/wp-login"
        r"|\.(pdf|zip|doc|xls|csv)$)",
        re.IGNORECASE,
    )

    seen_links = set()
    product_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or NAV_SKIP.search(href):
            continue
        abs_url = href if href.startswith("http") else urljoin(start_url, href)
        parsed = urlparse(abs_url)
        # Same domain only, path must have depth >= 2 (e.g. /products/item-name)
        netloc = parsed.netloc
        if netloc not in (base_netloc, "www." + base_netloc, base_netloc.replace("www.", "")):
            continue
        path = parsed.path.rstrip("/")
        if path.count("/") < 1 or abs_url == start_url:
            continue
        if abs_url not in seen_links:
            seen_links.add(abs_url)
            product_links.append(abs_url)

    if not product_links:
        # Treat start URL as the single product page
        log("  未发现子链接，将当前页作为产品页处理")
        product_links = [start_url]

    # Prioritise URLs that look like product detail pages
    _PRODUCT_PATH = re.compile(
        r"/(product|item|detail|sku|buy|shop/[^/]+/[^/]+|collections/[^/]+/products/)",
        re.IGNORECASE,
    )
    product_links.sort(key=lambda u: 0 if _PRODUCT_PATH.search(u) else 1)

    log(f"  发现 {len(product_links)} 个候选页，抓取前 {min(limit, len(product_links))} 个")

    results = []
    for i, prod_url in enumerate(product_links[:limit]):
        slug = urlparse(prod_url).path.rstrip("/").split("/")[-1] or f"item_{i+1}"
        log(f"  [{i+1}/{min(limit, len(product_links))}] {slug}")
        try:
            if prod_url == start_url:
                prod_html, intercepted = start_html, start_intercepted
            else:
                prod_html, intercepted = render_page_intercept(prod_url, timeout, headless)

            real_name = extract_product_name(prod_html, "reddot") or slug
            model_code = extract_model_code(real_name)
            log(f"    产品: {real_name}  →  型号: {model_code}")

            # A+B: breadcrumb first, nav category (topic) as fallback
            crumbs = extract_breadcrumbs(prod_html, prod_url)
            log(f"    分类: {crumbs or topic}")

            cat_folder = build_category_folder(crumbs, nav_category=topic)
            prefix = build_image_prefix(model_code)

            images = universal_extract_images(prod_html, prod_url, intercepted=intercepted)
            log(f"    找到 {len(images)} 张图")

            if download_root and images:
                folder = Path(download_root) / cat_folder / model_code
                folder.mkdir(parents=True, exist_ok=True)
                ok = 0
                for j, img_url in enumerate(images):
                    ext = Path(urlparse(img_url).path).suffix.lower() or ".jpg"
                    if ext not in _IMG_EXTS:
                        ext = ".jpg"
                    fname = f"{prefix}_{j+1:02d}{ext}"
                    dest = folder / fname
                    if download_image(img_url, dest, session):
                        if is_valid_image(dest, min_px=500):
                            ok += 1
                            log(f"    [OK] {fname}")
                        else:
                            dest.unlink(missing_ok=True)
                            log(f"    [过滤] {fname}")
                log(f"    下载 {ok}/{len(images)} 张 -> {folder}")

            results.append({"product": real_name, "url": prod_url, "images": images,
                            "category": crumbs or [topic]})
        except Exception as e:
            log(f"    [跳过] {e}")
        time.sleep(1)
    return results


def _count_downloaded(download_root):
    """Count image files actually saved under download_root."""
    if not download_root:
        return 0
    root = Path(download_root)
    if not root.exists():
        return 0
    return sum(1 for f in root.rglob("*") if f.suffix.lower() in _IMG_EXTS)


# ══════════════════════════════════════════════════════════════════════════
# BRAND ALLOWED CATEGORIES — per-brand whitelist (None = no filter)
# ══════════════════════════════════════════════════════════════════════════

_BRAND_ALLOWED_CATEGORIES = {
    # 灯具
    "artemide":         ["台灯", "落地灯", "吊灯", "壁灯", "吸顶灯", "户外灯"],
    "foscarini":        ["台灯", "落地灯", "吊灯", "壁灯"],
    "louis_poulsen":    ["台灯", "落地灯", "吊灯", "壁灯", "户外灯"],
    "flos":             ["台灯", "落地灯", "吊灯", "壁灯", "吸顶灯"],
    "bega":             ["户外灯", "室内灯"],
    "philips_lighting": ["LED灯泡", "LED灯管", "LED灯", "智能灯"],
    "nitecore":         ["手电筒", "头灯", "营地灯", "信号灯", "钥匙灯", "帽夹灯", "工作灯"],
    "biolite":          ["户外灯", "营地灯", "头灯", "充电设备", "户外炊具"],
    "rab_lighting":     ["户外灯", "场地灯", "泛光灯", "壁灯", "庭院灯", "车库灯"],
    "wac_lighting":     ["户外灯", "轨道灯", "筒灯", "吊灯"],
    "ifdesign_lighting": None,
    # 电动工具
    "dewalt":              None,
    "milwaukee":           ["电钻", "电锯", "角磨机", "砂光机", "多功能工具", "混凝土设备", "管道工具", "电池系统", "手动工具", "照明", "存储设备", "园林工具", "剪板机"],
    "makita":              ["电钻", "电锯", "角磨机", "砂光机", "多功能工具", "园林工具", "充电器"],
    "bosch_professional":  ["电钻", "电锯", "角磨机", "砂光机", "铣", "测量工具"],
    # 消费电子
    "apple":    ["笔记本", "台式机", "平板", "手机", "智能手表", "耳机", "音箱", "显示器", "键盘", "鼠标"],
    "logitech": ["鼠标", "键盘", "键鼠套装", "耳机", "摄像头", "音箱"],
    "sony":     ["耳机", "音箱", "相机", "电视", "游戏设备"],
    # 音箱
    "sonos":        ["智能音箱", "条形音箱", "低音炮", "便携音箱", "耳机"],
    "bose":         ["蓝牙音箱", "智能音箱", "条形音箱", "耳机", "降噪耳机"],
    "bang_olufsen": ["蓝牙音箱", "耳机", "电视", "条形音箱"],
    # 户外装备
    "garmin": ["运动手表", "户外设备", "船用设备", "健身设备"],
    "olight": ["手电筒", "头灯", "营地灯"],
    "yeti":   ["保温杯", "保温箱", "户外包袋"],
    # 小家电
    "shark":  ["吸尘器", "扫地机器人", "蒸汽拖把", "空气净化器"],
    "tineco": ["洗地机", "吸尘器", "吹风机"],
    "dyson":  ["吸尘器", "吹风机", "卷发器", "空气净化器", "台灯"],
    # 医疗
    "braun": ["剃须刀", "电动牙刷", "脱毛器", "体温计"],
    "omron": ["血压计", "理疗仪", "呼吸设备", "体重秤"],
}

# ══════════════════════════════════════════════════════════════════════════
# BRAND CATEGORY MAPPING — English breadcrumbs → Chinese 2-level hierarchy
# ══════════════════════════════════════════════════════════════════════════

# 品类映射表：英文关键词 → (大类, 小类)
# 每个品类覆盖该品类下所有品牌的产品线
_BRAND_CATEGORY_MAP = {
    # ── 电动工具 ─────────────────────────────────────────────────────────
    "drill": ("电钻", None),
    "hammer drill": ("电钻", "锤钻"),
    "impact drill": ("电钻", "冲击钻"),
    "cordless drill": ("电钻", "充电电钻"),
    "driver": ("电钻", "螺丝刀"),
    "impact driver": ("电钻", "冲击起子"),
    "impact wrench": ("扳手", "冲击扳手"),
    "wrench": ("扳手", None),
    "saw": ("电锯", None),
    "circular saw": ("电锯", "圆锯"),
    "reciprocating saw": ("电锯", "往复锯"),
    "jig saw": ("电锯", "曲线锯"),
    "jigsaw": ("电锯", "曲线锯"),
    "miter saw": ("电锯", "斜切锯"),
    "table saw": ("电锯", "台锯"),
    "band saw": ("电锯", "带锯"),
    "chainsaw": ("电锯", "链锯"),
    "grinder": ("角磨机", None),
    "angle grinder": ("角磨机", None),
    "sander": ("砂光机", None),
    "orbital sander": ("砂光机", "轨道砂光机"),
    "belt sander": ("砂光机", "砂带机"),
    "planer": ("刨", "电刨"),
    "router": ("铣", "修边机"),
    "rotary tool": ("铣", "旋转工具"),
    "nail gun": ("钉枪", None),
    "nailer": ("钉枪", None),
    "stapler": ("钉枪", "订书机"),
    "blower": ("吹风设备", "吹叶机"),
    "trimmer": ("园林工具", "修剪机"),
    "string trimmer": ("园林工具", "打草机"),
    "lawn mower": ("园林工具", "割草机"),
    "mower": ("园林工具", "割草机"),
    "hedge trimmer": ("园林工具", "绿篱机"),
    "pressure washer": ("清洗设备", "高压清洗机"),
    "vacuum": ("吸尘设备", "工业吸尘器"),
    "dust extractor": ("吸尘设备", "除尘器"),
    "flashlight": ("照明", "手电筒"),
    "work light": ("照明", "工作灯"),
    "laser": ("测量工具", "激光仪"),
    "level": ("测量工具", "水平仪"),
    "measuring": ("测量工具", None),
    "multitool": ("多功能工具", None),
    "oscillating": ("多功能工具", "摆动工具"),
    "heat gun": ("热工具", "热风枪"),
    "soldering": ("热工具", "焊接工具"),
    "battery": ("电池系统", None),
    "charger": ("电池系统", "充电器"),
    "power station": ("电池系统", "移动电站"),
    "radio": ("工地设备", "工地收音机"),
    "speaker": ("工地设备", "工地音箱"),
    "fan": ("工地设备", "工地风扇"),
    "jobsite fan": ("工地设备", "工地风扇"),
    # ── 电动工具补充（DeWalt/Milwaukee/Makita/Bosch） ────────────────────
    "impact driver": ("电钻", "冲击起子"),
    "cordless screwdriver": ("电钻", "电动螺丝刀"),
    "drywall screw gun": ("电钻", "石膏板螺丝枪"),
    "magnetic drill": ("电钻", "磁座钻"),
    "drill press": ("电钻", "台钻"),
    "core drill": ("电钻", "取芯钻"),
    "chop saw": ("电锯", "型材切割锯"),
    "concrete saw": ("电锯", "混凝土锯"),
    "tile saw": ("电锯", "瓷砖锯"),
    "masonry saw": ("电锯", "石材锯"),
    "pole saw": ("电锯", "高枝锯"),
    "hand saw": ("手动工具", "手锯"),
    "die grinder": ("角磨机", "模具磨"),
    "bench grinder": ("角磨机", "台式砂轮机"),
    "band file": ("角磨机", "带式锉"),
    "cut off tool": ("角磨机", "切割工具"),
    "cut tool": ("角磨机", "切割工具"),
    "polisher": ("抛光机", None),
    "shear": ("剪板机", None),
    "nibbler": ("剪板机", "冲剪机"),
    "framing nailer": ("钉枪", "框架钉枪"),
    "oscillating tool": ("多功能工具", "摆动工具"),
    "cut out tool": ("多功能工具", "切割工具"),
    "caulk gun": ("胶枪", None),
    "adhesive gun": ("胶枪", None),
    "compressor": ("气动设备", "空气压缩机"),
    "air tool": ("气动设备", None),
    "air drill": ("气动设备", "气动钻"),
    "air ratchet": ("气动设备", "气动棘轮"),
    "air sander": ("气动设备", "气动砂光机"),
    "cable cutter": ("电工工具", "电缆剪"),
    "cable stripper": ("电工工具", "剥线钳"),
    "crimping tool": ("电工工具", "压接工具"),
    "knockout tool": ("电工工具", "打孔工具"),
    "threaded rod cutter": ("电工工具", "螺杆切断器"),
    "drain cleaning": ("管道工具", "排水管清洁"),
    "pex tool": ("管道工具", "PEX工具"),
    "pipe press": ("管道工具", "管道压接"),
    "pipe threading": ("管道工具", "管道套丝"),
    "plumbing tool": ("管道工具", None),
    "concrete screed": ("混凝土设备", "混凝土抹光机"),
    "concrete vibrator": ("混凝土设备", "混凝土振动器"),
    "plate compactor": ("混凝土设备", "平板夯"),
    "rammer": ("混凝土设备", "冲击夯"),
    "dust extractor": ("吸尘设备", "除尘器"),
    "dust management": ("吸尘设备", None),
    "lifting": ("起重工具", None),
    "jack": ("起重工具", "千斤顶"),
    # ── 手动工具 ─────────────────────────────────────────────────────────
    "hammer": ("手动工具", "锤子"),
    "claw hammer": ("手动工具", "羊角锤"),
    "framing hammer": ("手动工具", "框架锤"),
    "axe": ("手动工具", "斧头"),
    "clamp": ("手动工具", "夹具"),
    "vise": ("手动工具", "台钳"),
    "plier": ("手动工具", "钳子"),
    "wrench": ("手动工具", "扳手"),
    "adjustable wrench": ("手动工具", "活动扳手"),
    "torque wrench": ("手动工具", "扭矩扳手"),
    "combination wrench": ("手动工具", "组合扳手"),
    "ratchet": ("手动工具", "棘轮"),
    "socket": ("手动工具", "套筒"),
    "hex key": ("手动工具", "内六角"),
    "screwdriver": ("手动工具", "螺丝刀"),
    "nut driver": ("手动工具", "套筒起子"),
    "chisel": ("手动工具", "凿子"),
    "punch": ("手动工具", "冲子"),
    "pry bar": ("手动工具", "撬棍"),
    "scraper": ("手动工具", "刮刀"),
    "knife": ("手动工具", "刀具"),
    "utility knife": ("手动工具", "美工刀"),
    "folding knife": ("手动工具", "折叠刀"),
    "snap knife": ("手动工具", "美工刀"),
    "tape measure": ("测量工具", "卷尺"),
    "stud finder": ("测量工具", "探测仪"),
    "square": ("测量工具", "角尺"),
    "rivet": ("手动工具", "铆钉枪"),
    "staple gun": ("手动工具", "订枪"),
    "tap": ("手动工具", "丝锥"),
    "die": ("手动工具", "板牙"),
    "magnetic tool": ("手动工具", "磁力工具"),
    "ratchet strap": ("手动工具", "棘轮绑带"),
    # ── 户外电动设备 ─────────────────────────────────────────────────────
    "generator": ("户外电动", "发电机"),
    "lawn mower": ("户外电动", "割草机"),
    "push mower": ("户外电动", "手推割草机"),
    "self propelled mower": ("户外电动", "自走割草机"),
    "leaf blower": ("户外电动", "吹叶机"),
    "snow blower": ("户外电动", "除雪机"),
    "snow removal": ("户外电动", "除雪设备"),
    "sump pump": ("户外电动", "排水泵"),
    "extension cord": ("户外配件", "延长线"),
    "ladder": ("户外配件", "梯子"),
    "garden hose": ("户外配件", "花园水管"),
    "sprayer": ("户外配件", "喷雾器"),
    "shovel": ("户外配件", "铲子"),
    "rake": ("户外配件", "耙子"),
    "garden hoe": ("户外配件", "锄头"),
    # ── 存储组织 ─────────────────────────────────────────────────────────
    "tool bag": ("存储设备", "工具包"),
    "tool belt": ("存储设备", "工具腰带"),
    "tool box": ("存储设备", "工具箱"),
    "tool cabinet": ("存储设备", "工具柜"),
    "storage": ("存储设备", None),
    "shelf": ("存储设备", "置物架"),
    "cart": ("存储设备", "推车"),
    "dolly": ("存储设备", "搬运车"),
    "bucket": ("存储设备", "工具桶"),
    "tote": ("存储设备", "收纳箱"),
    "cooler": ("存储设备", "保温箱"),
    # ── 小家电 ───────────────────────────────────────────────────────────
    "vacuum cleaner": ("吸尘器", None),
    "stick vacuum": ("吸尘器", "手持吸尘器"),
    "handheld vacuum": ("吸尘器", "手持吸尘器"),
    "robot vacuum": ("吸尘器", "扫地机器人"),
    "upright vacuum": ("吸尘器", "立式吸尘器"),
    "canister vacuum": ("吸尘器", "桶式吸尘器"),
    "cordless vacuum": ("吸尘器", "无线吸尘器"),
    "wet dry vacuum": ("吸尘器", "干湿吸尘器"),
    "hair dryer": ("吹风机", None),
    "dryer": ("吹风机", None),
    "styler": ("美发工具", "造型器"),
    "straightener": ("美发工具", "直发器"),
    "curler": ("美发工具", "卷发器"),
    "air purifier": ("空气净化器", None),
    "purifier": ("空气净化器", None),
    "humidifier": ("空气净化器", "加湿器"),
    "heater": ("取暖设备", None),
    "fan": ("风扇", None),
    "floor washer": ("清洁机", "洗地机"),
    "mop": ("清洁机", "拖把机"),
    "steam": ("清洁机", "蒸汽清洁机"),
    # ── 消费电子 ─────────────────────────────────────────────────────────
    "macbook": ("笔记本", "MacBook"),
    "laptop": ("笔记本", None),
    "imac": ("台式机", "iMac"),
    "mac mini": ("台式机", "Mac mini"),
    "mac pro": ("台式机", "Mac Pro"),
    "mac studio": ("台式机", "Mac Studio"),
    "ipad": ("平板", "iPad"),
    "tablet": ("平板", None),
    "iphone": ("手机", "iPhone"),
    "phone": ("手机", None),
    "watch": ("智能手表", None),
    "apple watch": ("智能手表", "Apple Watch"),
    "keyboard": ("键盘", None),
    "mouse": ("鼠标", None),
    "trackpad": ("鼠标", "触控板"),
    "webcam": ("摄像头", "网络摄像头"),
    "camera": ("摄像头", None),
    "monitor": ("显示器", None),
    "display": ("显示器", None),
    "headset": ("耳机", "头戴耳机"),
    "headphone": ("耳机", "头戴耳机"),
    "earbuds": ("耳机", "真无线耳机"),
    "earphone": ("耳机", None),
    "airpods": ("耳机", "AirPods"),
    "controller": ("游戏设备", "手柄"),
    "gamepad": ("游戏设备", "手柄"),
    "streaming": ("游戏设备", "直播设备"),
    "microphone": ("音频设备", "麦克风"),
    # ── 音箱 ─────────────────────────────────────────────────────────────
    "portable speaker": ("蓝牙音箱", "便携音箱"),
    "bluetooth speaker": ("蓝牙音箱", None),
    "smart speaker": ("智能音箱", None),
    "home speaker": ("智能音箱", "家用音箱"),
    "soundbar": ("条形音箱", None),
    "sound bar": ("条形音箱", None),
    "subwoofer": ("低音炮", None),
    "surround": ("家庭影院", "环绕音箱"),
    "home theater": ("家庭影院", None),
    "home theatre": ("家庭影院", None),
    "noise cancelling": ("耳机", "降噪耳机"),
    "over-ear": ("耳机", "头戴耳机"),
    "on-ear": ("耳机", "头戴耳机"),
    "in-ear": ("耳机", "入耳式耳机"),
    "true wireless": ("耳机", "真无线耳机"),
    "earbud": ("耳机", "真无线耳机"),
    "turntable": ("音频设备", "唱片机"),
    "amplifier": ("音频设备", "功放"),
    # ── 户外装备 ─────────────────────────────────────────────────────────
    "cooler": ("保温容器", "保温箱"),
    "tumbler": ("保温容器", "保温杯"),
    "bottle": ("保温容器", "保温瓶"),
    "mug": ("保温容器", "马克杯"),
    "jug": ("保温容器", "保温壶"),
    "bag": ("户外包袋", None),
    "backpack": ("户外包袋", "背包"),
    "flashlight": ("手电筒", None),
    "torch": ("手电筒", None),
    "headlamp": ("手电筒", "头灯"),
    "lantern": ("手电筒", "营地灯"),
    "gps": ("导航设备", "GPS"),
    "watch": ("运动手表", None),
    "fitness": ("运动手表", "健身手环"),
    "cycling": ("运动设备", "骑行设备"),
    "running": ("运动设备", "跑步设备"),
    "golf": ("运动设备", "高尔夫设备"),
    "fish finder": ("户外电子", "鱼探"),
    "marine": ("户外电子", "船用设备"),
    "dash cam": ("户外电子", "行车记录仪"),
    "action camera": ("户外电子", "运动相机"),
    # ── 医疗设备 ─────────────────────────────────────────────────────────
    "shaver": ("剃须刀", None),
    "razor": ("剃须刀", None),
    "electric shaver": ("剃须刀", "电动剃须刀"),
    "beard trimmer": ("剃须刀", "修剪器"),
    "groomer": ("剃须刀", "修剪器"),
    "toothbrush": ("口腔护理", "电动牙刷"),
    "oral": ("口腔护理", None),
    "blood pressure": ("健康监测", "血压计"),
    "thermometer": ("健康监测", "体温计"),
    "nebulizer": ("健康监测", "雾化器"),
    "tens": ("健康监测", "理疗仪"),
    "body composition": ("健康监测", "体脂秤"),
    "scale": ("健康监测", "体重秤"),
    "iron": ("家用电器", "熨斗"),
    "epilator": ("美容仪器", "脱毛器"),
    "ipl": ("美容仪器", "IPL脱毛仪"),
    "hair removal": ("美容仪器", "脱毛器"),
    # ── URL path segment matches (DeWalt/brand category pages) ───────────
    "anchors fasteners": ("紧固工具", "锚栓紧固件"),
    "fastener": ("紧固工具", "紧固工具"),
    "drywall tools": ("手动工具", "石膏板工具"),
    "drywall": ("手动工具", "石膏板工具"),
    "clamps vises": ("手动工具", "夹具"),
    "pliers": ("手动工具", "钳子"),
    "hand saws": ("手动工具", "手锯"),
    "wrecking pry bars": ("手动工具", "撬棍"),
    "hex keys": ("手动工具", "内六角"),
    "sockets ratchets": ("手动工具", "套筒"),
    "taps dies": ("手动工具", "丝锥"),
    "knives blades": ("手动工具", "刀具"),
    "lifting jack tools": ("起重工具", "起重工具"),
    "cable cutting crimping": ("电工工具", "电工工具"),
    "cable cutting": ("电工工具", "电工工具"),
    "sheers nibblers": ("剪板机", "剪板机"),
    "concrete equipment": ("混凝土设备", "混凝土设备"),
    "woodworking tools": ("木工工具", "木工工具"),
    "woodworking": ("木工工具", "木工工具"),
    "tool belts": ("存储设备", "工具腰带"),
    "buckets totes": ("存储设备", "收纳箱"),
    "utility carts dollies": ("存储设备", "推车"),
    "utility carts": ("存储设备", "推车"),
    "outdoor combo kits": ("户外电动", "套装"),
    "combo kit": ("户外电动", "套装"),
    "snow removal equipment": ("户外电动", "除雪设备"),
    "sump utility pumps": ("户外电动", "排水泵"),
    "sump pump": ("户外电动", "排水泵"),
    "cordless ratchets": ("电钻", "电动棘轮"),
    "cordless ratchet": ("电钻", "电动棘轮"),
    "polishers": ("抛光机", "抛光机"),
    "jobsite fans": ("工地设备", "工地风扇"),
    "jobsite fan": ("工地设备", "工地风扇"),
    "radios speakers": ("工地设备", "工地音箱"),
    "power stations": ("电池系统", "移动电站"),
    "adapters": ("电池系统", "适配器"),
    "battery charger kits": ("电池系统", "充电器套装"),
    "battery charger kit": ("电池系统", "充电器套装"),
    # ── Broader pattern matches for URL paths ────────────────────────────
    "plumbing": ("管道工具", "管道工具"),
    "concrete": ("混凝土设备", "混凝土设备"),
    "cable": ("电工工具", "电工工具"),
    # ── 灯具（住宅/商业照明） ─────────────────────────────────────────
    "table lamp": ("台灯", "台灯"),
    "desk lamp": ("台灯", "工作台灯"),
    "reading lamp": ("台灯", "阅读灯"),
    "floor lamp": ("落地灯", "落地灯"),
    "pendant": ("吊灯", "吊灯"),
    "suspension": ("吊灯", "吊灯"),
    "chandelier": ("吊灯", "枝形吊灯"),
    "wall lamp": ("壁灯", "壁灯"),
    "sconce": ("壁灯", "壁灯"),
    "wall light": ("壁灯", "壁灯"),
    "ceiling lamp": ("吸顶灯", "吸顶灯"),
    "ceiling light": ("吸顶灯", "吸顶灯"),
    "flush mount": ("吸顶灯", "吸顶灯"),
    "recessed": ("筒灯", "筒灯"),
    "downlight": ("筒灯", "筒灯"),
    "spot light": ("射灯", "射灯"),
    "spotlight": ("射灯", "射灯"),
    "track light": ("轨道灯", "轨道灯"),
    "track lighting": ("轨道灯", "轨道灯"),
    "outdoor light": ("户外灯", "户外灯"),
    "outdoor lamp": ("户外灯", "户外灯"),
    "garden light": ("户外灯", "庭院灯"),
    "bollard": ("户外灯", "庭院灯"),
    "path light": ("户外灯", "路灯"),
    "flood light": ("户外灯", "泛光灯"),
    "floodlight": ("户外灯", "泛光灯"),
    "area light": ("户外灯", "场地灯"),
    "led bulb": ("LED灯", "LED灯泡"),
    "led tube": ("LED灯", "LED灯管"),
    "led strip": ("LED灯", "LED灯带"),
    "smart light": ("智能灯", "智能灯"),
    "smart bulb": ("智能灯", "智能灯泡"),
    "hue": ("智能灯", "Hue系列"),
    # ── 灯具 URL path 补充 ───────────────────────────────────────────
    "table": ("台灯", "台灯"),
    "floor": ("落地灯", "落地灯"),
    "wall-ceiling": ("壁灯", "壁灯"),
    "outdoor": ("户外灯", "户外灯"),
    "luminaire": ("灯具", "灯具"),
    "lighting": ("照明", "照明"),
    # ── 中文关键词（中文品牌站/nitecore.cn等）─────────────────────────
    "\u5934\u706f": ("\u624b\u7535\u7b52", "\u5934\u706f"),
    "手电": ("手电筒", "手电筒"),
    "钥匙灯": ("手电筒", "钥匙灯"),
    "营地灯": ("手电筒", "营地灯"),
    "信号灯": ("手电筒", "信号灯"),
    "帽夹灯": ("手电筒", "帽夹灯"),
    "工作灯": ("照明", "工作灯"),
    "台灯": ("台灯", "台灯"),
    "吊灯": ("吊灯", "吊灯"),
    "壁灯": ("壁灯", "壁灯"),
    "落地灯": ("落地灯", "落地灯"),
    "吸顶灯": ("吸顶灯", "吸顶灯"),
    "射灯": ("射灯", "射灯"),
    "筒灯": ("筒灯", "筒灯"),
    "户外灯": ("户外灯", "户外灯"),
    "庭院灯": ("户外灯", "庭院灯"),
    "智能灯": ("智能灯", "智能灯"),
    "充电器": ("充电设备", "充电器"),
    "电池": ("充电设备", "电池"),
}

# Products to SKIP (accessories, consumables, not core products)
_ACCESSORY_SKIP = re.compile(
    r"(replacement|refill|filter|bag|strap|band|case|cover|sleeve|mount"
    r"|adapter|cable|charger\s+only|cord|attachment|accessory|accessories"
    r"|lens|mask|glove|gogg|boot|shoe|sock|vest|jacket|pant|shirt|hat|cap"
    r"|apron|holster|pouch|belt|lanyard|hook|clip|clamp|nail|screw|bit\b"
    r"|blade\b|pad\b|disc|wheel|brush\s+head|tip\b|nozzle|hose"
    r"|cartridge|toner|ink\b|paper\b|label|tape\b|wire\b|staple"
    r"|ear\s*plug|face\s*mask|respirator|hard\s*hat|helmet\b"
    r"|replacement\s+lense|shield\s+replacement)",
    re.IGNORECASE,
)

# Pages to SKIP (non-product pages that slip through URL filter)
_NON_PRODUCT_PAGE_SKIP = re.compile(
    r"(404|error|not.found|sitemap|search|login|account|cart|checkout"
    r"|privacy|terms|legal|about|contact|blog|news|faq|support|warranty"
    r"|recall|register|dealer|retailer|store.locator|service.center"
    r"|all.locations|built.for|campaign|event|collection$|system$"
    r"|giveaway|sweepstake|contest|promo)",
    re.IGNORECASE,
)

# User-Agent rotation pool
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


def _classify_brand_product(product_name, breadcrumbs, brand_name=None):
    """
    Map product name + breadcrumbs to (大类, 小类) using _BRAND_CATEGORY_MAP.
    If brand_name is provided, only returns categories in that brand's whitelist.
    Returns None if no valid match found (caller should skip/discard the image).
    """
    text = (product_name + " " + " ".join(breadcrumbs)).lower()

    # Get brand whitelist (None = allow all)
    allowed = None
    if brand_name and brand_name in _BRAND_ALLOWED_CATEGORIES:
        allowed = _BRAND_ALLOWED_CATEGORIES[brand_name]

    # Sort by key length descending so "circular saw" matches before "saw"
    candidates = sorted(_BRAND_CATEGORY_MAP.keys(), key=len, reverse=True)
    for keyword in candidates:
        if keyword in text:
            major, minor = _BRAND_CATEGORY_MAP[keyword]

            # Check whitelist: skip if category not allowed for this brand
            check_cat = minor or major
            if allowed is not None and check_cat not in allowed and major not in allowed:
                continue

            return (major, minor)

    return None


def scrape_brand_via_category_pages(category_page_urls, download_root, timeout, headless, session,
                                    min_px=600):
    """
    Scrape a brand by visiting its CATEGORY LISTING pages (not individual product pages).
    Used for heavy SPA sites (DeWalt, etc.) where product pages don't render properly.

    Strategy:
      1. Visit each category listing page with Playwright
      2. Extract product image URLs from the grid (thumbnails)
      3. Upgrade thumbnail URLs to highest available resolution
      4. Classify based on the category page URL structure
      5. Download with sequential numbering per subfolder
    """
    import hashlib, random
    from bs4 import BeautifulSoup

    folder_counters = {}
    seen_hashes = set()
    seen_img_urls = set()
    seen_skus = set()  # Dedup by product SKU extracted from CDN filename
    results = []
    total_ok = [0]

    _SKU_RE = re.compile(r'([A-Z]{2,}[\w-]*\d[\w-]*)(?:_\d+)?\.(?:webp|jpg|jpeg|png)', re.IGNORECASE)

    def _extract_sku_from_url(url):
        """Extract product SKU from CDN URL filename, e.g. DCD706B from DCD706B_1_1280.webp"""
        fname = urlparse(url).path.rsplit("/", 1)[-1]
        m = _SKU_RE.match(fname)
        if m:
            # Normalize: strip trailing size suffix like _1280, _320
            sku = re.sub(r'_\d{3,4}$', '', m.group(1))
            return sku.upper()
        return None

    def _upgrade_dewalt_thumbnail(url):
        """Upgrade DeWalt CDN thumbnails: _320.webp → _1280.webp"""
        return re.sub(r'_320\.(webp|jpg|png)', r'_1280.\1', url)

    def _extract_category_from_url(url):
        """Extract 2-level Chinese category from listing page URL path."""
        path = urlparse(url).path.rstrip("/")
        parts = [p for p in path.split("/") if p and p not in ("en-us", "en", "products")]
        text = " ".join(parts).replace("-", " ").replace("_", " ")
        return _classify_brand_product(text, parts)

    def _on_category_page(page_url, html, intercepted):
        soup = BeautifulSoup(html, "html.parser")
        major, minor = _extract_category_from_url(page_url)

        # Extract product images using universal extractor (works for all brands)
        all_images = universal_extract_images(html, page_url, intercepted=intercepted)
        product_imgs = []
        for img_url in all_images:
            if UNIVERSAL_SKIP.search(img_url):
                continue
            upgraded = _upgrade_dewalt_thumbnail(img_url)
            if upgraded in seen_img_urls:
                continue
            sku = _extract_sku_from_url(upgraded)
            if sku and sku in seen_skus:
                continue
            seen_img_urls.add(upgraded)
            if sku:
                seen_skus.add(sku)
            product_imgs.append(upgraded)

        if not product_imgs:
            return

        # Download
        folder_key = f"{major}/{minor}" if minor else major
        folder = Path(download_root) / major / minor if minor else Path(download_root) / major
        folder.mkdir(parents=True, exist_ok=True)

        if folder_key not in folder_counters:
            existing = len([f for f in folder.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png')])
            folder_counters[folder_key] = existing

        ok_this = 0
        for img_url in product_imgs:
            counter = folder_counters.get(folder_key, 0) + 1
            dest = folder / f"{counter:02d}.jpg"
            if not download_image(img_url, dest, session):
                dest.unlink(missing_ok=True)
                continue
            dest = Path(convert_webp_to_jpg(dest))
            if not is_valid_image(dest, min_px=min_px):
                dest.unlink(missing_ok=True)
                continue
            try:
                h = hashlib.md5(dest.read_bytes()).hexdigest()
                if h in seen_hashes:
                    dest.unlink(missing_ok=True)
                    continue
                seen_hashes.add(h)
            except Exception:
                pass
            folder_counters[folder_key] = counter
            ok_this += 1
            total_ok[0] += 1

        if ok_this > 0:
            results.append({"category": [major, minor], "images_saved": ok_this})
            log(f"    {major}/{minor}: {ok_this} 张")

    log(f"\n  [品类列表爬取] 共 {len(category_page_urls)} 个分类页")
    render_pages_batch(category_page_urls, timeout, headless, _on_category_page, delay=2.0)

    log(f"\n  [brand] 完成: {total_ok[0]} 张图片")
    for fk, cnt in sorted(folder_counters.items()):
        if cnt > 0:
            log(f"    {fk}: {cnt} 张")
    return results


def scrape_brand_with_fallback(brand_url, topic, download_root, limit, timeout, headless, session,
                               images_per_product=2):
    """
    Full-coverage brand scraper matching Red Dot/iF output format:
      - Two-level Chinese folder hierarchy: 大类/小类/
      - Sequential numbering per subfolder: 01.jpg, 02.jpg...
      - Max 2 images per product, min 1500px, jpg/png only
      - Product verification: skip accessories, non-product pages
      - Anti-bot: random delays, User-Agent rotation, 429 retry
    """
    import random, hashlib
    parsed = urlparse(brand_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    # ── Phase 0: check for category listing pages in sitemap ────────────────
    # Heavy SPA sites (DeWalt, etc.) serve empty product pages but render
    # category listing pages with product grids. Use those instead.
    try:
        import xml.etree.ElementTree as ET
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        listing_urls = []
        r = session.get(origin + "/sitemap.xml", timeout=20)
        if r.status_code == 200:
            root_el = ET.fromstring(r.text)
            for loc in root_el.findall(".//s:url/s:loc", ns):
                u = (loc.text or "").strip()
                if "listing_page" in u and u.endswith(".xml"):
                    try:
                        r2 = session.get(u, timeout=20)
                        if r2.status_code == 200:
                            root2 = ET.fromstring(r2.text)
                            for loc2 in root2.findall(".//s:url/s:loc", ns):
                                u2 = (loc2.text or "").strip()
                                if u2 and "/products/" in u2:
                                    listing_urls.append(u2)
                    except Exception:
                        pass

        if listing_urls:
            # Filter out PPE / clothing / accessories / manuals listing pages
            _LISTING_SKIP = re.compile(
                r"(safety-equipment|ppe|jobsite-apparel|hats|shirts|pants|jackets|shoes"
                r"|gloves|knee-pads|head-protection|ear-protection|safety-glasses"
                r"|fall-protection|harness|lanyard|manuals|phone-accessories"
                r"|power-tool-accessories|outdoor-accessories|nails-staples"
                r"|grinder-attachments|drill-impact-bits|oscillating-tool-accessories"
                r"|hole-saws|vacuum-accessories|woodworking-accessories"
                r"|nailer-accessories|oil$|combo-kit)",
                re.IGNORECASE,
            )
            listing_urls = [u for u in listing_urls if not _LISTING_SKIP.search(u)]
            log(f"  [brand] 发现 {len(listing_urls)} 个分类列表页（已排除PPE/配件），使用列表页模式")
            return scrape_brand_via_category_pages(
                listing_urls, download_root, timeout, headless, session
            )
    except Exception:
        pass

    # ── Phase 1: collect catalog page URLs to scrape ──────────────────────
    # Strategy: find category/catalog pages from sitemap and scrape product
    # thumbnails from those pages. NEVER visit individual product pages
    # (too slow — thousands of Playwright renders).
    catalog_pages = []

    # Try sitemap for category/catalog URLs (paths with 2-3 segments under /products/)
    product_urls = discover_product_urls_from_sitemap(origin, session, timeout=20)
    if product_urls:
        # Extract unique category-level URLs (parent paths of product URLs)
        cat_paths = set()
        for u in product_urls:
            path = urlparse(u).path.rstrip("/")
            # Go up one level to get category page
            parent = "/".join(path.split("/")[:-1])
            if parent and len(parent.split("/")) >= 3:
                cat_paths.add(origin + parent)
        catalog_pages = sorted(cat_paths)
        log(f"  [brand] 从sitemap推导出 {len(catalog_pages)} 个分类目录页")

    # If no catalog pages from sitemap, use the provided URL + crawl for more
    if not catalog_pages:
        catalog_pages = [brand_url]
        # Also try common catalog paths
        for path in ["/products", "/shop", "/collections/all", "/en/products",
                     "/us/products", "/en-us/products", "/catalog"]:
            alt = origin + path
            if alt.rstrip("/") != brand_url.rstrip("/"):
                try:
                    r = session.get(alt, timeout=10, allow_redirects=True)
                    if r.status_code == 200:
                        catalog_pages.append(alt)
                except Exception:
                    pass
        log(f"  [brand] 使用 {len(catalog_pages)} 个目录页（含主URL）")

    # Limit to 300 catalog pages max (prevent runaway on huge sitemaps)
    if len(catalog_pages) > 300:
        catalog_pages = catalog_pages[:300]
        log(f"  [brand] 截断至300个目录页")

    # Use the category page scraper for all catalog pages
    return scrape_brand_via_category_pages(
        catalog_pages, download_root, timeout, headless, session
    )

    # Dead code removed — all paths now go through scrape_brand_via_category_pages above


# ══════════════════════════════════════════════════════════════════════════
# DESIGN CLASSIFIER — organise results into super-categories + report
# ══════════════════════════════════════════════════════════════════════════

_KEYWORD_CATEGORY_MAP = {
    "chair": "furniture", "sofa": "furniture", "table": "furniture",
    "desk": "furniture", "shelf": "furniture", "cabinet": "furniture",
    "lamp": "lighting", "light": "lighting", "led": "lighting",
    "kitchen": "kitchen-household", "cook": "tableware-cooking",
    "phone": "smartphones-tablets", "tablet": "smartphones-tablets",
    "laptop": "computers-information-technology",
    "computer": "computers-information-technology",
    "monitor": "computers-information-technology",
    "speaker": "audio", "headphone": "audio", "earphone": "audio",
    "camera": "cameras", "lens": "cameras",
    "watch": "watches-jewellery", "ring": "watches-jewellery",
    "car": "automotive", "vehicle": "automotive",
    "bicycle": "bicycles-e-mobility", "bike": "bicycles-e-mobility",
    "stroller": "baby-child", "baby": "baby-child",
    "medical": "medical-rehabilitation", "wheelchair": "medical-rehabilitation",
    "bathroom": "bath-sanitary", "shower": "bath-sanitary",
    "garden": "garden", "outdoor": "garden",
    "robot": "robots", "drone": "robots",
    "fitness": "wearables-fitness", "tracker": "wearables-fitness",
    "sport": "sports-outdoor", "gym": "sports-outdoor",
    "bag": "fashion-accessories", "suitcase": "fashion-accessories",
    "packaging": "packaging", "package": "packaging",
    "office": "office", "printer": "office",
    "tool": "tools", "drill": "tools",
}


def _classify_product(product_name, primary_category=None):
    """Return (primary_category, super_category) for a product."""
    if primary_category and primary_category in REDDOT_CATEGORIES:
        return primary_category, _REDDOT_SUB_TO_SUPER.get(primary_category, "其他")
    # Keyword fallback
    name_lower = product_name.lower()
    from collections import Counter
    scores = Counter()
    for kw, cat in _KEYWORD_CATEGORY_MAP.items():
        if kw in name_lower:
            scores[cat] += 1
    if scores:
        primary = scores.most_common(1)[0][0]
        return primary, _REDDOT_SUB_TO_SUPER.get(primary, "其他")
    return "uncategorized", "其他"


def classify_results(all_results, download_root):
    """
    Post-process scraped results: reorganise images into super-category subfolders
    and write a classification_report.json + classification_summary.txt.

    all_results: dict returned by the scraper  {topic: [product, ...]}
    download_root: base download directory (str or Path)
    """
    import shutil
    from collections import Counter, defaultdict

    if not download_root:
        log("[分类] 未指定下载目录，跳过文件整理")
        return

    root = Path(download_root)
    classified_root = root / "_classified"
    classified_root.mkdir(parents=True, exist_ok=True)

    by_super = defaultdict(list)
    award_counts = Counter()
    total = 0

    for topic, products in all_results.items():
        for p in products:
            name = p.get("product", "")
            # Try to infer primary category from topic or crumbs
            crumbs = p.get("category", [])
            primary_hint = None
            for c in crumbs:
                slug = c.lower().replace(" ", "-")
                if slug in REDDOT_CATEGORIES:
                    primary_hint = slug
                    break

            primary, super_cat = _classify_product(name, primary_hint)
            award = p.get("award_level", "winner")
            award_counts[award] += 1
            by_super[super_cat].append({"product": name, "primary": primary,
                                        "super": super_cat, "award": award,
                                        "url": p.get("url", "")})
            total += 1

            # Move/copy image folder into _classified/<super_cat>/
            # The image folder is at download_root/<model_code> (no extra topic subfolder)
            model_code = extract_model_code(name)
            src_folder = root / model_code
            if src_folder.exists():
                dst_folder = classified_root / super_cat / model_code
                if not dst_folder.exists():
                    shutil.copytree(str(src_folder), str(dst_folder))

    # Write report
    report = {
        "total_products": total,
        "by_super_category": {k: len(v) for k, v in
                               sorted(by_super.items(), key=lambda x: -len(x[1]))},
        "by_award_level": dict(award_counts.most_common()),
        "detail": {k: v for k, v in by_super.items()},
    }
    report_path = root / "classification_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Write text summary
    summary_path = root / "classification_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("设计奖抓取结果 — 分类统计报告\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"总产品数: {total}\n\n")
        f.write("【大类分布】\n")
        for cat, count in sorted(by_super.items(), key=lambda x: -len(x[1])):
            pct = len(count) / max(total, 1) * 100
            bar = "█" * int(pct / 2)
            f.write(f"  {cat:<12} {len(count):>5} ({pct:5.1f}%) {bar}\n")
        f.write("\n【奖项分布】\n")
        for level, count in award_counts.most_common():
            f.write(f"  {level:<25} {count:>5}\n")

    log(f"\n[分类完成] {total} 个产品 → {classified_root}")
    log(f"  报告: {report_path}")
    log(f"  摘要: {summary_path}")
    for cat, items in sorted(by_super.items(), key=lambda x: -len(x[1])):
        log(f"    {cat}: {len(items)} 个")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def detect_site(url):
    if "rablighting" in url:
        return "rab"
    if "red-dot.org" in url or "reddot.org" in url:
        return "reddot"
    if "ifdesign.com" in url:
        return "ifdesign"
    return "auto"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default=None, help="目标网址（与 --brand / --bear-mode 二选一）")
    parser.add_argument("--brand", default=None, help="品牌名，自动搜索官网产品页")
    parser.add_argument("--site", default=None, choices=["rab", "reddot", "ifdesign", "auto"])
    parser.add_argument("--download", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--no-headless", dest="headless", action="store_false", default=True)
    # ── Bear analysis mode ─────────────────────────────────────────────────
    parser.add_argument("--bear-mode", action="store_true",
                        help="熊主题产品图抓取模式（淘宝+小红书，三个价格带）")
    parser.add_argument("--platform", default="all", choices=["all", "taobao", "xhs"],
                        help="bear-mode 平台选择：all | taobao | xhs（默认 all）")
    parser.add_argument("--pages", type=int, default=2,
                        help="bear-mode 每个价格带每个关键词抓取页数（默认 2）")
    parser.add_argument("--start-band", default=None, metavar="BAND",
                        help="bear-mode 从指定价格带开始（如 200-300），跳过之前的价格带")
    # ── Red Dot category + year options ───────────────────────────────────
    parser.add_argument("--category", default=None,
                        metavar="CATEGORY",
                        help=("Red Dot 类别（32选1）。"
                              f"可选值: {', '.join(sorted(REDDOT_CATEGORIES.keys()))}"))
    parser.add_argument("--years", nargs="+", type=int, default=None,
                        metavar="YEAR",
                        help="Red Dot 年份过滤，可多选，如: --years 2022 2023 2024")
    parser.add_argument("--max-per-product", type=int, default=2,
                        dest="max_per_product",
                        help="每个产品最多下载几张图（默认 2，避免同产品亮/灭重复图）")
    # ── Post-processing ────────────────────────────────────────────────────
    parser.add_argument("--classify", action="store_true",
                        help="抓完后按8大类自动归档，并生成分类报告")
    args = parser.parse_args()

    # ── Bear analysis mode ─────────────────────────────────────────────────
    if args.bear_mode:
        download_root = args.download or str(Path.home() / "Desktop" / "bear_analysis")
        start_band = getattr(args, "start_band", None)
        log(f"\n[熊分析模式] 平台={args.platform}  下载目录={download_root}"
            + (f"  起始价格带={start_band}" if start_band else ""))
        session = requests.Session()
        session.headers.update(HEADERS)
        if args.platform in ("all", "taobao"):
            scrape_taobao_bear(download_root, pages_per_band=args.pages,
                               timeout=args.timeout, headless=args.headless,
                               session=session, start_band=start_band)
        if args.platform in ("all", "xhs"):
            scrape_xhs_bear(download_root, timeout=args.timeout, headless=args.headless, session=session)
        log("\n[熊分析] 全部完成")
        return

    # ── Resolve URL from brand name if needed ───────────────────────────────
    if args.brand and not args.url:
        log(f"\n[品牌模式] {args.brand}")
        homepage = search_brand_url(args.brand, timeout=args.timeout, headless=args.headless)
        if not homepage:
            log("[错误] 未能找到品牌官网，请直接提供 URL")
            sys.exit(1)
        args.url = find_catalog_page(homepage, timeout=args.timeout, headless=args.headless)
        log(f"[入口页] {args.url}")
    elif not args.url:
        log("[错误] 请提供 URL、使用 --brand 指定品牌名，或使用 --bear-mode")
        sys.exit(1)

    site = args.site or detect_site(args.url)
    log(f"[模式] {site}  |  limit={args.limit}")

    session = requests.Session()
    session.headers.update(HEADERS)
    session._max_per_product = args.max_per_product  # passed to scrape_reddot_sitemap via session
    all_results = {}

    parsed = urlparse(args.url)
    qs = parse_qs(parsed.query)
    if args.brand:
        topic = re.sub(r"[^\w]", "_", args.brand.strip().lower())
    elif site == "reddot" and "q" in qs:
        topic = re.sub(r"[^\w]", "_", qs["q"][0].strip().lower())
    elif site == "ifdesign" and "categoryId" in qs:
        # Map known iF category IDs to readable names
        IF_CATEGORY_NAMES = {
            "129": "Lighting", "135": "Home_Furniture", "542": "Household_Appliances",
            "772": "Kitchen_Appliances", "168": "Bath", "44": "Babies_Kids",
            "93": "Computer", "56": "Audio", "82": "Communication_Devices",
            "224": "Medical_Healthcare", "233": "Industry", "198": "Public_Design",
        }
        cat_id = qs["categoryId"][0]
        topic = IF_CATEGORY_NAMES.get(cat_id, f"Category_{cat_id}")
    else:
        topic = parsed.path.strip("/").split("/")[-1] or parsed.netloc.split(".")[0]

    if site == "rab":
        results = scrape_rab(args.url, topic, args.download, args.limit, args.timeout, args.headless, session)
        all_results[topic] = results
    elif site == "reddot":
        # Resolve keywords: --category takes priority, then URL-inferred topic, then lighting default
        if args.category and args.category in REDDOT_CATEGORY_KEYWORDS:
            kws = REDDOT_CATEGORY_KEYWORDS[args.category]
            if not args.brand:
                topic = args.category
        elif args.category:
            # Unknown category slug — use it as a keyword directly
            kws = [args.category.replace("-", " ")]
            topic = args.category
        else:
            kws = REDDOT_LIGHTING_KWS  # default: lighting

        # Use sitemap-based scraper for search/ranking pages (Vue SPA) or when
        # --category / --years is specified (sitemap is the only reliable approach)
        use_sitemap = (
            any(k in args.url for k in ["/project/search/", "/project/ranking/", "?q="])
            or args.category is not None
            or args.years is not None
        )
        if use_sitemap:
            # Sub-category keyword mapping for sitemap secondary filter
            _LAMP_SUB_KWS = {
                "pendant":      ["pendant", "chandelier", "hanging", "suspension"],
                "wall":         ["wall", "sconce", "bracket", "bedside", "mounted", "vanity"],
                "wall+lamp":    ["wall", "sconce", "bracket", "bedside", "mounted", "vanity"],
                "floor+lamp":   ["floor", "torchiere", "standing"],
                "floor":        ["floor", "torchiere", "standing"],
                "table+lamp":   ["table", "desk", "study"],
                "table":        ["table", "desk", "study"],
                "desk+lamp":    ["desk", "table", "study"],
                "downlight":    ["downlight", "recessed"],
                "spotlight":    ["spotlight", "spot"],
                "downlight+spotlight": ["downlight", "spotlight", "recessed", "spot"],
                "ceiling":      ["ceiling", "flush", "overhead"],
                "outdoor":      ["outdoor", "street", "bollard", "garden"],
            }
            q_param = qs.get("q", [None])[0]
            sub_kws = None
            if q_param:
                q_lower = q_param.lower().strip()
                # parse_qs decodes + as space; re-normalize spaces→+ for dict key lookup
                q_key = q_lower.replace(" ", "+")
                sub_kws = _LAMP_SUB_KWS.get(q_key, None) or _LAMP_SUB_KWS.get(q_lower, None)
                if sub_kws is None:
                    # Fallback: split q words, strip generic non-specific terms
                    _GENERIC_WORDS = {"lamp", "led", "light", "the", "and", "or", "for"}
                    sub_kws = [w for w in q_lower.split()
                               if len(w) > 3 and w not in _GENERIC_WORDS] or None
            # Only apply lighting-specific fixture verification for the lighting category.
            # Other categories (shavers, furniture, etc.) pass verify_fn=None (accept all).
            _verify = _verify_lighting if args.category == "lighting" else None

            # Sub-type classification: map q param → main lamp category → subtype_fn
            _Q_TO_MAIN = {
                "pendant": "pendant",
                "wall+lamp": "wall", "wall": "wall",
                "floor+lamp": "floor", "floor": "floor",
                "table+lamp": "table", "table": "table",
                "desk+lamp": "table", "desk": "table",
                "downlight+spotlight": "downlight", "downlight": "downlight",
                "spotlight": "downlight",
                "ceiling": "downlight",
            }
            _st_fn = None
            if args.category == "lighting":
                if q_param:
                    main_hint = _Q_TO_MAIN.get(q_key, None) or _Q_TO_MAIN.get(q_lower, None)
                    _st_fn = _make_lamp_subtype_fn(main_hint) if main_hint else _classify_all_lighting
                else:
                    _st_fn = _classify_all_lighting

            # Full lighting scan (no q param): use breadcrumb-based full scan to catch
            # ALL lighting products regardless of URL slug keywords.
            if args.category == "lighting" and not q_param:
                results = scrape_reddot_full_lighting_scan(
                    args.download, args.limit, args.timeout, session,
                    years=args.years, verify_fn=_verify_lighting,
                    subtype_fn=_classify_all_lighting,
                )
            else:
                results = scrape_reddot_sitemap(
                    kws, topic, args.download, args.limit, args.timeout, session,
                    years=args.years, sub_keywords=sub_kws, verify_fn=_verify,
                    subtype_fn=_st_fn,
                )
        else:
            results = scrape_reddot(args.url, topic, args.download, args.limit, args.timeout, args.headless, session)
        all_results[topic] = results
    elif site == "ifdesign":
        # Use REST API when categoryId is present in URL
        if "categoryId" in args.url:
            _qs = parse_qs(parsed.query)
            cat_id = int(_qs.get("categoryId", ["129"])[0])
            results = scrape_ifdesign_api(cat_id, topic, args.download, args.limit, args.timeout, session)
        else:
            results = scrape_ifdesign(args.url, topic, args.download, args.limit, args.timeout, args.headless, session)
        all_results[topic] = results
    else:
        # Universal mode with automatic fallback when images are insufficient
        results = scrape_brand_with_fallback(args.url, topic, args.download, args.limit,
                                             args.timeout, args.headless, session)
        all_results[topic] = results

    if args.out:
        out_path = Path(args.out)
        if out_path.is_dir() or str(args.out).endswith(("/", "\\")):
            out_path = out_path / "results.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        log(f"\n[完成] JSON: {out_path.resolve()}")

    total = sum(len(p.get("images", [])) for v in all_results.values() for p in v)
    log(f"\n[汇总] {total} 张图片")

    if args.classify and all_results:
        classify_results(all_results, args.download)


if __name__ == "__main__":
    main()
