#!/usr/bin/env python3
"""
筛选脚本：
  --task 05  重建 05_渲染参考库/产品主视觉：每个品牌/品类留3张（文件最大的3张），删其余
  --task 02  筛选 02_品牌语法库：每个品牌 current_line≤15张，premium_series≤5张，删其余
  --task all 两个都做
"""
import sys, shutil, argparse, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')
from pathlib import Path
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

BASE_01 = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库"
BASE_02 = Path.home() / "Desktop" / "设计素材库" / "02_品牌语法库"
BASE_05 = Path.home() / "Desktop" / "设计素材库" / "05_渲染参考库"
EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
MIN_KB = 50
MIN_LONG = 800

# ── 图片质量分析（和 auto_classify 一致）─────────────────────

def corner_brightness(img):
    w, h = img.size
    pts = [(0,0),(w-1,0),(0,h-1),(w-1,h-1),(w//2,0),(w//2,h-1),(0,h//2),(w-1,h//2)]
    rgb = img.convert('RGB')
    vals = [(rgb.getpixel((min(x,w-1), min(y,h-1)))[0]+
             rgb.getpixel((min(x,w-1), min(y,h-1)))[1]+
             rgb.getpixel((min(x,w-1), min(y,h-1)))[2])/3 for x,y in pts]
    return sum(vals)/len(vals)

def edge_saturation(img):
    w, h = img.size
    rgb = img.convert('RGB')
    pixels = []
    step = max(1, min(w, h)//20)
    for x in range(0, w, step):
        pixels.append(rgb.getpixel((x, 0)))
        pixels.append(rgb.getpixel((x, h-1)))
    for y in range(0, h, step):
        pixels.append(rgb.getpixel((0, y)))
        pixels.append(rgb.getpixel((w-1, y)))
    sats = [(max(r,g,b)-min(r,g,b))/max(max(r,g,b),1) for r,g,b in pixels]
    return sum(sats)/max(len(sats),1)*255

def is_product_visual(img_path):
    """判断是否属于产品主视觉（白/浅色背景，产品为主体）。"""
    try:
        with Image.open(img_path) as img:
            w, h = img.size
            if max(w, h) < MIN_LONG:
                return False
            ratio = w / max(h, 1)
            if ratio > 2.0 or ratio < 0.5:
                return False  # 极端比例 → 材质特写
            cb = corner_brightness(img)
            es = edge_saturation(img)
            if es > 25 and cb < 160:
                return False  # 场景氛围
            return True
    except Exception:
        return False


# ── 任务05：重建产品主视觉 ────────────────────────────────────

def filter_05(keep_per_group=3):
    print("== 筛选 05_渲染参考库/产品主视觉 ==\n")
    dest_dir = BASE_05 / "产品主视觉"

    # 清空现有内容
    deleted = 0
    for f in list(dest_dir.glob("*.*")):
        try:
            f.unlink()
            deleted += 1
        except Exception:
            pass
    print(f"  清空旧文件：{deleted} 张\n")

    copied_total = 0
    group_count = 0

    # 遍历 01_品类标杆库/{大类}/{品牌}/{小品类}/
    for category_dir in sorted(BASE_01.iterdir()):
        if not category_dir.is_dir():
            continue
        for brand_dir in sorted(category_dir.iterdir()):
            if not brand_dir.is_dir():
                continue
            for subcategory_dir in sorted(brand_dir.iterdir()):
                if not subcategory_dir.is_dir():
                    continue

                # 收集该分组的所有图
                imgs = []
                for f in sorted(subcategory_dir.rglob('*')):
                    if f.suffix.lower() not in EXTS:
                        continue
                    if f.stat().st_size / 1024 < MIN_KB:
                        continue
                    imgs.append(f)

                if not imgs:
                    continue

                # 筛选产品主视觉类图片，按文件大小降序
                visuals = [f for f in imgs if is_product_visual(f)]
                if not visuals:
                    # 若没有判断为产品主视觉的，取最大的3张兜底
                    visuals = sorted(imgs, key=lambda f: f.stat().st_size, reverse=True)

                visuals_sorted = sorted(visuals, key=lambda f: f.stat().st_size, reverse=True)
                top = visuals_sorted[:keep_per_group]

                group_label = f"{category_dir.name}/{brand_dir.name}/{subcategory_dir.name}"
                group_count += 1
                copied = 0

                for src in top:
                    dst_name = f"{brand_dir.name}_{subcategory_dir.name}_{src.name}"
                    dst = dest_dir / dst_name
                    # 避免重名
                    if dst.exists():
                        dst = dest_dir / f"{group_count:04d}_{dst_name}"
                    shutil.copy2(src, dst)
                    copied += 1

                copied_total += copied
                print(f"  {group_label}: {len(imgs)}→{copied} 张")

    print(f"\n完成！共 {group_count} 个品牌/品类组，保留 {copied_total} 张")
    print(f"→ 请打开 桌面/设计素材库/05_渲染参考库/产品主视觉/ 查看")


# ── 任务02：筛选品牌语法库 ────────────────────────────────────

BRAND_DIRS = {
    "DeWalt":    BASE_02 / "电动工具" / "DeWalt",
    "Milwaukee": BASE_02 / "电动工具" / "Milwaukee",
    "BEGA":      BASE_02 / "灯具" / "BEGA",
    "Artemide":  BASE_02 / "灯具" / "Artemide",
    "Festool":   BASE_02 / "电动工具" / "Festool",
}

SUB_KEEP = {
    "current_line": 15,
    "premium_series": 5,
    "detail_views": 10,
    "competitor_boundary": 999,  # 用户手动填，不删
}

def filter_02():
    print("== 筛选 02_品牌语法库 ==\n")

    for brand_key, brand_base in BRAND_DIRS.items():
        if not brand_base.exists():
            print(f"  [{brand_key}] 文件夹不存在，跳过")
            continue

        print(f"  [{brand_key}]")
        for sub_name, keep_n in SUB_KEEP.items():
            sub_dir = brand_base / sub_name
            if not sub_dir.exists():
                continue

            files = [f for f in sorted(sub_dir.iterdir())
                     if f.suffix.lower() in EXTS]
            if not files:
                continue

            # 按文件大小降序，保留前 keep_n 张
            files_sorted = sorted(files, key=lambda f: f.stat().st_size, reverse=True)
            keep = files_sorted[:keep_n]
            delete = files_sorted[keep_n:]

            for f in delete:
                try:
                    f.unlink()
                except Exception:
                    pass

            print(f"    {sub_name}: {len(files)} → {len(keep)} 张（删 {len(delete)} 张）")

    print(f"\n完成！")
    print("→ 请打开 桌面/设计素材库/02_品牌语法库/ 查看，删不合适的即可")


# ── 主入口 ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["05", "02", "all"], default="all")
    parser.add_argument("--keep", type=int, default=3, help="05任务每组保留张数（默认3）")
    args = parser.parse_args()

    if args.task in ("05", "all"):
        filter_05(keep_per_group=args.keep)
        print()
    if args.task in ("02", "all"):
        filter_02()


if __name__ == "__main__":
    main()
