#!/usr/bin/env python3
"""
素材库全面清理：
Phase 1: 删除不可用数据
Phase 2: 修正分类错误
Phase 3: 结构修复（扁平化、去重、重编号）
"""
import sys, os, shutil, hashlib
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from PIL import Image
from collections import defaultdict

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库"

stats = {'deleted': 0, 'moved': 0, 'deduped': 0, 'renumbered': 0}


def delete_file(f):
    try:
        os.remove(str(f))
        stats['deleted'] += 1
        return True
    except:
        return False


def move_file(src, dest_dir, counter_dict):
    dest_dir.mkdir(parents=True, exist_ok=True)
    fk = str(dest_dir)
    if fk not in counter_dict:
        counter_dict[fk] = len([f for f in dest_dir.iterdir()
                                if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg')])
    counter_dict[fk] += 1
    dest = dest_dir / f"{counter_dict[fk]:02d}.jpg"
    try:
        shutil.move(str(src), str(dest))
        stats['moved'] += 1
        return True
    except:
        return False


# ══════════════════════════════════════════════════════════════
# Phase 1: 删除不可用数据
# ══════════════════════════════════════════════════════════════
def phase1():
    print("=" * 55)
    print("Phase 1: 删除不可用数据")
    print("=" * 55)

    # 1a. 删除完全废掉的品牌
    for path in [
        BASE / "消费电子" / "apple",   # 8张全是banner
        BASE / "音箱" / "devialet",     # 2张
    ]:
        if path.exists():
            count = sum(1 for f in path.rglob('*') if f.is_file())
            shutil.rmtree(str(path))
            print(f"  删除 {path.relative_to(BASE)} ({count}张，不可用)")

    # 1b. bega下的Hue系列（Philips的产品不是Bega的）
    hue = BASE / "灯具" / "bega" / "智能灯" / "Hue系列"
    if hue.exists():
        count = sum(1 for f in hue.rglob('*') if f.is_file())
        shutil.rmtree(str(hue))
        print(f"  删除 bega/智能灯/Hue系列 ({count}张，Philips产品误入)")

    # 1c. 删除所有 <200px 缩略图
    tiny = 0
    for f in list(BASE.rglob('*.jpg')) + list(BASE.rglob('*.jpeg')):
        try:
            if f.stat().st_size < 3000:
                delete_file(f); tiny += 1; continue
            img = Image.open(f)
            w, h = img.size; img.close()
            if max(w, h) < 200:
                delete_file(f); tiny += 1
        except:
            pass
    print(f"  删除 {tiny} 张 <200px 缩略图/<3KB 垃圾")

    # 1d. 删除纯banner图 (宽高比>3:1 且非产品图)
    banner = 0
    for f in list(BASE.rglob('*.jpg')):
        try:
            img = Image.open(f)
            w, h = img.size; img.close()
            ratio = max(w, h) / max(min(w, h), 1)
            if ratio > 3.0:
                delete_file(f); banner += 1
        except:
            pass
    print(f"  删除 {banner} 张 banner 图 (宽高比>3:1)")

    # 1e. 品牌内去重（保留第一张，删除重复）
    deduped = 0
    for cat_dir in BASE.iterdir():
        if not cat_dir.is_dir(): continue
        for brand_dir in cat_dir.iterdir():
            if not brand_dir.is_dir(): continue
            seen = {}
            for f in sorted(brand_dir.rglob('*.jpg')):
                try:
                    h = hashlib.md5(f.read_bytes()).hexdigest()
                    if h in seen:
                        delete_file(f); deduped += 1
                    else:
                        seen[h] = f
                except:
                    pass
    stats['deduped'] = deduped
    print(f"  去重 {deduped} 张品牌内重复图")

    print()


# ══════════════════════════════════════════════════════════════
# Phase 2: 修正分类错误
# ══════════════════════════════════════════════════════════════
def phase2():
    print("=" * 55)
    print("Phase 2: 修正分类错误")
    print("=" * 55)
    counters = {}

    # 2a. foscarini/手动工具 → 全是灯的lifestyle照，移到对应灯具分类
    # 这些是Birdie系列的台灯和落地灯场景图
    src = BASE / "灯具" / "foscarini" / "手动工具"
    if src.exists():
        dest = BASE / "灯具" / "foscarini" / "装饰落地灯"
        for f in list(src.rglob('*.jpg')):
            move_file(f, dest, counters)
        shutil.rmtree(str(src), ignore_errors=True)
        print(f"  foscarini/手动工具 → 装饰落地灯 (灯具被误分类)")

    # 2b. flos/电工工具 → 全是灯的场景照
    src = BASE / "灯具" / "flos" / "电工工具"
    if src.exists():
        dest = BASE / "灯具" / "flos" / "创意吊灯"
        for f in list(src.rglob('*.jpg')):
            move_file(f, dest, counters)
        shutil.rmtree(str(src), ignore_errors=True)
        print(f"  flos/电工工具 → 创意吊灯 (灯具被误分类)")

    # 2c. garmin/户外灯 → 全是手表，移到运动手表
    src = BASE / "户外装备" / "garmin" / "户外灯"
    if src.exists():
        dest = BASE / "户外装备" / "garmin" / "运动手表" / "智能手表"
        for f in list(src.rglob('*.jpg')):
            move_file(f, dest, counters)
        shutil.rmtree(str(src), ignore_errors=True)
        print(f"  garmin/户外灯 → 运动手表/智能手表 (手表被误分类为灯)")

    # 2d. artemide/其他灯具 173张 → 按现有的正确分类名重归类
    # artemide只做灯，"其他灯具"太模糊，合并到已有的灯具分类或保留为"装饰灯"
    src = BASE / "灯具" / "artemide" / "其他灯具"
    if src.exists():
        dest = BASE / "灯具" / "artemide" / "装饰灯"
        for f in list(src.rglob('*.jpg')):
            move_file(f, dest, counters)
        shutil.rmtree(str(src), ignore_errors=True)
        print(f"  artemide/其他灯具(173张) → 装饰灯")

    # 2e. bega/灯具(71张) 和 bega/照明(74张) → 合并为 室内灯/综合
    for name in ["灯具", "照明"]:
        src = BASE / "灯具" / "bega" / name
        if src.exists():
            dest = BASE / "灯具" / "bega" / "室内灯" / "综合"
            for f in list(src.rglob('*.jpg')):
                move_file(f, dest, counters)
            shutil.rmtree(str(src), ignore_errors=True)
            print(f"  bega/{name} → 室内灯/综合")

    # 2f. bega/智能灯 (剩余的非Hue图) → 室内灯/智能灯
    src = BASE / "灯具" / "bega" / "智能灯"
    if src.exists():
        imgs = list(src.glob('*.jpg'))
        if imgs:
            dest = BASE / "灯具" / "bega" / "室内灯" / "智能灯"
            for f in imgs:
                move_file(f, dest, counters)
        shutil.rmtree(str(src), ignore_errors=True)
        print(f"  bega/智能灯 → 室内灯/智能灯")

    # 2g. bega/射灯 → 室内灯/射灯
    src = BASE / "灯具" / "bega" / "射灯"
    if src.exists():
        dest = BASE / "灯具" / "bega" / "室内灯" / "射灯"
        for f in list(src.rglob('*.jpg')):
            move_file(f, dest, counters)
        shutil.rmtree(str(src), ignore_errors=True)
        print(f"  bega/射灯 → 室内灯/射灯")

    # 2h. louis_poulsen/照明(26张) → 重归类为 综合产品图
    src = BASE / "灯具" / "louis_poulsen" / "照明"
    if src.exists():
        dest = BASE / "灯具" / "louis_poulsen" / "产品总览"
        for f in list(src.rglob('*.jpg')):
            move_file(f, dest, counters)
        shutil.rmtree(str(src), ignore_errors=True)
        print(f"  louis_poulsen/照明 → 产品总览")

    # 2i. louis_poulsen: 合并 户外灯 和 户外灯具 重复品类
    src = BASE / "灯具" / "louis_poulsen" / "户外灯具"
    if src.exists():
        dest = BASE / "灯具" / "louis_poulsen" / "户外灯"
        for f in list(src.rglob('*.jpg')):
            move_file(f, dest, counters)
        shutil.rmtree(str(src), ignore_errors=True)
        print(f"  louis_poulsen/户外灯具 → 户外灯 (合并重复品类)")

    # 2j. rab_lighting 英文文件夹 → 合并到对应中文分类
    rab = BASE / "灯具" / "rab_lighting"
    eng_mapping = {
        "Cylinders": ("室内灯", "筒灯"),
        "Panels_Troffers": ("室内灯", "面板灯"),
        "Recessed_Downlights": ("室内灯", "商用筒灯"),
        "Strips_Wraps": ("室内灯", "条形灯"),
    }
    for eng_name, (major, minor) in eng_mapping.items():
        src = rab / eng_name
        if src.exists():
            dest = rab / major / minor
            for f in list(src.rglob('*.jpg')) + list(src.rglob('*.png')):
                move_file(f, dest, counters)
            shutil.rmtree(str(src), ignore_errors=True)
            print(f"  rab/{eng_name} → {major}/{minor}")

    # 2k. shark/吸尘器 — 里面混了非吸尘器产品（美发工具、空气炸锅、空气净化器）
    # 无法自动区分内容，但可以把 吸尘器/ 下直接放的图（非子文件夹）标记
    # shark结构：吸尘器/（52张混杂）+ 吸尘器/扫地机器人（81张）
    # 吸尘器/下的52张有banner和错分产品，先不动（需要人工审核或后续优化爬虫）

    print()


# ══════════════════════════════════════════════════════════════
# Phase 3: 结构修复
# ══════════════════════════════════════════════════════════════
def phase3():
    print("=" * 55)
    print("Phase 3: 结构修复")
    print("=" * 55)
    counters = {}

    # 3a. 扁平化：只有一个子文件夹的父文件夹 → 提升子文件夹
    changed = True
    total_flat = 0
    while changed:
        changed = False
        for d in sorted(BASE.rglob('*'), key=lambda x: len(x.parts), reverse=True):
            if not d.is_dir(): continue
            if d == BASE: continue
            children = list(d.iterdir())
            dirs = [c for c in children if c.is_dir()]
            files = [c for c in children if c.is_file()]

            # 只有一个子目录，没有文件 → 提升
            if len(dirs) == 1 and not files:
                child = dirs[0]
                # 把child的内容全部移到parent
                for item in list(child.iterdir()):
                    dest = d / item.name
                    if dest.exists():
                        # 如果同名冲突，加后缀
                        if item.is_file():
                            base_name = item.stem
                            ext = item.suffix
                            i = 1
                            while dest.exists():
                                dest = d / f"{base_name}_{i}{ext}"
                                i += 1
                        else:
                            # 目录同名，跳过
                            continue
                    shutil.move(str(item), str(dest))
                child.rmdir()
                total_flat += 1
                changed = True

    print(f"  扁平化 {total_flat} 个单子文件夹")

    # 3b. 混合层级修复：同级有图片+子文件夹 → 图片移入"综合"子文件夹
    mixed_fixed = 0
    for d in sorted(BASE.rglob('*')):
        if not d.is_dir(): continue
        files = [f for f in d.iterdir() if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png')]
        subdirs = [f for f in d.iterdir() if f.is_dir()]
        if files and subdirs:
            # 有图片也有子文件夹 → 把图片移到"综合"
            dest = d / "综合"
            dest.mkdir(exist_ok=True)
            for f in files:
                shutil.move(str(f), str(dest / f.name))
            mixed_fixed += 1
    print(f"  修复 {mixed_fixed} 个混合层级")

    # 3c. 重编号：所有叶子文件夹重新从01开始
    renumbered = 0
    for d in sorted(BASE.rglob('*')):
        if not d.is_dir(): continue
        subdirs = [f for f in d.iterdir() if f.is_dir()]
        if subdirs: continue  # 非叶子

        imgs = sorted([f for f in d.iterdir() if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png')])
        if not imgs: continue

        # 检查是否需要重编号
        needs_renum = False
        for i, f in enumerate(imgs, 1):
            expected = f"{i:02d}"
            if f.stem != expected:
                needs_renum = True
                break

        if needs_renum:
            # 先重命名为临时名避免冲突
            for i, f in enumerate(imgs):
                tmp = d / f"_tmp_{i}{f.suffix}"
                f.rename(tmp)
            # 再按顺序编号
            tmps = sorted([f for f in d.iterdir() if f.name.startswith('_tmp_')])
            for i, f in enumerate(tmps, 1):
                final = d / f"{i:02d}{f.suffix}"
                f.rename(final)
            renumbered += 1

    stats['renumbered'] = renumbered
    print(f"  重编号 {renumbered} 个文件夹")

    # 3d. 清理空文件夹
    empty = 0
    for d in sorted(BASE.rglob('*'), key=lambda x: len(x.parts), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
            empty += 1
    print(f"  清理 {empty} 个空文件夹")

    print()


if __name__ == '__main__':
    print("素材库全面清理")
    print()
    phase1()
    phase2()
    phase3()

    print("=" * 55)
    print(f"完成: 删除{stats['deleted']}张 | 移动{stats['moved']}张 | 去重{stats['deduped']}张 | 重编号{stats['renumbered']}个文件夹")

    # 最终统计
    print()
    total = 0
    for cat_dir in sorted(BASE.iterdir()):
        if not cat_dir.is_dir(): continue
        cat_count = sum(1 for f in cat_dir.rglob('*') if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png'))
        total += cat_count
        print(f"  {cat_dir.name}: {cat_count}张")
    print(f"  总计: {total}张")
