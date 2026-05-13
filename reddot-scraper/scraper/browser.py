"""
浏览器引擎 - 使用 Selenium 绕过反爬防护
Browser Engine - Uses Selenium to bypass anti-scraping protection
"""
import os
import time
import random
import logging
from typing import Optional

# 绕过系统代理对 WebDriver 本地连接的拦截
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")
os.environ.setdefault("no_proxy", "localhost,127.0.0.1")
# 清除可能干扰 WebDriver 的代理环境变量（仅对 subprocess 有效）
for _proxy_var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    if _proxy_var in os.environ:
        os.environ[_proxy_var] = ""

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

import sys
sys.path.insert(0, "..")
from config import (
    HEADLESS, WINDOW_SIZE, PAGE_LOAD_TIMEOUT,
    REQUEST_DELAY_MIN, REQUEST_DELAY_MAX, REQUEST_HEADERS
)

logger = logging.getLogger(__name__)


class BrowserEngine:
    """Selenium 浏览器引擎，用于动态页面抓取"""

    def __init__(self, headless: bool = HEADLESS):
        if not HAS_SELENIUM:
            raise ImportError(
                "Selenium 未安装。请运行: pip install selenium webdriver-manager"
            )
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None

    def start(self):
        """启动浏览器"""
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument(f"--window-size={WINDOW_SIZE[0]},{WINDOW_SIZE[1]}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-proxy-server")
        options.add_argument("--disable-extensions")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument(f"--user-agent={REQUEST_HEADERS['User-Agent']}")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception:
            # 回退：尝试系统自带的 chromedriver
            self.driver = webdriver.Chrome(options=options)

        self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        # 注入脚本隐藏 webdriver 特征
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}};
            """}
        )
        logger.info("浏览器引擎已启动")

    def stop(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("浏览器引擎已关闭")

    def get_page(self, url: str, wait_selector: str = None, scroll: bool = True) -> str:
        """
        获取页面HTML内容
        Args:
            url: 目标URL
            wait_selector: 等待元素的CSS选择器
            scroll: 是否滚动加载更多内容
        Returns:
            页面HTML源码
        """
        if not self.driver:
            self.start()

        try:
            self.driver.get(url)
            time.sleep(random.uniform(1.5, 3.0))

            if wait_selector:
                WebDriverWait(self.driver, PAGE_LOAD_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )

            if scroll:
                self._scroll_page()

            return self.driver.page_source
        except TimeoutException:
            logger.warning(f"页面加载超时: {url}")
            return self.driver.page_source
        except WebDriverException as e:
            logger.error(f"浏览器错误: {e}")
            return ""

    def _scroll_page(self, scroll_pause: float = 1.5, max_scrolls: int = 20):
        """滚动页面以触发懒加载"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scrolls = 0

        while scrolls < max_scrolls:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause + random.uniform(0, 1.0))
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scrolls += 1

    def click_load_more(self, selector: str, max_clicks: int = 50):
        """点击"加载更多"按钮"""
        clicks = 0
        while clicks < max_clicks:
            try:
                btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                self.driver.execute_script("arguments[0].click();", btn)
                clicks += 1
                time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))
            except (TimeoutException, WebDriverException):
                break
        return clicks

    def get_element_attribute(self, selector: str, attribute: str) -> list:
        """获取所有匹配元素的指定属性"""
        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
        return [el.get_attribute(attribute) for el in elements if el.get_attribute(attribute)]

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
