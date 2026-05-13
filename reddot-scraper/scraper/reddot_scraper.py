"""
红点设计奖抓取器核心模块
Red Dot Design Award Scraper - Core Module

支持两种抓取模式：
1. Selenium 模式（推荐）：绕过反爬，支持动态页面
2. Requests 模式（备用）：轻量快速，用于API端点
"""
import os
import re
import json
import time
import random
import hashlib
import logging
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict, field
from datetime import datetime

import requests
from bs4 import BeautifulSoup

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    REDDOT_BASE_URL, CATEGORIES, REQUEST_HEADERS,
    REQUEST_DELAY_MIN, REQUEST_DELAY_MAX, MAX_RETRIES, RETRY_BACKOFF,
    IMAGE_MIN_WIDTH, IMAGE_MIN_HEIGHT, MAX_IMAGES_PER_PRODUCT,
    IMAGES_DIR, METADATA_DIR, YEAR_START, YEAR_END,
)

logger = logging.getLogger(__name__)


@dataclass
class DesignProduct:
    """设计产品数据模型"""
    id: str = ""
    title: str = ""
    designer: str = ""
    manufacturer: str = ""
    category: str = ""
    category_cn: str = ""
    year: int = 0
    award_level: str = ""          # "winner" / "best of the best" / "honourable mention"
    description: str = ""
    url: str = ""
    image_urls: List[str] = field(default_factory=list)
    local_images: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    scraped_at: str = ""


class RedDotScraper:
    """红点设计奖抓取器"""

    # 红点已知的 URL 模式
    EXHIBITION_URL = f"{REDDOT_BASE_URL}/pd/online-exhibition"
    SEARCH_API_URL = f"{REDDOT_BASE_URL}/api/projects"
    WINNERS_URL = f"{REDDOT_BASE_URL}/pd/online-exhibition/work"

    # 红点网站常见的图片 CSS 选择器
    IMAGE_SELECTORS = [
        "img.project-image",
        "img.work-image",
        "img[data-src]",
        ".gallery img",
        ".slider img",
        ".product-image img",
        ".image-container img",
        "picture source",
        ".swiper-slide img",
        "figure img",
        ".hero-image img",
        'img[src*="red-dot"]',
        'img[src*="reddot"]',
        'img[src*="cloudfront"]',
        'img[src*="amazonaws"]',
    ]

    # 产品信息 CSS 选择器
    PRODUCT_SELECTORS = {
        "title": [
            "h1.project-title", "h1.work-title", ".product-name h1",
            "h1", "[class*='title'] h1", "[class*='name']"
        ],
        "designer": [
            ".designer-name", ".project-designer", "[class*='designer']",
            "[class*='author']", "dt:contains('Designer') + dd"
        ],
        "manufacturer": [
            ".manufacturer-name", ".project-manufacturer",
            "[class*='manufacturer']", "[class*='company']",
            "dt:contains('Manufacturer') + dd"
        ],
        "description": [
            ".project-description", ".work-description",
            ".product-description", "[class*='description']",
            ".content-text", "article p"
        ],
        "category": [
            ".project-category", ".work-category", "[class*='category']",
            ".breadcrumb a", "nav.breadcrumb li"
        ],
    }

    # 项目链接选择器
    PROJECT_LINK_SELECTORS = [
        "a.project-link",
        "a.work-link",
        ".project-card a",
        ".work-card a",
        ".grid-item a",
        ".product-item a",
        'a[href*="/work/"]',
        'a[href*="/project/"]',
        ".exhibition-item a",
        ".winner-item a",
    ]

    # "加载更多" 按钮选择器
    LOAD_MORE_SELECTORS = [
        "button.load-more",
        "[class*='load-more']",
        "[class*='show-more']",
        "button[class*='more']",
        ".pagination .next",
        "a.next-page",
    ]

    def __init__(self, use_selenium: bool = True):
        self.use_selenium = use_selenium
        self.session = requests.Session()
        self.session.headers.update(REQUEST_HEADERS)
        self.browser = None
        self.products: List[DesignProduct] = []
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保目录存在"""
        os.makedirs(IMAGES_DIR, exist_ok=True)
        os.makedirs(METADATA_DIR, exist_ok=True)
        for cat_key in CATEGORIES:
            os.makedirs(os.path.join(IMAGES_DIR, cat_key), exist_ok=True)

    def _init_browser(self):
        """按需初始化浏览器"""
        if self.use_selenium and not self.browser:
            from scraper.browser import BrowserEngine
            self.browser = BrowserEngine()
            self.browser.start()

    def _random_delay(self):
        """随机延迟，避免被封"""
        time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))

    # === 页面抓取 ===

    def fetch_page(self, url: str, wait_selector: str = None) -> str:
        """获取页面内容（自动选择引擎）"""
        if self.use_selenium:
            self._init_browser()
            return self.browser.get_page(url, wait_selector=wait_selector)
        else:
            return self._fetch_with_requests(url)

    def _fetch_with_requests(self, url: str) -> str:
        """使用 requests 获取页面"""
        for attempt in range(MAX_RETRIES):
            try:
                resp = self.session.get(url, timeout=30)
                if resp.status_code == 200:
                    return resp.text
                elif resp.status_code == 403:
                    logger.warning(f"403 被拦截: {url}，切换 Selenium 模式")
                    self.use_selenium = True
                    self._init_browser()
                    return self.browser.get_page(url)
                elif resp.status_code == 429:
                    wait = RETRY_BACKOFF ** (attempt + 1) * 10
                    logger.warning(f"429 限速，等待 {wait:.0f}s")
                    time.sleep(wait)
                else:
                    logger.warning(f"HTTP {resp.status_code}: {url}")
            except requests.RequestException as e:
                logger.error(f"请求失败 (尝试 {attempt+1}): {e}")
                time.sleep(RETRY_BACKOFF ** attempt)
        return ""

    # === 类别列表抓取 ===

    # 红点网站过滤按钮的 CSS 选择器（按类别过滤）
    FILTER_BUTTON_SELECTORS = [
        # 通用过滤器按钮模式
        "[data-filter='lighting']",
        "[data-discipline='lighting']",
        "[data-value='lighting']",
        "button[data-filter*='lighting']",
        ".filter-item[data-value*='lighting']",
        # 文字匹配（备用）
        "button:contains('Lighting')",
        "a:contains('Lighting')",
        ".filter-tag:contains('Lighting')",
    ]

    def _click_filter_and_collect(self, category_key: str, year: int = None) -> List[str]:
        """
        策略：
        1. 加载展览页，扫描 HTML 找出所有包含 lighting/discipline 关键词的链接
        2. 访问这些过滤链接，收集产品 URL
        3. 尝试点击过滤按钮（data-* 属性 或 文字匹配）
        """
        if not self.use_selenium:
            return []
        self._init_browser()
        if not (self.browser and self.browser.driver):
            return []

        import time
        driver = self.browser.driver
        all_found_links = []

        try:
            from selenium.webdriver.common.by import By

            # === 步骤1：加载展览主页，分析页面结构 ===
            exhibition_url = f"{REDDOT_BASE_URL}/de/pd/online-exhibition/"
            driver.get(exhibition_url)
            time.sleep(4)
            self.browser._scroll_page(scroll_pause=1.0, max_scrolls=3)

            html = driver.page_source
            soup = BeautifulSoup(html, "lxml")

            # === 步骤2：从页面 HTML 找过滤链接 ===
            filter_urls = set()
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                txt = a.get_text().strip().lower()
                if (("lighting" in href.lower() or "discipline" in href.lower())
                        and "project" not in href and "work" not in href):
                    full = urljoin(exhibition_url, href)
                    filter_urls.add(full)
                    logger.info(f"  发现过滤链接: {full}")

            # 记录当前页找到的所有产品链接（未过滤前）
            all_product_hrefs = set()
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "/project/" in href or "/work/" in href:
                    all_product_hrefs.add(urljoin(exhibition_url, href))

            logger.info(f"  页面发现 {len(all_product_hrefs)} 个产品链接, {len(filter_urls)} 个过滤链接")

            # === 步骤3：访问发现的过滤链接 ===
            for furl in list(filter_urls)[:5]:
                try:
                    driver.get(furl)
                    time.sleep(3)
                    self.browser._scroll_page(scroll_pause=1.5, max_scrolls=30)
                    # 点击"加载更多"
                    for sel in self.LOAD_MORE_SELECTORS:
                        clicks = self.browser.click_load_more(sel)
                        if clicks > 0:
                            logger.info(f"  加载更多: {clicks} 次")
                            break
                    fhtml = driver.page_source
                    flinks = self._extract_project_links(fhtml, furl)
                    logger.info(f"  过滤页 {furl[-60:]} 找到 {len(flinks)} 个产品")
                    all_found_links.extend(flinks)
                except Exception as e:
                    logger.debug(f"  过滤链接访问失败: {e}")

            # === 步骤4：尝试点击 JS 过滤按钮 ===
            filter_clicked = False
            driver.get(exhibition_url)
            time.sleep(4)

            # 方法A：data-* 属性按钮
            for attr_value in [category_key, "Lighting", "lighting",
                               category_key.replace("-", " ")]:
                for attr in ["data-filter", "data-discipline", "data-value",
                             "data-category", "data-tag", "data-slug"]:
                    try:
                        btn = driver.find_element(
                            By.CSS_SELECTOR, f"[{attr}='{attr_value}']")
                        driver.execute_script("arguments[0].click();", btn)
                        filter_clicked = True
                        logger.info(f"  点击过滤按钮: [{attr}='{attr_value}']")
                        time.sleep(3)
                        break
                    except Exception:
                        pass
                if filter_clicked:
                    break

            # 方法B：文字/href 匹配
            if not filter_clicked:
                elems = driver.find_elements(By.XPATH,
                    "//*[contains(translate(text(),'LIGHTING','lighting'),'lighting') "
                    "or contains(@href,'lighting') or contains(@data-filter,'lighting')]")
                for el in elems[:10]:
                    tag = el.tag_name.lower()
                    href = el.get_attribute("href") or ""
                    if tag in ("a", "button", "span", "div", "li") and \
                            "project" not in href and "work" not in href:
                        try:
                            driver.execute_script("arguments[0].click();", el)
                            filter_clicked = True
                            logger.info(f"  点击元素: <{tag}> '{el.text[:30]}'")
                            time.sleep(3)
                            break
                        except Exception:
                            pass

            if filter_clicked:
                self.browser._scroll_page(scroll_pause=1.5, max_scrolls=40)
                for sel in self.LOAD_MORE_SELECTORS:
                    clicks = self.browser.click_load_more(sel)
                    if clicks > 0:
                        logger.info(f"  加载更多: {clicks} 次")
                        break
                js_html = driver.page_source
                js_links = self._extract_project_links(js_html, exhibition_url)
                logger.info(f"  JS过滤后找到 {len(js_links)} 个产品链接")
                all_found_links.extend(js_links)

        except Exception as e:
            logger.warning(f"  JS过滤器异常: {e}")

        unique_links = list(set(all_found_links))
        if unique_links:
            logger.info(f"  JS过滤器共获取 {len(unique_links)} 个产品链接")
        return unique_links

    def scrape_category_list(self, category_key: str, year: int = None) -> List[str]:
        """
        抓取某个类别下的所有产品链接
        Returns: 产品详情页URL列表
        """
        product_urls = []

        # === 策略1：Selenium 点击 JS 过滤按钮（最准确）===
        if self.use_selenium and year is None:
            # 首次加载时尝试点击过滤器
            js_links = self._click_filter_and_collect(category_key, year)
            if js_links:
                product_urls.extend(js_links)
                logger.info(f"  通过JS过滤器找到 {len(js_links)} 个产品链接")
                return list(set(product_urls))

        # === 策略2：URL 参数过滤（备用）===
        year_params = []
        if year:
            year_params = [f"year={year}", f"filter%5Byear%5D%5B%5D={year}"]

        # 主要URL列表（红点网站已知有效模式）
        base_urls = [
            f"{REDDOT_BASE_URL}/de/pd/online-exhibition/?filter%5Bdiscipline%5D%5B%5D={category_key}",
            f"{REDDOT_BASE_URL}/pd/online-exhibition/?filter%5Bdiscipline%5D%5B%5D={category_key}",
            f"{REDDOT_BASE_URL}/de/pd/online-exhibition/?discipline={category_key}",
            f"{REDDOT_BASE_URL}/pd/online-exhibition/?category={category_key}",
            f"{REDDOT_BASE_URL}/de/pd/online-exhibition/{category_key}/",
        ]

        urls_to_try = []
        for bu in base_urls:
            if year_params:
                sep = "&" if "?" in bu else "?"
                for yp in year_params:
                    urls_to_try.append(f"{bu}{sep}{yp}")
            else:
                urls_to_try.append(bu)

        working_url = None
        for url in urls_to_try:
            logger.info(f"尝试抓取类别页: {url}")
            html = self.fetch_page(url, wait_selector="a")
            if not html:
                continue

            links = self._extract_project_links(html, url)
            if links:
                product_urls.extend(links)
                working_url = url
                logger.info(f"  找到 {len(links)} 个产品链接")
                break
            self._random_delay()

        # 使用 Selenium 时尝试点击"加载更多"
        if self.use_selenium and self.browser and self.browser.driver and working_url:
            for selector in self.LOAD_MORE_SELECTORS:
                clicks = self.browser.click_load_more(selector)
                if clicks > 0:
                    html = self.browser.driver.page_source
                    extra_links = self._extract_project_links(html, working_url)
                    new_links = [l for l in extra_links if l not in product_urls]
                    product_urls.extend(new_links)
                    logger.info(f"  加载更多后新增 {len(new_links)} 个链接")
                    break

        return list(set(product_urls))

    def _extract_project_links(self, html: str, base_url: str) -> List[str]:
        """从页面提取产品详情页链接"""
        soup = BeautifulSoup(html, "lxml")
        links = set()

        for selector in self.PROJECT_LINK_SELECTORS:
            for el in soup.select(selector):
                href = el.get("href", "")
                if href and not href.startswith(("#", "javascript:")):
                    full_url = urljoin(base_url, href)
                    if "red-dot.org" in full_url:
                        links.add(full_url)

        # 备用：提取所有含产品详情路径的链接（红点多种路径模式）
        if not links:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if any(pat in href for pat in ["/work/", "/project/", "/pd/", "/winner/"]):
                    full_url = urljoin(base_url, href)
                    # 只保留产品详情页（排除列表页、筛选页等）
                    if "red-dot.org" in full_url and not any(
                        x in full_url for x in ["online-exhibition/?", "online-exhibition/page"]
                    ):
                        links.add(full_url)

        # 最终备用：提取所有红点内部链接中包含产品标识的
        if not links:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                full_url = urljoin(base_url, href)
                if ("red-dot.org" in full_url and
                        re.search(r'/(?:work|project|winner|pd/[^/]+/work)/[^/?]+', full_url)):
                    links.add(full_url)

        return list(links)

    # === 产品详情抓取 ===

    # 灯具类关键词（用于产品页验证，确保错误率<2%）
    LIGHTING_KEYWORDS = {
        "lamp", "light", "luminaire", "luminair", "fixture", "lighting",
        "lantern", "chandelier", "pendant", "sconce", "luminary",
        "illuminat", "led", "bulb", "lumen", "spotlight", "floodlight",
        "downlight", "uplight", "torch", "flashlight", "candle",
        "leuchte", "lampe", "licht",  # German
        "灯", "照明", "光源", "发光", "亮度",
    }

    # 排除关键词：产品页若含这些但不含灯具词，则大概率不是灯具
    NON_LIGHTING_BREADCRUMBS = {
        "furniture", "chair", "sofa", "table", "desk", "shelf",
        "kitchen", "cookware", "tableware", "bath", "sanitary",
        "automotive", "bicycle", "camera", "audio", "speaker",
        "medical", "sport", "fashion", "watch", "packaging",
        "office", "tool", "robot", "smartphone", "laptop",
    }

    def _validate_lighting_product(self, soup: BeautifulSoup, title: str,
                                    description: str, target_category: str) -> bool:
        """
        严格验证产品是否为灯具（确保错误率<2%）。
        策略：
        1. 优先信任页面上的类别元数据（面包屑/标签）
        2. 次选：标题+描述必须含灯具关键词
        3. 两者都无 -> 拒绝（宁可漏抓，不要错误引入非灯具）
        """
        if not target_category or target_category != "lighting":
            return True  # 仅对 lighting 类别做严格验证

        title_lower = title.lower()
        desc_lower = description.lower()
        text_combined = title_lower + " " + desc_lower

        # === 第1层：读取页面结构化类别数据 ===
        category_selectors = [
            ".breadcrumb", "nav.breadcrumb", "ol.breadcrumb",
            "[class*='breadcrumb']", "[class*='category']",
            "[class*='discipline']", "[class*='tag']",
            "[data-category]", "meta[name='category']",
        ]
        page_category_text = ""
        for sel in category_selectors:
            for el in soup.select(sel):
                page_category_text += " " + el.get_text().lower()

        # 读取 URL 中可能的类别信息（如 /de/project/xxx 中通常无类别，但检查页面所有链接）
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "discipline" in href or "category" in href or "lighting" in href:
                page_category_text += " " + href.lower() + " " + a.get_text().lower()

        # 如果页面结构明确标注 lighting -> 通过
        if any(kw in page_category_text for kw in ["lighting", "leuchten", "beleuchtung", "照明"]):
            return True

        # 如果页面结构明确标注其他类别 -> 拒绝
        if any(kw in page_category_text for kw in self.NON_LIGHTING_BREADCRUMBS):
            logger.warning(f"  [过滤-类别不符] {title[:50]}")
            return False

        # === 第2层：标题+描述灯具关键词匹配 ===
        # 要求至少命中2个不同灯具关键词，OR 命中核心词（lamp/light/luminaire等）
        CORE_KEYWORDS = {"lamp", "light", "luminaire", "chandelier", "lantern",
                         "sconce", "灯", "照明", "led fixture", "lighting fixture",
                         "leuchte", "luminar"}
        SECONDARY_KEYWORDS = {"led", "bulb", "lumen", "spotlight", "pendant",
                               "downlight", "fixture", "illuminat", "torch",
                               "brightness", "dimmer", "watt", "lumens"}

        core_hits = sum(1 for kw in CORE_KEYWORDS if kw in text_combined)
        secondary_hits = sum(1 for kw in SECONDARY_KEYWORDS if kw in text_combined)

        if core_hits >= 1:
            return True  # 核心词命中 -> 接受
        if secondary_hits >= 2:
            return True  # 2个次级词命中 -> 接受

        # === 第3层：全页文本扫描（最后防线）===
        full_text = soup.get_text().lower()
        # 在产品描述区域找灯具词（不用整个页面避免导航栏干扰）
        desc_area = ""
        for sel in [".project-description", ".work-description", ".product-description",
                    "[class*='description']", "article", "main", ".content"]:
            el = soup.select_one(sel)
            if el:
                desc_area = el.get_text().lower()
                break

        if desc_area:
            core_in_desc = sum(1 for kw in CORE_KEYWORDS if kw in desc_area)
            if core_in_desc >= 1:
                return True

        # 两层都无法确认 -> 严格拒绝（保证错误率<2%）
        logger.warning(f"  [过滤-关键词不匹配] {title[:50]}")
        return False

    def scrape_product(self, url: str, category_key: str = "") -> Optional[DesignProduct]:
        """抓取单个产品的详细信息和图片"""
        logger.info(f"抓取产品: {url}")
        html = self.fetch_page(url, wait_selector="img")
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        product = DesignProduct(
            id=self._generate_id(url),
            url=url,
            category=category_key,
            category_cn=CATEGORIES.get(category_key, ""),
            scraped_at=datetime.now().isoformat(),
        )

        # 提取文本信息
        product.title = self._extract_text(soup, self.PRODUCT_SELECTORS["title"])
        product.designer = self._extract_text(soup, self.PRODUCT_SELECTORS["designer"])
        product.manufacturer = self._extract_text(soup, self.PRODUCT_SELECTORS["manufacturer"])
        product.description = self._extract_text(soup, self.PRODUCT_SELECTORS["description"])

        if not product.category:
            product.category = self._extract_text(soup, self.PRODUCT_SELECTORS["category"])

        # 【关键验证】：确认产品属于目标类别（错误率控制 <2%）
        if category_key and not self._validate_lighting_product(
                soup, product.title, product.description, category_key):
            logger.info(f"  [跳过] 产品不属于 {category_key} 类别: {product.title}")
            return None

        # 提取年份
        year_match = re.search(r'20[12]\d', url + product.title + product.description)
        if year_match:
            product.year = int(year_match.group())

        # 提取奖项级别
        page_text = soup.get_text().lower()
        if "best of the best" in page_text:
            product.award_level = "best_of_the_best"
        elif "honourable mention" in page_text:
            product.award_level = "honourable_mention"
        else:
            product.award_level = "winner"

        # 提取图片
        product.image_urls = self._extract_images(soup, url)
        logger.info(f"  标题: {product.title}, 图片: {len(product.image_urls)} 张")

        return product

    def _extract_text(self, soup: BeautifulSoup, selectors: list) -> str:
        """使用多个选择器尝试提取文本"""
        for selector in selectors:
            try:
                el = soup.select_one(selector)
                if el:
                    text = el.get_text(strip=True)
                    if text and len(text) > 1:
                        return text
            except Exception:
                continue
        return ""

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """提取产品设计图片URL"""
        image_urls = set()

        for selector in self.IMAGE_SELECTORS:
            for el in soup.select(selector):
                # 检查多种图片属性
                for attr in ["src", "data-src", "data-lazy-src", "data-original",
                             "srcset", "data-srcset", "content"]:
                    value = el.get(attr, "")
                    if not value:
                        continue

                    # 处理 srcset（取最大尺寸）
                    if "srcset" in attr:
                        urls = self._parse_srcset(value)
                        for u in urls:
                            full = urljoin(base_url, u)
                            if self._is_valid_image_url(full):
                                image_urls.add(full)
                    else:
                        full = urljoin(base_url, value)
                        if self._is_valid_image_url(full):
                            image_urls.add(full)

        # 额外：从 CSS 背景图提取
        for el in soup.select("[style]"):
            style = el.get("style", "")
            bg_urls = re.findall(r'url\(["\']?(.*?)["\']?\)', style)
            for u in bg_urls:
                full = urljoin(base_url, u)
                if self._is_valid_image_url(full):
                    image_urls.add(full)

        # 额外：从 JSON-LD 结构化数据提取
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                self._extract_json_images(data, image_urls)
            except (json.JSONDecodeError, TypeError):
                pass

        return list(image_urls)[:MAX_IMAGES_PER_PRODUCT]

    def _parse_srcset(self, srcset: str) -> List[str]:
        """解析 srcset 属性，返回URL列表（按尺寸降序）"""
        entries = []
        for part in srcset.split(","):
            part = part.strip()
            tokens = part.split()
            if tokens:
                url = tokens[0]
                size = 0
                if len(tokens) > 1:
                    size_match = re.search(r'(\d+)', tokens[1])
                    if size_match:
                        size = int(size_match.group(1))
                entries.append((url, size))
        entries.sort(key=lambda x: x[1], reverse=True)
        return [e[0] for e in entries]

    def _extract_json_images(self, data, image_set: set):
        """从 JSON-LD 数据递归提取图片"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ("image", "photo", "thumbnail", "logo"):
                    if isinstance(value, str):
                        image_set.add(value)
                    elif isinstance(value, list):
                        for v in value:
                            if isinstance(v, str):
                                image_set.add(v)
                            elif isinstance(v, dict) and "url" in v:
                                image_set.add(v["url"])
                elif isinstance(value, (dict, list)):
                    self._extract_json_images(value, image_set)
        elif isinstance(data, list):
            for item in data:
                self._extract_json_images(item, image_set)

    def _is_valid_image_url(self, url: str) -> bool:
        """判断是否为有效的产品图片URL"""
        if not url or len(url) < 10:
            return False
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        # 过滤 logo/icon/social 等非产品图
        skip_patterns = [
            "logo", "icon", "favicon", "social", "banner",
            "sprite", "pixel", "tracking", "analytics",
            "1x1", "blank", "spacer", "arrow", "button",
            "facebook", "twitter", "linkedin", "instagram",
            "share", "badge", "certificate",
        ]
        url_lower = url.lower()
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False
        # 检查扩展名
        img_extensions = (".jpg", ".jpeg", ".png", ".webp", ".avif", ".tif", ".tiff")
        path = parsed.path.lower()
        has_ext = any(path.endswith(ext) for ext in img_extensions)
        # 允许 CDN URL（可能无扩展名）
        is_cdn = any(cdn in parsed.netloc for cdn in
                     ["cloudfront", "amazonaws", "cloudinary", "imgix", "akamai"])
        return has_ext or is_cdn

    # === 图片下载 ===

    def download_image(self, url: str, category_key: str, product_id: str,
                       index: int = 0) -> Optional[str]:
        """下载单张图片到分类目录"""
        ext = self._get_image_ext(url)
        filename = f"{product_id}_{index:02d}.{ext}"
        category_dir = os.path.join(IMAGES_DIR, category_key) if category_key else IMAGES_DIR
        os.makedirs(category_dir, exist_ok=True)
        filepath = os.path.join(category_dir, filename)

        if os.path.exists(filepath):
            return filepath

        for attempt in range(MAX_RETRIES):
            try:
                resp = self.session.get(url, timeout=30, stream=True)
                if resp.status_code == 200:
                    content_type = resp.headers.get("Content-Type", "")
                    if "image" not in content_type and "octet" not in content_type:
                        return None

                    with open(filepath, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)

                    # 验证图片尺寸
                    if self._validate_image(filepath):
                        logger.debug(f"  下载成功: {filename}")
                        return filepath
                    else:
                        os.remove(filepath)
                        return None
                elif resp.status_code == 429:
                    time.sleep(RETRY_BACKOFF ** (attempt + 1) * 5)
                else:
                    logger.debug(f"  下载失败 HTTP {resp.status_code}: {url}")
                    return None
            except requests.RequestException as e:
                logger.debug(f"  下载异常 (尝试 {attempt+1}): {e}")
                time.sleep(RETRY_BACKOFF ** attempt)
        return None

    def _validate_image(self, filepath: str) -> bool:
        """验证图片有效性和最小尺寸"""
        try:
            from PIL import Image
            with Image.open(filepath) as img:
                w, h = img.size
                return w >= IMAGE_MIN_WIDTH and h >= IMAGE_MIN_HEIGHT
        except Exception:
            return False

    def _get_image_ext(self, url: str) -> str:
        """从URL推断图片扩展名"""
        path = urlparse(url).path.lower()
        for ext in ["png", "webp", "avif", "tiff", "tif"]:
            if ext in path:
                return ext
        return "jpg"

    def _generate_id(self, url: str) -> str:
        """生成产品唯一ID"""
        return hashlib.md5(url.encode()).hexdigest()[:12]

    # === Solr API 搜索（主力方法）===

    SOLR_API_URL = "https://www.red-dot.org/de/search/search.json"

    # 红点 Product Design 灯具子类的分类代码（Licht & Leuchten）
    LIGHTING_CATEGORY_FILTER = "meta_categories:/11/119/"

    # API 请求头（避免 brotli 编码问题，requests 不支持）
    _API_HEADERS = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
    }

    def _api_fetch_page(self, solr_page: int, category_filter: str = None,
                        query: str = "") -> dict:
        """
        请求 Solr API 的单页数据。
        注意：红点 API 使用 solr[page] 参数翻页，规律为：
          solr[page]=0 → 第1批(偏移0)
          solr[page]=1 → 同第1批(重复，跳过)
          solr[page]=2 → 第2批(偏移12)
          solr[page]=N → 第N批(偏移(N-1)*12)
        """
        params = {
            "q": query,
            "resultsPerPage": 12,
            "solr[page]": solr_page,
        }
        if category_filter:
            params["solr[filter][]"] = category_filter

        headers = {**REQUEST_HEADERS, **self._API_HEADERS}
        try:
            resp = self.session.get(
                self.SOLR_API_URL,
                params=params,
                headers=headers,
                timeout=30,
            )
            if resp.status_code != 200:
                logger.warning(f"  API HTTP {resp.status_code}: solr[page]={solr_page}")
                return {}
            return resp.json()
        except Exception as e:
            logger.error(f"  API page {solr_page} error: {e}")
            return {}

    def _api_fetch_all_lighting_products(self) -> List[str]:
        """
        通过 Solr API 灯具分类过滤器（/11/119/ = Licht & Leuchten）
        分页获取全部灯具产品 URL。

        红点 API 每页 12 条，solr[page]=0 为第1批，solr[page]=2 起为第2批开始。
        总计约 1158 条，需约 97 次请求。
        """
        all_docs = self._api_fetch_all_lighting_docs()
        return [d["_product_url"] for d in all_docs if d.get("_product_url")]

    def _api_fetch_all_lighting_docs(self) -> List[dict]:
        """
        通过 Solr API 获取全部灯具产品的完整文档（含标题、年份、奖项、图片URL）。
        API 文档结构：
          {title, url, meta_first(子类别), meta_fourth(年份+奖项), image{large}, data{year,award,category}}
        """
        all_docs: List[dict] = []
        seen_urls: set = set()

        def collect_docs(docs):
            added = 0
            for doc in docs:
                rel_url = doc.get("url", "")
                if not rel_url or rel_url in seen_urls:
                    continue
                seen_urls.add(rel_url)
                full_url = ("https://www.red-dot.org" + rel_url
                            if not rel_url.startswith("http") else rel_url)
                img_data = doc.get("image", {})
                img_url = img_data.get("large") or img_data.get("medium") or img_data.get("small") or ""
                if img_url and not img_url.startswith("http"):
                    img_url = "https://www.red-dot.org" + img_url
                data = doc.get("data", {})
                enriched = {
                    "_product_url": full_url,
                    "_image_url": img_url,
                    "title": doc.get("title", ""),
                    "subcategory": doc.get("meta_first", ""),
                    "year_info": doc.get("meta_fourth", ""),
                    "year": int(data.get("year", 0) or 0),
                    "award_level": data.get("award", ""),
                    "category_name": data.get("category", ""),
                }
                all_docs.append(enriched)
                added += 1
            return added

        # 第一页
        first = self._api_fetch_page(0, self.LIGHTING_CATEGORY_FILTER)
        if not first:
            logger.error("  API 首页请求失败")
            return []

        total = first.get("meta", {}).get("count", 0)
        docs0 = first.get("result", {}).get("docs", [])
        extra_pages = max(0, (total - 12 + 11) // 12)
        last_page = extra_pages + 1

        logger.info(f"  灯具产品总数: {total}, 需翻页到 solr[page]={last_page}")
        collect_docs(docs0)
        logger.info(f"  page=0: {len(all_docs)} 条")

        for solr_pg in range(2, last_page + 1):
            if solr_pg % 10 == 0:
                logger.info(f"  API solr[page]={solr_pg}/{last_page} (已收集 {len(all_docs)} 条)")
            data = self._api_fetch_page(solr_pg, self.LIGHTING_CATEGORY_FILTER)
            if not data:
                logger.warning(f"  第 {solr_pg} 页失败，重试...")
                time.sleep(3)
                data = self._api_fetch_page(solr_pg, self.LIGHTING_CATEGORY_FILTER)
                if not data:
                    continue

            page_docs = data.get("result", {}).get("docs", [])
            if not page_docs:
                logger.info(f"  solr[page]={solr_pg} 无数据，终止")
                break

            collect_docs(page_docs)
            time.sleep(random.uniform(0.5, 1.2))

        logger.info(f"API 获取完成，共 {len(all_docs)} 个唯一灯具产品")
        return all_docs

    # === 主抓取流程 ===

    def scrape_all(self, categories: List[str] = None,
                   years: List[int] = None,
                   download_images: bool = True) -> List[DesignProduct]:
        """
        全量抓取主入口
        优化：对于单类别（如 lighting），先用 JS 过滤器一次性获取所有产品链接，
        再按年份分批处理，避免重复访问。
        Args:
            categories: 要抓取的类别列表，None=全部
            years: 要抓取的年份列表，None=配置范围
            download_images: 是否下载图片
        """
        cats = categories or list(CATEGORIES.keys())
        yrs = years or list(range(YEAR_START, YEAR_END + 1))

        logger.info(f"开始抓取: {len(cats)} 个类别, {len(yrs)} 个年份")
        total_products = 0
        scraped_urls = set()  # 防止重复抓取同一产品

        for cat_key in cats:
            cat_cn = CATEGORIES.get(cat_key, cat_key)
            logger.info(f"\n{'='*60}")
            logger.info(f"类别: {cat_cn} ({cat_key})")
            logger.info(f"{'='*60}")

            # === 策略一：Solr API 直接获取灯具数据（最可靠）===
            api_docs = []
            all_product_urls = []
            if cat_key == "lighting":
                logger.info("  使用 Solr API 获取全量灯具产品数据...")
                api_docs = self._api_fetch_all_lighting_docs()
                if api_docs:
                    all_product_urls = [d["_product_url"] for d in api_docs]
                    logger.info(f"  Solr API 获取到 {len(api_docs)} 个灯具产品")

            # === 策略二（备用）：逐年URL抓取（非lighting类别或API无结果时）===
            if not all_product_urls:
                for year in yrs:
                    logger.info(f"  年份: {year}")
                    year_urls = self.scrape_category_list(cat_key, year)
                    new_urls = [u for u in year_urls if u not in all_product_urls]
                    if new_urls:
                        all_product_urls.extend(new_urls)
                        logger.info(f"  年份 {year} 补充 {len(new_urls)} 个新产品链接")
                    self._random_delay()

            all_product_urls = list(dict.fromkeys(all_product_urls))  # 去重保序
            logger.info(f"\n  共找到 {len(all_product_urls)} 个待处理产品（去重后）")

            # 建立 url -> api_doc 映射（lighting 类别使用）
            api_doc_map = {d["_product_url"]: d for d in api_docs}

            # === 批量处理产品 ===
            for i, url in enumerate(all_product_urls):
                if url in scraped_urls:
                    continue
                scraped_urls.add(url)

                # 若 API 已提供完整元数据，直接构建产品对象（无需加载产品页）
                if url in api_doc_map:
                    doc = api_doc_map[url]
                    product = DesignProduct(
                        id=self._generate_id(url),
                        url=url,
                        title=doc["title"],
                        category=cat_key,
                        category_cn=CATEGORIES.get(cat_key, ""),
                        year=doc["year"],
                        award_level=doc["award_level"],
                        description=doc.get("subcategory", ""),
                        tags=[doc["subcategory"], doc["category_name"]],
                        scraped_at=datetime.now().isoformat(),
                    )
                    if doc["_image_url"]:
                        product.image_urls = [doc["_image_url"]]
                    logger.info(f"  [{i+1}/{len(all_product_urls)}] API: {product.title} ({product.year}) images={len(product.image_urls)}")
                else:
                    logger.info(f"  [{i+1}/{len(all_product_urls)}] 抓取: {url}")
                    product = self.scrape_product(url, cat_key)
                    if not product:
                        continue
                    if not product.year:
                        year_match = re.search(r'20[12]\d', url)
                        if year_match:
                            product.year = int(year_match.group())

                # 下载图片
                if download_images and product.image_urls:
                    downloaded = 0
                    for idx, img_url in enumerate(product.image_urls):
                        local_path = self.download_image(
                            img_url, cat_key, product.id, idx
                        )
                        if local_path:
                            product.local_images.append(local_path)
                            downloaded += 1
                    if downloaded > 0:
                        logger.info(f"    图片下载: {downloaded}/{len(product.image_urls)}")

                self.products.append(product)
                total_products += 1

                # 保存进度（每20个产品保存一次）
                if total_products % 20 == 0:
                    self.save_metadata()
                    logger.info(f"    进度已保存: {total_products} 个产品")

        self.save_metadata()
        logger.info(f"\n抓取完成! 共 {total_products} 个产品")
        return self.products

    def scrape_single_category(self, category_key: str,
                                download_images: bool = True) -> List[DesignProduct]:
        """抓取单个类别"""
        return self.scrape_all(
            categories=[category_key],
            download_images=download_images
        )

    # === 数据持久化 ===

    def save_metadata(self):
        """保存抓取数据为 JSON"""
        filepath = os.path.join(METADATA_DIR, "products.json")
        data = [asdict(p) for p in self.products]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"元数据已保存: {filepath} ({len(data)} 个产品)")

        # 按类别分别保存
        by_category = {}
        for p in self.products:
            cat = p.category or "uncategorized"
            by_category.setdefault(cat, []).append(asdict(p))

        for cat, items in by_category.items():
            cat_file = os.path.join(METADATA_DIR, f"{cat}.json")
            with open(cat_file, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)

    def load_metadata(self) -> List[DesignProduct]:
        """从 JSON 加载已有数据"""
        filepath = os.path.join(METADATA_DIR, "products.json")
        if not os.path.exists(filepath):
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.products = []
        for item in data:
            item.pop("local_images", None)
            item.pop("image_urls", None)
            item.pop("tags", None)
            p = DesignProduct(**{k: v for k, v in item.items()
                                if k in DesignProduct.__dataclass_fields__})
            self.products.append(p)
        return self.products

    def close(self):
        """清理资源"""
        if self.browser:
            self.browser.stop()
        self.session.close()
