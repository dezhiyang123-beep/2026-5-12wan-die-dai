"""
红点设计奖抓取器 - 配置文件
Red Dot Design Award Scraper - Configuration
"""
import os

# === 基础路径 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
METADATA_DIR = os.path.join(DATA_DIR, "metadata")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# === 红点网站配置 ===
REDDOT_BASE_URL = "https://www.red-dot.org"

# 红点产品设计奖 - 类别体系
# 基于红点官方分类（Red Dot Award: Product Design）
CATEGORIES = {
    "living-rooms-bedrooms": "客厅与卧室",
    "kitchen-household": "厨房与家居",
    "tableware-cooking": "餐具与烹饪",
    "bath-sanitary": "浴室与卫浴",
    "interior-design": "室内设计",
    "furniture": "家具",
    "lighting": "照明",
    "garden": "花园与户外",
    "heating-air-conditioning": "暖通空调",
    "consumer-electronics": "消费电子",
    "computers-information-technology": "计算机与信息技术",
    "smartphones-tablets": "智能手机与平板",
    "audio": "音频设备",
    "cameras": "相机与摄影",
    "wearables-fitness": "可穿戴与健身",
    "sports-outdoor": "运动与户外",
    "baby-child": "母婴与儿童",
    "fashion-accessories": "时尚与配饰",
    "watches-jewellery": "手表与珠宝",
    "medical-rehabilitation": "医疗与康复",
    "life-science": "生命科学",
    "tools": "工具",
    "industry-crafts-trade": "工业与手工艺",
    "automotive": "汽车",
    "bicycles-e-mobility": "自行车与电动出行",
    "urban-public-design": "城市与公共设计",
    "office": "办公用品",
    "communication-design": "传播设计",
    "packaging": "包装设计",
    "material-surface": "材料与表面",
    "technology": "技术与创新",
    "robots": "机器人",
}

# === 请求配置 ===
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# === 抓取速率控制 ===
REQUEST_DELAY_MIN = 2.0       # 最小请求间隔（秒）
REQUEST_DELAY_MAX = 5.0       # 最大请求间隔（秒）
MAX_RETRIES = 3               # 最大重试次数
RETRY_BACKOFF = 2.0           # 重试退避倍数
CONCURRENT_DOWNLOADS = 3      # 并发下载数
PAGE_LOAD_TIMEOUT = 30        # Selenium页面加载超时（秒）

# === 图片下载配置 ===
IMAGE_MIN_WIDTH = 200         # 最小图片宽度（过滤缩略图/图标）
IMAGE_MIN_HEIGHT = 200        # 最小图片高度
MAX_IMAGES_PER_PRODUCT = 10   # 每个产品最多下载图片数
IMAGE_FORMAT = "jpg"          # 保存图片格式

# === 奖项年份范围 ===
YEAR_START = 2020
YEAR_END = 2026

# === Selenium 配置 ===
HEADLESS = True               # 无头模式
WINDOW_SIZE = (1920, 1080)    # 浏览器窗口大小
