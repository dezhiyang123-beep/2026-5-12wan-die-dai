#!/usr/bin/env python3
"""
Clean the design reference library: remove misclassified images, English residuals,
empty dirs, and enforce per-brand category whitelists.
"""
import os, re, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scrape_images import _BRAND_ALLOWED_CATEGORIES

BASE = Path(os.environ.get("SCRAPE_BASE", str(Path.home() / "Desktop" / "设计素材库" / "01_品类标杆库")))

# Regex: directory name is purely ASCII (English website residual)
_ENGLISH_DIR = re.compile(r'^[a-zA-Z0-9_\-\.\s/]+$')


def clean_brand(category_dir, brand_name, brand_path):
    """Clean one brand directory. Returns (kept_images, deleted_images, deleted_dirs)."""
    allowed = _BRAND_ALLOWED_CATEGORIES.get(brand_name)
    kept = 0
    deleted_imgs = 0
    deleted_dirs = []

    if not brand_path.exists():
        return 0, 0, []

    # Pass 1: Walk all subdirectories, decide keep or delete
    dirs_to_delete = []
    for dirpath, dirnames, filenames in os.walk(brand_path, topdown=False):
        dp = Path(dirpath)
        rel = dp.relative_to(brand_path)
        parts = rel.parts

        if len(parts) == 0:
            # Brand root — delete any flat files here
            for f in filenames:
                fp = dp / f
                if fp.suffix.lower() in ('.jpg', '.png', '.webp'):
                    fp.unlink()
                    deleted_imgs += 1
            continue

        # Get the top-level directory name (大类 or 大类/小类)
        top_dir_name = parts[0]

        should_delete = False

        # Rule 1: Delete "其他" catch-all
        if top_dir_name == "其他":
            should_delete = True

        # Rule 2: Delete English-named directories
        elif _ENGLISH_DIR.match(top_dir_name):
            should_delete = True

        # Rule 3: Check against brand whitelist
        elif allowed is not None:
            # Check if top_dir_name matches any allowed category
            if top_dir_name not in allowed:
                should_delete = True

        if should_delete and dp.exists():
            # Only mark top-level dirs for deletion (avoid double-deleting)
            top_path = brand_path / top_dir_name
            if top_path not in dirs_to_delete:
                dirs_to_delete.append(top_path)

    # Execute deletions
    for d in dirs_to_delete:
        if d.exists():
            img_count = sum(1 for f in d.rglob("*") if f.suffix.lower() in ('.jpg', '.png'))
            deleted_imgs += img_count
            deleted_dirs.append(f"{d.name}/ ({img_count} imgs)")
            shutil.rmtree(d)

    # Pass 2: Flatten redundant nesting (吊灯/吊灯/ → 吊灯/)
    for d in brand_path.iterdir():
        if not d.is_dir():
            continue
        children = [c for c in d.iterdir() if c.is_dir()]
        if len(children) == 1 and children[0].name == d.name:
            # Move files from child to parent, remove child
            child = children[0]
            for f in child.iterdir():
                dest = d / f.name
                if f.is_file() and not dest.exists():
                    f.rename(dest)
            # Remove child if empty now
            if child.exists() and not any(child.iterdir()):
                child.rmdir()

    # Pass 3: Renumber images in each leaf directory (01.jpg, 02.jpg...)
    for d in sorted(brand_path.rglob("*")):
        if not d.is_dir():
            continue
        imgs = sorted([f for f in d.iterdir() if f.is_file() and f.suffix.lower() in ('.jpg', '.png')])
        if not imgs:
            continue
        # Rename to temp first to avoid collision
        temp_names = []
        for i, f in enumerate(imgs):
            temp = f.parent / f"__temp_{i:04d}{f.suffix}"
            f.rename(temp)
            temp_names.append(temp)
        # Rename to final
        for i, temp in enumerate(temp_names):
            final = temp.parent / f"{i+1:02d}.jpg"
            temp.rename(final)
            kept += 1

    # Pass 4: Remove all empty directories
    for dirpath, dirnames, filenames in os.walk(brand_path, topdown=False):
        dp = Path(dirpath)
        if dp != brand_path and not any(dp.iterdir()):
            dp.rmdir()

    return kept, deleted_imgs, deleted_dirs


def main():
    print("=" * 60)
    print("品类标杆库清洗")
    print("=" * 60)

    total_kept = 0
    total_deleted = 0

    for category_dir in sorted(BASE.iterdir()):
        if not category_dir.is_dir():
            continue
        for brand_path in sorted(category_dir.iterdir()):
            if not brand_path.is_dir():
                continue
            brand_name = brand_path.name

            kept, deleted, deleted_dirs = clean_brand(category_dir.name, brand_name, brand_path)
            total_kept += kept
            total_deleted += deleted

            status = "OK" if not deleted_dirs else "CLEANED"
            print(f"[{status:7s}] {category_dir.name}/{brand_name}: {kept} kept, {deleted} deleted")
            for d in deleted_dirs:
                print(f"          DEL: {d}")

    print()
    print(f"总计: {total_kept} 保留, {total_deleted} 删除")


if __name__ == "__main__":
    main()
