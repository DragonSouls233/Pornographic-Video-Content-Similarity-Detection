"""
Selenium 辅助模块 - 用于网页抓取
支持多种浏览器和代理配置
"""

import logging
import time
from typing import Optional, Dict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


class SeleniumHelper:
    """Selenium 浏览器助手类"""
    
    def __init__(self, config: dict = None):
        """
        初始化 Selenium 助手
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.driver: Optional[webdriver.Chrome] = None
        self.logger = logging.getLogger(__name__)
        
    def setup_driver(self) -> webdriver.Chrome:
        """
        配置并启动 Chrome 浏览器
        
        Returns:
            WebDriver 实例
        """
        selenium_config = self.config.get('selenium', {})
        network_config = self.config.get('network', {})
        
        # Chrome 选项
        chrome_options = ChromeOptions()
        
        # 无头模式
        if selenium_config.get('headless', True):
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
        
        # 窗口大小
        window_size = selenium_config.get('window_size', '1920x1080')
        chrome_options.add_argument(f'--window-size={window_size}')
        
        # 禁用扩展
        if selenium_config.get('disable_extensions', True):
            chrome_options.add_argument('--disable-extensions')
        
        # 其他优化选项
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        # User Agent
        user_agent = network_config.get('user_agent', 
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument(f'user-agent={user_agent}')
        
        # 代理设置
        proxy_config = network_config.get('proxy', {})
        if proxy_config.get('enabled', False):
            proxy_url = proxy_config.get('http', '')
            if proxy_url:
                self.logger.info(f"Selenium - 使用代理: {proxy_url}")
                # 移除协议前缀（Selenium 代理格式）
                proxy_address = proxy_url.replace('http://', '').replace('https://', '').replace('socks5://', '')
                
                # 根据代理类型设置
                proxy_type = proxy_config.get('type', 'http')
                if proxy_type == 'socks5':
                    chrome_options.add_argument(f'--proxy-server=socks5://{proxy_address}')
                else:
                    chrome_options.add_argument(f'--proxy-server={proxy_address}')
        
        # 用户数据目录
        user_data_dir = selenium_config.get('user_data_dir', '')
        if user_data_dir:
            chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
        
        # 配置文件目录
        profile_directory = selenium_config.get('profile_directory', '')
        if profile_directory:
            chrome_options.add_argument(f'--profile-directory={profile_directory}')
        
        # 实验性选项
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 禁用图片加载（加速）
        prefs = {
            'profile.managed_default_content_settings.images': 2,
            'profile.default_content_setting_values': {
                'notifications': 2
            }
        }
        chrome_options.add_experimental_option('prefs', prefs)
        
        try:
            # 使用 webdriver-manager 自动管理驱动
            chromedriver_path = selenium_config.get('chromedriver_path', '')
            
            if chromedriver_path:
                # 使用指定路径
                service = Service(chromedriver_path)
                self.logger.info(f"Selenium - 使用指定的 ChromeDriver: {chromedriver_path}")
            else:
                # 自动下载并使用
                self.logger.info("Selenium - 自动下载 ChromeDriver")
                service = Service(ChromeDriverManager().install())
            
            # 创建 WebDriver
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 设置超时时间
            page_load_timeout = selenium_config.get('page_load_timeout', 600)
            script_timeout = selenium_config.get('script_timeout', 300)
            driver.set_page_load_timeout(page_load_timeout)
            driver.set_script_timeout(script_timeout)
            
            # 隐藏 webdriver 特征
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
            self.logger.info("✅ Selenium - Chrome 浏览器启动成功")
            return driver
            
        except WebDriverException as e:
            self.logger.error(f"❌ Selenium - Chrome 浏览器启动失败: {e}")
            raise
    
    def get_page(self, url: str, wait_element: Optional[str] = None, 
                 wait_timeout: int = 10) -> bool:
        """
        访问页面并等待加载完成
        
        Args:
            url: 目标URL
            wait_element: 等待的元素选择器（CSS）
            wait_timeout: 等待超时时间（秒）
            
        Returns:
            是否成功加载
        """
        try:
            if not self.driver:
                self.driver = self.setup_driver()
            
            self.logger.info(f"Selenium - 访问页面: {url}")
            self.driver.get(url)
            
            # 如果指定了等待元素
            if wait_element:
                try:
                    WebDriverWait(self.driver, wait_timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_element))
                    )
                    self.logger.info(f"Selenium - 页面元素加载完成: {wait_element}")
                except TimeoutException:
                    self.logger.warning(f"Selenium - 等待元素超时: {wait_element}")
                    return False
            else:
                # 简单等待页面加载
                time.sleep(2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Selenium - 页面访问失败: {e}")
            return False
    
    def get_page_source(self) -> str:
        """
        获取当前页面源代码
        
        Returns:
            HTML 源代码
        """
        if self.driver:
            return self.driver.page_source
        return ""
    
    def scroll_to_bottom(self, pause_time: float = 1.0):
        """
        滚动到页面底部（用于加载动态内容）
        
        Args:
            pause_time: 每次滚动后的暂停时间
        """
        if not self.driver:
            return
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # 滚动到底部
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_time)
            
            # 计算新的高度
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    
    def click_next_page(self, next_selector: str) -> bool:
        """
        点击下一页按钮
        
        Args:
            next_selector: 下一页按钮的选择器
            
        Returns:
            是否成功点击
        """
        try:
            if not self.driver:
                return False
            
            next_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, next_selector))
            )
            next_button.click()
            time.sleep(2)  # 等待页面加载
            return True
            
        except Exception as e:
            self.logger.debug(f"Selenium - 无法点击下一页: {e}")
            return False
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Selenium - 浏览器已关闭")
            except Exception as e:
                self.logger.warning(f"Selenium - 关闭浏览器时出错: {e}")
            finally:
                self.driver = None
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


def create_selenium_helper(config: dict) -> Optional[SeleniumHelper]:
    """
    创建 Selenium 助手实例的工厂函数
    
    Args:
        config: 配置字典
        
    Returns:
        SeleniumHelper 实例，如果失败返回 None
    """
    try:
        helper = SeleniumHelper(config)
        return helper
    except Exception as e:
        logging.error(f"创建 Selenium 助手失败: {e}")
        return None
