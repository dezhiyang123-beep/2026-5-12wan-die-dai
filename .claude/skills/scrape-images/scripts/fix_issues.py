#!/usr/bin/env python3
"""
修复素材库两类问题：
1. 重复嵌套文件夹（大类/大类/ → 合并到 大类/）
2. 黑色背景图片 → 白底填充
"""
import sys, shutil
from pathlib import Path
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库"


# ── 修复1：重复嵌套 ──────────────────────────────────────────────

def fix_nested_duplicates():
    """找到 大类/大类/ 的嵌套，把子文件夹图片合并到父文件夹，删除子文件夹。"""
    print("=" * 50)
    print("修复重复嵌套文件夹")
    print("=" * 50)

    fixed = 0
    for brand_dir in sorted(BASE.rglob('*')):
        if not brand_dir.is_dir():
            continue
        # 找 parent/child 同名的情况
        for sub in sorted(brand_dir.iterdir()):
            if not sub.is_dir():
                continue
            if sub.name == brand_dir.name and brand_dir.parent.is_dir():
                # sub 就是嵌套的重复文件夹
                parent = brand_dir  # 图片应该在这里
                child = sub         # 需要合并到 parent

                # 收集 parent 里已有的文件hash
                parent_files = set()
                for f in parent.iterdir():
                    if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png'):
                        parent_files.add(f.name)

                # 获取 parent 当前最大编号
                max_num = 0
                for f in parent.iterdir():
                    if f.is_file():
                        try:
                            max_num = max(max_num, int(f.stem))
                        except ValueError:
                            pass

                # 移动 child 里的图片到 parent
                moved = 0
                dupes = 0
                for f in sorted(child.iterdir()):
                    if not f.is_file():
                        continue
                    if f.suffix.lower() not in ('.jpg', '.jpeg', '.png'):
                        continue

                    # 检查是否和 parent 里的图片重复（按文件大小判断）
                    is_dupe = False
                    for pf in parent.iterdir():
                        if pf.is_file() and pf.stat().st_size == f.stat().st_size:
                            is_dupe = True
                            break

                    if is_dupe:
                        f.unlink()
                        dupes += 1
                    else:
                        max_num += 1
                        dest = parent / f"{max_num:02d}{f.suffix}"
                        shutil.move(str(f), str(dest))
                        moved += 1

                # 删除空的子文件夹
                if not any(child.iterdir()):
                    child.rmdir()

                rel = child.relative_to(BASE)
                print(f"  {rel}: 合并{moved}张, 去重{dupes}张")
                fixed += 1

    print(f"\n共修复 {fixed} 个嵌套文件夹\n")


# ── 修复2：黑色背景 ──────────────────────────────────────────────

def has_black_background(img_path):
    """检查图片是否有黑色背景（至少3个角为黑色）。"""
    try:
        img = Image.open(img_path)
        rgb = img.convert('RGB')
        w, h = rgb.size
        corners = [
            rgb.getpixel((0, 0)),
            rgb.getpixel((w-1, 0)),
            rgb.getpixel((0, h-1)),
            rgb.getpixel((w-1, h-1)),
        ]
        black = sum(1 for c in corners if all(v < 15 for v in c))
        return black >= 3
    except Exception:
        return False


def fix_black_to_white(img_path):
    """把黑色背景替换为白色背景。
    方法：将图片转为RGBA，把接近黑色的像素变为透明，然后粘贴到白底上。
    """
    try:
        img = Image.open(img_path).convert('RGBA')
        w, h = img.size
        pixels = img.load()

        # 找到边缘的黑色像素，用flood-fill思路把连通的黑色区域变透明
        # 简化方法：扫描所有像素，如果RGB都<20就设为透明
        # 但这样可能把产品内部的黑色也去掉
        # 更安全的方法：只处理边缘连通的黑色区域

        # 用简单的边缘扫描：上下左右各5px的边框区域，黑色变白色
        # 然后用白底合成
        # 实际上最安全的做法：直接用白底合成，不改原图透明度
        # 因为很多是PNG转JPG时透明变黑的问题

        # 检测是否原图有alpha通道信息
        orig = Image.open(img_path)
        if orig.mode in ('RGBA', 'LA', 'PA'):
            # 有alpha通道，直接白底合成
            bg = Image.new('RGB', (w, h), (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            bg.save(img_path, 'JPEG', quality=95)
            return True

        # 没有alpha通道（JPG），黑色背景是实际的黑色像素
        # 用边缘检测：如果边缘大部分是黑色，把黑色像素替换为白色
        # 但只替换"背景区域"的黑色，不动产品本身
        # 安全做法：用边缘flood fill

        rgb = orig.convert('RGB')
        pixels_rgb = rgb.load()

        # 创建mask：从四个角flood fill黑色区域
        visited = [[False]*h for _ in range(w)]
        bg_mask = [[False]*h for _ in range(w)]

        def is_near_black(x, y):
            r, g, b = pixels_rgb[x, y]
            return r < 30 and g < 30 and b < 30

        # BFS from corners
        from collections import deque
        queue = deque()
        for sx, sy in [(0,0), (w-1,0), (0,h-1), (w-1,h-1)]:
            if is_near_black(sx, sy):
                queue.append((sx, sy))
                visited[sx][sy] = True
                bg_mask[sx][sy] = True

        while queue:
            x, y = queue.popleft()
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = x+dx, y+dy
                if 0 <= nx < w and 0 <= ny < h and not visited[nx][ny]:
                    visited[nx][ny] = True
                    if is_near_black(nx, ny):
                        bg_mask[nx][ny] = True
                        queue.append((nx, ny))

        # Apply: set background pixels to white
        changed = 0
        for x in range(w):
            for y in range(h):
                if bg_mask[x][y]:
                    pixels_rgb[x, y] = (255, 255, 255)
                    changed += 1

        if changed > 0:
            rgb.save(img_path, 'JPEG', quality=95)
            return True
        return False

    except Exception as e:
        print(f"    错误: {img_path.name}: {e}")
        return False


def fix_black_backgrounds():
    """修复所有黑色背景图片。"""
    print("=" * 50)
    print("修复黑色背景")
    print("=" * 50)

    total_fixed = 0
    for cat_dir in sorted(BASE.iterdir()):
        if not cat_dir.is_dir():
            continue
        for brand_dir in sorted(cat_dir.iterdir()):
            if not brand_dir.is_dir():
                continue
            brand = brand_dir.name
            black_files = []
            for f in brand_dir.rglob('*'):
                if f.suffix.lower() in ('.jpg', '.jpeg', '.png') and has_black_background(f):
                    black_files.append(f)

            if not black_files:
                continue

            print(f"\n  [{brand}] {len(black_files)}张黑色背景", flush=True)
            fixed = 0
            for f in black_files:
                if fix_black_to_white(f):
                    fixed += 1

            print(f"    修复 {fixed}/{len(black_files)} 张")
            total_fixed += fixed

    print(f"\n共修复 {total_fixed} 张黑色背景\n")


if __name__ == '__main__':
    fix_nested_duplicates()
    fix_black_backgrounds()
    print("全部修复完成")
