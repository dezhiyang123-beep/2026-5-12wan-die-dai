#!/usr/bin/env python3
"""
自动分类脚本：
  任务4 — 把01_品类标杆库候选图自动分类到05_渲染参考库五个子文件夹
  任务5 — 把重点品牌图自动分类到02_品牌语法库四个子文件夹

分类后用户直接进文件夹删不合适的即可，不需要看contact sheet。

用法：
  python auto_classify.py --task 05   # 分类05渲染参考库
  python auto_classify.py --task 02   # 分类02品牌语法库
  python auto_classify.py --task all  # 两个都做
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

# 05子文件夹
RENDER_FOLDERS = {
    "产品主视觉": BASE_05 / "产品主视觉",
    "材质特写":   BASE_05 / "材质特写",
    "结构细节":   BASE_05 / "结构细节",
    "场景氛围":   BASE_05 / "场景氛围",
    "多角度":     BASE_05 / "多角度",
}

# 02品牌配置
BRAND_MAP = {
    "DeWalt":    ("电动工具/dewalt",    "电动工具/DeWalt"),
    "Milwaukee": ("电动工具/milwaukee", "电动工具/Milwaukee"),
    "BEGA":      ("灯具/bega",          "灯具/BEGA"),
    "Artemide":  ("灯具/artemide",      "灯具/Artemide"),
    "Festool":   ("电动工具/festool",   "电动工具/Festool"),
}
GRAMMAR_SUBS = ["current_line", "premium_series", "detail_views", "competitor_boundary"]

EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
MIN_LONG = 1000
MIN_KB   = 100


# ── 图片特征分析 ──────────────────────────────────────────

def corner_brightness(img: Image.Image) -> float:
    """四角平均亮度，0-255。高=白底，低=深色背景。"""
    w, h = img.size
    pts = [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1),
           (w//2, 0), (w//2, h-1), (0, h//2), (w-1, h//2)]
    vals = []
    rgb = img.convert('RGB')
    for x, y in pts:
        r, g, b = rgb.getpixel((min(x, w-1), min(y, h-1)))
        vals.append((r + g + b) / 3)
    return sum(vals) / len(vals)


def edge_saturation(img: Image.Image) -> float:
    """边缘像素平均饱和度，高 = 场景照（有色彩），低 = 白底产品图。"""
    w, h = img.size
    rgb = img.convert('RGB')
    pixels = []
    step = max(1, min(w, h) // 20)
    for x in range(0, w, step):
        pixels.append(rgb.getpixel((x, 0)))
        pixels.append(rgb.getpixel((x, h-1)))
    for y in range(0, h, step):
        pixels.append(rgb.getpixel((0, y)))
        pixels.append(rgb.getpixel((w-1, y)))
    sats = []
    for r, g, b in pixels:
        mx, mn = max(r, g, b), min(r, g, b)
        sats.append((mx - mn) / max(mx, 1))
    return sum(sats) / max(len(sats), 1) * 255


def classify_render(img_path: Path) -> str:
    """返回05子文件夹名。"""
    path_str = str(img_path).lower().replace('\\', '/')

    # 路径提示最优先
    if 'detail_view' in path_str or '/detail/' in path_str:
        return "多角度"

    size_kb = img_path.stat().st_size / 1024
    try:
        with Image.open(img_path) as img:
            w, h = img.size
            ratio = w / max(h, 1)
            cb = corner_brightness(img)
            es = edge_saturation(img)
    except Exception:
        return "产品主视觉"

    # 场景氛围：边缘高饱和 + 背景偏暗
    if es > 25 and cb < 160:
        return "场景氛围"

    # 材质特写：比例极端（超宽或超高）或极小面积
    if ratio > 2.0 or ratio < 0.5:
        return "材质特写"
    if max(w, h) < 1200 and size_kb < 200:
        return "材质特写"

    # 结构细节：文件名暗示局部/细节
    fname = img_path.stem.lower()
    if any(k in fname for k in ['close', 'detail', 'zoom', 'crop', 'part']):
        return "结构细节"

    # 多角度：文件名暗示角度
    if any(k in fname for k in ['side', 'back', 'front', 'top', 'bottom', 'angle']):
        return "多角度"

    # 白底产品图 → 产品主视觉
    if cb >= 200:
        return "产品主视觉"

    # 其余场景感图
    if cb < 140:
        return "场景氛围"

    return "产品主视觉"


# ── 任务4：05渲染参考库 ───────────────────────────────────

def classify_05():
    print("== 任务4：自动分类 → 05_渲染参考库 ==\n")
    for f in RENDER_FOLDERS.values():
        f.mkdir(parents=True, exist_ok=True)

    counts = {k: 0 for k in RENDER_FOLDERS}
    skipped = 0
    total = 0

    for img_path in sorted(BASE_01.rglob('*')):
        if img_path.suffix.lower() not in EXTS:
            continue
        if any(p.startswith('__') for p in img_path.parts):
            continue
        size_kb = img_path.stat().st_size / 1024
        if size_kb < MIN_KB:
            continue
        try:
            with Image.open(img_path) as img:
                if max(img.size) < MIN_LONG:
                    continue
        except Exception:
            skipped += 1
            continue

        cat = classify_render(img_path)
        dest_dir = RENDER_FOLDERS[cat]
        dest = dest_dir / img_path.name
        # 文件名冲突时加品牌前缀
        if dest.exists():
            brand = img_path.parent.name
            dest = dest_dir / f"{brand}_{img_path.name}"
        shutil.copy2(img_path, dest)
        counts[cat] += 1
        total += 1
        if total % 100 == 0:
            print(f"  已处理 {total} 张...", flush=True)

    print(f"\n完成！共拷贝 {total} 张（跳过 {skipped} 张损坏图）")
    print("\n各文件夹分布：")
    for cat, n in counts.items():
        print(f"  {cat}: {n} 张")
    print(f"\n→ 请打开 桌面/设计素材库/05_渲染参考库/ 直接删除不合适的图片")


# ── 任务5：02品牌语法库 ───────────────────────────────────

def classify_brand(imgs: list, brand_key: str, dest_base: Path):
    """
    自动分配规则：
    - 有 detail_views 路径的 → detail_views
    - 文件最大的前15张 → current_line（主力产品）
    - 文件大小排名16-20 → premium_series（高端系列）
    - 其余高分辨率图 → current_line（继续补充）
    - competitor_boundary 留空（无竞品数据，用户自填）
    """
    if not imgs:
        return 0

    # 按文件大小降序
    imgs_with_size = []
    for p in imgs:
        try:
            sz = p.stat().st_size
            imgs_with_size.append((sz, p))
        except Exception:
            pass
    imgs_with_size.sort(reverse=True)

    for sub in GRAMMAR_SUBS:
        (dest_base / sub).mkdir(parents=True, exist_ok=True)

    copied = 0
    current_count = 0
    premium_count = 0

    for rank, (sz, p) in enumerate(imgs_with_size):
        path_str = str(p).lower().replace('\\', '/')
        fname = p.stem.lower()

        # detail_views子文件夹的图 → detail_views
        if 'detail_view' in path_str or 'detail/' in path_str:
            sub = "detail_views"
        # 多角度暗示 → detail_views
        elif any(k in fname for k in ['side', 'back', 'front', 'top', 'angle', 'view']):
            sub = "detail_views"
        # 前5大文件 → premium_series
        elif premium_count < 5:
            sub = "premium_series"
            premium_count += 1
        # 接下来的较大文件 → current_line（最多15张）
        elif current_count < 15:
            sub = "current_line"
            current_count += 1
        # 超出后继续放current_line
        else:
            sub = "current_line"

        dest = dest_base / sub / p.name
        if dest.exists():
            dest = dest_base / sub / f"{rank:04d}_{p.name}"
        shutil.copy2(p, dest)
        copied += 1

    return copied


def classify_02():
    print("== 任务5：自动分类 → 02_品牌语法库 ==\n")

    for brand_key, (src_rel, dest_rel) in BRAND_MAP.items():
        src_dir = BASE_01 / Path(src_rel)
        dest_base = BASE_02 / Path(dest_rel)

        if not src_dir.exists():
            print(f"  [{brand_key}] 跳过：01中路径不存在 ({src_rel})", flush=True)
            continue

        imgs = [p for p in sorted(src_dir.rglob('*'))
                if p.suffix.lower() in EXTS
                and not any(x.startswith('__') for x in p.parts)]

        if not imgs:
            print(f"  [{brand_key}] 跳过：无图片", flush=True)
            continue

        n = classify_brand(imgs, brand_key, dest_base)

        # 统计各子文件夹
        sub_counts = {s: len(list((dest_base / s).glob('*.*'))) for s in GRAMMAR_SUBS}
        current = sub_counts.get('current_line', 0)
        detail = sub_counts.get('detail_views', 0)
        status = "✓" if current >= 10 and detail >= 5 else "⚠"
        print(f"  [{brand_key}] {n} 张 {status}")
        for s, c in sub_counts.items():
            if c > 0:
                print(f"    {s}: {c} 张")

    print(f"\n→ 请打开 桌面/设计素材库/02_品牌语法库/ 直接删除不合适的图片")
    print("  competitor_boundary 文件夹留空，请手动添加竞品图")


# ── 主入口 ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="自动分类到05/02素材库")
    parser.add_argument("--task", choices=["05", "02", "all"], default="all")
    args = parser.parse_args()

    if args.task in ("05", "all"):
        classify_05()
        print()
    if args.task in ("02", "all"):
        classify_02()


if __name__ == "__main__":
    main()
