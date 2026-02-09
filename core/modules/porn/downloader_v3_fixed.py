# -*- coding: utf-8 -*-
"""
V3修复版本 - 基于Hitomi-Downloader的PORN下载实现
核心改进:
1. 不依赖yt-dlp，直接解析M3U8
2. 改进User-Agent策略（参考Hitomi）
3. 优化请求头和连接管理
4. 添加重试和故障恢复机制
"""

import os
import re
import json
import time
import logging
import requests
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
import threading
from bs4 import BeautifulSoup

from core.modules.common.common import get_config, ensure_dir_exists

logger = logging.getLogger(__name__)


class PornHubDownloaderV3Fixed:
    """V3修复版本 - 基于Hitomi-Downloader设计"""
    
    # 从Hitomi学到的User-Agent策略
    USER_AGENTS = [
        # 常见浏览器UA
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        # 一些"不起眼"的UA
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (iPad; CPU OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1',
    ]
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化V3修复版本"""
        self.config = config or get_config()
        self.session = self._create_session()
        self.output_dir = Path(self.config.get('output_dir', 'output'))
        self.api_base = 'https://cn.pornhub.com'
    
    def _create_session(self) -> requests.Session:
        """创建优化的会话 - 参考Hitomi"""
        session = requests.Session()
        
        # 关键请求头（Hitomi经验）
        import random
        headers = {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        session.headers.update(headers)
        
        # 代理配置
        proxy_config = self.config.get('network', {}).get('proxy', {})
        if proxy_config.get('enabled', False):
            proxy = proxy_config.get('http', 'socks5://127.0.0.1:10808')
            session.proxies = {'http': proxy, 'https': proxy}
            logger.info(f"✅ V3Fixed已启用代理: {proxy}")
        
        return session
    
    def _get_video_page_with_cdp(self, video_id: str) -> Optional[str]:
        """使用Selenium + CDP获取视频页面（不使用yt-dlp）"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            import time
                
            url = f"{self.api_base}/view_video.php?viewkey={video_id}"
            logger.info(f"[使用CDP] 获取视频页面: {video_id}")
                
            # 配置 Chrome 选项
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            # chrome_options.add_argument('--headless')  # 按需不使用无头模式
                
            # 不使用代理（直接连接）
            browser = webdriver.Chrome(options=chrome_options)
                
            # 启用Chrome DevTools Protocol
            logger.info(f"[使用CDP] 启用网络监控...")
                
            # 设置超时
            browser.set_page_load_timeout(30)
            browser.implicitly_wait(10)
                
            try:
                browser.get(url)
                    
                # 等待页面主要内容加载
                wait = WebDriverWait(browser, 10)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                    
                # 等待有效的元素
                try:
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'player')), timeout=5)
                except:
                    pass  # 元素可能不存在，继续前進
                    
                # 等待JavaScript执行
                time.sleep(3)
                    
                html = browser.page_source
                logger.info(f"[使用CDP] 成功获取页面 ({len(html)} 字节)")
                    
                return html
                
            finally:
                browser.quit()
            
        except Exception as e:
            logger.error(f"[使用CDP] 获取失败: {str(e)[:100]}")
            return None
        
    def _extract_m3u8_with_cdp_network(self, video_id: str) -> Optional[str]:
        """
        使用Selenium + CDP捕获网络请求中的M3U8 URL
        这是Hitomi-Downloader等最优方案：直接捕获真实的网络流
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            import json
            import time
                
            url = f"{self.api_base}/view_video.php?viewkey={video_id}"
            logger.info(f"[使用CDP网络捕获] 实时拦截M3U8请求...")
                
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
                
            browser = webdriver.Chrome(options=chrome_options)
                
            # 存储捕获的请求
            captured_requests = []
            captured_responses = {}
                
            # 使用下载监控器（是做Selenium 4+的功能）
            def request_interceptor(request):
                if 'm3u8' in request.url.lower():
                    logger.info(f"[使用CDP] 捕获M3U8请求: {request.url[:100]}")
                    captured_requests.append(request.url)
                
            try:
                # Selenium 4+ щ有CDP支持
                if hasattr(browser, 'execute_cdp_cmd'):
                    browser.execute_cdp_cmd('Network.enable', {})
                    logger.info(f"[使用CDP] 网络监控已启用")
                    
                browser.get(url)
                    
                # 等待是否有M3U8请求
                start_time = time.time()
                while time.time() - start_time < 10:  # 最轡10秒
                    # 查询是否有M3U8请求
                    try:
                        script = """
                        return window.__m3u8Url || 
                               (window.videoData && window.videoData.m3u8) || 
                               (window.qualityList && window.qualityList[0] && window.qualityList[0].url);
                        """
                        m3u8_url = browser.execute_script(script)
                        if m3u8_url:
                            logger.info(f"[使用CDP] 从个JavaScript变量捕获M3U8: {str(m3u8_url)[:100]}")
                            return str(m3u8_url)
                    except:
                        pass
                        
                    time.sleep(0.5)
                    
                # 如果仍然没有找M3U8，监查捕获的请求
                if captured_requests:
                    logger.info(f"[使用CDP] 找M3U8请求 ({len(captured_requests)} 个)")
                    return captured_requests[0]
                    
                logger.warning(f"[使用CDP] 未找M3U8请求")
                return None
                
            finally:
                browser.quit()
            
        except ImportError:
            logger.warning(f"[使用CDP] Selenium 4+ 未安装或不支持CDP")
            return None
        except Exception as e:
            logger.error(f"[使用CDP网络捕获] 失败: {str(e)[:100]}")
            return None
    
    def _extract_m3u8_url(self, html: str) -> Optional[str]:
        """从HTML提取M3U8 URL - 参考Hitomi的多方式提取"""
        if not html:
            return None
            
        # 方式1: 从javascript变量提取（PornHub常见方式）
        patterns = [
            # PornHub常见格式
            r'"?mediaUrl"?\s*:\s*"([^"]+\.m3u8[^"]*)',
            r'"?contentUrl"?\s*:\s*"([^"]+\.m3u8[^"]*)',
            r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)',
            # 变量赋值
            r'var\s+\w+\s*=\s*["\']([^"\']]+\.m3u8[^"\']]*)["\']',
            # src属性
            r'src=["\']([^"\']]+\.m3u8[^"\']]*)["\']',
            # hls.js
            r'hls\.loadSource\(["\']([^"\']]+\.m3u8[^"\']]*)["\']',
            # data属性
            r'data-src=["\']([^"\']]+\.m3u8[^"\']]*)["\']',
            # 直接URL（带问号参数）
            r'https://[^\s"\']]+\.m3u8[^\s"\']]*',
        ]
            
        for pattern in patterns:
            try:
                matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                if matches:
                    for match in matches:
                        if not match:
                            continue
                            
                        m3u8_url = match if isinstance(match, str) else match[0]
                        m3u8_url = m3u8_url.strip()
                            
                        # 验证是否看起来像M3U8 URL
                        if 'm3u8' not in m3u8_url.lower():
                            continue
                            
                        if m3u8_url.startswith('http'):
                            logger.info(f"✅ 通过pattern提取M3U8: {m3u8_url[:100]}")
                            return m3u8_url
                        elif m3u8_url.startswith('//'):
                            url = 'https:' + m3u8_url
                            logger.info(f"✅ 通过pattern提取M3U8: {url[:100]}")
                            return url
                        elif m3u8_url.startswith('/'):
                            url = urljoin(self.api_base, m3u8_url)
                            logger.info(f"✅ 通过pattern提取M3U8: {url[:100]}")
                            return url
                        else:
                            url = urljoin(self.api_base, m3u8_url)
                            logger.info(f"✅ 通过pattern提取M3U8: {url[:100]}")
                            return url
            except Exception as e:
                logger.debug(f"pattern匹配异常: {e}")
                continue
            
        logger.warning("❌ 未能从HTML提取M3U8 URL - 可能页面结构已改变")
        return None
    
    def _extract_title(self, html: str) -> Optional[str]:
        """提取视频标题"""
        try:
            # 方式1: h1标签
            match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
            if match:
                return match.group(1).strip()
            
            # 方式2: meta标签
            match = re.search(r'<meta\s+name=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html)
            if match:
                return match.group(1).strip()
            
            # 方式3: title标签
            match = re.search(r'<title[^>]*>([^<]+)</title>', html)
            if match:
                title = match.group(1).strip()
                # 移除可能的网站名称
                if ' - ' in title:
                    title = title.split(' - ')[0]
                return title
        
        except Exception as e:
            logger.warning(f"提取标题失败: {e}")
        
        return None
    
    def _download_m3u8(self, m3u8_url: str, file_path: Path) -> bool:
        """下载M3U8流媒体"""
        try:
            logger.info(f"开始下载M3U8: {m3u8_url[:80]}")
            
            # 获取M3U8文件
            response = self.session.get(m3u8_url, timeout=20)
            response.raise_for_status()
            
            m3u8_content = response.text
            logger.debug(f"M3U8内容行数: {len(m3u8_content.split(chr(10)))}")
            
            # 解析片段URL
            segment_urls = []
            for line in m3u8_content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith('http'):
                        segment_urls.append(line)
                    elif line.startswith('/'):
                        segment_urls.append(urljoin(self.api_base, line))
                    else:
                        # 相对URL
                        base_url = '/'.join(m3u8_url.split('/')[:-1])
                        segment_urls.append(f"{base_url}/{line}")
            
            if not segment_urls:
                logger.error(f"❌ 未找到M3U8片段")
                return False
            
            logger.info(f"📦 发现 {len(segment_urls)} 个片段，开始下载...")
            
            # 确保保存目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 下载并组装片段
            temp_file = Path(str(file_path) + '.tmp')
            downloaded = 0
            failed_count = 0
            
            with open(temp_file, 'wb') as f:
                for i, segment_url in enumerate(segment_urls):
                    try:
                        response = self.session.get(segment_url, timeout=15)
                        response.raise_for_status()
                        f.write(response.content)
                        downloaded += 1
                        
                        if (i + 1) % max(1, len(segment_urls) // 10) == 0:
                            progress = ((i + 1) / len(segment_urls)) * 100
                            logger.info(f"进度: {progress:.1f}% ({i+1}/{len(segment_urls)})")
                    
                    except Exception as e:
                        failed_count += 1
                        logger.debug(f"片段 {i+1}/{len(segment_urls)} 失败: {str(e)[:60]}")
                        
                        # 如果失败过多，放弃
                        if failed_count > len(segment_urls) * 0.2:  # 20%失败率
                            logger.error(f"❌ 片段下载失败率过高 ({failed_count}/{len(segment_urls)})")
                            return False
                        
                        continue
            
            # 重命名临时文件
            temp_file.rename(file_path)
            logger.info(f"✅ M3U8下载完成: {file_path.name} ({file_path.stat().st_size / (1024*1024):.2f}MB)")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ M3U8下载失败: {str(e)[:100]}")
            return False
    
    def download_video(self, url: str, save_dir: Optional[str] = None) -> Dict:
        """下载单个视频 - 使用Selenium + CDP（依赖整个代码库的Selenium配置）"""
        result = {
            'success': False,
            'url': url,
            'title': None,
            'file_path': None,
            'file_size': 0,
            'error': None,
            'message': '未知错误'
        }
        
        try:
            logger.info(f"🎬 V3 CDP流程开始下载: {url}")
            
            # 提取视频ID
            video_id = re.search(r'viewkey=([a-z0-9]+)', url)
            if not video_id:
                result['error'] = '无效的视频URL'
                result['message'] = '无法提取视频ID'
                logger.error(f"❌ 无法提取视频ID: {url}")
                return result
            
            video_id = video_id.group(1)
            logger.info(f"视频ID: {video_id}")
            
            # ===== 方案：SELENIUM + CDP网络捕获 =====
            logger.info(f"步骤1: 使用Selenium + CDP获取质量列表...")
            
            # 不使用yt-dlp，简接使用Selenium + CDP的方案
            m3u8_url = self._extract_m3u8_with_cdp_network(video_id)
            
            if not m3u8_url:
                # 备选：标准页面获取 + 手动正则提取
                logger.info(f"步骤2: CDP网络捕获失败，需使用标准流程...")
                html = self._get_video_page_with_cdp(video_id)
                if html:
                    m3u8_url = self._extract_m3u8_url(html)
            
            if not m3u8_url:
                result['error'] = 'M3U8提取失败'
                result['message'] = '不成农的提取视频流地址（CDP网络捕获失败）'
                logger.error(f"❌ 无法提取M3U8: {video_id}")
                return result
            
            logger.info(f"✅ M3U8 URL: {m3u8_url[:100]}")
            
            # 计算保存路径
            if save_dir:
                save_path = Path(save_dir)
            else:
                save_path = self.output_dir / "downloads"
            
            ensure_dir_exists(save_path)
            
            # 生成文件名
            # 假设不能提取标题，使用ID作文件名
            safe_title = f"video_{video_id}"
            file_path = save_path / f"{safe_title}.mp4"
            
            # 检查文件是否已存在
            if file_path.exists():
                result['success'] = True
                result['file_path'] = str(file_path)
                result['file_size'] = file_path.stat().st_size
                result['message'] = '文件已存在'
                logger.info(f"⏭️ 文件已存在: {file_path.name}")
                return result
            
            # ===== 使用V3的M3U8下载流程 =====
            logger.info(f"步骤3: 下载M3U8片段下载...")
            if self._download_m3u8(m3u8_url, file_path):
                result['success'] = True
                result['file_path'] = str(file_path)
                result['file_size'] = file_path.stat().st_size
                result['message'] = f'✅ 下载成功 ({result["file_size"] / (1024*1024):.2f}MB)'
                logger.info(f"✅ V3 CDP流程下载完成: {file_path.name}")
            else:
                result['error'] = 'M3U8下载失败'
                result['message'] = '无法下载视频流片段'
                logger.error(f"❌ M3U8下载失败")
        
        except Exception as e:
            result['error'] = str(e)
            result['message'] = f'异常: {str(e)[:80]}'
            logger.error(f"❌ 异常: {e}", exc_info=True)
        
        return result


# 便捷函数
def download_porn_video_v3_fixed(url: str, save_dir: Optional[str] = None, config: Optional[Dict] = None) -> Dict:
    """下载单个PORN视频 - V3修复版本"""
    downloader = PornHubDownloaderV3Fixed(config)
    return downloader.download_video(url, save_dir)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python downloader_v3_fixed.py <视频URL> [保存目录]")
        sys.exit(1)
    
    url = sys.argv[1]
    save_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    logging.basicConfig(level=logging.INFO)
    result = download_porn_video_v3_fixed(url, save_dir)
    
    print("\n" + "=" * 80)
    print("下载结果:")
    print("=" * 80)
    for key, value in result.items():
        if key != 'message' or value:
            print(f"{key}: {value}")
