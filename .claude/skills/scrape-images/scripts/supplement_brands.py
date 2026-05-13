#!/usr/bin/env python3
"""Supplement low-image-count brands via Amazon og:image with classification."""
import requests, hashlib, time, sys
from bs4 import BeautifulSoup
from pathlib import Path
from PIL import Image

s = requests.Session()
s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库"


def dl_classified(name, base_dir, category_urls):
    """
    Download og:image from URLs into classified folders.
    category_urls: dict of {(大类, 小类): [url1, url2, ...]}
    """
    base_dir = Path(base_dir)
    seen_hashes = set()
    total = 0

    # Collect existing image hashes for dedup
    for f in base_dir.rglob("*.jpg"):
        try:
            seen_hashes.add(hashlib.md5(f.read_bytes()).hexdigest())
        except Exception:
            pass
    for f in base_dir.rglob("*.png"):
        try:
            seen_hashes.add(hashlib.md5(f.read_bytes()).hexdigest())
        except Exception:
            pass

    for (major, minor), urls in category_urls.items():
        dest_dir = base_dir / major / minor
        dest_dir.mkdir(parents=True, exist_ok=True)
        existing = len([f for f in dest_dir.iterdir() if f.suffix.lower() in ('.jpg', '.png')])
        counter = existing

        for url in urls:
            try:
                r = s.get(url, timeout=15, allow_redirects=True)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, 'html.parser')

                # Extract image URL: og:image > twitter:image > ld+json
                img_url = None
                og = soup.find('meta', property='og:image')
                if og and og.get('content'):
                    img_url = og['content']
                if not img_url:
                    tw = soup.find('meta', attrs={'name': 'twitter:image'})
                    if tw and tw.get('content'):
                        img_url = tw['content']
                if not img_url:
                    continue

                if not img_url.startswith('http'):
                    continue

                # Download
                r2 = s.get(img_url, timeout=15)
                if r2.status_code != 200 or len(r2.content) < 3000:
                    continue

                # Dedup
                h = hashlib.md5(r2.content).hexdigest()
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)

                counter += 1
                dest = dest_dir / f"{counter:02d}.jpg"
                dest.write_bytes(r2.content)

                # Convert webp/png if needed
                if dest.suffix == '.jpg':
                    try:
                        img = Image.open(dest)
                        if img.format in ('WEBP', 'PNG'):
                            img.convert('RGB').save(dest, 'JPEG', quality=95)
                    except Exception:
                        pass

                # Validate size
                try:
                    img = Image.open(dest)
                    if max(img.size) < 400:
                        dest.unlink()
                        counter -= 1
                        continue
                except Exception:
                    dest.unlink(missing_ok=True)
                    counter -= 1
                    continue

                total += 1
                time.sleep(0.3)
            except Exception:
                pass

    print(f'[{name}] +{total} images', flush=True)
    return total


# ══════════════════════════════════════════════════════════════
# Brand supplement data: Amazon product URLs grouped by category
# ══════════════════════════════════════════════════════════════

SUPPLEMENTS = {
    "braun": (BASE / "医疗设备" / "braun", {
        ("剃须刀", "电动剃须刀"): [
            "https://www.amazon.com/Braun-Electric-Razor-Waterproof-Rechargeable/dp/B09MJLHB2W",
            "https://www.amazon.com/Braun-Electric-Razor-Rechargeable-Ergonomic/dp/B0BF7MVKM3",
            "https://www.amazon.com/Braun-Electric-Shaver-ProSkin-Precision/dp/B0CG8NX4VW",
            "https://www.amazon.com/Braun-Electric-Shaver-Precision-Waterproof/dp/B09MKB1CNH",
            "https://www.amazon.com/Braun-Electric-Razor-Series-Rechargeable/dp/B0DCGZRM3R",
            "https://www.amazon.com/Braun-Electric-Razor-Waterproof-Rechargeable/dp/B0DCGS67M9",
            "https://www.amazon.com/Braun-Electric-Razor-Waterproof-Rechargeable/dp/B0DCGZ4MV6",
            "https://www.amazon.com/Braun-Shaver-EasyClick-Precision-Attachment/dp/B0D7GQGXHZ",
        ],
        ("口腔护理", "电动牙刷"): [
            "https://www.amazon.com/Oral-B-iO-Series-Electric-Toothbrush/dp/B0C6C56Z5W",
            "https://www.amazon.com/Oral-B-Electric-Toothbrush-Rechargeable-Connected/dp/B0CDT8LZ8H",
            "https://www.amazon.com/Oral-B-Genius-Electric-Rechargeable-Toothbrush/dp/B0CDT6ZS2V",
            "https://www.amazon.com/Oral-B-Toothbrush-Rechargeable-CrossAction-Sensitive/dp/B0CDT4DRVX",
        ],
        ("美容仪器", "脱毛器"): [
            "https://www.amazon.com/Braun-Silk-Expert-Pro5-PL5137/dp/B084BGYJCL",
            "https://www.amazon.com/Braun-Silk-epil-Epilator-Cordless-Rechargeable/dp/B0DCGTMHZ4",
            "https://www.amazon.com/Braun-Silk-epil-Epilator-Bikini-Trimmer/dp/B0DCGJBNB7",
        ],
        ("健康监测", "体温计"): [
            "https://www.amazon.com/Braun-Digital-No-Touch-Thermometer-BNT400/dp/B08MZY3D7S",
            "https://www.amazon.com/Braun-ThermoScan-Ear-Thermometer-ExacTemp/dp/B00DKGOJIQ",
        ],
    }),

    "bose": (BASE / "音箱" / "bose", {
        ("蓝牙音箱", "便携音箱"): [
            "https://www.amazon.com/Bose-SoundLink-Flex-Bluetooth-Waterproof/dp/B097B5BYL4",
            "https://www.amazon.com/Bose-SoundLink-Max-Portable-Bluetooth/dp/B0D7SXDJ2W",
            "https://www.amazon.com/Bose-SoundLink-Micro-Bluetooth-Speaker/dp/B0C4PSQHHN",
            "https://www.amazon.com/Bose-SoundLink-Revolve-Portable-Bluetooth/dp/B0CCY86JV7",
            "https://www.amazon.com/Bose-SoundLink-Revolve-Bluetooth-speaker/dp/B0CCY8NF2W",
        ],
        ("智能音箱", "家用音箱"): [
            "https://www.amazon.com/Bose-Portable-Smart-Speaker-Bluetooth/dp/B088FQQL8Z",
            "https://www.amazon.com/Bose-Home-Speaker-500-Built/dp/B07B8FBRPJ",
            "https://www.amazon.com/Bose-Home-Speaker-300-Built/dp/B07QTW17GR",
        ],
        ("条形音箱", "条形音箱"): [
            "https://www.amazon.com/Bose-Smart-Soundbar-Dolby-Atmos/dp/B0CCY83JNW",
            "https://www.amazon.com/Bose-TV-Speaker-Soundbar-Bluetooth/dp/B088KRPCQJ",
            "https://www.amazon.com/Bose-Smart-Soundbar-600-Dolby/dp/B0B4PSQHD3",
            "https://www.amazon.com/Bose-Smart-Ultra-Soundbar-Bluetooth/dp/B0CCXBG8VX",
        ],
        ("耳机", "降噪耳机"): [
            "https://www.amazon.com/Bose-QuietComfort-Ultra-Headphones-Cancelling/dp/B0CCZ1L489",
            "https://www.amazon.com/Bose-QuietComfort-Cancelling-Headphones-Bluetooth/dp/B0CCZ26B5V",
            "https://www.amazon.com/Bose-QuietComfort-Cancelling-Earbuds-Bluetooth/dp/B0D7RP7NS3",
            "https://www.amazon.com/Bose-Ultra-Open-Earbuds-Immersive/dp/B0CPFXCPKQ",
        ],
    }),

    "shark": (BASE / "小家电" / "shark", {
        ("吸尘器", "手持吸尘器"): [
            "https://www.amazon.com/Shark-Cordless-Stick-Vacuum-IZ862H/dp/B09BNZPW7F",
            "https://www.amazon.com/Shark-Detect-Pro-Cordless-Vacuum/dp/B0D17JMCYD",
            "https://www.amazon.com/Shark-Cordless-Pet-Stick-Vacuum/dp/B0CZWHNHMH",
            "https://www.amazon.com/Shark-Navigator-Lift-Away-Upright-NV352/dp/B00AZBIXSG",
            "https://www.amazon.com/Shark-IZ562H-Anti-Allergen-PowerFins-Technology/dp/B09BNTQ39F",
        ],
        ("吸尘器", "扫地机器人"): [
            "https://www.amazon.com/Shark-Matrix-Self-Empty-Robot-Vacuum/dp/B0CDQJ14LT",
            "https://www.amazon.com/Shark-AV2501AE-AI-Robot-Vacuum/dp/B0BQ2YVHR7",
        ],
        ("清洁机", "蒸汽拖把"): [
            "https://www.amazon.com/Shark-S1000A-Powerful-Lightweight-Steam/dp/B07BGQP45K",
            "https://www.amazon.com/Shark-SK410-Steam-Pocket-Mop/dp/B003ZSHNGS",
        ],
    }),

    "olight": (BASE / "户外装备" / "olight", {
        ("手电筒", "手电筒"): [
            "https://www.amazon.com/OLIGHT-Warrior-Mini-Rechargeable-Flashlight/dp/B0BTBMX27S",
            "https://www.amazon.com/OLIGHT-Baton-Rechargeable-Flashlight-Battery/dp/B0C2CL3LBR",
            "https://www.amazon.com/OLIGHT-Seeker-Flashlight-Rechargeable-MCC3/dp/B08NF9STSY",
            "https://www.amazon.com/OLIGHT-Warrior-Rechargeable-Flashlight-Battery/dp/B0CQS1WR5Q",
            "https://www.amazon.com/OLIGHT-Marauder-Flashlight-Rechargeable-Searching/dp/B0CTTKZ6CP",
            "https://www.amazon.com/OLIGHT-S2R-Baton-Rechargeable-Flashlight/dp/B0CF2CMSCC",
            "https://www.amazon.com/OLIGHT-Baton-EDC-Flashlight-Rechargeable/dp/B0CW1GVNK3",
            "https://www.amazon.com/OLIGHT-Warrior-Rechargeable-Tactical-Flashlight/dp/B0BJ3BM9R3",
        ],
        ("手电筒", "头灯"): [
            "https://www.amazon.com/OLIGHT-Perun-Headlamp-Rechargeable-Flashlight/dp/B09R6R4N8B",
            "https://www.amazon.com/OLIGHT-Array-Headlamp-Rechargeable-Running/dp/B0BQMSHS69",
            "https://www.amazon.com/OLIGHT-H16-Wave-Headlamp-Hands-Free/dp/B0D3GCV7VT",
        ],
        ("手电筒", "营地灯"): [
            "https://www.amazon.com/OLIGHT-Olantern-Rechargeable-Camping-Lantern/dp/B098DQWFNJ",
            "https://www.amazon.com/OLIGHT-Obulb-Pro-Rechargeable-Flashlight/dp/B09V7GQLLJ",
        ],
    }),

    "bosch_professional": (BASE / "电动工具" / "bosch_professional", {
        ("电钻", "冲击钻"): [
            "https://www.amazon.com/Bosch-GBH18V-26DK15-Brushless-Connected-Ready/dp/B07G7FHXNQ",
            "https://www.amazon.com/Bosch-GSB18V-1330CN-PROFACTOR-Connected-Ready/dp/B0BK5XHX7N",
            "https://www.amazon.com/Bosch-GBH18V-34CQN-PROFACTOR-SDS-plus-Connected/dp/B09YJCMDWQ",
        ],
        ("电钻", "充电电钻"): [
            "https://www.amazon.com/Bosch-GSR18V-1330CN-PROFACTOR-Connected-Ready/dp/B0BK5SHR9G",
            "https://www.amazon.com/Bosch-GSR18V-755CN-Connected-Ready-Brushless/dp/B089P3D7NJ",
        ],
        ("电锯", "圆锯"): [
            "https://www.amazon.com/Bosch-GKS18V-26GCN-PROFACTOR-Connected-Ready/dp/B0BWQK6QZM",
            "https://www.amazon.com/Bosch-GKT18V-20GCL-PROFACTOR-Connected-Ready/dp/B0BK5WZ7HX",
        ],
        ("角磨机", "角磨机"): [
            "https://www.amazon.com/Bosch-GWS18V-13CN-PROFACTOR-Connected-Ready/dp/B09YKYXJ6H",
            "https://www.amazon.com/Bosch-GWX18V-13CN-PROFACTOR-Connected-Ready/dp/B0BK5TLWV5",
        ],
        ("砂光机", "轨道砂光机"): [
            "https://www.amazon.com/Bosch-GEX18V-5N-Brushless-Variable-Speed/dp/B085M5VHQW",
        ],
        ("铣", "修边机"): [
            "https://www.amazon.com/Bosch-GKF18V-25CN-PROFACTOR-Connected-Ready/dp/B0BK5TZFL1",
        ],
    }),

    "flos": (BASE / "灯具" / "flos", {
        ("台灯", "台灯"): [
            "https://www.amazon.com/Flos-Tab-Table-Lamp-Black/dp/B005C2WQYG",
        ],
        ("灯具", "综合"): [
            "https://www.amazon.com/Flos-Aim-Suspension-Lamp-Black/dp/B00OCP1NB0",
            "https://www.amazon.com/Flos-Captain-Flint-Floor-Lamp/dp/B074GYK4VB",
            "https://www.amazon.com/Flos-String-Light-Sphere-Head/dp/B074H2JYDW",
            "https://www.amazon.com/FLOS-IC-Lights-Table-Brass/dp/B073TV7Q6P",
        ],
    }),

    "louis_poulsen": (BASE / "灯具" / "louis_poulsen", {
        ("吊灯", "吊灯"): [
            "https://www.amazon.com/Louis-Poulsen-Pendant-Designed-Henningsen/dp/B0BX1PDKJX",
            "https://www.amazon.com/Louis-Poulsen-PH-5-Pendant/dp/B00FU3NPUM",
        ],
        ("台灯", "台灯"): [
            "https://www.amazon.com/Louis-Poulsen-Panthella-Table-Lamp/dp/B01N7B9X3F",
            "https://www.amazon.com/Louis-Poulsen-AJ-Table-Lamp/dp/B0032Z4WSQ",
        ],
    }),

    "bega": (BASE / "灯具" / "bega", {
        ("户外灯", "壁灯"): [
            "https://www.amazon.com/BEGA-22215-3-LED-Outdoor-Sconce/dp/B01M8LKLB1",
            "https://www.amazon.com/BEGA-33549-3-LED-Outdoor-Sconce/dp/B01M8LJ0G7",
        ],
    }),
}


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(SUPPLEMENTS.keys())

    total = 0
    for name in targets:
        if name not in SUPPLEMENTS:
            print(f'[跳过] 未知品牌: {name}', flush=True)
            continue
        base_dir, category_urls = SUPPLEMENTS[name]
        count = dl_classified(name, base_dir, category_urls)
        total += count

    print(f'\n=== 补爬完成: +{total} images ===', flush=True)


if __name__ == "__main__":
    main()
