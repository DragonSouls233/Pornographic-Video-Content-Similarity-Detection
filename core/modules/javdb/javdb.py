import os
import time
import random
import re
import requests
from typing import Set, Dict, List, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- JAVDB特定功能 ---
def fetch_with_requests_javdb(url: str, logger, max_pages: int = -1, config: dict = None,
                              smart_cache=None, model_name: str = None) -> Tuple[Set[str], Dict[str, str]]:
    """JAVDB专用的抓取，支持requests和Selenium，抓取视频标题和链接，支持翻页（支持增量更新）"""
    if config is None:
        config = {}
    
    # 检查是否使用 Selenium
    use_selenium = config.get('use_selenium', False)
    scraper = config.get('scraper', 'selenium')
    
    if use_selenium or scraper == 'selenium':
        try:
            return fetch_with_selenium_javdb(url, logger, max_pages, config, smart_cache, model_name)
        except Exception as e:
            logger.warning(f"  JAVDB - Selenium 抓取失败，回退到 requests: {e}")
            # 回退到 requests
            return fetch_with_requests_only_javdb(url, logger, max_pages, config, smart_cache, model_name)
    else:
        return fetch_with_requests_only_javdb(url, logger, max_pages, config, smart_cache, model_name)


def fetch_with_selenium_javdb(url: str, logger, max_pages: int = -1, config: dict = None,
                              smart_cache=None, model_name: str = None) -> Tuple[Set[str], Dict[str, str]]:
    """使用 Selenium 抓取 JAVDB 视频（支持增量更新）"""
    try:
        from ..common.selenium_helper import SeleniumHelper
    except ImportError:
        logger.error("  JAVDB - Selenium 助手模块未找到")
        raise
    
    all_titles = set()
    title_to_url = {}
    
    # 确定抓取范围（支持增量更新）
    start_page = 1
    if smart_cache and model_name:
        start_page, max_pages = smart_cache.get_incremental_fetch_range(model_name, max_pages)
        if start_page > 1:
            # 加载已缓存的标题
            cached_titles = smart_cache.get_cached_titles(model_name)
            all_titles.update(cached_titles)
            logger.info(f"  JAVDB - 增量模式，已加载 {len(cached_titles)} 个缓存标题")
    
    page_num = start_page
    consecutive_empty_pages = 0
    
    selenium = None
    try:
        # 创建 Selenium 助手
        selenium = SeleniumHelper(config)
        selenium.driver = selenium.setup_driver()
        
        logger.info("  JAVDB - 使用 Selenium 模式抓取")
        
        while True:
            # 检查该页是否需要更新（智能缓存）
            if smart_cache and model_name and page_num < start_page + 3:  # 只检查前3页
                if not smart_cache.should_update_page(model_name, page_num):
                    logger.debug(f"  JAVDB - 第 {page_num} 页在缓存有效期内，跳过")
                    page_num += 1
                    continue
            
            # 构建分页URL
            page_url = url
            if page_num > 1:
                if '?' in url:
                    page_url = f"{url}&page={page_num}"
                else:
                    page_url = f"{url}?page={page_num}"
            
            logger.info(f"  JAVDB - Selenium 抓取第 {page_num} 页: {page_url}")
            
            # 访问页面
            if not selenium.get_page(page_url, wait_element='a.video-title, .movie-title a, .film-title a, .title', wait_timeout=15):
                logger.warning(f"  JAVDB - Selenium 页面加载失败")
                break
            
            # 随机延时
            time.sleep(random.uniform(2.5, 4.5))
            
            # 获取页面源码
            page_source = selenium.get_page_source()
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 提取标题
            page_titles = set()
            page_videos = []  # 用于智能缓存
            
            # 选择器1: JAVDB特有的视频标题选择器
            for elem in soup.select('a.video-title, .movie-title a, .film-title a'):
                title = elem.get_text(strip=True)
                if title and len(title) > 3:
                    cleaned_title = clean_javdb_title(title, config.get('filename_clean_patterns', []))
                    page_titles.add(cleaned_title)
                    video_url = elem.get('href')
                    if video_url:
                        if not video_url.startswith('http'):
                            video_url = urljoin(url, video_url)
                        title_to_url[cleaned_title] = video_url
                        page_videos.append((cleaned_title, video_url))
            
            # 选择器2: 通用标题选择器
            if not page_titles:
                for elem in soup.select('.title, .video-title, h3.title'):
                    title = elem.get_text(strip=True)
                    if title and len(title) > 3:
                        cleaned_title = clean_javdb_title(title, config.get('filename_clean_patterns', []))
                        page_titles.add(cleaned_title)
                        link_elem = elem.find_parent('a')
                        if link_elem:
                            video_url = link_elem.get('href')
                            if video_url:
                                if not video_url.startswith('http'):
                                    video_url = urljoin(url, video_url)
                                title_to_url[cleaned_title] = video_url
                                page_videos.append((cleaned_title, video_url))
            
            if page_titles:
                prev_count = len(all_titles)
                all_titles.update(page_titles)
                new_titles = len(all_titles) - prev_count
                
                logger.info(f"  JAVDB - Selenium 第 {page_num} 页提取到 {len(page_titles)} 个标题（新增 {new_titles} 个）")
                
                # 更新智能缓存
                if smart_cache and model_name:
                    videos_with_page = [(title, url, page_num) for title, url in page_videos]
                    smart_cache.add_videos(model_name, videos_with_page)
                    smart_cache.update_page_timestamp(model_name, page_num)
                
                if page_num == 1 or page_num == start_page:
                    sample = list(page_titles)[:5]
                    for i, title in enumerate(sample, 1):
                        logger.info(f"    样本{i}: {title[:80]}{'...' if len(title) > 80 else ''}")
                
                consecutive_empty_pages = 0
            else:
                logger.warning(f"  JAVDB - Selenium 第 {page_num} 页未找到视频标题")
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= 2:
                    logger.info("  JAVDB - 连续2页无数据，停止抓取")
                    break
            
            # 检查是否有下一页
            next_buttons = soup.select('a.next, a[rel="next"], .pagination-next, .page-item.next a')
            has_next = False
            for button in next_buttons:
                text = button.get_text(strip=True).lower()
                if text in ['next', '>', '下一页', '下一頁']:
                    has_next = True
                    break
            
            if not has_next:
                logger.info("  JAVDB - Selenium 没有下一页，停止抓取")
                # 标记完整抓取完成
                if smart_cache and model_name:
                    smart_cache.mark_full_fetch_completed(model_name, page_num)
                break
            
            # 检查最大页数
            if max_pages > 0 and page_num >= max_pages:
                logger.info(f"  JAVDB - Selenium 达到最大页数限制 {max_pages}，停止抓取")
                break
            
            page_num += 1
        
    except Exception as e:
        logger.error(f"  JAVDB - Selenium 抓取失败: {e}")
        raise
    finally:
        if selenium:
            selenium.close()
    
    logger.info(f"  JAVDB - Selenium 总共提取到 {len(all_titles)} 个视频标题")
    return all_titles, title_to_url


def fetch_with_requests_only_javdb(url: str, logger, max_pages: int = -1, config: dict = None,
                                   smart_cache=None, model_name: str = None) -> Tuple[Set[str], Dict[str, str]]:
    """使用 requests 抓取 JAVDB 视频（支持增量更新）"""
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
    
    # 从配置中获取代理设置
    proxies = {}
    if config.get('network', {}).get('proxy', {}).get('enabled', False):
        http_proxy = config['network']['proxy'].get('http', '')
        https_proxy = config['network']['proxy'].get('https', '')
        if http_proxy:
            proxies['http'] = http_proxy
        if https_proxy:
            proxies['https'] = https_proxy
        logger.info(f"  JAVDB - 使用代理: {proxies}")
    
    all_titles = set()
    title_to_url = {}
    
    # 确定抓取范围（支持增量更新）
    start_page = 1
    if smart_cache and model_name:
        start_page, max_pages = smart_cache.get_incremental_fetch_range(model_name, max_pages)
        if start_page > 1:
            # 加载已缓存的标题
            cached_titles = smart_cache.get_cached_titles(model_name)
            all_titles.update(cached_titles)
            logger.info(f"  JAVDB - 增量模式，已加载 {len(cached_titles)} 个缓存标题")
    
    page_num = start_page
    consecutive_empty_pages = 0
    
    try:
        while True:
            # 检查该页是否需要更新（智能缓存）
            if smart_cache and model_name and page_num < start_page + 3:  # 只检查前3页
                if not smart_cache.should_update_page(model_name, page_num):
                    logger.debug(f"  JAVDB - 第 {page_num} 页在缓存有效期内，跳过")
                    page_num += 1
                    continue
            
            # 构建分页URL
            page_url = url
            if page_num > 1:
                if '?' in url:
                    page_url = f"{url}&page={page_num}"
                else:
                    page_url = f"{url}?page={page_num}"
            
            # 确保URL编码正确
            page_url = page_url.replace(' ', '%20')
            logger.info(f"  JAVDB - 抓取第 {page_num} 页: {page_url}")
            
            # 随机延时
            time.sleep(random.uniform(2.0, 4.0))  # JAVDB可能需要更长的延时
            
            try:
                resp = requests.get(page_url, headers=headers, timeout=20, proxies=proxies, verify=False)
                resp.raise_for_status()
                
                # 检查编码
                if resp.encoding.lower() != 'utf-8':
                    resp.encoding = 'utf-8'
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # JAVDB特定的选择器
                page_titles = set()
                page_videos = []  # 用于智能缓存
                
                # 选择器1: JAVDB特有的视频标题选择器
                for elem in soup.select('a.video-title, .movie-title a, .film-title a'):
                    title = elem.get_text(strip=True)
                    if title and len(title) > 3:
                        # 对在线标题应用清理流程
                        cleaned_title = clean_javdb_title(title, config.get('filename_clean_patterns', []))
                        page_titles.add(cleaned_title)
                        video_url = elem.get('href')
                        if video_url:
                            if not video_url.startswith('http'):
                                video_url = urljoin(url, video_url)
                            title_to_url[cleaned_title] = video_url
                            page_videos.append((cleaned_title, video_url))
                
                # 选择器2: 通用标题选择器
                if not page_titles:
                    for elem in soup.select('.title, .video-title, h3.title'):
                        title = elem.get_text(strip=True)
                        if title and len(title) > 3:
                            cleaned_title = clean_javdb_title(title, config.get('filename_clean_patterns', []))
                            page_titles.add(cleaned_title)
                            # 尝试找到父链接
                            link_elem = elem.find_parent('a')
                            if link_elem:
                                video_url = link_elem.get('href')
                                if video_url:
                                    if not video_url.startswith('http'):
                                        video_url = urljoin(url, video_url)
                                    title_to_url[cleaned_title] = video_url
                                    page_videos.append((cleaned_title, video_url))
                
                if page_titles:
                    prev_count = len(all_titles)
                    all_titles.update(page_titles)
                    new_titles = len(all_titles) - prev_count
                    
                    logger.info(f"  JAVDB - 第 {page_num} 页提取到 {len(page_titles)} 个标题（新增 {new_titles} 个）")
                    
                    # 更新智能缓存
                    if smart_cache and model_name:
                        videos_with_page = [(title, url, page_num) for title, url in page_videos]
                        smart_cache.add_videos(model_name, videos_with_page)
                        smart_cache.update_page_timestamp(model_name, page_num)
                    
                    # 显示样本
                    if page_num == 1 or page_num == start_page:
                        sample = list(page_titles)[:5]
                        for i, title in enumerate(sample, 1):
                            logger.info(f"    样本{i}: {title[:80]}{'...' if len(title) > 80 else ''}")
                    
                    consecutive_empty_pages = 0
                else:
                    logger.warning(f"  JAVDB - 第 {page_num} 页未找到视频标题")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 2:
                        logger.info("  JAVDB - 连续2页无数据，停止抓取")
                        break
                
                # 检查是否有下一页
                has_next = False
                
                # JAVDB特定的分页检查
                next_buttons = soup.select('a.next, a[rel="next"], .pagination-next, .page-item.next a')
                if next_buttons:
                    for button in next_buttons:
                        text = button.get_text(strip=True).lower()
                        href = button.get('href', '')
                        if text in ['next', '>', '下一页', '下一頁'] or 'page=' in href:
                            # 检查是否是最后一页
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
                
                # 尝试通用分页检查
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
                
                if not has_next:
                    logger.info("  JAVDB - 没有下一页，停止抓取")
                    # 标记完整抓取完成
                    if smart_cache and model_name:
                        smart_cache.mark_full_fetch_completed(model_name, page_num)
                    break
                
                # 检查最大页数
                if max_pages > 0 and page_num >= max_pages:
                    logger.info(f"  JAVDB - 达到最大页数限制 {max_pages}，停止抓取")
                    break
                
                page_num += 1
                
            except requests.exceptions.RequestException as e:
                logger.error(f"  JAVDB - 第 {page_num} 页请求失败: {e}")
                break
                
    except Exception as e:
        logger.error(f"  JAVDB - Requests抓取失败: {e}")
    
    logger.info(f"  JAVDB - 总共提取到 {len(all_titles)} 个视频标题")
    return all_titles, title_to_url

def clean_javdb_title(title: str, patterns: List[str]) -> str:
    """清理JAVDB视频标题"""
    # 先应用通用清理
    from ..common.common import clean_filename
    cleaned = clean_filename(title, patterns)
    
    # JAVDB特定的清理
    # 移除JAVDB特有的标记
    cleaned = re.sub(r'\b(javdb|JAVDB)\b', '', cleaned, flags=re.IGNORECASE)
    # 移除JAVDB特有的标签格式
    cleaned = re.sub(r'(?i)\[javdb\]\s*', '', cleaned)
    # 移除常见的JAV标记
    cleaned = re.sub(r'\b(JAV|jav)\b', '', cleaned, flags=re.IGNORECASE)
    # 再次清理空格
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def scan_javdb_models(config_models: dict, local_roots: List[str], video_exts: Set[str], 
                     clean_patterns: List[str], logger) -> List[Tuple[str, str, str, str]]:
    """
    扫描JAVDB格式的本地模特目录（不带前缀）
    返回(模特名, 模特根路径, 原始目录名, 国家)元组列表
    """
    from ..common.common import clean_filename
    
    matched = []
    
    for root in local_roots:
        root = os.path.normpath(root)
        
        if not os.path.exists(root):
            logger.warning(f"⚠ JAVDB - 路径不存在: {root}")
            continue
            
        logger.info(f"JAVDB - 扫描目录: {root}")
        
        try:
            # 递归扫描所有子目录
            for current_dir, _, subdirs in os.walk(root):
                # 检查当前目录是否是JAVDB格式的模特目录（不带前缀）
                dir_name = os.path.basename(current_dir)
                
                # 跳过根目录本身
                if current_dir == root:
                    logger.debug(f"  JAVDB - 跳过根目录: {dir_name}")
                    continue
                
                # 提取模特名
                model_name = None
                original_dir = dir_name
                
                # JAVDB格式：直接使用目录名作为模特名（不带前缀）
                if dir_name.startswith("[Channel] ") or re.match(r'^\[.*?\]\s+', dir_name):
                    # 跳过带前缀的目录
                    logger.debug(f"  JAVDB - 跳过带前缀的目录: {dir_name}")
                    continue
                else:
                    model_name = dir_name.strip()
                    logger.debug(f"  JAVDB - 提取模特名: {model_name} (从 {dir_name})")
                
                # 在配置中查找匹配的模特名
                matched_model = None
                for config_model in config_models.keys():
                    # 更灵活的匹配
                    config_lower = config_model.lower().replace(' ', '').replace('_', '').replace('-', '')
                    model_lower = model_name.lower().replace(' ', '').replace('_', '').replace('-', '')
                    
                    logger.debug(f"  JAVDB - 匹配测试: {model_name} vs {config_model}")
                    logger.debug(f"  JAVDB - 标准化: {model_lower} vs {config_lower}")
                    
                    if (model_lower == config_lower or 
                        model_lower in config_lower or 
                        config_lower in model_lower):
                        matched_model = config_model
                        logger.debug(f"  JAVDB - 匹配成功: {model_name} -> {matched_model}")
                        break
                
                # 如果没有精确匹配，尝试模糊匹配
                if not matched_model:
                    # 直接使用目录提取的模特名
                    matched_model = model_name
                    logger.debug(f"  JAVDB - 模糊匹配: 使用目录名作为模特名: {matched_model}")
                
                if matched_model:
                    # 提取国家信息：从路径中提取国家目录
                    relative_path = os.path.relpath(current_dir, root)
                    path_parts = relative_path.split(os.path.sep)
                    country = path_parts[0] if len(path_parts) > 0 else "未知国家"
                    matched.append((matched_model, current_dir, original_dir, country))
                    logger.info(f"  JAVDB - 找到本地模特: {matched_model} ({original_dir}) 在 {os.path.join(country, original_dir)}")
        except PermissionError:
            logger.error(f"  JAVDB - 权限不足，无法访问: {root}")
            continue
    
    logger.info(f"JAVDB - ✅ 共找到 {len(matched)} 个匹配的本地模特目录")
    return matched
