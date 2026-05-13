#!/usr/bin/env python3
"""
Scrape brands using sitemap + og:image with Chinese 2-level classification.
For each product page, extracts category from page title/breadcrumbs/URL path,
then downloads og:image into classified folders: brand/大类/小类/NN.jpg
"""
import requests, json, re, xml.etree.ElementTree as ET, hashlib, time, sys
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin, urlparse
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import _classify_brand_product, HEADERS

s = requests.Session()
s.headers.update(HEADERS)
BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库"


def get_sitemap_urls(origin, max_urls=500):
    urls, visited, queue = [], set(), []
    try:
        r = s.get(origin + '/robots.txt', timeout=10)
        for m in re.finditer(r'Sitemap:\s*(.*)', r.text, re.I):
            queue.append(m.group(1).strip())
    except Exception:
        pass
    if not queue:
        queue = [origin + '/sitemap.xml']
    while queue and len(urls) < max_urls:
        sm = queue.pop(0)
        if sm in visited:
            continue
        visited.add(sm)
        try:
            r = s.get(sm, timeout=15)
            if r.status_code != 200 or '<' not in r.text[:100]:
                continue
            root = ET.fromstring(r.text)
            ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            for loc in root.findall('.//s:sitemap/s:loc', ns):
                u = (loc.text or '').strip()
                if u and u not in visited:
                    queue.append(u)
            for loc in root.findall('.//s:url/s:loc', ns):
                u = (loc.text or '').strip()
                if not u:
                    continue
                if u.endswith('.xml') and 'sitemap' in u.lower():
                    if u not in visited:
                        queue.append(u)
                else:
                    urls.append(u)
        except Exception:
            pass
    return urls


# Pages to skip (not product pages)
_SKIP_URL = re.compile(
    r'(/blog|/support|/about|/legal|/press|/career|/faq|/contact|/news'
    r'|/terms|/privacy|/warranty|/login|/account|/cart|/checkout'
    r'|/stories|/magazine|/journal|/events|/dealers|/professionals'
    r'|\.pdf$|\.xml$)', re.I
)

# Brand-specific product URL patterns (only visit these)
_BRAND_PRODUCT_PATTERNS = {
    "artemide": re.compile(r'/products?/', re.I),
    "foscarini": re.compile(r'/products?/', re.I),
    "louis_poulsen": re.compile(r'/(private|professional)/', re.I),
    "nitecore": re.compile(r'/(product|category)/', re.I),
    "biolite": re.compile(r'/(products|collections)/', re.I),
    "bega": re.compile(r'/products?/', re.I),
    "philips_lighting": re.compile(r'/(consumer|professional|product)/', re.I),
    "rab_lighting": re.compile(r'/products?/', re.I),
    "wac_lighting": re.compile(r'/products?/', re.I),
    "flos": re.compile(r'/products?/', re.I),
}

# Products to skip for specific brands (accessories, non-core products)
_BRAND_SKIP_PATTERNS = {
    "nitecore": re.compile(
        r'(充电器|电池|battery|charger|adapter|战术笔|pen|clip|扣夹|挎包|bag|pack'
        r'|fan|风扇|flask|holster|mount|filter|diffuser|strap|lanyard)', re.I
    ),
}


def _extract_page_category(url, soup, brand_name=None):
    """Extract product category from page content: title, breadcrumbs, URL path, ld+json."""
    texts = []

    # 1. Page title
    title = soup.find('title')
    if title and title.string:
        texts.append(title.string.strip())

    # 2. og:title
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        texts.append(og_title['content'].strip())

    # 3. Breadcrumb nav
    for nav in soup.find_all(['nav', 'ol', 'ul'], class_=re.compile(r'breadcrumb', re.I)):
        for li in nav.find_all(['li', 'a', 'span']):
            t = li.get_text(strip=True)
            if t:
                texts.append(t)

    # 4. ld+json breadcrumbs
    for sc in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(sc.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get('@type') == 'BreadcrumbList':
                    for el in item.get('itemListElement', []):
                        name = el.get('name', '') or el.get('item', {}).get('name', '')
                        if name:
                            texts.append(name)
                # Product type/category
                if item.get('@type') == 'Product':
                    cat = item.get('category', '')
                    if cat:
                        texts.append(cat)
        except Exception:
            pass

    # 5. URL path segments
    path = urlparse(url).path
    texts.append(path.replace('/', ' ').replace('-', ' ').replace('_', ' '))

    return _classify_brand_product(' '.join(texts), texts, brand_name=brand_name)


def dl(img_url, dest):
    """Download image, validate, convert webp to jpg."""
    try:
        r = s.get(img_url, timeout=15)
        if r.status_code != 200 or len(r.content) < 3000:
            return False
        dest.write_bytes(r.content)
        if dest.suffix.lower() not in ('.jpg', '.jpeg'):
            img = Image.open(dest).convert('RGB')
            new = dest.with_suffix('.jpg')
            img.save(new, 'JPEG', quality=95)
            dest.unlink()
            dest = new
        img = Image.open(dest)
        if max(img.size) < 400:
            dest.unlink()
            return False
        return True
    except Exception:
        dest.unlink(missing_ok=True)
        return False


def scrape_classified(name, out_base, sitemap_origin=None, cdn=None, product_pattern=None, skip_pattern=None, brand_name=None):
    """Scrape brand with classification into 大类/小类 subfolders."""
    out_base = Path(out_base)
    out_base.mkdir(parents=True, exist_ok=True)
    seen_hashes = set()
    folder_counters = {}  # {folder_path: count}
    saved = 0

    def _next_path(folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        if folder not in folder_counters:
            existing = [f for f in folder.iterdir() if f.suffix.lower() in ('.jpg', '.png')]
            folder_counters[folder] = len(existing)
        folder_counters[folder] += 1
        return folder / f"{folder_counters[folder]:02d}.jpg"

    def _save_image(img_url, dest_folder):
        nonlocal saved
        h = hashlib.md5(img_url.encode()).hexdigest()
        if h in seen_hashes:
            return
        seen_hashes.add(h)
        dest = _next_path(dest_folder)
        if dl(img_url, dest):
            # Content hash dedup
            try:
                ch = hashlib.md5(dest.read_bytes()).hexdigest()
                if ch in seen_hashes:
                    dest.unlink(missing_ok=True)
                    folder_counters[dest.parent] -= 1
                    return
                seen_hashes.add(ch)
            except Exception:
                pass
            saved += 1
        else:
            folder_counters[dest.parent] -= 1

    # CDN direct URLs (no classification available — put in root)
    if cdn:
        for img_url in cdn:
            _save_image(img_url, out_base / "其他" / "其他")

    # Sitemap-based scraping with classification
    if sitemap_origin:
        urls = get_sitemap_urls(sitemap_origin)
        urls = [u for u in urls if not _SKIP_URL.search(u)]

        # Filter to product pages if pattern provided
        if product_pattern:
            urls = [u for u in urls if product_pattern.search(u)]

        print(f'  [{name}] {len(urls)} product URLs from sitemap', flush=True)

        for url in urls[:300]:
            try:
                r = s.get(url, timeout=10, allow_redirects=True)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, 'html.parser')

                # Skip non-core products (accessories, etc.)
                page_text = (soup.find('title').string if soup.find('title') and soup.find('title').string else '') + ' ' + url
                if skip_pattern and skip_pattern.search(page_text):
                    continue

                # Classify from page content — skip if no valid match
                result = _extract_page_category(url, soup, brand_name=brand_name or name)
                if result is None:
                    continue  # No "其他" fallback — discard unclassifiable
                major, minor = result
                dest_folder = out_base / major / minor

                # Extract image URLs
                img_urls = []
                og = soup.find('meta', property='og:image')
                if og and og.get('content'):
                    iu = og['content']
                    if not iu.startswith('http'):
                        iu = urljoin(url, iu)
                    img_urls.append(iu)

                for sc in soup.find_all('script', type='application/ld+json'):
                    try:
                        data = json.loads(sc.string)
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            imgs = item.get('image', [])
                            if isinstance(imgs, str):
                                img_urls.append(imgs)
                            elif isinstance(imgs, list):
                                for i in imgs[:2]:
                                    if isinstance(i, str):
                                        img_urls.append(i)
                                    elif isinstance(i, dict) and i.get('url'):
                                        img_urls.append(i['url'])
                    except Exception:
                        pass

                for img_url in img_urls[:2]:
                    if not img_url.startswith('http'):
                        img_url = urljoin(url, img_url)
                    _save_image(img_url, dest_folder)

                time.sleep(0.3)
            except Exception:
                pass

    print(f'  [{name}] DONE: {saved} images', flush=True)
    return saved


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else None

    BRANDS = {
        "artemide": (BASE / '灯具' / 'artemide', 'https://www.artemide.com'),
        "foscarini": (BASE / '灯具' / 'foscarini', 'https://www.foscarini.com'),
        "biolite": (BASE / '灯具' / 'biolite', 'https://www.bioliteenergy.com'),
        "nitecore": (BASE / '灯具' / 'nitecore', 'https://www.nitecore.com'),
        "philips_lighting": (BASE / '灯具' / 'philips_lighting', 'https://www.lighting.philips.com'),
        "rab_lighting": (BASE / '灯具' / 'rab_lighting', 'https://www.rablighting.com'),
        "wac_lighting": (BASE / '灯具' / 'wac_lighting', 'https://www.waclighting.com'),
        "louis_poulsen": (BASE / '灯具' / 'louis_poulsen', 'https://www.louispoulsen.com'),
        "bega": (BASE / '灯具' / 'bega', 'https://www.bega.com'),
        "flos": (BASE / '灯具' / 'flos', 'https://www.flos.com'),
    }

    if targets:
        brands_to_run = {k: v for k, v in BRANDS.items() if k in targets}
    else:
        brands_to_run = BRANDS

    total = 0
    for name, (out_dir, origin) in brands_to_run.items():
        pattern = _BRAND_PRODUCT_PATTERNS.get(name)
        skip = _BRAND_SKIP_PATTERNS.get(name)
        count = scrape_classified(name, out_dir, sitemap_origin=origin, product_pattern=pattern, skip_pattern=skip, brand_name=name)
        total += count

    print(f'\n=== ALL DONE: {total} images ===', flush=True)
