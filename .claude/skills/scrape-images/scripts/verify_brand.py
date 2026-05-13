#!/usr/bin/env python3
"""
品牌数据验收脚本 — 每个品牌爬完后必须运行。
任何一项不通过就报错退出。

用法: python verify_brand.py <品牌文件夹路径>
示例: python verify_brand.py ~/Desktop/设计素材库/01_品类标杆库/电动工具/bosch_professional
"""
import sys
from pathlib import Path
from PIL import Image


def verify(brand_dir: Path):
    errors = []
    warnings = []

    if not brand_dir.exists():
        print(f"❌ 路径不存在: {brand_dir}")
        sys.exit(1)

    # 1. 检查图片总数
    all_imgs = list(brand_dir.rglob("*.jpg"))
    if len(all_imgs) == 0:
        errors.append("无任何图片")

    # 2. 检查 大类/大类 重复文件夹
    for d in brand_dir.iterdir():
        if d.is_dir():
            dup = d / d.name
            if dup.exists() and dup.is_dir():
                errors.append(f"重复文件夹: {d.name}/{d.name}")

    # 3. 检查空文件夹
    empty_dirs = [d for d in brand_dir.rglob("*") if d.is_dir() and not any(d.iterdir())]
    if empty_dirs:
        errors.append(f"{len(empty_dirs)} 个空文件夹: {[str(d.relative_to(brand_dir)) for d in empty_dirs[:3]]}")

    # 4. 检查图片质量
    low_res = 0
    black_bg = 0
    tiny = 0
    for f in all_imgs:
        try:
            img = Image.open(f)
            w, h = img.size
            # 分辨率检查
            if max(w, h) < 300:
                tiny += 1
            # 黑色背景检查
            corners = [img.getpixel((0, 0)), img.getpixel((w-1, 0)),
                       img.getpixel((0, h-1)), img.getpixel((w-1, h-1))]
            if sum(1 for c in corners if sum(c[:3]) < 30) >= 3:
                black_bg += 1
        except Exception:
            errors.append(f"无法打开图片: {f.name}")

    if tiny > 0:
        errors.append(f"{tiny} 张图片分辨率过低 (<300px)")
    if black_bg > 0:
        errors.append(f"{black_bg} 张图片有黑色背景（RGBA转换问题）")

    # 5. 检查错分类（电动工具品牌下不该有的分类）
    brand_name = brand_dir.name
    parent_cat = brand_dir.parent.name
    if parent_cat == "电动工具":
        bad_cats = {"保温容器", "健康监测", "家用电器", "游戏设备", "户外包袋"}
        for d in brand_dir.iterdir():
            if d.is_dir() and d.name in bad_cats:
                imgs_in = len(list(d.rglob("*.jpg")))
                if imgs_in > 0:
                    errors.append(f"错分类: {d.name}/ ({imgs_in} 张非电动工具图片)")

    # 输出结果
    print(f"\n{'='*50}")
    print(f"验收: {brand_dir.name} ({parent_cat})")
    print(f"{'='*50}")
    print(f"图片总数: {len(all_imgs)}")

    # 分类统计
    for d in sorted(brand_dir.iterdir()):
        if d.is_dir():
            direct = len(list(d.glob("*.jpg")))
            sub_total = len(list(d.rglob("*.jpg")))
            subs = [sd for sd in d.iterdir() if sd.is_dir()]
            if subs:
                print(f"  {d.name}/ ({direct} 直接)")
                for sd in sorted(subs):
                    sc = len(list(sd.rglob("*.jpg")))
                    if sc > 0:
                        print(f"    {sd.name}/: {sc}")
            elif sub_total > 0:
                print(f"  {d.name}/: {sub_total}")

    if warnings:
        print(f"\n⚠️  警告:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"\n❌ 不通过:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"\n✅ 验收通过")
        sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python verify_brand.py <品牌文件夹路径>")
        sys.exit(1)
    verify(Path(sys.argv[1]).expanduser())
