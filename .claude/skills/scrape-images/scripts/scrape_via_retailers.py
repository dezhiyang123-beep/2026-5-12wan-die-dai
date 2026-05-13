#!/usr/bin/env python3
"""Scrape remaining brands via retailer websites (Lumens, Amazon, Finnish Design Shop etc.)"""
import requests, hashlib, time
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin

s = requests.Session()
s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库"


def dl_ogimage(name, out, urls):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    seen, counter, saved = set(), 0, 0
    for url in urls:
        try:
            r = s.get(url, timeout=15, allow_redirects=True)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            img_url = None
            # Try og:image
            og = soup.find('meta', property='og:image')
            if og and og.get('content'):
                img_url = og['content']
                if not img_url.startswith('http'):
                    img_url = urljoin(url, img_url)
            # Try twitter:image
            if not img_url:
                tw = soup.find('meta', attrs={'name': 'twitter:image'})
                if tw and tw.get('content'):
                    img_url = tw['content']
                    if not img_url.startswith('http'):
                        img_url = urljoin(url, img_url)
            if not img_url:
                continue
            h = hashlib.md5(img_url.encode()).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            r2 = s.get(img_url, timeout=15)
            if r2.status_code != 200 or len(r2.content) < 3000:
                continue
            counter += 1
            ext = '.png' if 'png' in r2.headers.get('Content-Type', '') else '.jpg'
            (out / f'{counter:03d}{ext}').write_bytes(r2.content)
            saved += 1
            time.sleep(0.3)
        except Exception:
            pass
    print(f'[{name}] {saved} images', flush=True)


# Artemide via Lumens/Lightology
dl_ogimage('artemide', BASE / '灯具' / 'artemide', [
    'https://www.lightology.com/index.php?module=prod_detail&prod_id=51267',
    'https://www.lightology.com/index.php?module=prod_detail&prod_id=51259',
    'https://www.lumens.com/tolomeo-classic-table-lamp-by-artemide-uu126021.html',
    'https://www.lumens.com/nur-mini-pendant-by-artemide-uu127127.html',
    'https://www.lumens.com/pirce-pendant-by-artemide-uu543340.html',
    'https://www.lumens.com/mercury-mini-pendant-by-artemide-uu543369.html',
    'https://www.lumens.com/cadmo-floor-lamp-by-artemide-uu543339.html',
    'https://www.lumens.com/demetra-led-table-lamp-by-artemide-uu543322.html',
    'https://www.lumens.com/melampo-table-lamp-by-artemide-uu543333.html',
    'https://www.lumens.com/nh-s2-22-suspension-by-artemide-uu543363.html',
    'https://www.lumens.com/empatia-table-lamp-by-artemide-uu543348.html',
    'https://www.lumens.com/logico-mini-single-ceiling-light-by-artemide-uu543378.html',
])

# Louis Poulsen via Finnish Design Shop / DWR / Lumens
dl_ogimage('louis_poulsen', BASE / '灯具' / 'louis_poulsen', [
    'https://www.finnishdesignshop.com/en-us/product/ph-5-pendant-white-classic',
    'https://www.finnishdesignshop.com/en-us/product/ph-5-pendant-white-modern',
    'https://www.finnishdesignshop.com/en-us/product/ph-5-monochrome-pendant-white',
    'https://www.dwr.com/lighting-ceiling/ph5-pendant-lamp/6013.html?lang=en_US',
    'https://www.lumens.com/ph-5-pendant-by-louis-poulsen-uu169939.html',
    'https://www.lumens.com/panthella-table-lamp-by-louis-poulsen-uu159960.html',
    'https://www.lumens.com/aj-table-lamp-by-louis-poulsen-uu159973.html',
    'https://www.lumens.com/toldbod-pendant-by-louis-poulsen-uu574555.html',
    'https://www.lumens.com/above-pendant-by-louis-poulsen-uu507019.html',
    'https://www.lumens.com/patera-pendant-by-louis-poulsen-uu166068.html',
    'https://www.lumens.com/yuh-table-lamp-by-louis-poulsen-uu472296.html',
])

# BEGA via bega-us.com + Lumens
dl_ogimage('bega', BASE / '灯具' / 'bega', [
    'https://www.lumens.com/33549-led-outdoor-wall-sconce-by-bega-uu503966.html',
    'https://www.lumens.com/22215-led-outdoor-wall-sconce-by-bega-uu503951.html',
    'https://www.lumens.com/33590-led-bollard-by-bega-uu503983.html',
    'https://www.lumens.com/24128-led-flush-mount-ceiling-light-by-bega-uu503920.html',
    'https://www.lumens.com/33224-led-outdoor-wall-sconce-by-bega-uu503959.html',
    'https://www.lumens.com/77263-77265-led-outdoor-floor-lamp-by-bega-uu504006.html',
])

# Foscarini via Lumens
dl_ogimage('foscarini', BASE / '灯具' / 'foscarini', [
    'https://www.lumens.com/binic-table-lamp-by-foscarini-uu112779.html',
    'https://www.lumens.com/twiggy-floor-lamp-by-foscarini-uu112765.html',
    'https://www.lumens.com/caboche-pendant-by-foscarini-uu112769.html',
    'https://www.lumens.com/spokes-2-pendant-by-foscarini-uu112772.html',
    'https://www.lumens.com/rituals-table-lamp-by-foscarini-uu112780.html',
    'https://www.lumens.com/lumiere-table-lamp-by-foscarini-uu543440.html',
    'https://www.lumens.com/birdie-table-lamp-by-foscarini-uu543439.html',
])

# BioLite via Shopify
dl_ogimage('biolite', BASE / '灯具' / 'biolite', [
    'https://www.bioliteenergy.com/products/alpenglow-500',
    'https://www.bioliteenergy.com/products/alpenglow-250',
    'https://www.bioliteenergy.com/products/headlamp-800-pro',
    'https://www.bioliteenergy.com/products/sunlight-100',
    'https://www.bioliteenergy.com/products/sitelight-string-lights',
    'https://www.bioliteenergy.com/products/firepit-plus',
    'https://www.bioliteenergy.com/products/charge-80-pd',
])

# Nitecore via Amazon
dl_ogimage('nitecore', BASE / '灯具' / 'nitecore', [
    'https://www.amazon.com/Nitecore-MH12-Pro-Rechargeable-Flashlight/dp/B0B5CVNH6B',
    'https://www.amazon.com/Nitecore-P20iX-Rechargeable-Flashlight-Battery/dp/B09J8M15VJ',
    'https://www.amazon.com/Nitecore-i4000R-Rechargeable-Flashlight-Batteries/dp/B09BCH55JL',
    'https://www.amazon.com/NITECORE-TM9K-Flashlight-Rechargeable-Battery/dp/B08CBDBDVZ',
    'https://www.amazon.com/Nitecore-Rechargeable-Flashlight-CRI-Camping/dp/B0CBJT1N33',
    'https://www.amazon.com/Nitecore-NU25-Rechargeable-Headlamp-Ultralight/dp/B0CG6WS4NC',
])

# Philips via Amazon
dl_ogimage('philips', BASE / '灯具' / 'philips_lighting', [
    'https://www.amazon.com/Philips-Hue-Bluetooth-Compatible-Assistant/dp/B07QV9XB87',
    'https://www.amazon.com/Philips-Hue-Gradient-Lightstrip-Bluetooth/dp/B08CKJWSFS',
    'https://www.amazon.com/Philips-Hue-Bluetooth-Assistant-Required/dp/B0BQ2JKC21',
    'https://www.amazon.com/Philips-Hue-Ambiance-Starter-Generation/dp/B09SVZB2L2',
    'https://www.amazon.com/Philips-Hue-Bluetooth-Ambiance-Compatible/dp/B08M5YPCRV',
])

# WAC via Lumens
dl_ogimage('wac', BASE / '灯具' / 'wac_lighting', [
    'https://www.lumens.com/tube-indoor-outdoor-led-wall-sconce-by-wac-lighting-uu312299.html',
    'https://www.lumens.com/mini-monopoint-led-pendant-by-wac-lighting-uu312290.html',
    'https://www.lumens.com/rubix-indoor-outdoor-led-wall-sconce-by-wac-lighting-uu312300.html',
    'https://www.lumens.com/templar-outdoor-led-wall-sconce-by-wac-lighting-uu568449.html',
    'https://www.lumens.com/ds-ws05-120-led-wall-sconce-by-wac-lighting-uu312297.html',
])

# Dyson via Amazon
dl_ogimage('dyson', BASE / '小家电' / 'dyson', [
    'https://www.amazon.com/Dyson-Detect-Cordless-Vacuum-Yellow/dp/B0979R48CX',
    'https://www.amazon.com/Dyson-Detect-Cordless-Vacuum-Cleaner/dp/B0C2J8KJH9',
    'https://www.amazon.com/Dyson-Supersonic-Hair-Dryer-Iron/dp/B0CPXHDKSR',
    'https://www.amazon.com/Dyson-Airwrap-Multi-Styler-Complete/dp/B0BYK7HTQQ',
    'https://www.amazon.com/Dyson-Purifier-HEPA-Cool-Formaldehyde/dp/B09RDX8KHN',
    'https://www.amazon.com/Dyson-V11-Torque-Drive-Cord-free/dp/B07NX8XBMP',
    'https://www.amazon.com/Dyson-Outsize-Absolute-Cordless-Cleaner/dp/B098DKQ1VP',
    'https://www.amazon.com/Dyson-Gen5detect-Cordless-Vacuum-Cleaner/dp/B0CB9YJTG5',
])

# Sony via Amazon
dl_ogimage('sony', BASE / '消费电子' / 'sony', [
    'https://www.amazon.com/Sony-WH-1000XM5-Canceling-Headphones-Hands-Free/dp/B09XS7JWHH',
    'https://www.amazon.com/Sony-WF-1000XM5-Bluetooth-Canceling-Headphones/dp/B0C33XXS56',
    'https://www.amazon.com/Sony-SRS-XB100-Portable-Bluetooth-Waterproof/dp/B0C295LHFM',
    'https://www.amazon.com/Sony-WH-CH720N-Canceling-Headphones-Bluetooth/dp/B0BS1QXVK2',
    'https://www.amazon.com/Sony-Full-Frame-Mirrorless-Interchangeable-Body/dp/B0B7Z8K1GK',
    'https://www.amazon.com/Sony-ZV-E10-Mirrorless-Camera-Body/dp/B0DFV7FN3C',
    'https://www.amazon.com/PlayStation-5-Console-CFI-2000-slim/dp/B0CL61F39H',
    'https://www.amazon.com/Sony-INZONE-H9-Canceling-Headset/dp/B0B7TQHBKF',
])

# YETI via Amazon
dl_ogimage('yeti', BASE / '户外装备' / 'yeti', [
    'https://www.amazon.com/YETI-Rambler-Stainless-Insulated-MagSlider/dp/B073WJY2XC',
    'https://www.amazon.com/YETI-Rambler-Vacuum-Insulated-Stainless/dp/B09GCFRPVN',
    'https://www.amazon.com/YETI-Tundra-Cooler-White/dp/B002IHIGQ2',
    'https://www.amazon.com/YETI-Roadie-Wheeled-Cooler-White/dp/B09BRXSQY9',
    'https://www.amazon.com/YETI-Hopper-Portable-Cooler-Alpine/dp/B0BZ3BZ3Y7',
    'https://www.amazon.com/YETI-LoadOut-Bucket-Charcoal/dp/B07PN8TSN5',
    'https://www.amazon.com/YETI-Camino-Carryall-Tote-Bag/dp/B0BX2DQGYL',
])

print('\n=== ALL DONE ===', flush=True)
