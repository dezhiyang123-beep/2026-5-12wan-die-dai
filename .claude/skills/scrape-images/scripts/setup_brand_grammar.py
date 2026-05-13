#!/usr/bin/env python3
"""
任务5 — 从 01_品类标杆库 为重点品牌建立 02_品牌语法库 子结构。

两步流程：
  步骤1 — 生成品牌 contact sheet（从01中取该品牌所有图）
  步骤2 — 按用户分配拷贝到 current_line/premium_series/detail_views/competitor_boundary

目标品牌（按01中图片数量）：
  DeWalt（584）/ Milwaukee（269）/ BEGA（329）/ Artemide（199）/ Festool（132）

用法：
  python setup_brand_grammar.py --step sheets                  # 为5个品牌生成图板
  python setup_brand_grammar.py --step copy --assign a.txt    # 执行分类拷贝
  python setup_brand_grammar.py --step status                 # 查看当前进度
"""
import sys, argparse, shutil, json, math
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import warnings
warnings.filterwarnings('ignore', category=Image.DecompressionBombWarning)
Image.MAX_IMAGE_PIXELS = None

BASE_01 = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库"
BASE_02 = Path.home() / "Desktop" / "设计素材库" / "02_品牌语法库"
SHEETS_DIR = Path.home() / "Desktop" / "contact_sheets_02"

# 目标品牌配置：(01路径, 02目标路径)
TARGET_BRANDS = {
    "DeWalt":    ("电动工具/dewalt",    "电动工具/DeWalt"),
    "Milwaukee": ("电动工具/milwaukee", "电动工具/Milwaukee"),
    "BEGA":      ("灯具/bega",          "灯具/BEGA"),
    "Artemide":  ("灯具/artemide",      "灯具/Artemide"),
    "Festool":   ("电动工具/festool",   "电动工具/Festool"),
}

GRAMMAR_SUBFOLDERS = ["current_line", "premium_series", "detail_views", "competitor_boundary"]


def get_brand_images(brand_key: str) -> list:
    src_path_rel, _ = TARGET_BRANDS[brand_key]
    src_dir = BASE_01 / Path(src_path_rel)
    exts = {'.jpg', '.jpeg', '.png', '.webp'}
    imgs = []
    if not src_dir.exists():
        return imgs
    for p in sorted(src_dir.rglob('*')):
        if p.suffix.lower() in exts and not any(x.startswith('__') for x in p.parts):
            imgs.append(p)
    return imgs


def make_contact_sheet(images: list, title: str, out_path: Path,
                       thumb_w: int = 240, cols: int = 8):
    if not images:
        print(f"  [跳过] {title}：没有图片", flush=True)
        return

    thumb_h = int(thumb_w * 0.8)
    label_h = 22
    cell_h = thumb_h + label_h
    rows = math.ceil(len(images) / cols)

    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except Exception:
        font = ImageFont.load_default()

    sheet = Image.new('RGB', (cols * thumb_w, 40 + rows * cell_h), (235, 235, 235))
    draw = ImageDraw.Draw(sheet)
    draw.rectangle([0, 0, sheet.width, 38], fill=(40, 40, 40))
    draw.text((8, 10), title, fill=(255, 255, 255), font=font)

    for i, img_path in enumerate(images):
        row, col = divmod(i, cols)
        x = col * thumb_w
        y = 40 + row * cell_h

        try:
            with Image.open(img_path) as img:
                img.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
                cell = Image.new('RGB', (thumb_w, thumb_h), (190, 190, 190))
                ox = (thumb_w - img.width) // 2
                oy = (thumb_h - img.height) // 2
                cell.paste(img, (ox, oy))
        except Exception:
            cell = Image.new('RGB', (thumb_w, thumb_h), (170, 170, 170))

        sheet.paste(cell, (x, y))
        draw.rectangle([x, y + thumb_h, x + thumb_w, y + cell_h], fill=(25, 25, 25))
        # 编号 = 1-based
        draw.text((x + 3, y + thumb_h + 3), f"#{i + 1}  {img_path.name[:20]}",
                  fill=(210, 210, 210), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(out_path), 'JPEG', quality=85)
    print(f"  → {out_path.name}  ({len(images)} 张)", flush=True)


def step_sheets():
    print(f"生成品牌语法库 contact sheets → {SHEETS_DIR}")
    index = {}  # brand → [path, ...]

    for brand_key in TARGET_BRANDS:
        imgs = get_brand_images(brand_key)
        if not imgs:
            print(f"  [跳过] {brand_key}：01中找不到路径", flush=True)
            continue
        out_path = SHEETS_DIR / f"{brand_key}.jpg"
        make_contact_sheet(imgs, f"{brand_key}  ({len(imgs)}张)", out_path)
        index[brand_key] = [str(p) for p in imgs]

    # 保存索引（供copy步骤使用）
    idx_path = Path.home() / "Desktop" / "brand_grammar_index.json"
    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"\n索引已保存: {idx_path}")
    print(
        "\n查看图板后，创建 assignments.txt，格式：\n"
        "  DeWalt #5 current_line\n"
        "  DeWalt #12 premium_series\n"
        "  DeWalt #7 detail_views\n"
        "  DeWalt #3 competitor_boundary\n"
        "  DeWalt #9 删除\n"
        "然后运行: python setup_brand_grammar.py --step copy --assign assignments.txt"
    )


def step_copy(assign_file: str):
    idx_path = Path.home() / "Desktop" / "brand_grammar_index.json"
    if not idx_path.exists():
        print("请先运行 --step sheets")
        return

    with open(idx_path, encoding='utf-8') as f:
        index = json.load(f)

    # 解析分配文件
    assignments = []  # [(brand, idx_1based, subfolder)]
    with open(assign_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            brand = parts[0]
            try:
                num = int(parts[1].lstrip('#'))
            except ValueError:
                continue
            subfolder = parts[2]
            assignments.append((brand, num, subfolder))

    copied = 0
    for brand, num, subfolder in assignments:
        if subfolder == "删除":
            continue
        if subfolder not in GRAMMAR_SUBFOLDERS:
            print(f"  [未知子文件夹] {brand} #{num} → {subfolder}")
            continue
        if brand not in index:
            print(f"  [未知品牌] {brand}")
            continue
        imgs = index[brand]
        if num < 1 or num > len(imgs):
            print(f"  [越界] {brand} #{num}（共{len(imgs)}张）")
            continue

        src = Path(imgs[num - 1])
        _, dest_rel = TARGET_BRANDS[brand]
        dest_dir = BASE_02 / dest_rel / subfolder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        if dest.exists():
            dest = dest_dir / f"{src.stem}_{num}{src.suffix}"
        shutil.copy2(src, dest)
        copied += 1
        print(f"  ✓ {brand} #{num} → {subfolder}/{dest.name}", flush=True)

    print(f"\n完成：{copied} 张已拷贝到 02_品牌语法库")


def step_status():
    print("== 02_品牌语法库 当前进度 ==\n")
    for brand_key, (_, dest_rel) in TARGET_BRANDS.items():
        dest_base = BASE_02 / dest_rel
        total = 0
        sub_counts = {}
        for sub in GRAMMAR_SUBFOLDERS:
            sub_dir = dest_base / sub
            n = len(list(sub_dir.glob('*.*'))) if sub_dir.exists() else 0
            sub_counts[sub] = n
            total += n
        status = "✓ 满足最低要求" if sub_counts.get("current_line", 0) >= 10 \
            and sub_counts.get("detail_views", 0) >= 5 else "⚠ 未达标"
        print(f"  {brand_key}: {total}张  {status}")
        for sub, n in sub_counts.items():
            if n > 0:
                print(f"    {sub}: {n}张")
    print()


def main():
    parser = argparse.ArgumentParser(description="02_品牌语法库建立工具")
    parser.add_argument("--step", choices=["sheets", "copy", "status"], required=True)
    parser.add_argument("--assign", help="分配文件（step=copy时必填）")
    args = parser.parse_args()

    if args.step == "sheets":
        step_sheets()
    elif args.step == "copy":
        if not args.assign:
            print("--step copy 需要 --assign 参数")
            return
        step_copy(args.assign)
    elif args.step == "status":
        step_status()


if __name__ == "__main__":
    main()
