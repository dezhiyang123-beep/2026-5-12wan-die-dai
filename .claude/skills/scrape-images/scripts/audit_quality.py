#!/usr/bin/env python3
"""
素材库质量审计脚本。
检查：结构问题、分辨率、文件大小、黑色背景、损坏文件、跨品牌重复。
"""
import hashlib, os, sys, json
from pathlib import Path
from PIL import Image
from collections import defaultdict

# Fix Windows GBK encoding
sys.stdout.reconfigure(encoding='utf-8')

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库"
MIN_PX = 1000  # 最小边长阈值


def check_structure(brand_path):
    """检查文件夹结构问题。"""
    issues = []
    dirs = [d for d in brand_path.rglob('*') if d.is_dir()]
    for d in dirs:
        # 重复嵌套：大类/大类
        if d.parent != brand_path and d.name == d.parent.name:
            issues.append(f"重复嵌套: {d.relative_to(brand_path)}")
    # 空文件夹
    for d in dirs:
        files = [f for f in d.iterdir() if f.is_file()]
        subdirs = [f for f in d.iterdir() if f.is_dir()]
        if not files and not subdirs:
            issues.append(f"空文件夹: {d.relative_to(brand_path)}")
    # 编号断号
    for d in dirs:
        jpgs = sorted([f for f in d.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg')])
        if len(jpgs) >= 2:
            nums = []
            for f in jpgs:
                try:
                    nums.append(int(f.stem))
                except ValueError:
                    pass
            if nums and max(nums) > len(nums) + 5:
                issues.append(f"编号不连续: {d.relative_to(brand_path)} (max={max(nums)}, count={len(nums)})")
    return issues


def check_images(brand_path):
    """检查图片质量。"""
    stats = {
        'total': 0,
        'corrupt': [],
        'under_1000': [],
        'under_500': [],
        'tiny_file': [],  # <5KB
        'black_bg': [],
        'sizes': [],  # (max_dim, path)
    }
    for f in brand_path.rglob('*'):
        if f.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
            continue
        stats['total'] += 1
        rel = str(f.relative_to(brand_path))

        # File size
        fsize = f.stat().st_size
        if fsize < 5000:
            stats['tiny_file'].append(f"{rel} ({fsize}B)")
            continue

        # Try open
        try:
            img = Image.open(f)
            img.verify()
            img = Image.open(f)  # re-open after verify
            w, h = img.size
        except Exception as e:
            stats['corrupt'].append(f"{rel}: {e}")
            continue

        max_dim = max(w, h)
        stats['sizes'].append(max_dim)

        if max_dim < 500:
            stats['under_500'].append(f"{rel} ({w}x{h})")
        elif max_dim < 1000:
            stats['under_1000'].append(f"{rel} ({w}x{h})")

        # Black background check (sample 4 corners)
        try:
            rgb = img.convert('RGB')
            corners = [
                rgb.getpixel((0, 0)),
                rgb.getpixel((w-1, 0)),
                rgb.getpixel((0, h-1)),
                rgb.getpixel((w-1, h-1)),
            ]
            black_corners = sum(1 for c in corners if all(v < 15 for v in c))
            if black_corners >= 3:
                stats['black_bg'].append(rel)
        except Exception:
            pass

    return stats


def check_duplicates_across_brands(category_path):
    """同品类内跨品牌去重。"""
    hash_map = defaultdict(list)  # hash -> [(brand, rel_path)]
    for brand_dir in sorted(category_path.iterdir()):
        if not brand_dir.is_dir():
            continue
        brand = brand_dir.name
        for f in brand_dir.rglob('*'):
            if f.suffix.lower() not in ('.jpg', '.jpeg'):
                continue
            try:
                h = hashlib.md5(f.read_bytes()).hexdigest()
                hash_map[h].append(f"{brand}/{f.relative_to(brand_dir)}")
            except Exception:
                pass
    dupes = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
    return dupes


def main():
    print("=" * 60)
    print("素材库质量审计报告")
    print("=" * 60)

    all_issues = {}
    all_stats = {}

    for cat_dir in sorted(BASE.iterdir()):
        if not cat_dir.is_dir():
            continue
        cat_name = cat_dir.name
        print(f"\n{'─' * 50}")
        print(f"【{cat_name}】")
        print(f"{'─' * 50}")

        # Cross-brand duplicates
        dupes = check_duplicates_across_brands(cat_dir)
        if dupes:
            print(f"\n  ⚠ 跨品牌重复: {len(dupes)} 组")
            for h, paths in list(dupes.items())[:5]:
                print(f"    {' = '.join(paths)}")
            if len(dupes) > 5:
                print(f"    ...还有 {len(dupes)-5} 组")

        for brand_dir in sorted(cat_dir.iterdir()):
            if not brand_dir.is_dir():
                continue
            brand = brand_dir.name
            img_count = sum(1 for f in brand_dir.rglob('*')
                          if f.suffix.lower() in ('.jpg', '.jpeg'))
            if img_count == 0:
                continue

            # Structure
            struct_issues = check_structure(brand_dir)

            # Images
            img_stats = check_images(brand_dir)

            # Summary
            sizes = img_stats['sizes']
            if sizes:
                min_s, med_s, max_s = min(sizes), sorted(sizes)[len(sizes)//2], max(sizes)
            else:
                min_s = med_s = max_s = 0

            has_problems = (struct_issues or img_stats['corrupt'] or
                           img_stats['under_500'] or img_stats['tiny_file'] or
                           img_stats['black_bg'])

            status = "❌" if has_problems else ("⚠" if img_stats['under_1000'] else "✅")

            print(f"\n  {status} {brand}: {img_stats['total']}张 | 分辨率 {min_s}-{med_s}-{max_s}px")

            if img_stats['under_1000']:
                pct = len(img_stats['under_1000']) * 100 // max(img_stats['total'], 1)
                print(f"    ⚠ <1000px: {len(img_stats['under_1000'])}张 ({pct}%)")
                if pct > 80:
                    print(f"      → 可能是官网本身无高清图")

            if struct_issues:
                for s in struct_issues[:3]:
                    print(f"    ❌ {s}")

            if img_stats['corrupt']:
                for c in img_stats['corrupt'][:3]:
                    print(f"    ❌ 损坏: {c}")

            if img_stats['under_500']:
                print(f"    ❌ <500px: {len(img_stats['under_500'])}张")
                for u in img_stats['under_500'][:3]:
                    print(f"      {u}")

            if img_stats['tiny_file']:
                print(f"    ❌ <5KB: {len(img_stats['tiny_file'])}张")

            if img_stats['black_bg']:
                print(f"    ❌ 黑色背景: {len(img_stats['black_bg'])}张")
                for b in img_stats['black_bg'][:3]:
                    print(f"      {b}")

    print(f"\n{'=' * 60}")
    print("审计完成")


if __name__ == '__main__':
    main()
