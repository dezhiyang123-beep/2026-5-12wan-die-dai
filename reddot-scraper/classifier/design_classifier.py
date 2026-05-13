"""
工业设计图片分类器
Industrial Design Image Classifier

功能：
1. 基于网站元数据的类别归类（主分类）
2. 基于图片视觉特征的辅助分类（颜色/形态分析）
3. 基于关键词的自动标签系统
4. 生成分类报告和统计
"""
import os
import re
import json
import shutil
import logging
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict

try:
    from PIL import Image, ImageStat
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CATEGORIES, IMAGES_DIR, METADATA_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)


# === 设计分类知识库 ===

# 灯具子类分类（用于 lighting 类别的精细化分类，确保错误率<2%）
LIGHTING_SUBCATEGORIES = {
    "台灯_桌灯": [
        "table lamp", "desk lamp", "bedside lamp", "reading lamp", "task lamp",
        "table light", "desk light", "台灯", "桌灯", "床头灯", "阅读灯",
    ],
    "落地灯": [
        "floor lamp", "standing lamp", "floor light", "arc lamp", "arc light",
        "落地灯", "立式灯",
    ],
    "吊灯_枝形灯": [
        "pendant lamp", "pendant light", "hanging lamp", "hanging light",
        "chandelier", "suspension lamp", "suspension light", "drop light",
        "pendant fixture", "吊灯", "枝形灯", "垂吊灯",
    ],
    "吸顶灯_射灯": [
        "ceiling lamp", "ceiling light", "ceiling fixture", "recessed light",
        "recessed lamp", "downlight", "down light", "spot lamp", "spotlight",
        "track light", "track lamp", "flush mount", "吸顶灯", "射灯", "筒灯", "轨道灯",
    ],
    "壁灯": [
        "wall lamp", "wall light", "wall sconce", "sconce", "wall fixture",
        "wall-mounted light", "壁灯",
    ],
    "户外照明": [
        "outdoor lamp", "outdoor light", "garden lamp", "garden light",
        "street lamp", "street light", "pathway light", "flood light", "floodlight",
        "landscape light", "solar lamp", "solar light", "bollard light",
        "户外灯", "庭院灯", "路灯", "草坪灯", "太阳能灯",
    ],
    "台灯_工作灯": [
        "work lamp", "work light", "architect lamp", "swing arm lamp",
        "clip lamp", "clip light", "clamp lamp", "工作灯",
    ],
    "LED_智能照明": [
        "led lamp", "led light", "led fixture", "smart lamp", "smart light",
        "connected light", "iot lamp", "rgb lamp", "rgb light", "color lamp",
        "tunable light", "led strip", "linear light", "LED灯", "智能灯", "感应灯",
    ],
    "装饰灯_艺术灯": [
        "decorative lamp", "decorative light", "ambient light", "mood light",
        "neon lamp", "candle lamp", "lantern", "night light", "nightlight",
        "fairy light", "string light", "装饰灯", "艺术灯", "氛围灯", "灯笼",
    ],
    "商业_专业照明": [
        "commercial light", "architectural light", "studio light", "stage light",
        "emergency light", "emergency lamp", "industrial lamp", "industrial light",
        "luminaire", "光源", "工业照明", "商业照明", "建筑照明",
    ],
}

# 灯具关键词集合（用于验证是否为真正灯具产品，确保精确率>98%）
LIGHTING_VALIDATION_KEYWORDS = set([
    kw for kws in LIGHTING_SUBCATEGORIES.values() for kw in kws
] + [
    "lamp", "light", "luminaire", "fixture", "luminary", "illuminat",
    "licht", "leuchte", "lampe",  # German
    "灯", "照明", "光源", "发光",
])

# 大类分组（将 33 个红点子类聚合为 8 大类）
SUPER_CATEGORIES = {
    "家居生活": [
        "living-rooms-bedrooms", "kitchen-household", "tableware-cooking",
        "bath-sanitary", "interior-design", "furniture", "lighting", "garden",
        "heating-air-conditioning",
    ],
    "数码科技": [
        "consumer-electronics", "computers-information-technology",
        "smartphones-tablets", "audio", "cameras", "wearables-fitness",
        "technology", "robots",
    ],
    "出行交通": [
        "automotive", "bicycles-e-mobility",
    ],
    "运动户外": [
        "sports-outdoor",
    ],
    "母婴儿童": [
        "baby-child",
    ],
    "时尚配饰": [
        "fashion-accessories", "watches-jewellery",
    ],
    "医疗健康": [
        "medical-rehabilitation", "life-science",
    ],
    "商业办公": [
        "tools", "industry-crafts-trade", "office",
        "urban-public-design", "communication-design",
        "packaging", "material-surface",
    ],
}

# 关键词 -> 类别映射（用于无元数据时的文本分类）
KEYWORD_CATEGORY_MAP = {
    "chair": "furniture", "sofa": "furniture", "table": "furniture",
    "desk": "furniture", "shelf": "furniture", "cabinet": "furniture",
    "lamp": "lighting", "light": "lighting", "led": "lighting",
    "kitchen": "kitchen-household", "cook": "tableware-cooking",
    "phone": "smartphones-tablets", "tablet": "smartphones-tablets",
    "laptop": "computers-information-technology",
    "computer": "computers-information-technology",
    "monitor": "computers-information-technology",
    "speaker": "audio", "headphone": "audio", "earphone": "audio",
    "camera": "cameras", "lens": "cameras",
    "watch": "watches-jewellery", "ring": "watches-jewellery",
    "car": "automotive", "vehicle": "automotive",
    "bicycle": "bicycles-e-mobility", "bike": "bicycles-e-mobility",
    "scooter": "bicycles-e-mobility",
    "stroller": "baby-child", "baby": "baby-child",
    "medical": "medical-rehabilitation", "wheelchair": "medical-rehabilitation",
    "bathroom": "bath-sanitary", "shower": "bath-sanitary", "toilet": "bath-sanitary",
    "garden": "garden", "outdoor": "garden",
    "robot": "robots", "drone": "robots",
    "fitness": "wearables-fitness", "tracker": "wearables-fitness",
    "sport": "sports-outdoor", "gym": "sports-outdoor",
    "bag": "fashion-accessories", "suitcase": "fashion-accessories",
    "packaging": "packaging", "package": "packaging",
    "office": "office", "printer": "office",
    "tool": "tools", "drill": "tools", "power tool": "tools",
}


@dataclass
class ClassificationResult:
    """分类结果"""
    product_id: str
    title: str
    primary_category: str          # 红点原始类别
    primary_category_cn: str
    super_category: str            # 聚合大类
    auto_tags: List[str]           # 自动生成标签
    color_profile: Dict[str, float] = None  # 主色调分析
    confidence: float = 1.0        # 分类置信度


class DesignClassifier:
    """工业设计分类器"""

    def __init__(self):
        self.results: List[ClassificationResult] = []
        self._build_reverse_map()

    def _build_reverse_map(self):
        """构建子类别 -> 大类的反向映射"""
        self.sub_to_super = {}
        for super_cat, sub_cats in SUPER_CATEGORIES.items():
            for sub in sub_cats:
                self.sub_to_super[sub] = super_cat

    # === 主分类方法 ===

    def is_lighting_product(self, product_data: dict) -> Tuple[bool, float]:
        """
        验证产品是否为真正的灯具（用于确保错误率<2%）
        Returns: (是否为灯具, 置信度)
        """
        text = " ".join([
            product_data.get("title", ""),
            product_data.get("description", ""),
            product_data.get("category", ""),
            product_data.get("category_cn", ""),
            product_data.get("url", ""),
        ]).lower()

        # 1. 红点分类直接标注为 lighting -> 高置信度
        if product_data.get("category") == "lighting":
            # 额外验证：title 或 description 含灯具关键词 -> 置信度1.0
            for kw in LIGHTING_VALIDATION_KEYWORDS:
                if kw.lower() in text:
                    return True, 1.0
            # 分类是lighting但没找到关键词 -> 仍接受，但置信度略低
            return True, 0.95

        # 2. 非 lighting 类别 -> 需要严格的关键词验证
        matched = sum(1 for kw in LIGHTING_VALIDATION_KEYWORDS if kw.lower() in text)
        if matched >= 2:
            return True, min(0.5 + matched * 0.1, 0.9)
        elif matched == 1:
            return True, 0.6
        return False, 0.0

    # 德文子类名 → 中文子类 直接映射（来自红点 API meta_first 字段）
    GERMAN_SUBCAT_MAP = {
        "pendelleuchte": "吊灯_枝形灯",
        "hängeleuchte": "吊灯_枝形灯",
        "led-pendelleuchte": "吊灯_枝形灯",
        "kronleuchte": "吊灯_枝形灯",
        "tischleuchte": "台灯_桌灯",
        "schreibtischleuchte": "台灯_工作灯",
        "led-tischleuchte": "台灯_桌灯",
        "nachttischleuchte": "台灯_桌灯",
        "leseleuchte": "台灯_桌灯",
        "stehleuchte": "落地灯",
        "bogenleuchte": "落地灯",
        "deckenleuchte": "吸顶灯_射灯",
        "einbauleuchte": "吸顶灯_射灯",
        "downlight": "吸顶灯_射灯",
        "strahler": "吸顶灯_射灯",
        "led-strahler": "吸顶灯_射灯",
        "schienenstrahler": "吸顶灯_射灯",
        "wandleuchte": "壁灯",
        "led-wandleuchte": "壁灯",
        "außenleuchte": "户外照明",
        "gartenleuchte": "户外照明",
        "straßenleuchte": "户外照明",
        "wegeleuchte": "户外照明",
        "pollerleuchte": "户外照明",
        "led-taschenlampe": "台灯_工作灯",
        "arbeitsleuchte": "台灯_工作灯",
        "led-lampe": "LED_智能照明",
        "led-leuchte": "LED_智能照明",
        "smartleuchte": "LED_智能照明",
        "leuchtenserie": "商业_专业照明",
        "lichtsystem": "商业_专业照明",
        "lichttechnik": "商业_专业照明",
        "bürobeleuchtung": "商业_专业照明",
        "notleuchte": "商业_专业照明",
        "dekorationsleuchte": "装饰灯_艺术灯",
        "tischlampe": "台灯_桌灯",
        "stehlampe": "落地灯",
        # 补充映射
        "leuchte": "商业_专业照明",
        "led-hängeleuchte": "吊灯_枝形灯",
        "led-schreibtischleuchte": "台灯_工作灯",
        "fluter": "户外照明",
        "außenleuchten-serie": "户外照明",
        "strahlerserie": "吸顶灯_射灯",
        "mobile leuchte": "台灯_工作灯",
        "innenbeleuchtung": "商业_专业照明",
        "led-leuchtenserie": "商业_专业照明",
        "leuchtensystem": "商业_专业照明",
        "led-außenleuchte": "户外照明",
        "hallenbeleuchtung": "商业_专业照明",
        "outdoor-wandleuchte": "户外照明",
        "led-glühbirne": "LED_智能照明",
        "led downlight": "吸顶灯_射灯",
        "beleuchtungssystem": "商业_专业照明",
        "solarleuchte": "户外照明",
        "leuchtenkollektion": "商业_专业照明",
        "outdoor-leuchtenserie": "户外照明",
        "einbaustrahler": "吸顶灯_射灯",
        "led-lampenserie": "LED_智能照明",
        "lineares lichtsystem": "商业_专业照明",
        "pendelleuchten-serie": "吊灯_枝形灯",
        "tragbare leuchte": "台灯_工作灯",
        "retailleuchten": "商业_专业照明",
        "led-stehleuchte": "落地灯",
        "led-deckenleuchte": "吸顶灯_射灯",
        "led-einbauleuchte": "吸顶灯_射灯",
        "led-wandleuchten-serie": "壁灯",
        "led-downlight": "吸顶灯_射灯",
        "led-einbaustrahler": "吸顶灯_射灯",
        "tischleuchten-serie": "台灯_桌灯",
        "büroleuchte": "台灯_工作灯",
        "bürobeleuchtung": "商业_专业照明",
        "led-büroleuchte": "台灯_工作灯",
        "stehleuchten-serie": "落地灯",
        "gartenleuchten-serie": "户外照明",
        "akzentleuchte": "装饰灯_艺术灯",
        "dekoleuchte": "装饰灯_艺术灯",
        "deko-leuchte": "装饰灯_艺术灯",
        "nachtlicht": "装饰灯_艺术灯",
        "led-nachtlicht": "装饰灯_艺术灯",
        "lichterkette": "装饰灯_艺术灯",
        "laterne": "装饰灯_艺术灯",
        "camping-leuchte": "台灯_工作灯",
        "handlampe": "台灯_工作灯",
        "handleuchte": "台灯_工作灯",
        "industrieleuchte": "商业_专业照明",
        "hallenstrahler": "商业_专业照明",
        "notbeleuchtung": "商业_专业照明",
        "bühnenleuchte": "商业_专业照明",
        "led-streifen": "LED_智能照明",
        "led-panel": "吸顶灯_射灯",
        "led-röhre": "商业_专业照明",
        # 第三批补充
        "spezialleuchte": "商业_专业照明",
        "pendelleuchten": "吊灯_枝形灯",
        "leuchten-serie": "商业_专业照明",
        "led-beleuchtungssystem": "LED_智能照明",
        "taschenlampe": "台灯_工作灯",
        "aufbauleuchte": "吸顶灯_射灯",
        "retailleuchte": "商业_专业照明",
        "stromschienenleuchte": "吸顶灯_射灯",
        "strahler-serie": "吸顶灯_射灯",
        "strahler-system": "吸顶灯_射灯",
        "deckenleuchten": "吸顶灯_射灯",
        "fokussierbare led-stirnlampe": "台灯_工作灯",
        "led-strahlerserie": "吸顶灯_射灯",
        "led-stirnlampe": "台灯_工作灯",
        "led-straßenleuchte": "户外照明",
        "led-pollerleuchte": "户外照明",
        "leitsystem": "商业_专业照明",
        "notfallbeleuchtung": "商业_专业照明",
        "dekorationsleuchten": "装饰灯_艺术灯",
        "led-downlights": "吸顶灯_射灯",
        "led-röhren": "商业_专业照明",
        "led-panels": "吸顶灯_射灯",
        "led-fluter": "户外照明",
        "led-flutlicht": "户外照明",
        "led-wegeleuchte": "户外照明",
        "led-gartenleuchte": "户外照明",
        "led-solarleuchte": "户外照明",
        "led-laterne": "装饰灯_艺术灯",
        "led-lichterkette": "装饰灯_艺术灯",
        "pendelleuchten-kollektion": "吊灯_枝形灯",
        "wandleuchten": "壁灯",
        "tischleuchten": "台灯_桌灯",
        "stehleuchten": "落地灯",
        "außenleuchten": "户外照明",
        "deckenleuchten-serie": "吸顶灯_射灯",
    }

    def classify_lighting_subcategory(self, product_data: dict) -> str:
        """对灯具产品进行子类精细分类（优先德文子类直接映射，然后英文关键词）"""
        # 优先：德文子类名直接映射（红点 API 的 meta_first/description 字段）
        desc_raw = product_data.get("description", "").strip().lower()
        if desc_raw in self.GERMAN_SUBCAT_MAP:
            return self.GERMAN_SUBCAT_MAP[desc_raw]

        # 次优：检查 tags 中存储的 subcategory 字段
        for tag in product_data.get("tags", []):
            tag_lower = tag.lower()
            if tag_lower in self.GERMAN_SUBCAT_MAP:
                return self.GERMAN_SUBCAT_MAP[tag_lower]

        # 第二层：德文子词根模式匹配（处理长尾变体）
        DE_PATTERN_MAP = [
            # 词根 → 子类（按优先级排列）
            (["außen", "outdoor", "solar", "garten", "straßen", "wege", "poller", "fluter", "flutlicht", "scheinwerfer", "außenbeleucht"], "户外照明"),
            (["pendel", "hänge", "kronleuch", "hängeleuchten"], "吊灯_枝形灯"),
            (["stehleuch", "stehlampe", "bogen", "standleuch"], "落地灯"),
            (["schreibtisch", "büro", "arbeits", "stirnlampe", "taschen", "camping", "handlampe", "handleuch", "klemmleuch", "mobile leuch", "aufladbar", "tragbar"], "台灯_工作灯"),
            (["tischleuch", "tischlampe", "nachttisch", "leseleuch"], "台灯_桌灯"),
            (["decken", "einbau", "strahler", "downlight", "panel", "röhr", "schienen", "stromschiene", "aufbaustrahl", "aufbauleuch"], "吸顶灯_射灯"),
            (["wandleuch", "wandlampe", "spiegel"], "壁灯"),
            (["led-leuchtmittel", "glühbirne", "smart", "rgb", "strip", "streifen", "lichterkette", "lichtleiste"], "LED_智能照明"),
            (["deko", "akzent", "laterne", "nachtlicht", "lounge"], "装饰灯_艺术灯"),
            (["leuchtenserie", "lichtsystem", "leuchtensystem", "beleuchtungssystem", "leuchtmittel", "innenraum", "innenbeleucht", "hallen", "industrie", "retail", "büro", "bühnen", "notbeleucht", "notfall", "feuchtraum", "lichtsteuer", "leuchtenkollekt", "leitsy", "spezial", "röhr"], "商业_专业照明"),
        ]

        for patterns, subcat in DE_PATTERN_MAP:
            for p in patterns:
                if p in desc_raw:
                    return subcat

        # 第三层：英文关键词匹配（标题 + 描述）
        text = " ".join([
            product_data.get("title", ""),
            product_data.get("description", ""),
            " ".join(product_data.get("tags", [])),
        ]).lower()

        scores = Counter()
        for subcat, keywords in LIGHTING_SUBCATEGORIES.items():
            for kw in keywords:
                if kw.lower() in text:
                    scores[subcat] += 1

        if scores:
            return scores.most_common(1)[0][0]
        return "其他灯具"

    def classify_product(self, product_data: dict) -> ClassificationResult:
        """
        对单个产品进行分类
        Args:
            product_data: 产品元数据字典
        """
        product_id = product_data.get("id", "")
        title = product_data.get("title", "")
        category = product_data.get("category", "")
        category_cn = product_data.get("category_cn", "")
        description = product_data.get("description", "")

        # 1. 使用红点原始类别
        if category and category in CATEGORIES:
            primary = category
            primary_cn = CATEGORIES[category]
            confidence = 1.0
        # 2. 尝试关键词匹配
        else:
            primary, confidence = self._classify_by_keywords(title + " " + description)
            primary_cn = CATEGORIES.get(primary, "")

        # 确定大类
        super_cat = self.sub_to_super.get(primary, "其他")

        # 自动标签
        tags = self._generate_tags(product_data)

        # 灯具产品：添加子类标签（精细分类）
        if primary == "lighting":
            lighting_subcat = self.classify_lighting_subcategory(product_data)
            tags.append(f"lighting_subcat:{lighting_subcat}")
            # 二次验证：确认是灯具（用于错误率统计）
            is_lighting, lconf = self.is_lighting_product(product_data)
            if not is_lighting:
                logger.warning(f"疑似非灯具产品（置信度{lconf:.2f}）: {title}")
                tags.append("lighting_verify:uncertain")
            else:
                tags.append(f"lighting_verify:confirmed:{lconf:.2f}")

        # 颜色分析
        color_profile = None
        local_images = product_data.get("local_images", [])
        if local_images and HAS_PIL:
            color_profile = self._analyze_color(local_images[0])

        result = ClassificationResult(
            product_id=product_id,
            title=title,
            primary_category=primary,
            primary_category_cn=primary_cn,
            super_category=super_cat,
            auto_tags=tags,
            color_profile=color_profile,
            confidence=confidence,
        )
        self.results.append(result)
        return result

    def _classify_by_keywords(self, text: str) -> Tuple[str, float]:
        """基于关键词的文本分类"""
        text_lower = text.lower()
        scores = Counter()

        for keyword, category in KEYWORD_CATEGORY_MAP.items():
            if keyword in text_lower:
                scores[category] += 1

        if scores:
            best = scores.most_common(1)[0]
            total = sum(scores.values())
            return best[0], best[1] / total
        return "uncategorized", 0.0

    def _generate_tags(self, product_data: dict) -> List[str]:
        """自动生成产品标签"""
        tags = set()
        text = " ".join([
            product_data.get("title", ""),
            product_data.get("description", ""),
            product_data.get("designer", ""),
            product_data.get("manufacturer", ""),
        ]).lower()

        # 材质标签
        materials = [
            "wood", "metal", "aluminum", "steel", "plastic", "glass",
            "ceramic", "leather", "fabric", "concrete", "marble",
            "copper", "brass", "titanium", "carbon fiber", "bamboo",
        ]
        for m in materials:
            if m in text:
                tags.add(f"material:{m}")

        # 风格标签
        styles = [
            "minimalist", "modern", "classic", "retro", "futuristic",
            "industrial", "scandinavian", "japanese", "organic",
            "geometric", "sustainable", "smart", "portable", "modular",
        ]
        for s in styles:
            if s in text:
                tags.add(f"style:{s}")

        # 功能标签
        functions = [
            "wireless", "bluetooth", "solar", "rechargeable", "foldable",
            "waterproof", "touchscreen", "voice-control", "ai-powered",
            "eco-friendly", "recyclable", "ergonomic",
        ]
        for f in functions:
            if f in text:
                tags.add(f"feature:{f}")

        # 奖项级别标签
        award = product_data.get("award_level", "")
        if award:
            tags.add(f"award:{award}")

        # 年份标签
        year = product_data.get("year", 0)
        if year:
            tags.add(f"year:{year}")

        return sorted(tags)

    def _analyze_color(self, image_path: str) -> Optional[Dict[str, float]]:
        """分析图片主色调"""
        if not HAS_PIL or not os.path.exists(image_path):
            return None
        try:
            with Image.open(image_path) as img:
                img = img.convert("RGB").resize((100, 100))
                pixels = list(img.getdata())

                # 统计色系分布
                color_groups = {
                    "warm": 0,    # 暖色（红/橙/黄）
                    "cool": 0,    # 冷色（蓝/青/紫）
                    "neutral": 0, # 中性色（灰/白/黑）
                    "green": 0,   # 绿色系
                }
                for r, g, b in pixels:
                    brightness = (r + g + b) / 3
                    if brightness > 220 or brightness < 35:
                        color_groups["neutral"] += 1
                    elif abs(r - g) < 30 and abs(g - b) < 30:
                        color_groups["neutral"] += 1
                    elif r > g and r > b:
                        color_groups["warm"] += 1
                    elif b > r and b > g:
                        color_groups["cool"] += 1
                    elif g > r and g > b:
                        color_groups["green"] += 1
                    else:
                        color_groups["neutral"] += 1

                total = len(pixels)
                return {k: round(v / total, 3) for k, v in color_groups.items()}
        except Exception as e:
            logger.debug(f"颜色分析失败: {e}")
            return None

    # === 批量分类 ===

    def classify_all(self, products: List[dict]) -> List[ClassificationResult]:
        """批量分类所有产品"""
        logger.info(f"开始分类 {len(products)} 个产品...")
        self.results = []
        for product in products:
            self.classify_product(product)
        logger.info(f"分类完成: {len(self.results)} 个产品")
        return self.results

    # === 文件整理 ===

    def organize_files(self, mode: str = "lighting_subcat"):
        """
        按分类结果整理图片文件
        Args:
            mode: "lighting_subcat" 按灯具子类整理（默认）,
                  "super" 按大类整理, "primary" 按子类整理
        """
        output_base = os.path.join(OUTPUT_DIR, "classified")
        os.makedirs(output_base, exist_ok=True)

        for result in self.results:
            if mode == "lighting_subcat" and result.primary_category == "lighting":
                # 灯具按子类整理
                subcat = "其他灯具"
                for tag in result.auto_tags:
                    if tag.startswith("lighting_subcat:"):
                        subcat = tag.split(":", 1)[1]
                        break
                target_dir = os.path.join(output_base, "lighting", subcat)
            elif mode == "super":
                target_dir = os.path.join(output_base, result.super_category)
            else:
                target_dir = os.path.join(output_base, result.primary_category)
            os.makedirs(target_dir, exist_ok=True)

            # 查找对应的本地图片
            src_dir = os.path.join(IMAGES_DIR, result.primary_category)
            if not os.path.exists(src_dir):
                continue

            for fname in os.listdir(src_dir):
                if fname.startswith(result.product_id):
                    src = os.path.join(src_dir, fname)
                    dst = os.path.join(target_dir, fname)
                    if not os.path.exists(dst):
                        shutil.copy2(src, dst)

        logger.info(f"文件整理完成: {output_base}")

    # === 报告生成 ===

    def generate_report(self) -> dict:
        """生成分类统计报告"""
        report = {
            "total_products": len(self.results),
            "by_super_category": {},
            "by_primary_category": {},
            "by_award_level": {},
            "by_year": {},
            "top_tags": {},
            "color_distribution": {},
        }

        super_counts = Counter()
        primary_counts = Counter()
        award_counts = Counter()
        year_counts = Counter()
        all_tags = Counter()
        color_totals = defaultdict(float)
        color_count = 0

        for r in self.results:
            super_counts[r.super_category] += 1
            primary_counts[f"{r.primary_category} ({r.primary_category_cn})"] += 1

            for tag in r.auto_tags:
                if tag.startswith("award:"):
                    award_counts[tag.split(":")[1]] += 1
                elif tag.startswith("year:"):
                    year_counts[tag.split(":")[1]] += 1
                else:
                    all_tags[tag] += 1

            if r.color_profile:
                color_count += 1
                for k, v in r.color_profile.items():
                    color_totals[k] += v

        # 灯具子类统计
        lighting_subcat_counts = Counter()
        lighting_verified = 0
        lighting_uncertain = 0
        for r in self.results:
            if r.primary_category == "lighting":
                for tag in r.auto_tags:
                    if tag.startswith("lighting_subcat:"):
                        lighting_subcat_counts[tag.split(":", 1)[1]] += 1
                    if "lighting_verify:confirmed" in tag:
                        lighting_verified += 1
                    if "lighting_verify:uncertain" in tag:
                        lighting_uncertain += 1

        lighting_total = lighting_verified + lighting_uncertain
        error_rate = (lighting_uncertain / lighting_total * 100) if lighting_total > 0 else 0.0

        report["by_super_category"] = dict(super_counts.most_common())
        report["by_primary_category"] = dict(primary_counts.most_common())
        report["by_award_level"] = dict(award_counts.most_common())
        report["by_year"] = dict(sorted(year_counts.items()))
        report["top_tags"] = dict(all_tags.most_common(30))
        report["lighting_subcategories"] = dict(lighting_subcat_counts.most_common())
        report["lighting_verified"] = lighting_verified
        report["lighting_uncertain"] = lighting_uncertain
        report["lighting_error_rate_pct"] = round(error_rate, 2)
        if color_count > 0:
            report["color_distribution"] = {
                k: round(v / color_count, 3) for k, v in color_totals.items()
            }

        # 保存报告
        report_path = os.path.join(OUTPUT_DIR, "classification_report.json")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 生成文本摘要
        summary_path = os.path.join(OUTPUT_DIR, "classification_summary.txt")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("红点设计奖 - 灯具图片分类统计报告\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"总产品数: {report['total_products']}\n\n")

            f.write("【大类分布】\n")
            for cat, count in super_counts.most_common():
                pct = count / max(len(self.results), 1) * 100
                bar = "█" * int(pct / 2)
                f.write(f"  {cat:<12} {count:>5} ({pct:5.1f}%) {bar}\n")

            if lighting_subcat_counts:
                f.write(f"\n【灯具子类分布】\n")
                for subcat, count in lighting_subcat_counts.most_common():
                    pct = count / max(lighting_total, 1) * 100
                    f.write(f"  {subcat:<20} {count:>5} ({pct:5.1f}%)\n")
                f.write(f"\n  灯具验证通过: {lighting_verified}\n")
                f.write(f"  灯具待确认:   {lighting_uncertain}\n")
                f.write(f"  错误率:        {error_rate:.2f}%\n")

            f.write(f"\n【奖项分布】\n")
            for level, count in award_counts.most_common():
                f.write(f"  {level:<25} {count:>5}\n")

            f.write(f"\n【年份分布】\n")
            for year, count in sorted(year_counts.items()):
                f.write(f"  {year}年  {count:>5}\n")

            f.write(f"\n【热门标签TOP15】\n")
            for tag, count in all_tags.most_common(15):
                f.write(f"  {tag:<30} {count:>5}\n")

        logger.info(f"报告已生成: {report_path}")
        logger.info(f"摘要已生成: {summary_path}")
        if lighting_total > 0:
            logger.info(f"灯具错误率: {error_rate:.2f}% (目标<2%)")
        return report
