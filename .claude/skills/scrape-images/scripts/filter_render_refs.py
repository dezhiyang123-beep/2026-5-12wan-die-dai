#!/usr/bin/env python3
"""
任务4a/4b — 从 01_品类标杆库 初筛高品质图片到 05_渲染参考库。

两步流程：
  步骤1 — 初筛（自动）：按分辨率+文件大小过滤，输出候选列表
  步骤2 — Contact sheet（自动）：按品牌生成缩略图网格，供用户确认

用法：
  # 步骤1：生成候选列表
  python filter_render_refs.py --step scan

  # 步骤2：生成contact sheet（每品牌一张图板，输出到桌面）
  python filter_render_refs.py --step sheets

  # 执行分类拷贝（用户看完contact sheet后说"编号X放产品主视觉"）
  python filter_render_refs.py --step copy --assign assignments.txt
"""
import sys, argparse, json, shutil
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from PIL import Image
from io import BytesIO
import math

BASE_01 = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库"
BASE_05 = Path.home() / "Desktop" / "设计素材库" / "05_渲染参考库"
SHEETS_DIR = Path.home() / "Desktop" / "contact_sheets_05"

SUBFOLDERS = {
    "产品主视觉": BASE_05 / "产品主视觉",
    "材质特写":   BASE_05 / "材质特写",
    "结构细节":   BASE_05 / "结构细节",
    "场景氛围":   BASE_05 / "场景氛围",
    "多角度":     BASE_05 / "多角度",
}

# 初筛阈值
MIN_LONG_SIDE = 1000    # 长边 ≥ 1000px
MIN_FILE_KB   = 100     # 文件 ≥ 100KB
MAX_RATIO     = 3.0     # 宽高比 < 3（排除横幅）


def scan_candidates() -> list:
    """扫描01，返回符合尺寸/大小要求的图片信息列表。"""
    import warnings
    warnings.filterwarnings('ignore', category=Image.DecompressionBombWarning)
    Image.MAX_IMAGE_PIXELS = None  # 允许超大图

    candidates = []
    img_id = 1
    exts = {'.jpg', '.jpeg', '.png', '.webp'}

    for img_path in sorted(BASE_01.rglob('*')):
        if img_path.suffix.lower() not in exts:
            continue
        # 跳过标记删除的文件夹
        if any(p.startswith('__') for p in img_path.parts):
            continue
        size_kb = img_path.stat().st_size / 1024
        if size_kb < MIN_FILE_KB:
            continue
        try:
            with Image.open(img_path) as img:
                w, h = img.size
        except Exception:
            continue
        long_side = max(w, h)
        if long_side < MIN_LONG_SIDE:
            continue
        ratio = w / max(h, 1)
        if ratio > MAX_RATIO or ratio < 1 / MAX_RATIO:
            continue

        # 从路径提取品类/品牌
        parts = img_path.relative_to(BASE_01).parts
        category = parts[0] if len(parts) > 0 else "unknown"
        brand = parts[1] if len(parts) > 1 else "unknown"

        candidates.append({
            "id": img_id,
            "path": str(img_path),
            "category": category,
            "brand": brand,
            "w": w,
            "h": h,
            "size_kb": round(size_kb, 1),
        })
        img_id += 1

    return candidates


def make_contact_sheet(images: list, title: str, out_path: Path,
                       thumb_w: int = 300, cols: int = 6):
    """生成缩略图网格图板，每张标编号。"""
    from PIL import ImageDraw, ImageFont
    if not images:
        return

    thumb_h = int(thumb_w * 0.8)
    label_h = 24
    cell_h = thumb_h + label_h
    rows = math.ceil(len(images) / cols)

    sheet = Image.new('RGB', (cols * thumb_w, rows * cell_h + 40), (240, 240, 240))
    draw = ImageDraw.Draw(sheet)

    # 标题
    draw.rectangle([0, 0, sheet.width, 36], fill=(50, 50, 50))
    draw.text((8, 8), title, fill=(255, 255, 255))

    try:
        font = ImageFont.truetype("arial.ttf", 14)
        small_font = ImageFont.truetype("arial.ttf", 11)
    except Exception:
        font = ImageFont.load_default()
        small_font = font

    for i, item in enumerate(images):
        row, col = divmod(i, cols)
        x = col * thumb_w
        y = 40 + row * cell_h

        # 缩略图
        try:
            with Image.open(item["path"]) as img:
                img.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
                thumb = Image.new('RGB', (thumb_w, thumb_h), (200, 200, 200))
                ox = (thumb_w - img.width) // 2
                oy = (thumb_h - img.height) // 2
                thumb.paste(img, (ox, oy))
        except Exception:
            thumb = Image.new('RGB', (thumb_w, thumb_h), (180, 180, 180))
        sheet.paste(thumb, (x, y))

        # 编号标签
        draw.rectangle([x, y + thumb_h, x + thumb_w, y + cell_h], fill=(30, 30, 30))
        label = f"#{item['id']}  {item['w']}×{item['h']}  {item['size_kb']}KB"
        draw.text((x + 4, y + thumb_h + 4), label, fill=(220, 220, 220), font=small_font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(out_path), 'JPEG', quality=88)
    print(f"  → {out_path.name}  ({len(images)} 张)", flush=True)


def step_scan():
    print("扫描 01_品类标杆库...", flush=True)
    candidates = scan_candidates()
    print(f"符合条件: {len(candidates)} 张（≥{MIN_LONG_SIDE}px长边, ≥{MIN_FILE_KB}KB）")

    # 按品牌统计
    from collections import Counter
    brand_counts = Counter(f"{c['category']}/{c['brand']}" for c in candidates)
    print("\n按品牌分布:")
    for brand, count in sorted(brand_counts.items(), key=lambda x: -x[1])[:20]:
        print(f"  {brand}: {count} 张")

    # 保存候选列表
    out = Path.home() / "Desktop" / "render_candidates.json"
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)
    print(f"\n候选列表已保存: {out}")
    print("下一步: python filter_render_refs.py --step sheets")


def step_sheets():
    candidates_file = Path.home() / "Desktop" / "render_candidates.json"
    if not candidates_file.exists():
        print("请先运行 --step scan")
        return

    with open(candidates_file, encoding='utf-8') as f:
        candidates = json.load(f)

    # 按品牌分组
    from collections import defaultdict
    by_brand = defaultdict(list)
    for c in candidates:
        key = f"{c['category']}_{c['brand']}"
        by_brand[key].append(c)

    print(f"生成 contact sheets → {SHEETS_DIR}")
    SHEETS_DIR.mkdir(parents=True, exist_ok=True)

    for brand_key, imgs in sorted(by_brand.items()):
        safe_name = brand_key.replace('/', '_').replace(' ', '_')
        out_path = SHEETS_DIR / f"{safe_name}.jpg"
        make_contact_sheet(imgs, f"{brand_key}  ({len(imgs)}张)", out_path)

    print(f"\n完成！{len(by_brand)} 个品牌图板已输出到桌面 contact_sheets_05/")
    print("查看后说明分类：\"#编号 → 产品主视觉/材质特写/结构细节/场景氛围/多角度/删除\"")
    print("然后运行: python filter_render_refs.py --step copy --assign assignments.txt")


def step_copy(assign_file: str):
    """
    按用户指定的分配文件执行拷贝。
    assignments.txt格式：每行 "#ID 子文件夹" 或 "#ID 删除"
    示例：
      #5 产品主视觉
      #12 材质特写
      #7 删除
    """
    candidates_file = Path.home() / "Desktop" / "render_candidates.json"
    with open(candidates_file, encoding='utf-8') as f:
        candidates = json.load(f)
    id_map = {c['id']: c for c in candidates}

    assignments = {}
    with open(assign_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith('#'):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            img_id = int(parts[0][1:])
            dest_cat = parts[1].strip()
            assignments[img_id] = dest_cat

    copied = 0
    skipped = 0
    for img_id, dest_cat in assignments.items():
        if dest_cat == "删除":
            skipped += 1
            continue
        if dest_cat not in SUBFOLDERS:
            print(f"  [未知分类] #{img_id} → {dest_cat}")
            continue
        if img_id not in id_map:
            print(f"  [未找到] #{img_id}")
            continue
        src = Path(id_map[img_id]['path'])
        dest_dir = SUBFOLDERS[dest_cat]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        if dest.exists():
            dest = dest_dir / f"{src.stem}_{img_id}{src.suffix}"
        shutil.copy2(src, dest)
        copied += 1

    print(f"拷贝完成: {copied} 张已分类，{skipped} 张标记删除")


def main():
    parser = argparse.ArgumentParser(description="05_渲染参考库筛选工具")
    parser.add_argument("--step", choices=["scan", "sheets", "copy"], required=True)
    parser.add_argument("--assign", help="分配文件路径（step=copy时必填）")
    args = parser.parse_args()

    if args.step == "scan":
        step_scan()
    elif args.step == "sheets":
        step_sheets()
    elif args.step == "copy":
        if not args.assign:
            print("--step copy 需要 --assign 参数")
            return
        step_copy(args.assign)


if __name__ == "__main__":
    main()
