import os
import sys
import json
import yaml
import time
import random
import re
import logging
import traceback
import requests
from datetime import datetime
from pathlib import Path
from typing import Set, List, Tuple, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urlencode, parse_qs, parse_qsl

# --- 日志配置 ---
def setup_logging(log_dir: str, config_name: str = "main"):
    """配置日志系统，返回日志器"""
    Path(log_dir).mkdir(exist_ok=True)
    
    # 创建国家日志目录
    countries_dir = os.path.join(log_dir, "countries")
    Path(countries_dir).mkdir(exist_ok=True)
    
    # 主日志文件
    main_log_file = os.path.join(log_dir, f"sync_{datetime.now().strftime('%Y%m%d')}.log")
    
    # 缺失视频专用日志文件
    missing_log_file = os.path.join(log_dir, f"missing_{datetime.now().strftime('%Y%m%d')}.log")
    
    # 配置根日志器
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(main_log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # 创建专门记录缺失视频的日志器
    missing_logger = logging.getLogger('missing_logger')
    missing_logger.setLevel(logging.INFO)
    
    # 避免重复添加处理器
    if not missing_logger.handlers:
        missing_handler = logging.FileHandler(missing_log_file, encoding='utf-8')
        missing_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
        missing_logger.addHandler(missing_handler)
    
    return logging.getLogger(__name__), missing_logger, countries_dir

# --- 配置加载 ---
def load_config(config_path: str = "config.yaml") -> dict:
    """加载YAML配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_text = f.read()
            config_text = config_text.replace('\\', '\\\\')
            return yaml.safe_load(config_text)
    except Exception as e:
        print(f"配置文件加载失败: {e}")
        sys.exit(1)

def load_models(model_path: str = "models.json") -> dict:
    """加载模特配置JSON文件"""
    try:
        with open(model_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"模特配置文件加载失败: {e}")
        sys.exit(1)

# --- 缓存管理 --- 
def get_cache_dir(config: dict) -> str:
    """获取缓存目录路径"""
    cache_dir = os.path.join(config['output_dir'], 'cache')
    Path(cache_dir).mkdir(exist_ok=True)
    return cache_dir

def get_model_cache_path(cache_dir: str, model_name: str) -> str:
    """获取模特缓存文件路径"""
    # 生成安全的文件名
    safe_model_name = re.sub(r'[^\w\-]', '_', model_name)
    return os.path.join(cache_dir, f"{safe_model_name}.json")

def load_cache(cache_path: str) -> Set[str]:
    """加载缓存文件"""
    if not os.path.exists(cache_path):
        return set()
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get('video_titles', []))
    except Exception as e:
        logging.warning(f"加载缓存失败: {e}")
        return set()

def save_cache(cache_path: str, video_titles: Set[str], model_name: str, url: str):
    """保存缓存文件"""
    try:
        data = {
            'model_name': model_name,
            'url': url,
            'video_titles': list(video_titles),
            'last_updated': datetime.now().isoformat()
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"保存缓存失败: {e}")

# --- 简化版本：使用基础功能，修复翻页 ---
def fetch_with_requests_simple(url: str, logger, max_pages: int = -1, config: dict = None) -> Tuple[Set[str], Dict[str, str]]:
    """简化的requests抓取，抓取视频标题和链接，支持翻页"""
    if config is None:
        config = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    all_titles = set()
    title_to_url = {}
    page_num = 1
    
    try:
        while True:
            # 构建分页URL
            page_url = url
            if page_num > 1:
                if '?' in url:
                    page_url = f"{url}&page={page_num}"
                else:
                    page_url = f"{url}?page={page_num}"
            
            # 确保URL编码正确
            page_url = page_url.replace(' ', '%20')
            logger.info(f"  抓取第 {page_num} 页: {page_url}")
            
            # 随机延时
            time.sleep(random.uniform(1.5, 3.0))
            
            try:
                resp = requests.get(page_url, headers=headers, timeout=15)
                resp.raise_for_status()
                
                # 检查编码
                if resp.encoding.lower() != 'utf-8':
                    resp.encoding = 'utf-8'
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 查找视频标题和链接 - 多种选择器
                page_titles = set()
                
                # 选择器1: thumbnailTitle类
                for elem in soup.select('a.thumbnailTitle'):
                    title = elem.get_text(strip=True)
                    if title and len(title) > 3:
                        # 对在线标题应用与本地文件相同的清理流程
                        cleaned_title = clean_filename(title, config.get('filename_clean_patterns', []))
                        page_titles.add(cleaned_title)
                        video_url = elem.get('href')
                        if video_url:
                            if not video_url.startswith('http'):
                                video_url = urljoin(url, video_url)
                            title_to_url[cleaned_title] = video_url
                
                # 选择器2: 标题类
                if not page_titles:
                    for elem in soup.select('.title, .video-title, h3.title'):
                        title = elem.get_text(strip=True)
                        if title and len(title) > 3:
                            # 对在线标题应用与本地文件相同的清理流程
                            cleaned_title = clean_filename(title, config.get('filename_clean_patterns', []))
                            page_titles.add(cleaned_title)
                            # 尝试找到父链接
                            link_elem = elem.find_parent('a')
                            if link_elem:
                                video_url = link_elem.get('href')
                                if video_url:
                                    if not video_url.startswith('http'):
                                        video_url = urljoin(url, video_url)
                                    title_to_url[cleaned_title] = video_url
                
                # 选择器3: 视频项中的标题
                if not page_titles:
                    for item in soup.select('.videoBox, .videoItem, .pcVideoListItem'):
                        title_elem = item.select_one('.title, a[title], .videoTitle')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if title and len(title) > 3:
                                # 对在线标题应用与本地文件相同的清理流程
                                cleaned_title = clean_filename(title, config.get('filename_clean_patterns', []))
                                page_titles.add(cleaned_title)
                                # 尝试找到视频链接
                                link_elem = item.select_one('a')
                                if link_elem:
                                    video_url = link_elem.get('href')
                                    if video_url:
                                        if not video_url.startswith('http'):
                                            video_url = urljoin(url, video_url)
                                        title_to_url[cleaned_title] = video_url
                
                if page_titles:
                    prev_count = len(all_titles)
                    all_titles.update(page_titles)
                    new_titles = len(all_titles) - prev_count
                    
                    logger.info(f"  第 {page_num} 页提取到 {len(page_titles)} 个标题（新增 {new_titles} 个）")
                    
                    # 显示样本
                    if page_num == 1:
                        sample = list(page_titles)[:5]
                        for i, title in enumerate(sample, 1):
                            logger.info(f"    样本{i}: {title[:80]}{'...' if len(title) > 80 else ''}")
                else:
                    logger.warning(f"  第 {page_num} 页未找到视频标题")
                    # 如果连续2页没有标题，停止
                    if page_num > 1:
                        break
                
                # 检查是否有下一页
                has_next = False
                
                # 方法1: 查找分页按钮
                next_buttons = soup.select('a.next, a[rel="next"], li.next a, .pagination_next, .orangeButton')
                if next_buttons:
                    for button in next_buttons:
                        text = button.get_text(strip=True).lower()
                        href = button.get('href', '')
                        if text in ['next', '>', '下一页'] or 'page=' in href:
                            # 检查是否是最后一页
                            # 如果按钮存在但链接指向当前页或没有page参数，说明是最后一页
                            if 'page=' in href:
                                # 提取page参数值
                                page_param = href.split('page=')[-1].split('&')[0]
                                if page_param.isdigit():
                                    # 如果page参数值小于等于当前页，说明是最后一页
                                    if int(page_param) <= page_num:
                                        continue
                            # 检查按钮是否可见或可用
                            style = button.get('style', '')
                            if 'display: none' in style or 'visibility: hidden' in style:
                                continue
                            has_next = True
                            break
                
                # 方法2: 查找分页器
                if not has_next:
                    pagination = soup.select_one('.pagination, .pages, .pageNumbers, .pagination.pagination-themed')
                    if pagination:
                        # 查找当前页和最大页
                        page_links = pagination.select('a')
                        page_numbers = []
                        for link in page_links:
                            text = link.get_text(strip=True)
                            if text.isdigit():
                                page_numbers.append(int(text))
                        
                        if page_numbers:
                            max_page = max(page_numbers)
                            if page_num < max_page:
                                has_next = True
                        
                        # 检查是否有下一页按钮
                        next_page_li = pagination.select_one('li.page_next')
                        if next_page_li:
                            # 检查下一页按钮是否可用
                            if 'disabled' not in next_page_li.get('class', []) and 'inactive' not in next_page_li.get('class', []):
                                has_next = True
                
                # 方法3: 查找特定的分页结构
                if not has_next:
                    pagination = soup.select_one('.pagination.pagination-themed')
                    if pagination:
                        next_link = pagination.select_one('a.orangeButton')
                        if next_link and 'page=' in next_link.get('href', ''):
                            # 检查是否是最后一页
                            href = next_link.get('href', '')
                            if 'page=' in href:
                                # 提取page参数值
                                page_param = href.split('page=')[-1].split('&')[0]
                                if page_param.isdigit():
                                    # 如果page参数值小于等于当前页，说明是最后一页
                                    if int(page_param) <= page_num:
                                        has_next = False
                                    else:
                                        has_next = True
                                else:
                                    has_next = True
                            else:
                                has_next = True
                
                # 方法4: 检查是否有视频结果
                if has_next:
                    # 如果当前页没有视频，说明已经到最后一页
                    if not page_titles:
                        has_next = False
                        logger.info("  当前页没有视频，停止抓取")
                
                if not has_next:
                    logger.info("  没有下一页，停止抓取")
                    break
                
                # 检查最大页数
                if max_pages > 0 and page_num >= max_pages:
                    logger.info(f"  达到最大页数限制 {max_pages}，停止抓取")
                    break
                
                page_num += 1
                
            except requests.exceptions.RequestException as e:
                logger.error(f"  第 {page_num} 页请求失败: {e}")
                break
                
    except Exception as e:
        logger.error(f"  Requests抓取失败: {e}")
    
    logger.info(f"  总共提取到 {len(all_titles)} 个视频标题")
    return all_titles, title_to_url

def fetch_with_selenium_simple(url: str, logger, max_pages: int = -1, config: dict = None) -> Tuple[Set[str], Dict[str, str]]:
    """简化的Selenium抓取，抓取视频标题和链接，支持翻页"""
    if config is None:
        config = {}
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException
        
        logger.info(f"  使用Selenium抓取: {url}")
        
        # 简化配置
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        driver = webdriver.Chrome(options=options)
        
        all_titles = set()
        title_to_url = {}
        page_num = 1
        
        try:
            while True:
                # 构建分页URL
                page_url = url
                if page_num > 1:
                    if '?' in url:
                        page_url = f"{url}&page={page_num}"
                    else:
                        page_url = f"{url}?page={page_num}"
                
                # 确保URL编码正确
                page_url = page_url.replace(' ', '%20')
                logger.info(f"  访问第 {page_num} 页: {page_url}")
                driver.get(page_url)
                
                # 等待页面加载
                try:
                    wait = WebDriverWait(driver, 10)
                    # 等待页面基本元素
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    
                    # 等待视频相关元素
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".videoSection, .videoBox, .thumbnailTitle, .title")))
                    except:
                        pass
                    
                    time.sleep(1)  # 额外等待
                    
                except TimeoutException:
                    logger.warning(f"  第 {page_num} 页加载超时")
                
                # 获取页面内容
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # 查找视频标题和链接
                page_titles = set()
                
                # 选择器1: thumbnailTitle类
                for elem in soup.select('a.thumbnailTitle'):
                    title = elem.get_text(strip=True)
                    if title and len(title) > 3:
                        # 对在线标题应用与本地文件相同的清理流程
                        cleaned_title = clean_filename(title, config.get('filename_clean_patterns', []))
                        page_titles.add(cleaned_title)
                        video_url = elem.get('href')
                        if video_url:
                            if not video_url.startswith('http'):
                                video_url = urljoin(url, video_url)
                            title_to_url[cleaned_title] = video_url
                
                # 选择器2: 标题类
                if not page_titles:
                    for elem in soup.select('.title, .video-title, h3.title'):
                        title = elem.get_text(strip=True)
                        if title and len(title) > 3:
                            # 对在线标题应用与本地文件相同的清理流程
                            cleaned_title = clean_filename(title, config.get('filename_clean_patterns', []))
                            page_titles.add(cleaned_title)
                            # 尝试找到父链接
                            link_elem = elem.find_parent('a')
                            if link_elem:
                                video_url = link_elem.get('href')
                                if video_url:
                                    if not video_url.startswith('http'):
                                        video_url = urljoin(url, video_url)
                                    title_to_url[cleaned_title] = video_url
                
                if page_titles:
                    prev_count = len(all_titles)
                    all_titles.update(page_titles)
                    new_titles = len(all_titles) - prev_count
                    
                    logger.info(f"  第 {page_num} 页提取到 {len(page_titles)} 个标题（新增 {new_titles} 个）")
                    
                    # 显示样本
                    if page_num == 1:
                        sample = list(page_titles)[:5]
                        for i, title in enumerate(sample, 1):
                            logger.info(f"    样本{i}: {title[:80]}{'...' if len(title) > 80 else ''}")
                else:
                    logger.warning(f"  第 {page_num} 页未找到视频标题")
                    # 如果连续2页没有标题，停止
                    if page_num > 1:
                        break
                
                # 检查是否有下一页
                has_next = False
                
                try:
                    # 查找下一页按钮
                    next_selectors = ['a.next', 'a[rel="next"]', '.nextPage', '.pagination_next', '.orangeButton']
                    for selector in next_selectors:
                        next_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                        if next_buttons:
                            for button in next_buttons:
                                if button.is_displayed() and button.is_enabled():
                                    text = button.text.strip().lower()
                                    href = button.get_attribute('href') or ''
                                    if text in ['next', '>', '下一页'] or 'page=' in href:
                                        # 检查是否是最后一页
                                        # 如果按钮存在但链接指向当前页或没有page参数，说明是最后一页
                                        if 'page=' in href:
                                            # 提取page参数值
                                            page_param = href.split('page=')[-1].split('&')[0]
                                            if page_param.isdigit():
                                                # 如果page参数值小于等于当前页，说明是最后一页
                                                if int(page_param) <= page_num:
                                                    continue
                                        # 检查按钮是否可见或可用
                                        style = button.get_attribute('style') or ''
                                        if 'display: none' in style or 'visibility: hidden' in style:
                                            continue
                                        has_next = True
                                        break
                            if has_next:
                                break
                except:
                    pass
                
                # 尝试通过页面内容检查分页
                if not has_next:
                    try:
                        # 查找分页器
                        pagination = driver.find_element(By.CSS_SELECTOR, '.pagination, .pages, .pageNumbers, .pagination.pagination-themed')
                        if pagination:
                            # 查找页码链接
                            page_links = pagination.find_elements(By.TAG_NAME, 'a')
                            page_numbers = []
                            for link in page_links:
                                text = link.text.strip()
                                if text.isdigit():
                                    page_numbers.append(int(text))
                            
                            if page_numbers:
                                max_page = max(page_numbers)
                                if page_num < max_page:
                                    has_next = True
                            
                            # 检查是否有下一页按钮
                            try:
                                next_page_li = pagination.find_element(By.CSS_SELECTOR, 'li.page_next')
                                if next_page_li:
                                    # 检查下一页按钮是否可用
                                    classes = next_page_li.get_attribute('class') or ''
                                    if 'disabled' not in classes and 'inactive' not in classes:
                                        has_next = True
                            except:
                                pass
                    except:
                        pass
                
                # 特殊处理：检查分页器中的页码元素
                if not has_next:
                    try:
                        # 查找所有页码元素
                        page_elements = driver.find_elements(By.CSS_SELECTOR, '.pagination li, .pages li, .pageNumbers li')
                        current_page_found = False
                        next_page_available = False
                        
                        for elem in page_elements:
                            text = elem.text.strip()
                            if text.isdigit():
                                if current_page_found:
                                    # 如果已经找到当前页，且下一个元素是页码，则说明有下一页
                                    next_page_available = True
                                    break
                                if 'current' in elem.get_attribute('class') or 'active' in elem.get_attribute('class'):
                                    current_page_found = True
                        
                        if next_page_available:
                            has_next = True
                    except:
                        pass
                
                # 方法4: 检查是否有视频结果
                if has_next:
                    # 如果当前页没有视频，说明已经到最后一页
                    if not page_titles:
                        has_next = False
                        logger.info("  当前页没有视频，停止抓取")
                
                if not has_next:
                    logger.info("  没有下一页，停止抓取")
                    break
                
                # 检查最大页数
                if max_pages > 0 and page_num >= max_pages:
                    logger.info(f"  达到最大页数限制 {max_pages}，停止抓取")
                    break
                
                page_num += 1
                
                # 页面间延时
                time.sleep(random.uniform(2.0, 3.5))
                    
        except Exception as e:
            logger.error(f"  Selenium抓取过程出错: {e}")
        
        finally:
            driver.quit()
        
        logger.info(f"  (Selenium) 总共提取到 {len(all_titles)} 个视频标题")
        return all_titles, title_to_url
        
    except ImportError:
        logger.error("  Selenium未安装，请运行: pip install selenium")
        return set(), {}
    except Exception as e:
        logger.error(f"  Selenium初始化失败: {e}")
        return set(), {}

# --- 本地文件处理（支持多层文件夹）---
def clean_filename(name: str, patterns: List[str]) -> str:
    """清理文件名中的干扰项"""
    original_name = name
    
    for pat in patterns:
        try:
            name = re.sub(pat, '', name, flags=re.IGNORECASE)
        except re.error as e:
            logging.debug(f"正则表达式错误 '{pat}': {e}")
    
    cleaned = name.strip()
    
    # 移除多余的空格和分隔符
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'[_\-\.]+', ' ', cleaned)
    cleaned = cleaned.strip(' _-.')
    
    # 移除常见的视频标识
    # 先移除文件名开头的[模特名]前缀
    cleaned = re.sub(r'^\[.*?\]\s*', '', cleaned)
    # 再移除末尾的哈希值或其他标识
    cleaned = re.sub(r'\s*\([^\)]*?\)\s*$', '', cleaned)
    
    # 全面的字符统一处理
    # 1. 全角转半角
    full_to_half = {}
    for i in range(0xFF01, 0xFF5F + 1):
        full_to_half[chr(i)] = chr(i - 0xFEE0)
    # 特殊处理空格
    full_to_half['　'] = ' '
    # 应用全角转半角
    cleaned = ''.join([full_to_half.get(c, c) for c in cleaned])
    
    # 2. 特殊字符统一
    # 统一处理破折号：将所有类型的破折号转换为标准的hyphen
    cleaned = re.sub(r'[\u2013\u2014\u2015]', '-', cleaned)
    # 统一处理引号：将所有类型的引号转换为标准的单引号
    cleaned = re.sub(r'[\u2018\u2019\u201c\u201d]', "'", cleaned)
    # 统一处理省略号：将所有类型的省略号转换为标准的三个点
    cleaned = re.sub(r'[\u2026]', '...', cleaned)
    # 统一处理斜杠：将全角斜杠转换为半角斜杠
    cleaned = re.sub(r'[\uFF0F]', '/', cleaned)
    
    # 3. 空格和分隔符标准化
    # 统一处理空格：将多个连续空格替换为单个空格
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # 移除分辨率和视频质量标识
    cleaned = re.sub(r'\d{3,4}[xp]\d{3,4}', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\d{3,4}p', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(hd|fhd|uhd|4k|fullhd)\b', '', cleaned, flags=re.IGNORECASE)
    # 移除多余的空格和分隔符
    cleaned = re.sub(r'[\s_\-\.]+', ' ', cleaned)
    cleaned = cleaned.strip(' _-.')
    
    if original_name != cleaned:
        logging.debug(f"清理文件名: '{original_name}' -> '{cleaned}'")
    
    return cleaned.strip()

def scan_local_models(config_models: dict, local_roots: List[str], video_exts: Set[str], 
                     clean_patterns: List[str], logger) -> List[Tuple[str, str, str, str]]:
    """
    扫描本地模特目录，支持多层文件夹结构
    返回(模特名, 模特根路径, 原始目录名, 国家)元组列表
    """
    matched = []
    
    for root in local_roots:
        root = os.path.normpath(root)
        
        if not os.path.exists(root):
            logger.warning(f"⚠ 路径不存在: {root}")
            continue
            
        logger.info(f"扫描目录: {root}")
        
        try:
            # 递归扫描所有子目录
            for current_dir, _, subdirs in os.walk(root):
                # 检查当前目录是否是模特目录
                dir_name = os.path.basename(current_dir)
                
                # 提取模特名
                model_name = None
                original_dir = dir_name
                
                # 匹配 [Channel] 前缀
                if dir_name.startswith("[Channel] "):
                    model_name = dir_name[len("[Channel] "):].strip()
                elif re.match(r'^\[.*?\]\s+', dir_name):
                    model_name = re.sub(r'^\[.*?\]\s+', '', dir_name).strip()
                else:
                    # 跳过非 [Channel] 格式的目录，避免在根目录匹配错误
                    continue
                
                # 在配置中查找匹配的模特名
                matched_model = None
                for config_model in config_models.keys():
                    # 更灵活的匹配
                    config_lower = config_model.lower().replace(' ', '').replace('_', '').replace('-', '')
                    model_lower = model_name.lower().replace(' ', '').replace('_', '').replace('-', '')
                    
                    if (model_lower == config_lower or 
                        model_lower in config_lower or 
                        config_lower in model_lower):
                        matched_model = config_model
                        break
                
                if matched_model:
                    # 提取国家信息：从路径中提取国家目录
                    # 路径格式: root/国家/[Channel] 模特名
                    relative_path = os.path.relpath(current_dir, root)
                    path_parts = relative_path.split(os.path.sep)
                    country = path_parts[0] if len(path_parts) > 0 else "未知国家"
                    matched.append((matched_model, current_dir, original_dir, country))
                    logger.info(f"  找到本地模特: {matched_model} ({original_dir}) 在 {os.path.join(country, original_dir)}")
        except PermissionError:
            logger.error(f"  权限不足，无法访问: {root}")
            continue
    
    logger.info(f"✅ 共找到 {len(matched)} 个匹配的本地模特目录")
    return matched

def extract_local_videos(folder: str, video_exts: Set[str], 
                        clean_patterns: List[str]) -> Set[str]:
    """
    提取本地视频文件，支持多层文件夹结构
    递归扫描子文件夹中的所有视频文件
    """
    videos = set()
    
    if not os.path.exists(folder):
        return videos
    
    # 递归扫描所有子目录
    for root_dir, _, files in os.walk(folder):
        for file in files:
            name, ext = os.path.splitext(file)
            
            if ext.lower() in video_exts:
                cleaned = clean_filename(name, clean_patterns)
                if cleaned:
                    videos.add(cleaned)
                else:
                    # 如果清理后为空，使用原始名称
                    cleaned_name = name.strip()
                    cleaned_name = re.sub(r'[\[\]\(\)].*?[\[\]\(\)]', '', cleaned_name)
                    videos.add(cleaned_name)
    
    return videos

def record_missing_videos(model_name: str, url: str, missing_titles: List[Tuple[str, str]], 
                         missing_logger, logger, local_count=0, online_count=0):
    """记录缺失视频到专用日志文件"""
    if not missing_titles and not online_count:
        return
    
    missing_logger.info("=" * 60)
    missing_logger.info(f"模特: {model_name}")
    missing_logger.info(f"链接: {url}")
    if online_count > 0:
        missing_logger.info(f"缺失视频数量: {len(missing_titles)}")
        missing_logger.info(f"总视频数量: {online_count} | 本地视频: {local_count} | 缺失视频: {len(missing_titles)}")
    else:
        missing_logger.info(f"缺失视频数量: {len(missing_titles)}")
    missing_logger.info("-" * 40)
    
    for i, (title, video_url) in enumerate(missing_titles, 1):
        if video_url:
            missing_logger.info(f"{i:3d}. {title}")
            missing_logger.info(f"    链接: {video_url}")
        else:
            missing_logger.info(f"{i:3d}. {title}")
    
    missing_logger.info("=" * 60 + "\n")
    logger.warning(f"  🔴 缺失 {len(missing_titles)} 个视频，已记录到缺失日志")

# --- 主程序 ---
def main():
    """主程序入口"""
    try:
        # 加载配置
        config = load_config()
        models = load_models()
        
        # 设置日志
        logger, missing_logger, countries_dir = setup_logging(config['log_dir'])
        
        logger.info("🚀 启动批量模特视频同步检查系统（简化修复版）")
        logger.info("=" * 60)
        logger.info(f"配置文件: config.yaml")
        logger.info(f"模特数量: {len(models)}")
        logger.info(f"本地目录: {config['local_roots']}")
        logger.info(f"输出目录: {config['output_dir']}")
        logger.info(f"使用Selenium: {config.get('use_selenium', True)}")
        logger.info(f"最大翻页: {config.get('max_pages', '无限制')}")
        logger.info("=" * 60)
        
        # 创建输出目录
        Path(config['output_dir']).mkdir(exist_ok=True)
        
        # 获取缓存目录
        cache_dir = get_cache_dir(config)
        logger.info(f"缓存目录: {cache_dir}")
        
        # 扫描本地模特目录
        local_matches = scan_local_models(
            models, 
            config['local_roots'], 
            set(config['video_extensions']), 
            config['filename_clean_patterns'],
            logger
        )
        
        if not local_matches:
            logger.error("❌ 未找到匹配的本地模特目录，程序退出")
            logger.info("提示: 确保本地目录包含以 '[Channel] 模特名' 格式命名的文件夹")
            return
        
        all_missing = []
        processed_count = 0
        error_count = 0
        
        # 处理每个本地模特
        for i, (model_name, folder, original_dir, country) in enumerate(local_matches, 1):
            logger.info(f"\n[{i}/{len(local_matches)}] 处理模特: {model_name} (国家: {country})")
            logger.info(f"  本地目录: {original_dir}")
            logger.info(f"  完整路径: {folder}")
            
            # 创建国家目录
            country_dir = os.path.join(countries_dir, country)
            Path(country_dir).mkdir(exist_ok=True)
            
            # 提取本地视频（支持多层文件夹）
            local_set = extract_local_videos(
                folder, 
                set(config['video_extensions']), 
                config['filename_clean_patterns']
            )
            
            logger.info(f"  本地视频文件: {len(local_set)} 个")
            
            if local_set:
                sample = list(local_set)[:5]
                logger.info(f"  本地样本:")
                for idx, title in enumerate(sample, 1):
                    logger.info(f"    {idx}. {title[:80]}{'...' if len(title) > 80 else ''}")
            else:
                logger.warning(f"  ⚠ 本地目录中没有找到视频文件")
            
            # 获取模特URL
            url = models.get(model_name)
            if not url:
                logger.error(f"  ❌ 配置中未找到模特 '{model_name}' 的URL")
                error_count += 1
                continue
            
            logger.info(f"  在线链接: {url}")
            
            # 生成缓存路径并加载缓存
            cache_path = get_model_cache_path(cache_dir, model_name)
            cached_titles = load_cache(cache_path)
            logger.info(f"  缓存文件: {os.path.basename(cache_path)}")
            logger.info(f"  已缓存标题: {len(cached_titles)} 个")
            
            # 延时策略
            if i > 1 and config.get('delay_between_pages'):
                min_delay = config['delay_between_pages'].get('min', 2.0)
                max_delay = config['delay_between_pages'].get('max', 3.5)
                delay = random.uniform(min_delay, max_delay)
                logger.info(f"  ⏳ 随机延时 {delay:.1f} 秒")
                time.sleep(delay)
            
            # 抓取在线视频标题
            online_set = set()
            use_selenium = config.get('use_selenium', True)
            max_pages = config.get('max_pages', -1)
            
            max_retries = config.get('retry_on_fail', 2)
            online_set = set()
            title_to_url = {}
            new_videos = set()
            
            for attempt in range(max_retries + 1):
                try:
                    if use_selenium:
                        online_set, title_to_url = fetch_with_selenium_simple(url, logger, max_pages, config)
                    else:
                        online_set, title_to_url = fetch_with_requests_simple(url, logger, max_pages, config)
                    
                    if online_set:
                        # 过滤出未缓存的新视频
                        new_videos = online_set - cached_titles
                        logger.info(f"  成功获取在线标题: {len(online_set)} 个")
                        logger.info(f"  新视频标题: {len(new_videos)} 个")
                        break
                    
                    if attempt < max_retries:
                        retry_delay = (attempt + 1) * 5
                        logger.warning(f"  第 {attempt + 1} 次尝试失败，{retry_delay}秒后重试...")
                        time.sleep(retry_delay)
                        
                except Exception as e:
                    logger.error(f"  抓取失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                    if attempt < max_retries:
                        time.sleep(5)
            
            if not online_set:
                logger.error(f"  ❌ 获取在线标题失败，跳过此模特")
                error_count += 1
                continue
            
            # 对比找出缺失视频（只检查新视频）
            missing = new_videos - local_set
            processed_count += 1
            
            # 更新缓存
            updated_titles = cached_titles.union(online_set)
            save_cache(cache_path, updated_titles, model_name, url)
            logger.info(f"  🔄 缓存已更新，共 {len(updated_titles)} 个标题")
            
            if missing:
                sorted_missing = sorted(list(missing))
                # 构建缺失视频列表，包含标题和链接
                missing_with_urls = []
                for title in sorted_missing:
                    video_url = title_to_url.get(title, "")
                    missing_with_urls.append((title, video_url))
                
                all_missing.append({
                    "model": model_name,
                    "url": url,
                    "local_folder": original_dir,
                    "local_count": len(local_set),
                    "online_count": len(online_set),
                    "new_videos_count": len(new_videos),
                    "missing_count": len(missing),
                    "missing_titles": sorted_missing,
                    "missing_with_urls": missing_with_urls
                })
                
                # 记录缺失视频
                record_missing_videos(model_name, url, missing_with_urls, missing_logger, logger, 
                                    local_count=len(local_set), online_count=len(online_set))
                
                logger.info(f"  🔴 发现 {len(missing)} 个缺失视频")
                logger.info(f"  📊 统计: 在线 {len(online_set)} 个 | 新视频 {len(new_videos)} 个 | 本地 {len(local_set)} 个 | 缺失 {len(missing)} 个")
                
                # 按照国家和模特结构保存日志
                country_model_dir = os.path.join(countries_dir, country, model_name)
                Path(country_model_dir).mkdir(exist_ok=True)
                
                # 保存国家-模特的详细报告
                country_model_report = os.path.join(country_model_dir, f"{model_name}_report_{datetime.now().strftime('%Y%m%d')}.txt")
                with open(country_model_report, 'w', encoding='utf-8') as f:
                    f.write("=" * 60 + "\n")
                    f.write(f"模特: {model_name}\n")
                    f.write(f"国家: {country}\n")
                    f.write(f"链接: {url}\n")
                    f.write(f"本地目录: {original_dir}\n")
                    f.write(f"完整路径: {folder}\n")
                    f.write(f"统计: 在线 {len(online_set)} 个 | 新视频 {len(new_videos)} 个 | 本地 {len(local_set)} 个 | 缺失 {len(missing)} 个\n")
                    f.write("=" * 60 + "\n\n")
                    
                    if missing:
                        f.write("缺失视频列表:\n")
                        f.write("-" * 40 + "\n")
                        for i, (title, video_url) in enumerate(missing_with_urls, 1):
                            f.write(f"{i:3d}. {title}\n")
                            if video_url:
                                f.write(f"    链接: {video_url}\n")
                        f.write("\n" + "=" * 60 + "\n")
                    else:
                        f.write("✅ 本地视频完整，无缺失\n")
                        f.write("\n" + "=" * 60 + "\n")
                
                logger.info(f"  📁 国家-模特报告已保存: {country_model_report}")
            else:
                logger.info("  ✅ 本地视频完整，无缺失")
        
        # 输出总结报告
        logger.info("\n" + "=" * 60)
        logger.info("处理完成！")
        logger.info(f"✅ 成功处理: {processed_count} 个模特")
        logger.info(f"❌ 处理失败: {error_count} 个模特")
        logger.info(f"🔴 发现缺失: {len(all_missing)} 个模特有缺失视频")
        
        # 如果有缺失，生成输出文件
        if all_missing:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 1. 生成TXT格式的缺失清单
            txt_path = os.path.join(config['output_dir'], f"missing_summary_{timestamp}.txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("缺失视频清单\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                for item in all_missing:
                    f.write(f"[{item['model']}]\n")
                    f.write(f"本地目录: {item['local_folder']}\n")
                    f.write(f"在线链接: {item['url']}\n")
                    f.write(f"统计: 本地 {item['local_count']} 个 | 在线 {item['online_count']} 个 | 新视频 {item.get('new_videos_count', 0)} 个 | 缺失 {item['missing_count']} 个\n")
                    f.write("-" * 50 + "\n")
                    
                    for i, (title, video_url) in enumerate(item.get('missing_with_urls', []), 1):
                        f.write(f"{i:3d}. {title}\n")
                        if video_url:
                            f.write(f"    链接: {video_url}\n")
                    
                    f.write("\n" + "=" * 60 + "\n\n")
            
            # 2. 生成JSON格式的详细报告
            json_path = os.path.join(config['output_dir'], f"missing_detail_{timestamp}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "generated_at": datetime.now().isoformat(),
                    "total_models_processed": processed_count,
                    "models_with_missing": len(all_missing),
                    "missing_details": all_missing
                }, f, ensure_ascii=False, indent=2)
            
            # 3. 生成简化的当前缺失文件
            current_txt_path = os.path.join(config['output_dir'], "missing_current.txt")
            with open(current_txt_path, 'w', encoding='utf-8') as f:
                for item in all_missing:
                    f.write(f"#{item['model']}#{item['url']}\n")
                    for title in item['missing_titles']:
                        f.write(f"{title}\n")
                    f.write("\n")
            
            logger.info(f"📄 详细报告已保存: {txt_path}")
            logger.info(f"📄 JSON数据已保存: {json_path}")
            logger.info(f"📄 当前缺失清单: {current_txt_path}")
            
        else:
            logger.info("🎉 恭喜！所有模特的本地视频都完整无缺！")
        
        logger.info(f"📁 日志文件位置: {config['log_dir']}")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\n⚠ 用户中断程序执行")
    except Exception as e:
        logger.critical(f"❌ 程序执行错误: {e}")
        logger.critical(f"详细错误信息:\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()