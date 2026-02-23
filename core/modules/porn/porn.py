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
                                smart_cache=None, model_name: str = None, selenium=None) -> Tuple[Set[str], Dict[str, str]]:
    """PORN专用的抓取，支持requests和Selenium，抓取视频标题和链接，支持翻页（支持增量更新）"""
    if config is None:
        config = {}

    # 检查是否使用 Selenium
    use_selenium = config.get('use_selenium', False)
    scraper = config.get('scraper', 'selenium')

    # 🚨 关键修复：对于模特页面，强制使用更严格的抓取模式
    if model_name and '/model/' in url:
        logger.info(f"  🎯 检测到模特专属页面，启用严格抓取模式")
        # 模特页：强制清理该模特缓存，避免历史误抓导致的"视频数暴涨"
        if smart_cache and smart_cache.enabled:
            logger.info(f"  🚨 模特页启用严格模式：清理 {model_name} 的缓存")
            try:
                smart_cache.clear_cache(model_name)
            except Exception as e:
                logger.warning(f"  ⚠️ 缓存清除失败: {e}")

    if use_selenium or scraper == 'selenium':
        try:
            return fetch_with_selenium_porn(url, logger, max_pages, config, smart_cache, model_name, selenium)
        except Exception as e:
            logger.warning(f"  PORN - Selenium 抓取失败，回退到 requests: {e}")
            # 回退到 requests
            return fetch_with_requests_only_porn(url, logger, max_pages, config, smart_cache, model_name)
    else:
        return fetch_with_requests_only_porn(url, logger, max_pages, config, smart_cache, model_name)


def fetch_with_selenium_porn(url: str, logger, max_pages: int = -1, config: dict = None,
                                smart_cache=None, model_name: str = None, selenium=None) -> Tuple[Set[str], Dict[str, str]]:
    """使用 Selenium 抓取 PORN 视频（支持增量更新）"""
    try:
        from ..common.selenium_helper import SeleniumHelper
    except ImportError:
        logger.error("  PORN - Selenium 助手模块未找到")
        raise

    # 如果没有提供 Selenium 实例，创建新的
    need_cleanup = False
    if selenium is None:
        try:
            selenium = SeleniumHelper(config)
            selenium.driver = selenium.setup_driver()
            need_cleanup = True
        except Exception as e:
            logger.error(f"  PORN - 创建 Selenium 实例失败: {e}")
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

    try:
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
            
            # 选择器1: 严格限定在模特视频容器内
            # 只从明确的视频容器中提取，避免抓取页面其他内容
            video_containers = soup.select('div.videoContainer, div.video, div.videoBrick, .nf-video-item')
            page_titles = set()
            page_videos = []  # 用于智能缓存
            
            logger.debug(f"  找到 {len(video_containers)} 个视频容器")
            
            for container in video_containers:
                # 🚨 关键修复：严格验证视频归属
                if not _is_video_belong_to_model(container, model_name, url, logger):
                    continue
                
                # 从容器内查找标题
                title_elem = container.select_one('a.title, span.title, a.nf-video-hover-title, .videoTitle')
                if not title_elem:
                    # 尝试其他可能的标题元素
                    title_elem = container.find('a', class_=lambda x: x and 'title' in x.lower()) or \
                                container.find('span', class_=lambda x: x and 'title' in x.lower())
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title and 3 < len(title) < 500:  # 严格的长度过滤
                        # 过滤掉明显是非视频内容的文本
                        excluded_keywords = [
                            'share', '分享', '收藏', 'report', '举报', '下载', 'download',
                            '广告', 'advertisement', 'photo', '照片', '图片', 'image',
                            'album', '相册', 'gallery', '画廊', 'picture', '壁纸',
                            'gif', '动图', 'avatar', '头像', 'profile', '直播', 'live'
                        ]
                        if any(keyword in title.lower() for keyword in excluded_keywords):
                            logger.debug(f"    跳过非视频内容: {title[:30]}...")
                            continue
                        
                        cleaned_title = clean_porn_title(title, config.get('filename_clean_patterns', []))
                        page_titles.add(cleaned_title)
                        
                        # 提取链接
                        video_url = None
                        if title_elem.name == 'a':
                            video_url = title_elem.get('href')
                        else:
                            parent_a = title_elem.find_parent('a')
                            if parent_a:
                                video_url = parent_a.get('href')
                        
                        # 从容器内的所有链接中查找视频链接
                        if not video_url:
                            for link in container.find_all('a', href=True):
                                href = link.get('href')
                                if href and '/view_video.php' in href:
                                    video_url = href
                                    break
                        
                        if video_url:
                            if not video_url.startswith('http'):
                                video_url = urljoin(url, video_url)
                            title_to_url[cleaned_title] = video_url
                            page_videos.append((cleaned_title, video_url))
                            logger.debug(f"    ✅ 提取视频: {cleaned_title[:50]}...")
                        else:
                            logger.debug(f"    ⚠️ 找到标题但无链接: {cleaned_title[:50]}...")
            
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
        # 只清理自己创建的 Selenium 实例
        if need_cleanup and selenium:
            try:
                selenium.close()
            except Exception as e:
                logger.warning(f"  PORN - 清理 Selenium 实例失败: {e}")

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
    """验证视频是否属于指定模特（更严格：防止把推荐/热门视频算进来）"""

    def _norm(s: str) -> str:
        return (s or "").lower().strip()

    def _norm_compact(s: str) -> str:
        return _norm(s).replace(' ', '').replace('_', '').replace('-', '')

    def _extract_model_slug(u: str) -> str:
        try:
            m = re.search(r"/model/([^/?#]+)/?", u or "")
            if not m:
                return ""
            return _norm(m.group(1)).replace('%20', '-')
        except Exception:
            return ""

    try:
        model_url = model_url or ""
        target_slug_from_url = _extract_model_slug(model_url)
        target_slug_from_name = _norm(model_name).replace(' ', '-')
        target_compact = _norm_compact(model_name)

        # 在模特专属页：必须看到"归属证据"才接受
        if '/model/' in model_url:
            # 证据1：容器内出现指向该模特的链接
            model_links = []
            for a in video_container.find_all('a', href=True):
                href = a.get('href', '')
                if href and '/model/' in href:
                    model_links.append(href)

            if model_links:
                def _match_slug(link: str) -> bool:
                    link_l = _norm(link)
                    # 既匹配URL里的slug，也匹配由名字推导的slug
                    if target_slug_from_url and target_slug_from_url in link_l:
                        return True
                    if target_slug_from_name and target_slug_from_name in link_l:
                        return True
                    # 再做一次紧凑匹配（容错大小写/分隔符）
                    return target_compact and target_compact in _norm_compact(link_l)

                if any(_match_slug(l) for l in model_links):
                    return True

                # 有模特链接但不匹配 -> 明确不属于
                return False

            # 证据2：容器内显示了上传者/模特名（文本）并与目标匹配
            model_indicators = video_container.select(
                '.username, .uploader, .channelName, .modelName, '
                '.userInfo .usernameWrap, [data-user-name], [data-channel-name]'
            )

            found_models = []
            for indicator in model_indicators:
                t = indicator.get_text(strip=True)
                if t and len(t) > 1:
                    found_models.append(_norm(t))

            if found_models:
                # 有指示文本时：必须能匹配目标，否则拒绝
                if any(target_compact in _norm_compact(t) or _norm_compact(t) in target_compact for t in found_models):
                    return True
                return False

            # 关键修复：没有任何归属证据时，拒绝（这类通常是推荐/热门/广告模块）
            return False

        # 非模特页：保持较保守策略（只要出现模特链接且匹配则接受）
        video_links = video_container.find_all('a', href=True)
        model_links = [l.get('href', '') for l in video_links if l.get('href') and '/model/' in l.get('href', '')]

        if model_links:
            target_model_slug = target_slug_from_url or target_slug_from_name
            if target_model_slug:
                has_target_link = any(target_model_slug in _norm(link) for link in model_links)
                has_other_model_link = any('/model/' in _norm(link) and target_model_slug not in _norm(link) for link in model_links)
                if has_target_link and not has_other_model_link:
                    return True
                if has_other_model_link:
                    return False

        return False

    except Exception as e:
        logger.debug(f"    ⚠️ 模特验证异常: {e}，保守拒绝")
        return False


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
    
    增强功能：
    - 支持多目录扫描
    - 添加详细的处理日志
    - 跨目录去重处理
    - 性能优化和统计信息
    """
    from ..common.common import clean_filename
    
    matched = []
    scanned_directories = set()  # 记录已扫描的目录，避免重复
    model_stats = {}  # 记录每个模特在各目录的视频数量
    
    logger.info(f"PORN - 开始扫描 {len(local_roots)} 个目录...")
    
    for root_idx, root in enumerate(local_roots, 1):
        root = os.path.normpath(root)
        
        if not os.path.exists(root):
            logger.warning(f"⚠ PORN - 路径不存在 [{root_idx}/{len(local_roots)}]: {root}")
            continue
            
        if root in scanned_directories:
            logger.debug(f"  PORN - 跳过已扫描目录: {root}")
            continue
            
        scanned_directories.add(root)
        logger.info(f"PORN - 扫描目录 [{root_idx}/{len(local_roots)}]: {root}")
        
        directory_video_count = 0
        directory_model_count = 0
        
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
                    # 检查是否已经在结果中（跨目录去重）
                    existing_match = None
                    for i, (existing_model, existing_path, existing_original, existing_country) in enumerate(matched):
                        if existing_model == matched_model:
                            existing_match = i
                            break
                    
                    if existing_match is not None:
                        # 合并目录路径信息
                        existing_model, existing_path, existing_original, existing_country = matched[existing_match]
                        # 更新为更完整的路径信息
                        combined_path = f"{existing_path};{current_dir}" if existing_path else current_dir
                        combined_original = f"{existing_original};{original_dir}"
                        matched[existing_match] = (matched_model, combined_path, combined_original, existing_country)
                        logger.debug(f"  PORN - 合并模特目录: {matched_model} -> 多个路径")
                        
                        # 更新统计信息
                        if matched_model not in model_stats:
                            model_stats[matched_model] = {'directories': [], 'videos': 0}
                        if current_dir not in model_stats[matched_model]['directories']:
                            model_stats[matched_model]['directories'].append(current_dir)
                    else:
                        # 添加新的匹配项
                        # 提取国家信息：从路径中提取国家目录
                        relative_path = os.path.relpath(current_dir, root)
                        path_parts = relative_path.split(os.path.sep)
                        country = path_parts[0] if len(path_parts) > 0 else "未知国家"
                        matched.append((matched_model, current_dir, original_dir, country))
                        directory_model_count += 1
                        
                        # 初始化统计信息
                        if matched_model not in model_stats:
                            model_stats[matched_model] = {'directories': [current_dir], 'videos': 0}
                        else:
                            model_stats[matched_model]['directories'].append(current_dir)
                    
                    # 统计该目录下的视频数量
                    try:
                        video_count = 0
                        for file in os.listdir(current_dir):
                            name, ext = os.path.splitext(file)
                            if ext.lower() in video_exts:
                                video_count += 1
                        directory_video_count += video_count
                        if matched_model in model_stats:
                            model_stats[matched_model]['videos'] += video_count
                        logger.debug(f"    PORN - 发现 {video_count} 个视频文件")
                    except Exception as e:
                        logger.warning(f"    PORN - 无法统计目录视频数量 {current_dir}: {e}")
                
            logger.info(f"  PORN - 目录扫描完成: 发现 {directory_model_count} 个模特, {directory_video_count} 个视频")
            
        except PermissionError:
            logger.error(f"  PORN - 权限不足，无法访问: {root}")
            continue
        except Exception as e:
            logger.error(f"  PORN - 扫描目录失败 {root}: {e}")
            continue
    
    # 输出统计信息
    if model_stats:
        logger.info(f"PORN - 扫描统计:")
        logger.info(f"  总计模特数: {len(model_stats)}")
        total_videos = sum(stats['videos'] for stats in model_stats.values())
        logger.info(f"  总计视频数: {total_videos}")
        logger.info(f"  平均每个模特: {total_videos/len(model_stats):.1f} 个视频")
        
        # 显示前5个模特的详细信息
        sorted_models = sorted(model_stats.items(), key=lambda x: x[1]['videos'], reverse=True)
        logger.info("  前5个模特详情:")
        for model_name, stats in sorted_models[:5]:
            dir_count = len(stats['directories'])
            video_count = stats['videos']
            logger.info(f"    {model_name}: {dir_count}个目录, {video_count}个视频")
    
    logger.info(f"PORN - 多目录扫描完成，共找到 {len(matched)} 个匹配的模特目录")
    return matched
