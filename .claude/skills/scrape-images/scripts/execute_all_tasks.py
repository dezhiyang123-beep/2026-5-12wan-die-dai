#!/usr/bin/env python3
"""
执行脚本 - 2026-05-07
任务A: 03_设计手法库补图 (H01/H02/H03/H04/H09/H12)
任务B: 02_品牌语法库 detail_views (BEGA/Artemide/Festool)
任务C: 05_渲染参考库/结构细节 + 多角度
"""
import sys, shutil, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')
from pathlib import Path
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

DESKTOP = Path.home() / "Desktop" / "设计素材库"
BASE_01 = DESKTOP / "01_品类标杆库"
BASE_02 = DESKTOP / "02_品牌语法库"
BASE_03 = DESKTOP / "03_设计手法库"
BASE_05 = DESKTOP / "05_渲染参考库"
EXTS = {'.jpg', '.jpeg', '.png', '.webp'}


def cp(src, dst):
    """拷贝并确保目标目录存在。返回True=成功。"""
    src = Path(src)
    dst = Path(dst)
    if not src.exists():
        print(f"  ⚠ 不存在: {src}")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


# ═══════════════════════════════════════════════════════════════
# 任务B: 02_品牌语法库 - 填充 detail_views
# ═══════════════════════════════════════════════════════════════

def task_b_detail_views():
    print("\n=== 任务B: detail_views ===\n")

    # BEGA detail_views (6张): 嵌入式吸顶灯 + 轨道射灯 + 嵌入式壁灯
    bega_details = [
        (BASE_01 / "灯具/bega/室内灯/嵌入式吸顶灯/05.jpg", "bega_嵌入式吸顶灯_copper_01.jpg"),
        (BASE_01 / "灯具/bega/室内灯/嵌入式吸顶灯/07.jpg", "bega_嵌入式吸顶灯_02.jpg"),
        (BASE_01 / "灯具/bega/室内灯/嵌入式吸顶灯/10.jpg", "bega_嵌入式吸顶灯_03.jpg"),
        (BASE_01 / "灯具/bega/室内灯/轨道射灯/01.jpg",     "bega_轨道射灯_01.jpg"),
        (BASE_01 / "灯具/bega/室内灯/轨道射灯/02.jpg",     "bega_轨道射灯_02.jpg"),
        (BASE_01 / "灯具/bega/室内灯/嵌入式壁灯/01.jpg",   "bega_嵌入式壁灯_01.jpg"),
        (BASE_01 / "灯具/bega/室内灯/嵌入式壁灯/02.jpg",   "bega_嵌入式壁灯_02.jpg"),
    ]
    bega_dst = BASE_02 / "灯具/bega/detail_views"
    n = 0
    for src, fname in bega_details:
        if cp(src, bega_dst / fname):
            n += 1
    print(f"  BEGA detail_views: +{n}张")

    # Artemide detail_views (6张): 射灯 + 轨道灯 + 户外壁灯 + 线型灯
    artemide_details = [
        (BASE_01 / "灯具/artemide/射灯/116.jpg",    "artemide_射灯_01.jpg"),
        (BASE_01 / "灯具/artemide/射灯/50.jpg",     "artemide_射灯_02.jpg"),
        (BASE_01 / "灯具/artemide/轨道灯/13.jpg",   "artemide_轨道灯_01.jpg"),
        (BASE_01 / "灯具/artemide/轨道灯/14.jpg",   "artemide_轨道灯_02.jpg"),
        (BASE_01 / "灯具/artemide/户外壁灯/02.jpg", "artemide_户外壁灯_01.jpg"),
        (BASE_01 / "灯具/artemide/线型灯/18.jpg",   "artemide_线型灯_01.jpg"),
        (BASE_01 / "灯具/artemide/线型灯/19.jpg",   "artemide_线型灯_02.jpg"),
    ]
    artemide_dst = BASE_02 / "灯具/artemide/detail_views"
    n = 0
    for src, fname in artemide_details:
        if cp(src, artemide_dst / fname):
            n += 1
    print(f"  Artemide detail_views: +{n}张")

    # Festool detail_views (7张): 砂光机特写 + 铣机 + 电锯局部
    festool_details = [
        (BASE_01 / "电动工具/festool/砂光机/偏心砂光机__01.jpg", "festool_偏心砂光机_01.jpg"),
        (BASE_01 / "电动工具/festool/砂光机/偏心砂光机__02.jpg", "festool_偏心砂光机_02.jpg"),
        (BASE_01 / "电动工具/festool/砂光机/偏心砂光机__03.jpg", "festool_偏心砂光机_03.jpg"),
        (BASE_01 / "电动工具/festool/砂光机/三角砂光机__01.jpg", "festool_三角砂光机_01.jpg"),
        (BASE_01 / "电动工具/festool/铣/铣__修边机__01.jpg",     "festool_铣_修边机_01.jpg"),
        (BASE_01 / "电动工具/festool/铣/铣__修边机__02.jpg",     "festool_铣_修边机_02.jpg"),
        (BASE_01 / "电动工具/festool/电锯/电锯__曲线锯__01.jpg", "festool_曲线锯_01.jpg"),
    ]
    festool_dst = BASE_02 / "电动工具/festool/detail_views"
    n = 0
    for src, fname in festool_details:
        if cp(src, festool_dst / fname):
            n += 1
    print(f"  Festool detail_views: +{n}张")


# ═══════════════════════════════════════════════════════════════
# 任务A: 03_设计手法库补图
# ═══════════════════════════════════════════════════════════════

def task_a_techniques():
    print("\n=== 任务A: 03_设计手法库 ===\n")

    # H01_减法设计: 镂空/圆环/切割形态
    # BEGA圆环吊灯+三环吸顶灯 + Artemide环形 + Flos圆环
    h01_files = [
        # 灯具品类
        (BASE_01 / "灯具/bega/室内灯/吊灯/21.jpg",        "H01_bega_001.jpg"),
        (BASE_01 / "灯具/bega/室内灯/吸顶灯/10.jpg",      "H01_bega_002.jpg"),
        (BASE_01 / "灯具/bega/室内灯/吸顶灯/30.jpg",      "H01_bega_003.jpg"),
        (BASE_01 / "灯具/artemide/吊灯/09.jpg",           "H01_artemide_001.jpg"),
        (BASE_01 / "灯具/flos/创意吊灯/01.jpg",           "H01_flos_001.jpg"),
        (BASE_01 / "灯具/flos/创意吊灯/02.jpg",           "H01_flos_002.jpg"),
        # 消费电子品类
        (BASE_01 / "灯具/bega/室内灯/吊灯/22.jpg",        "H01_bega_004.jpg"),
    ]
    _copy_technique("H01_减法设计", h01_files)

    # H02_包覆设计: 软硬材料包覆/橡胶包胶/双色注塑
    h02_files = [
        # 电动工具品类
        (BASE_01 / "电动工具/festool/电钻/电钻__充电电钻__01.jpg", "H02_festool_001.jpg"),
        (BASE_01 / "电动工具/festool/电钻/电钻__充电电钻__02.jpg", "H02_festool_002.jpg"),
        (BASE_01 / "电动工具/festool/砂光机/砂光机__偏心砂光机__01.jpg", "H02_festool_003.jpg"),
        (BASE_01 / "电动工具/dewalt/电钻/电钻__综合__01.jpg",      "H02_dewalt_001.jpg"),
        (BASE_01 / "电动工具/dewalt/角磨机/角磨机__切割工具__01.jpg", "H02_dewalt_002.jpg"),
        # 灯具品类 (Flos leather wrap)
        (BASE_01 / "灯具/flos/创意吊灯/03.jpg",           "H02_flos_001.jpg"),
    ]
    _copy_technique("H02_包覆设计", h02_files)

    # H03_分件线设计: 刻意设计的视觉分件线
    h03_files = [
        # 电动工具
        (BASE_01 / "电动工具/festool/吸尘设备/吸尘设备__01.jpg",   "H03_festool_001.jpg"),
        (BASE_01 / "电动工具/festool/吸尘设备/吸尘设备__02.jpg",   "H03_festool_002.jpg"),
        (BASE_01 / "电动工具/dewalt/电钻/电钻__综合__02.jpg",      "H03_dewalt_001.jpg"),
        (BASE_01 / "电动工具/dewalt/角磨机/角磨机__切割工具__02.jpg", "H03_dewalt_002.jpg"),
        # 灯具 (BEGA drum with copper band = clear parting line)
        (BASE_01 / "灯具/bega/室内灯/吊灯/13.jpg",                "H03_bega_001.jpg"),
    ]
    _copy_technique("H03_分件线设计", h03_files)

    # H04_参数化渐变: 渐变孔洞/纹理/数学规律图案
    h04_files = [
        # 灯具品类
        (BASE_01 / "灯具/artemide/吸顶灯/100.jpg",        "H04_artemide_001.jpg"),
        (BASE_01 / "灯具/artemide/吸顶灯/146.jpg",        "H04_artemide_002.jpg"),
        (BASE_01 / "灯具/foscarini/吊灯/02.jpg",         "H04_foscarini_001.jpg"),
        (BASE_01 / "灯具/foscarini/吊灯/03.jpg",         "H04_foscarini_002.jpg"),
        (BASE_01 / "灯具/flos/创意吊灯/05.jpg",           "H04_flos_001.jpg"),
        (BASE_01 / "灯具/flos/创意吊灯/06.jpg",           "H04_flos_002.jpg"),
        # 消费电子品类
        (BASE_01 / "灯具/artemide/吸顶灯/137.jpg",        "H04_artemide_003.jpg"),
    ]
    _copy_technique("H04_参数化渐变", h04_files)

    # H09_隐藏工程: 工程细节被巧妙隐藏
    h09_files = [
        # 灯具品类
        (BASE_01 / "灯具/bega/室内灯/嵌入式吸顶灯/05.jpg",  "H09_bega_001.jpg"),
        (BASE_01 / "灯具/bega/室内灯/嵌入式吸顶灯/01.jpg",  "H09_bega_002.jpg"),
        (BASE_01 / "灯具/bega/室内灯/吊灯/01.jpg",          "H09_bega_003.jpg"),
        (BASE_01 / "灯具/bega/室内灯/吊灯/02.jpg",          "H09_bega_004.jpg"),
        (BASE_01 / "灯具/artemide/吊灯/01.jpg",             "H09_artemide_001.jpg"),
        # 电动工具品类
        (BASE_01 / "电动工具/festool/吸尘设备/吸尘设备__05.jpg", "H09_festool_001.jpg"),
    ]
    _copy_technique("H09_隐藏工程", h09_files)

    # H12_人机界面强化: 按钮/旋钮/握持区被刻意放大突出
    h12_files = [
        # 电动工具品类
        (BASE_01 / "电动工具/festool/电钻/电钻__充电电钻__03.jpg",  "H12_festool_001.jpg"),
        (BASE_01 / "电动工具/festool/电钻/电钻__充电电钻__04.jpg",  "H12_festool_002.jpg"),
        (BASE_01 / "电动工具/festool/砂光机/砂光机__偏心砂光机__02.jpg", "H12_festool_003.jpg"),
        (BASE_01 / "电动工具/dewalt/电钻/电钻__综合__03.jpg",       "H12_dewalt_001.jpg"),
        (BASE_01 / "电动工具/dewalt/角磨机/角磨机__切割工具__03.jpg","H12_dewalt_002.jpg"),
        # 灯具品类 (BEGA嵌入式射灯-旋转调节机构)
        (BASE_01 / "灯具/bega/室内灯/射灯/01.jpg",                  "H12_bega_001.jpg"),
    ]
    _copy_technique("H12_人机界面强化", h12_files)


def _copy_technique(folder_name, file_list):
    dst_dir = BASE_03 / folder_name
    dst_dir.mkdir(parents=True, exist_ok=True)
    existing = len(list(dst_dir.glob("*.*")))
    copied = 0
    for src, fname in file_list:
        dst = dst_dir / fname
        if dst.exists():
            continue
        if cp(src, dst):
            copied += 1
    total = len(list(dst_dir.glob("*.*")))
    print(f"  {folder_name}: {existing}张 → {total}张 (+{copied})")


# ═══════════════════════════════════════════════════════════════
# 任务C: 05_渲染参考库/结构细节 + 多角度
# ═══════════════════════════════════════════════════════════════

def task_c_render_ref():
    print("\n=== 任务C: 05_渲染参考库 ===\n")

    dst_detail = BASE_05 / "结构细节"
    dst_multi  = BASE_05 / "多角度"
    dst_detail.mkdir(parents=True, exist_ok=True)
    dst_multi.mkdir(parents=True, exist_ok=True)

    # 结构细节: 分件线清晰、散热口、接口、铰链、卡扣等特写
    struct_files = [
        # Festool 工具接口/卡扣/收纳系统
        (BASE_01 / "电动工具/festool/吸尘设备/吸尘设备__01.jpg", "festool_吸尘设备_接口_01.jpg"),
        (BASE_01 / "电动工具/festool/吸尘设备/吸尘设备__02.jpg", "festool_吸尘设备_接口_02.jpg"),
        (BASE_01 / "电动工具/festool/吸尘设备/吸尘设备__03.jpg", "festool_吸尘设备_接口_03.jpg"),
        (BASE_01 / "电动工具/festool/吸尘设备/吸尘设备__04.jpg", "festool_吸尘设备_接口_04.jpg"),
        (BASE_01 / "电动工具/festool/电锯/电锯__轨道锯__01.jpg", "festool_轨道锯_导轨结构_01.jpg"),
        (BASE_01 / "电动工具/festool/电锯/电锯__轨道锯__02.jpg", "festool_轨道锯_导轨结构_02.jpg"),
        (BASE_01 / "电动工具/festool/砂光机/砂光机__三角砂光机__01.jpg", "festool_三角砂光机_01.jpg"),
        (BASE_01 / "电动工具/festool/砂光机/砂光机__三角砂光机__02.jpg", "festool_三角砂光机_02.jpg"),
        (BASE_01 / "电动工具/festool/砂光机/砂光机__三角砂光机__03.jpg", "festool_三角砂光机_03.jpg"),
        (BASE_01 / "电动工具/festool/铣/铣__修边机__01.jpg",     "festool_铣_修边机_结构_01.jpg"),
        (BASE_01 / "电动工具/festool/铣/铣__修边机__02.jpg",     "festool_铣_修边机_结构_02.jpg"),
        (BASE_01 / "电动工具/festool/铣/铣__封边修边机__01.jpg", "festool_铣_封边_结构_01.jpg"),
        (BASE_01 / "电动工具/festool/铣/铣__封边修边机__02.jpg", "festool_铣_封边_结构_02.jpg"),
        # DeWalt 工具接口细节
        (BASE_01 / "电动工具/dewalt/电钻/电钻__综合__01.jpg",    "dewalt_电钻_接口_01.jpg"),
        (BASE_01 / "电动工具/dewalt/电钻/电钻__综合__02.jpg",    "dewalt_电钻_接口_02.jpg"),
        (BASE_01 / "电动工具/dewalt/角磨机/角磨机__切割工具__01.jpg", "dewalt_角磨机_分件线_01.jpg"),
        (BASE_01 / "电动工具/dewalt/角磨机/角磨机__切割工具__02.jpg", "dewalt_角磨机_分件线_02.jpg"),
        (BASE_01 / "电动工具/dewalt/角磨机/角磨机__切割工具__03.jpg", "dewalt_角磨机_分件线_03.jpg"),
        # BEGA 嵌入式灯安装结构
        (BASE_01 / "灯具/bega/室内灯/嵌入式吸顶灯/01.jpg",  "bega_嵌入式_安装_01.jpg"),
        (BASE_01 / "灯具/bega/室内灯/嵌入式吸顶灯/02.jpg",  "bega_嵌入式_安装_02.jpg"),
        (BASE_01 / "灯具/bega/室内灯/嵌入式吸顶灯/03.jpg",  "bega_嵌入式_安装_03.jpg"),
        (BASE_01 / "灯具/bega/室内灯/嵌入式吸顶灯/04.jpg",  "bega_嵌入式_安装_04.jpg"),
        (BASE_01 / "灯具/bega/室内灯/嵌入式吸顶灯/05.jpg",  "bega_嵌入式_铜内腔_05.jpg"),
        (BASE_01 / "灯具/bega/室内灯/嵌入式吸顶灯/06.jpg",  "bega_嵌入式_安装_06.jpg"),
        (BASE_01 / "灯具/bega/室内灯/嵌入式壁灯/01.jpg",    "bega_嵌入式壁灯_01.jpg"),
        (BASE_01 / "灯具/bega/室内灯/嵌入式壁灯/02.jpg",    "bega_嵌入式壁灯_02.jpg"),
        (BASE_01 / "灯具/bega/室内灯/嵌入式壁灯/03.jpg",    "bega_嵌入式壁灯_03.jpg"),
        (BASE_01 / "灯具/bega/户外灯/嵌入式吸顶灯/01.jpg",  "bega_户外嵌入式_01.jpg"),
        (BASE_01 / "灯具/bega/户外灯/嵌入式吸顶灯/02.jpg",  "bega_户外嵌入式_02.jpg"),
        # Artemide 轨道/射灯接口
        (BASE_01 / "灯具/artemide/射灯/116.jpg",            "artemide_射灯_结构_01.jpg"),
        (BASE_01 / "灯具/artemide/射灯/50.jpg",             "artemide_射灯_结构_02.jpg"),
        (BASE_01 / "灯具/artemide/轨道灯/13.jpg",           "artemide_轨道灯_结构_01.jpg"),
        (BASE_01 / "灯具/artemide/轨道灯/14.jpg",           "artemide_轨道灯_结构_02.jpg"),
    ]

    n_detail = 0
    for src, fname in struct_files:
        dst = dst_detail / fname
        if not dst.exists() and cp(src, dst):
            n_detail += 1

    # 多角度: 非主视角 - 背面、侧面、底部、45度外角度
    multi_files = [
        # Festool 侧面/背面
        (BASE_01 / "电动工具/festool/吸尘设备/吸尘设备__06.jpg",  "festool_吸尘设备_侧面_06.jpg"),
        (BASE_01 / "电动工具/festool/吸尘设备/吸尘设备__07.jpg",  "festool_吸尘设备_侧面_07.jpg"),
        (BASE_01 / "电动工具/festool/吸尘设备/吸尘设备__08.jpg",  "festool_吸尘设备_后面_08.jpg"),
        (BASE_01 / "电动工具/festool/吸尘设备/吸尘设备__09.jpg",  "festool_吸尘设备_俯视_09.jpg"),
        (BASE_01 / "电动工具/festool/吸尘设备/吸尘设备__10.jpg",  "festool_吸尘设备_角度_10.jpg"),
        (BASE_01 / "电动工具/festool/电钻/电钻__充电电钻__05.jpg","festool_电钻_侧面_05.jpg"),
        (BASE_01 / "电动工具/festool/电钻/电钻__充电电钻__06.jpg","festool_电钻_后面_06.jpg"),
        (BASE_01 / "电动工具/festool/电钻/电钻__充电电钻__07.jpg","festool_电钻_底面_07.jpg"),
        (BASE_01 / "电动工具/festool/电锯/电锯__圆锯__01.jpg",    "festool_圆锯_侧面_01.jpg"),
        (BASE_01 / "电动工具/festool/电锯/电锯__圆锯__02.jpg",    "festool_圆锯_后面_02.jpg"),
        (BASE_01 / "电动工具/festool/电锯/电锯__斜切锯__01.jpg",  "festool_斜切锯_侧面_01.jpg"),
        (BASE_01 / "电动工具/festool/电锯/电锯__斜切锯__02.jpg",  "festool_斜切锯_正面_02.jpg"),
        (BASE_01 / "电动工具/festool/砂光机/砂光机__砂带机__01.jpg","festool_砂带机_侧面_01.jpg"),
        (BASE_01 / "电动工具/festool/砂光机/砂光机__轨道砂光机__02.jpg","festool_轨道砂光机_02.jpg"),
        (BASE_01 / "电动工具/festool/砂光机/砂光机__轨道砂光机__03.jpg","festool_轨道砂光机_03.jpg"),
        # DeWalt 多角度
        (BASE_01 / "电动工具/dewalt/电钻/电钻__综合__01.jpg",     "dewalt_电钻_角度A.jpg"),
        (BASE_01 / "电动工具/dewalt/电钻/电钻__综合__02.jpg",     "dewalt_电钻_角度B.jpg"),
        (BASE_01 / "电动工具/dewalt/电钻/电钻__综合__03.jpg",     "dewalt_电钻_角度C.jpg"),
        # BEGA 多角度灯具
        (BASE_01 / "灯具/bega/室内灯/吊灯/02.jpg",               "bega_吊灯_角度_02.jpg"),
        (BASE_01 / "灯具/bega/室内灯/吊灯/05.jpg",               "bega_吊灯_角度_05.jpg"),
        (BASE_01 / "灯具/bega/室内灯/吸顶灯/12.jpg",             "bega_吸顶灯_角度_12.jpg"),
        (BASE_01 / "灯具/bega/户外灯/壁灯/02.jpg",               "bega_户外壁灯_角度_02.jpg"),
        (BASE_01 / "灯具/bega/户外灯/壁灯/10.jpg",               "bega_户外壁灯_角度_10.jpg"),
        # Artemide 多角度
        (BASE_01 / "灯具/artemide/台灯/01.jpg",                  "artemide_台灯_角度_01.jpg"),
        (BASE_01 / "灯具/artemide/台灯/05.jpg",                  "artemide_台灯_角度_05.jpg"),
        (BASE_01 / "灯具/artemide/落地灯/105.jpg",               "artemide_落地灯_角度_105.jpg"),
        (BASE_01 / "灯具/artemide/落地灯/120.jpg",               "artemide_落地灯_角度_120.jpg"),
        (BASE_01 / "灯具/artemide/壁灯/02.jpg",                  "artemide_壁灯_角度_02.jpg"),
        (BASE_01 / "灯具/artemide/壁灯/13.jpg",                  "artemide_壁灯_角度_13.jpg"),
        # Flos 多角度
        (BASE_01 / "灯具/flos/创意台灯/01.jpg",                  "flos_台灯_角度_01.jpg"),
        (BASE_01 / "灯具/flos/创意台灯/04.jpg",                  "flos_台灯_角度_04.jpg"),
        (BASE_01 / "灯具/flos/创意台灯/07.jpg",                  "flos_台灯_角度_07.jpg"),
        (BASE_01 / "灯具/flos/装饰落地灯/01.jpg",                "flos_落地灯_角度_01.jpg"),
        (BASE_01 / "灯具/flos/装饰落地灯/02.jpg",                "flos_落地灯_角度_02.jpg"),
    ]

    n_multi = 0
    for src, fname in multi_files:
        dst = dst_multi / fname
        if not dst.exists() and cp(src, dst):
            n_multi += 1

    print(f"  结构细节: +{n_detail}张 (总计 {len(list(dst_detail.glob('*.*')))}张)")
    print(f"  多角度:   +{n_multi}张 (总计 {len(list(dst_multi.glob('*.*')))}张)")


# ═══════════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════════

def main():
    print("开始执行所有任务...\n")

    # 任务B: detail_views
    task_b_detail_views()

    # 任务A: 设计手法库
    task_a_techniques()

    # 任务C: 渲染参考库
    task_c_render_ref()

    # 最终统计
    print("\n=== 最终统计 ===\n")
    print("任务B - 02_品牌语法库:")
    for brand_path in ["灯具/bega", "灯具/artemide", "电动工具/festool"]:
        brand = brand_path.split("/")[1]
        base = BASE_02 / brand_path
        cl = len(list((base / "current_line").glob("*.*"))) if (base / "current_line").exists() else 0
        ps = len(list((base / "premium_series").glob("*.*"))) if (base / "premium_series").exists() else 0
        dv = len(list((base / "detail_views").glob("*.*"))) if (base / "detail_views").exists() else 0
        print(f"  {brand}: current_line={cl} / premium_series={ps} / detail_views={dv}")

    print("\n任务A - 03_设计手法库:")
    for h in ["H01_减法设计","H02_包覆设计","H03_分件线设计","H04_参数化渐变","H09_隐藏工程","H12_人机界面强化"]:
        d = BASE_03 / h
        n = len(list(d.glob("*.*"))) if d.exists() else 0
        print(f"  {h}: {n}张")

    print("\n任务C - 05_渲染参考库:")
    for sub in ["结构细节","多角度"]:
        d = BASE_05 / sub
        n = len(list(d.glob("*.*"))) if d.exists() else 0
        print(f"  {sub}: {n}张")


if __name__ == "__main__":
    main()
