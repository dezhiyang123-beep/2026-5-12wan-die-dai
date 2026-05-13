#!/usr/bin/env python3
"""清理后重新编号所有叶子文件夹的图片（无间隔连续编号）"""
import sys
from pathlib import Path

EXTS = {'.jpg', '.jpeg', '.png', '.webp'}

def renumber(base_path):
    base = Path(base_path)
    changed = 0
    for folder in sorted(base.rglob('*')):
        if not folder.is_dir():
            continue
        if any(x.is_dir() for x in folder.iterdir() if True):
            subdirs = [x for x in folder.iterdir() if x.is_dir()]
            if subdirs:
                continue
        imgs = sorted([f for f in folder.iterdir() if f.suffix.lower() in EXTS])
        if not imgs:
            continue
        # 先改成临时名避免冲突
        tmp = []
        for f in imgs:
            t = f.parent / f"__tmp_{f.name}"
            f.rename(t)
            tmp.append(t)
        # 重新编号
        for i, f in enumerate(tmp, 1):
            f.rename(f.parent / f"{i:02d}.jpg")
        print(f"  {folder.relative_to(base)}: {len(imgs)} 张")
        changed += 1
    print(f"\n完成：{changed} 个文件夹已重新编号")

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / "Desktop/设计素材库/01_品类标杆库")
    renumber(path)
