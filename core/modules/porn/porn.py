import os
import time
import random
import re
import requests
from typing import Set, Dict, List, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- PORN特定功能 ---
def fetch_with_requests_porn(url: str, logger, max_pages: int = -1, config: dict = None,
                                smart_cache=None, model_name: str = None) -> Tuple[Set[str], Dict[str, str]]:
    """PORN专用的抓取，支持requests和Selenium，抓取视频标题和链接，支持翻页（支持增量更新）"""
    if config is None:
        config = {}
    
    # 检查是否使用 Selenium
    use_selenium = config.get('use_selenium', False)
    scraper = config.get('scraper', 'selenium')
    
    if use_selenium or scraper == 'selenium':
        try:
            return fetch_with_selenium_porn(url, logger, max_pages, config, smart_cache, model_name)
        except Exception as e:
            logger.warning(f"  PORN - Selenium 抓取失败，回退到 requests: {e}")
            # 回退到 requests
            return fetch_with_requests_only_porn(url, logger, max_pages, config, smart_cache, model_name)
    else:
        return fetch_with_requests_only_porn(url, logger, max_pages, config, smart_cache, model_name)


def fetch_with_selenium_porn(url: str, logger, max_pages: int = -1, config: dict = None,
                                smart_cache=None, model_name: str = None) -> Tuple[Set[str], Dict[str, str]]:
    """使用 Selenium 抓取 PORN 视频（支持增量更新）"""
    try:
        from ..common.selenium_helper import SeleniumHelper
    except ImportError:
        logger.error("  PORN - Selenium 助手模块未找到")
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
            logger.info(f"  PORN - 增量模式，已加载 {len(cached_titles)} 个缓存标题")
    
    page_num = start_page
    consecutive_empty_pages = 0
    
    selenium = None
    try:
        # 创建 Selenium 助手
        selenium = SeleniumHelper(config)
        selenium.driver = selenium.setup_driver()
        
        logger.info("  PORN - 使用 Selenium 模式抓取")
        
        while True:
            # 检查该页是否需要更新（智能缓存）
            if smart_cache and model_name and page_num < start_page + 3:  # 只检查前3页
                if not smart_cache.should_update_page(model_name, page_num):
                    logger.debug(f"  PORN - 第 {page_num} 页在缓存有效期内，跳过")
                    page_num += 1
                    continue
            
            # 构建分页URL
            page_url = url
            if page_num > 1:
                if '?' in url:
                    page_url = f"{url}&page={page_num}"
                else:
                    page_url = f"{url}?page={page_num}"
            
            logger.info(f"  PORN - Selenium 抓取第 {page_num} 页: {page_url}")
            
            # 访问页面
            if not selenium.get_page(page_url, wait_element='a.thumbnailTitle, .title, .video-title', wait_timeout=15):
                logger.warning(f"  PORN - Selenium 页面加载失败")
                break
            
            # 随机延时
            time.sleep(random.uniform(2.0, 4.0))
            
            # 获取页面源码
            page_source = selenium.get_page_source()
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 提取标题
            page_titles = set()
            page_videos = []  # 用于智能缓存
            
            # 选择器1: 视频缩略图容器内的标题
            # PornHub当前结构: div.videoContainer a.title 或 div.nf-video-hover-title
            video_containers = soup.select('div.videoContainer, div.video, div.videoBrick, .nf-video-hover-title, a[href*="/view_video.php"]')
            for container in video_containers:
                # 从容器内查找标题
                title_elem = container.select_one('a.title, span.title, a.nf-video-hover-title')
                if not title_elem:
                    title_elem = container.find('a')
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title and len(title) > 3 and len(title) < 500:  # 过滤太长或太短的
                        # 过滤掉明显是非视频内容的文本
                        excluded_keywords = [
                            'share', '分享', '收藏', 'report', '举报', '下载', 'download',
                            '广告', 'advertisement', 'photo', '照片', '图片', 'image',
                            'album', '相册', 'gallery', '画廊', 'picture', '壁纸',
                            'gif', '动图', 'avatar', '头像', 'profile'
                        ]
                        if any(keyword in title.lower() for keyword in excluded_keywords):
                            continue
                        
                        # 🚨 关键修复：验证视频是否属于当前模特
                        if not _is_video_belong_to_model(container, model_name, url, logger):
                            logger.debug(f"    跳过非当前模特的视频: {title[:50]}...")
                            continue
                        
                        cleaned_title = clean_porn_title(title, config.get('filename_clean_patterns', []))
                        page_titles.add(cleaned_title)
                        
                        # 从容器获取链接
                        video_url = None
                        if title_elem.name == 'a':
                            video_url = title_elem.get('href')
                        else:
                            parent_a = title_elem.find_parent('a')
                            if parent_a:
                                video_url = parent_a.get('href')
                        
                        # 尝试从容器内的所有链接查找
                        if not video_url:
                            for link in container.find_all('a', href=True):
                                href = link.get('href')
                                if href:
                                    # 严格的视频URL过滤 - 只保留真正的视频链接
                                    if ('/view_video' in href and 
                                        'photo=' not in href and
                                        'image=' not in href and
                                        '/photo/' not in href and 
                                        '/album/' not in href and 
                                        '/gallery/' not in href and
                                        '/pictures/' not in href and
                                        '/images/' not in href):
                                        video_url = href
                                        break
                        
                        if video_url:
                            if not video_url.startswith('http'):
                                video_url = urljoin(url, video_url)
                            title_to_url[cleaned_title] = video_url
                            page_videos.append((cleaned_title, video_url))
                        else:
                            logger.debug(f"    注意: 找到了视频标题『{cleaned_title[:50]}...』但没有链接")
            
            # 选择器2: PORN特有的视频标题选择器（备选）
            if not page_titles:
                for elem in soup.select('a.thumbnailTitle'):
                    title = elem.get_text(strip=True)
                    if title and len(title) > 3 and len(title) < 500:
                        # 🚨 关键修复：验证视频是否属于当前模特
                        parent_container = elem.find_parent('div', class_=['videoContainer', 'video', 'videoBrick'])
                        if parent_container and not _is_video_belong_to_model(parent_container, model_name, url, logger):
                            logger.debug(f"    跳过非当前模特的视频: {title[:50]}...")
                            continue
                        
                        cleaned_title = clean_porn_title(title, config.get('filename_clean_patterns', []))
                        page_titles.add(cleaned_title)
                        video_url = elem.get('href')
                        if not video_url:
                            parent_a = elem.find_parent('a')
                            if parent_a:
                                video_url = parent_a.get('href')
                        
                        if video_url:
                            if not video_url.startswith('http'):
                                video_url = urljoin(url, video_url)
                            title_to_url[cleaned_title] = video_url
                            page_videos.append((cleaned_title, video_url))
                        else:
                            logger.debug(f"    注意: 找到了标题『{cleaned_title[:50]}...』但没有链接")
            
            # 选择器3: 通用标题选择器（仅当前两个选择器都没找到结果时）
            if not page_titles:
                # 更严格的选择器，只从已知的视频区域查找
                video_area = soup.find('div', class_=['videoPlaylist', 'videoPagination', 'nf-video-list', 'container'])
                if video_area:
                    for elem in video_area.select('a.title, a[href*="view_video"], span.title'):
                        title = elem.get_text(strip=True)
                        if title and len(title) > 3 and len(title) < 500:
                            # 过滤非视频内容
                            excluded_keywords = [
                                'share', '分享', '收藏', 'report', '举报', '下载',
                                'photo', '照片', '图片', 'image', 'album', '相册',
                                'gallery', '画廊', 'picture', '壁纸', 'gif', '动图'
                            ]
                            if any(keyword in title.lower() for keyword in excluded_keywords):
                                continue
                            
                            cleaned_title = clean_porn_title(title, config.get('filename_clean_patterns', []))
                            page_titles.add(cleaned_title)
                            
                            link_elem = elem if elem.name == 'a' else elem.find_parent('a')
                            if link_elem:
                                video_url = link_elem.get('href')
                                if video_url:
                                    if not video_url.startswith('http'):
                                        video_url = urljoin(url, video_url)
                                    title_to_url[cleaned_title] = video_url
                                    page_videos.append((cleaned_title, video_url))
                            else:
                                logger.debug(f"    注意: 找到了标题『{cleaned_title[:50]}...』但未找到链接父元素")
            
            if page_titles:
                prev_count = len(all_titles)
                all_titles.update(page_titles)
                new_titles = len(all_titles) - prev_count
                
                logger.info(f"  PORN - Selenium 第 {page_num} 页提取到 {len(page_titles)} 个标题（新增 {new_titles} 个）")
                
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
                logger.warning(f"  PORN - Selenium 第 {page_num} 页未找到视频标题")
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= 2:
                    logger.info("  PORN - 连续2页无数据，停止抓取")
                    break
            
            # 检查是否有下一页
            next_buttons = soup.select('a.next, a[rel="next"], li.next a, .pagination_next, .orangeButton')
            has_next = False
            for button in next_buttons:
                text = button.get_text(strip=True).lower()
                href = button.get('href', '')
                # 更严格的下一页检测
                if text in ['next', '>', '下一页', '→', 'next page'] or ('page=' in href and not 'javascript' in href.lower()):
                    # 检查是否是最后一页
                    if 'page=' in href:
                        try:
                            page_param = href.split('page=')[-1].split('&')[0]
                            if page_param.isdigit():
                                next_page_num = int(page_param)
                                if next_page_num <= page_num:
                                    continue
                                # 🚨 紧急修复：防止无限循环
                                if next_page_num > 100:
                                    logger.warning(f"  PORN - Selenium检测到异常大页码 {next_page_num}，停止抓取")
                                    has_next = False
                                    break
                        except:
                            pass
                    # 检查按钮是否可用
                    style = button.get('style', '')
                    disabled = button.get('disabled')
                    class_attr = button.get('class', [])
                    if 'display: none' in style or 'visibility: hidden' in style or disabled or 'disabled' in str(class_attr):
                        continue
                    has_next = True
                    break
            
            # 尝试通用分页检查
            if not has_next:
                pagination = soup.select_one('.pagination, .pages, .pageNumbers, .pagination.pagination-themed, nav.pagination')
                if pagination:
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
                logger.info("  PORN - Selenium 没有下一页，停止抓取")
                # 标记完整抓取完成
                if smart_cache and model_name:
                    smart_cache.mark_full_fetch_completed(model_name, page_num)
                break
            
            # 检查最大页数
            if max_pages > 0 and page_num >= max_pages:
                logger.info(f"  PORN - Selenium 达到最大页数限制 {max_pages}，停止抓取")
                break
            
            page_num += 1
        
    except Exception as e:
        logger.error(f"  PORN - Selenium 抓取失败: {e}")
        raise
    finally:
        if selenium:
            selenium.close()
    
    logger.info(f"  PORN - Selenium 总共提取到 {len(all_titles)} 个视频标题")
    return all_titles, title_to_url


def fetch_with_requests_only_porn(url: str, logger, max_pages: int = -1, config: dict = None,
                                     smart_cache=None, model_name: str = None) -> Tuple[Set[str], Dict[str, str]]:
    """使用 requests 抓取 PORN 视频（支持增量更新）"""
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
        logger.info(f"  PORN - 使用代理: {proxies}")
    
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
            logger.info(f"  PORN - 增量模式，已加载 {len(cached_titles)} 个缓存标题")
    
    page_num = start_page
    consecutive_empty_pages = 0
    
    try:
        while True:
            # 检查该页是否需要更新（智能缓存）
            if smart_cache and model_name and page_num < start_page + 3:  # 只检查前3页
                if not smart_cache.should_update_page(model_name, page_num):
                    logger.debug(f"  PORN - 第 {page_num} 页在缓存有效期内，跳过")
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
            logger.info(f"  PORN - 抓取第 {page_num} 页: {page_url}")
            
            # 随机延时
            time.sleep(random.uniform(1.5, 3.0))
            
            try:
                resp = requests.get(page_url, headers=headers, timeout=15, proxies=proxies, verify=False)
                resp.raise_for_status()
                
                # 检查编码
                if resp.encoding.lower() != 'utf-8':
                    resp.encoding = 'utf-8'
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # PORN特定的选择器
                page_titles = set()
                page_videos = []  # 用于智能缓存 [(title, url), ...]
                
                # 选择器1: PORN特有的视频标题选择器
                for elem in soup.select('a.thumbnailTitle'):
                    title = elem.get_text(strip=True)
                    if title and len(title) > 3:
                        # 🚨 关键修复：验证视频是否属于当前模特
                        parent_container = elem.find_parent('div', class_=['videoContainer', 'video', 'videoBrick'])
                        if parent_container and not _is_video_belong_to_model(parent_container, model_name, url, logger):
                            logger.debug(f"    跳过非当前模特的视频: {title[:50]}...")
                            continue
                        
                        # 对在线标题应用清理流程
                        cleaned_title = clean_porn_title(title, config.get('filename_clean_patterns', []))
                        page_titles.add(cleaned_title)
                        # 尝试提取链接 - 先从当前元素，改失败再向上查找
                        video_url = elem.get('href')
                        if not video_url:
                            # 如果当前元素没有href，尝试查找父上a标签
                            parent_a = elem.find_parent('a')
                            if parent_a:
                                video_url = parent_a.get('href')
                        
                        if video_url:
                            if not video_url.startswith('http'):
                                video_url = urljoin(url, video_url)
                            title_to_url[cleaned_title] = video_url
                            page_videos.append((cleaned_title, video_url))
                        else:
                            # 即使没有链接，也要樸保标题存在
                            logger.debug(f"    注意: 找到了标题『{cleaned_title[:50]}...』但没有链接")
                
                # 选择器2: 通用标题选择器（仅当第一个选择器没找到结果时）
                if not page_titles:
                    for elem in soup.select('.title, .video-title, h3.title'):
                        title = elem.get_text(strip=True)
                        if title and len(title) > 3:
                            # 🚨 关键修复：验证视频是否属于当前模特
                            parent_container = elem.find_parent('div', class_=['videoContainer', 'video', 'videoBrick'])
                            if parent_container and not _is_video_belong_to_model(parent_container, model_name, url, logger):
                                logger.debug(f"    跳过非当前模特的视频: {title[:50]}...")
                                continue
                            
                            # 额外的安全检查：确保标题和链接在同一视频容器内
                            parent_video_link = elem.find_parent('a', href=True)
                            if parent_video_link:
                                video_url = parent_video_link.get('href')
                                if video_url and not video_url.startswith('http'):
                                    video_url = urljoin(url, video_url)
                                
                                # 验证链接是否指向视频页面（而不是其他内容）
                                if '/view_video.php?' not in video_url and '/video/' not in video_url:
                                    logger.debug(f"    跳过非视频链接: {video_url[:100]}...")
                                    continue
                            
                            cleaned_title = clean_porn_title(title, config.get('filename_clean_patterns', []))
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
                            else:
                                logger.debug(f"    注意: 找到了标题『{cleaned_title[:50]}...』但未找到链接父元素")
                
                if page_titles:
                    prev_count = len(all_titles)
                    all_titles.update(page_titles)
                    new_titles = len(all_titles) - prev_count
                    
                    logger.info(f"  PORN - 第 {page_num} 页提取到 {len(page_titles)} 个标题（新增 {new_titles} 个）")
                    
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
                    logger.warning(f"  PORN - 第 {page_num} 页未找到视频标题")
                    consecutive_empty_pages += 1
                    # 如果连续2页没有标题，停止
                    if consecutive_empty_pages >= 2:
                        logger.info("  PORN - 连续2页无数据，停止抓取")
                        break
                
                # 检查是否有下一页
                has_next = False
                
                # PORN特定的分页检查
                next_buttons = soup.select('a.next, a[rel="next"], li.next a, .pagination_next, .orangeButton')
                if next_buttons:
                    for button in next_buttons:
                        text = button.get_text(strip=True).lower()
                        href = button.get('href', '')
                        # 更严格的下一页检测
                        if text in ['next', '>', '下一页', '→', 'next page'] or ('page=' in href and not 'javascript' in href.lower()):
                            # 检查是否是最后一页
                            if 'page=' in href:
                                # 提取page参数值
                                try:
                                    page_param = href.split('page=')[-1].split('&')[0]
                                    if page_param.isdigit():
                                        # 下一个页码应该大于当前页
                                        next_page_num = int(page_param)
                                        if next_page_num <= page_num:
                                            logger.debug(f"  PORN - 忽略无效下一页链接: {href}")
                                            continue
                                        # 🚨 紧急修复：防止无限循环 - 限制最大页数
                                        if next_page_num > 100:  # 安全限制
                                            logger.warning(f"  PORN - 检测到异常大的页码 {next_page_num}，可能存在分页循环，停止抓取")
                                            has_next = False
                                            break
                                except:
                                    pass
                            # 检查按钮是否可见或可用（禁用状态检查）
                            style = button.get('style', '')
                            disabled = button.get('disabled')
                            class_attr = button.get('class', [])
                            if 'display: none' in style or 'visibility: hidden' in style or disabled or 'disabled' in str(class_attr):
                                logger.debug(f"  PORN - 忽略已禁用的下一页按钮")
                                continue
                            logger.debug(f"  PORN - 找到下一页按钮: {href}")
                            has_next = True
                            break
                
                # 尝试通用分页检查（当上面没检测到时）
                if not has_next:
                    pagination = soup.select_one('.pagination, .pages, .pageNumbers, .pagination.pagination-themed, nav.pagination')
                    if pagination:
                        # 查找所有页码链接
                        page_links = pagination.select('a')
                        page_numbers = []
                        for link in page_links:
                            text = link.get_text(strip=True)
                            if text.isdigit():
                                page_numbers.append(int(text))
                        
                        if page_numbers:
                            max_page = max(page_numbers)
                            # 🚨 紧急修复：添加安全检查
                            if max_page > 100:  # 异常大的页数
                                logger.warning(f"  PORN - 检测到异常页数 {max_page}，可能存在分页错误，停止抓取")
                                has_next = False
                            elif page_num < max_page:
                                logger.debug(f"  PORN - 通用分页检测: 当前页={page_num}, 最大页={max_page}")
                                has_next = True
                
                if not has_next:
                    logger.info("  PORN - 没有下一页，停止抓取")
                    # 标记完整抓取完成
                    if smart_cache and model_name:
                        smart_cache.mark_full_fetch_completed(model_name, page_num)
                    break
                
                # 检查最大页数
                if max_pages > 0 and page_num >= max_pages:
                    logger.info(f"  PORN - 达到最大页数限制 {max_pages}，停止抓取")
                    break
                
                page_num += 1
                
            except requests.exceptions.RequestException as e:
                logger.error(f"  PORN - 第 {page_num} 页请求失败: {e}")
                break
                
    except Exception as e:
        logger.error(f"  PORN - Requests抓取失败: {e}")
    
    logger.info(f"  PORN - 总共提取到 {len(all_titles)} 个视频标题")
    return all_titles, title_to_url

def _is_video_belong_to_model(video_container, model_name: str, model_url: str, logger) -> bool:
    """
    验证视频是否属于指定模特
    
    Args:
        video_container: 视频容器元素
        model_name: 目标模特名称
        model_url: 模特页面URL
        logger: 日志记录器
        
    Returns:
        bool: True表示属于该模特，False表示不属于
    """
    try:
        # 方法1: 检查视频容器中是否包含模特相关信息
        # 查找模特名或用户名元素
        model_indicators = video_container.select(
            '.username, .uploader, .channelName, .modelName, '
            '.userInfo .usernameWrap, [data-user-name], [data-channel-name]'
        )
        
        positive_matches = 0  # 正面匹配计数
        negative_matches = 0  # 负面匹配计数
        
        for indicator in model_indicators:
            indicator_text = indicator.get_text(strip=True)
            if indicator_text:
                # 标准化比较
                indicator_clean = indicator_text.lower().replace(' ', '').replace('_', '').replace('-', '')
                model_clean = model_name.lower().replace(' ', '').replace('_', '').replace('-', '')
                
                # 检查是否匹配
                if (indicator_clean == model_clean or 
                    indicator_clean in model_clean or 
                    model_clean in indicator_clean):
                    positive_matches += 1
                    logger.debug(f"    ✅ 找到匹配的模特标识: {indicator_text} 匹配 {model_name}")
                elif indicator_clean:  # 如果有文本但不匹配
                    negative_matches += 1
                    logger.debug(f"    ⚠️ 找到其他模特标识: {indicator_text} 不匹配 {model_name}")
        
        # 判断逻辑：如果有正面匹配，优先认为属于；如果有负面匹配且无正面匹配，则不属于
        if positive_matches > 0:
            logger.debug(f"    ✅ 基于正面匹配，视频属于模特: {model_name}")
            return True
        elif negative_matches > 0:
            logger.debug(f"    ❌ 基于负面匹配，视频不属于模特: {model_name}")
            return False
        
        # 方法2: 检查视频链接是否指向正确的模特页面
        video_links = video_container.find_all('a', href=True)
        for link in video_links:
            href = link.get('href', '')
            # 如果链接包含模特页面信息
            if '/model/' in href and model_name.lower().replace(' ', '-') in href.lower():
                logger.debug(f"    ✅ 通过链接确认视频属于模特: {href}")
                return True
        
        # 方法3: 检查页面上下文（如果是模特专属页面）
        # 从model_url提取模特标识
        if '/model/' in model_url:
            # 如果是在模特专属页面，大部分视频应该属于该模特
            # 除非明确标识了其他模特
            logger.debug(f"    ✅ 在模特专属页面上，认为视频属于: {model_name}")
            return True
        
        # 方法4: 更严格的默认策略
        logger.debug(f"    ⚠️ 无法明确验证视频归属，默认拒绝")
        return False  # 默认拒绝，避免错误归类
        
    except Exception as e:
        logger.debug(f"    ⚠️ 模特验证出现异常: {e}，默认拒绝视频")
        return False  # 出现异常时保守处理


def clean_porn_title(title: str, patterns: List[str]) -> str:
    """清理PORN视频标题"""
    # 先应用通用清理
    from ..common.common import clean_filename
    cleaned = clean_filename(title, patterns)
    
    # PORN特定的清理
    # 移除PORN特有的标记
    cleaned = re.sub(r'\b(porn|PH)\b', '', cleaned, flags=re.IGNORECASE)
    # 移除PORN特有的标签格式
    cleaned = re.sub(r'(?i)\[porn\]\s*', '', cleaned)
    # 再次清理空格
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def scan_porn_models(config_models: dict, local_roots: List[str], video_exts: Set[str], 
                       clean_patterns: List[str], logger) -> List[Tuple[str, str, str, str]]:
    """
    扫描PORN格式的本地模特目录（带[Channel]前缀）
    返回(模特名, 模特根路径, 原始目录名, 国家)元组列表
    """
    from ..common.common import clean_filename
    
    matched = []
    
    for root in local_roots:
        root = os.path.normpath(root)
        
        if not os.path.exists(root):
            logger.warning(f"⚠ PORN - 路径不存在: {root}")
            continue
            
        logger.info(f"PORN - 扫描目录: {root}")
        
        try:
            # 递归扫描所有子目录
            for current_dir, _, subdirs in os.walk(root):
                # 跳过根目录本身
                if current_dir == root:
                    logger.debug(f"  PORN - 跳过根目录: {os.path.basename(current_dir)}")
                    continue
                
                # 检查当前目录是否是PORN格式的模特目录（带前缀）
                dir_name = os.path.basename(current_dir)
                
                # 提取模特名
                model_name = None
                original_dir = dir_name
                
                # 匹配 [Channel] 前缀
                if dir_name.startswith("[Channel] "):
                    model_name = dir_name[len("[Channel] "):].strip()
                    logger.debug(f"  PORN - 提取模特名: {model_name} (从 {dir_name})")
                elif re.match(r'^\[.*?\]\s+', dir_name):
                    model_name = re.sub(r'^\[.*?\]\s+', '', dir_name).strip()
                    logger.debug(f"  PORN - 提取模特名: {model_name} (从 {dir_name})")
                else:
                    # 跳过非PORN格式的目录
                    continue
                
                # 在配置中查找匹配的模特名
                matched_model = None
                for config_model in config_models.keys():
                    # 更灵活的匹配
                    config_lower = config_model.lower().replace(' ', '').replace('_', '').replace('-', '')
                    model_lower = model_name.lower().replace(' ', '').replace('_', '').replace('-', '')
                    
                    logger.debug(f"  PORN - 匹配测试: {model_name} vs {config_model}")
                    logger.debug(f"  PORN - 标准化: {model_lower} vs {config_lower}")
                    
                    if (model_lower == config_lower or 
                        model_lower in config_lower or 
                        config_lower in model_lower):
                        matched_model = config_model
                        logger.debug(f"  PORN - 匹配成功: {model_name} -> {matched_model}")
                        break
                
                # 如果没有精确匹配，尝试模糊匹配
                if not matched_model:
                    # 直接使用目录提取的模特名
                    matched_model = model_name
                    logger.debug(f"  PORN - 模糊匹配: 使用目录名作为模特名: {matched_model}")
                
                if matched_model:
                    # 提取国家信息：从路径中提取国家目录
                    relative_path = os.path.relpath(current_dir, root)
                    path_parts = relative_path.split(os.path.sep)
                    country = path_parts[0] if len(path_parts) > 0 else "未知国家"
                    matched.append((matched_model, current_dir, original_dir, country))
                    logger.info(f"  PORN - 找到本地模特: {matched_model} ({original_dir}) 在 {os.path.join(country, original_dir)}")
        except PermissionError:
            logger.error(f"  PORN - 权限不足，无法访问: {root}")
            continue
    
    logger.info(f"PORN - ✅ 共找到 {len(matched)} 个匹配的本地模特目录")
    return matched
