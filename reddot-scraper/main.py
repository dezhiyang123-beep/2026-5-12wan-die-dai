#!/usr/bin/env python3
"""
红点设计奖抓取与分类系统 - 主入口
Red Dot Design Award Scraper & Classifier - Main Entry

用法：
  # 全量抓取（所有类别，2020-2026）
  python main.py

  # 抓取指定类别
  python main.py --categories furniture lighting automotive

  # 抓取指定年份
  python main.py --years 2024 2025

  # 仅分类（已有数据）
  python main.py --classify-only

  # 不下载图片（仅抓取元数据）
  python main.py --no-images

  # 使用 requests 模式（不启动浏览器）
  python main.py --no-selenium

  # 查看所有可用类别
  python main.py --list-categories
"""
import os
import sys
import json
import argparse
import logging
from datetime import datetime

# 添加项目根目录到 path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from config import CATEGORIES, METADATA_DIR, OUTPUT_DIR, YEAR_START, YEAR_END
from scraper.reddot_scraper import RedDotScraper
from classifier.design_classifier import DesignClassifier


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    log_dir = os.path.join(PROJECT_ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(
        log_dir,
        f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ]
    )
    return logging.getLogger(__name__)


def list_categories():
    """列出所有可用类别"""
    print("\n红点设计奖 - 可用类别列表")
    print("=" * 60)
    print(f"{'英文标识':<45} {'中文名称'}")
    print("-" * 60)
    for key, cn in CATEGORIES.items():
        print(f"  {key:<43} {cn}")
    print(f"\n共 {len(CATEGORIES)} 个类别")


def run_scraper(args, logger):
    """运行抓取器"""
    categories = args.categories if args.categories else None
    years = args.years if args.years else None

    logger.info("=" * 60)
    logger.info("红点设计奖抓取器启动")
    logger.info(f"类别: {categories or '全部'}")
    logger.info(f"年份: {years or f'{YEAR_START}-{YEAR_END}'}")
    logger.info(f"Selenium: {'关闭' if args.no_selenium else '启用'}")
    logger.info(f"下载图片: {'否' if args.no_images else '是'}")
    logger.info("=" * 60)

    scraper = RedDotScraper(use_selenium=not args.no_selenium)
    try:
        products = scraper.scrape_all(
            categories=categories,
            years=years,
            download_images=not args.no_images,
        )
        logger.info(f"\n抓取完成! 共获取 {len(products)} 个产品")
        return products
    except KeyboardInterrupt:
        logger.info("\n用户中断，保存已有数据...")
        scraper.save_metadata()
        return scraper.products
    finally:
        scraper.close()


def run_classifier(logger):
    """运行分类器"""
    logger.info("\n" + "=" * 60)
    logger.info("启动设计分类器")
    logger.info("=" * 60)

    # 加载元数据
    metadata_file = os.path.join(METADATA_DIR, "products.json")
    if not os.path.exists(metadata_file):
        logger.error(f"未找到元数据文件: {metadata_file}")
        logger.error("请先运行抓取器获取数据")
        return

    with open(metadata_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    logger.info(f"加载 {len(products)} 个产品数据")

    # 分类
    classifier = DesignClassifier()
    results = classifier.classify_all(products)

    # 整理文件（灯具使用子类模式，其余用大类模式）
    classifier.organize_files(mode="lighting_subcat")

    # 生成报告
    report = classifier.generate_report()

    # 打印摘要
    print("\n" + "=" * 60)
    print("分类统计摘要")
    print("=" * 60)
    print(f"\n总产品数: {report['total_products']}")
    print("\n【大类分布】")
    for cat, count in report.get("by_super_category", {}).items():
        pct = count / max(report["total_products"], 1) * 100
        print(f"  {cat:<15} {count:>5} ({pct:.1f}%)")
    print("\n【奖项分布】")
    for level, count in report.get("by_award_level", {}).items():
        print(f"  {level:<25} {count:>5}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="红点设计奖抓取与分类系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--categories", "-c", nargs="+",
        help="指定抓取类别（空格分隔），如: furniture lighting automotive"
    )
    parser.add_argument(
        "--years", "-y", nargs="+", type=int,
        help="指定抓取年份，如: 2024 2025"
    )
    parser.add_argument(
        "--classify-only", action="store_true",
        help="仅运行分类器（使用已有数据）"
    )
    parser.add_argument(
        "--no-images", action="store_true",
        help="不下载图片（仅抓取元数据）"
    )
    parser.add_argument(
        "--no-selenium", action="store_true",
        help="不使用 Selenium（仅用 requests）"
    )
    parser.add_argument(
        "--list-categories", action="store_true",
        help="列出所有可用类别"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="详细日志输出"
    )

    args = parser.parse_args()
    logger = setup_logging(args.verbose)

    if args.list_categories:
        list_categories()
        return

    if args.classify_only:
        run_classifier(logger)
    else:
        # 先抓取，再分类
        products = run_scraper(args, logger)
        if products:
            run_classifier(logger)

    logger.info("\n全部任务完成!")


if __name__ == "__main__":
    main()
