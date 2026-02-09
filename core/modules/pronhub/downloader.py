# -*- coding: utf-8 -*-
"""
Pornhub视频下载模块
基于yt-dlp实现最高分辨率下载，支持会员内容和代理配置
"""
import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs

import requests
import yt_dlp
from bs4 import BeautifulSoup

# 导入项目通用模块
from core.modules.common.common import get_config, get_session, ensure_dir_exists


# 设置日志
logger = logging.getLogger(__name__)


class PornhubDownloader:
    """Pornhub视频下载器"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化下载器
        
        Args:
            config: 配置字典，如果为None则从全局配置读取
        """
        self.config = config or get_config()
        self.session = get_session()
        
        # 配置代理
        if self.config.get('network', {}).get('proxy', {}).get('enabled', False):
            proxy_config = self.config['network']['proxy']
            proxy_url = f"{proxy_config.get('http', 'socks5://127.0.0.1:10808')}"
            self.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
        else:
            self.proxies = None
            
        # 输出目录
        self.output_dir = Path(self.config.get('output_dir', 'output'))
        
        # 下载选项
        self.download_options = {
            'format': 'best[ext=mp4]/best',  # 优先选择mp4格式的最高分辨率
            'outtmpl': '%(title)s_%(id)s.%(ext)s',  # 文件名模板
            'restrictfilenames': True,  # 限制文件名中的特殊字符
            'noplaylist': True,  # 不下载播放列表
            'extractaudio': False,  # 不提取音频
            'audioformat': 'best',
            'embedsubs': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': True,  # 忽略错误继续下载
            'no_warnings': False,
            'progress_hooks': [self._progress_hook],  # 进度回调
        }
        
        # Cookie支持（用于会员内容）
        self.cookies_file = None
        if self.config.get('pornhub', {}).get('cookies_file'):
            self.cookies_file = self.config['pornhub']['cookies_file']
            if os.path.exists(self.cookies_file):
                self.download_options['cookiefile'] = self.cookies_file
    
    def _progress_hook(self, d: Dict) -> None:
        """下载进度回调"""
        if d['status'] == 'downloading':
            percent_str = d.get('_percent_str', 'N/A')
            speed_str = d.get('_speed_str', 'N/A')
            eta_str = d.get('_eta_str', 'N/A')
            logger.info(f"下载中: {percent_str} 速度: {speed_str} ETA: {eta_str}")
        elif d['status'] == 'finished':
            logger.info(f"下载完成: {d['filename']}")
        elif d['status'] == 'error':
            logger.error(f"下载错误: {d.get('error', 'Unknown error')}")
    
    def _clean_title(self, title: str) -> str:
        """清理视频标题"""
        if not title:
            return "unknown_title"
            
        # 移除特殊字符，但保留中文、英文、数字和基本符号
        title = re.sub(r'[<>:"/\\|?*]', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        
        # 限制长度
        if len(title) > 200:
            title = title[:200]
            
        return title or "unknown_title"
    
    def _get_model_dir(self, model_name: str) -> Path:
        """获取模特目录路径"""
        if not model_name:
            model_name = "Unknown_Model"
            
        # 清理模特名
        model_name = self._clean_title(model_name)
        
        # 创建模特目录：[Channel] 模特名
        model_dir = self.output_dir / f"[Channel] {model_name}"
        ensure_dir_exists(model_dir)
        
        return model_dir
    
    def _extract_video_info(self, url: str) -> Tuple[str, str]:
        """从URL或页面提取视频信息"""
        try:
            # 使用session获取页面
            response = self.session.get(url, proxies=self.proxies, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取标题
            title_elem = soup.find('h1', class_='title')
            if not title_elem:
                title_elem = soup.find('h1')
            
            if title_elem:
                # 移除不需要的子元素
                for elem in title_elem.find_all(class_='phpFree'):
                    elem.decompose()
                title = title_elem.get_text().strip()
            else:
                title = "Unknown_Title"
            
            # 提取模特名
            model_elem = soup.find('div', class_='userInfo')
            if model_elem:
                model_elem = model_elem.find('div', class_='usernameWrap')
                if model_elem:
                    model_name = model_elem.get_text().strip()
                else:
                    model_name = ""
            else:
                # 尝试其他可能的位置
                model_elem = soup.find('div', class_='usernameWrap')
                if model_elem:
                    model_name = model_elem.get_text().strip()
                else:
                    model_name = ""
            
            return self._clean_title(title), self._clean_title(model_name)
            
        except Exception as e:
            logger.warning(f"提取视频信息失败: {e}")
            return "Unknown_Title", "Unknown_Model"
    
    def download_single_video(self, url: str, save_dir: Optional[str] = None) -> Dict:
        """
        下载单个视频
        
        Args:
            url: Pornhub视频URL
            save_dir: 指定保存目录，如果为None则自动选择模特目录
            
        Returns:
            下载结果字典
        """
        logger.info(f"开始下载视频: {url}")
        
        # 提取视频信息
        title, model_name = self._extract_video_info(url)
        
        # 确定保存目录
        if save_dir:
            save_path = Path(save_dir)
            ensure_dir_exists(save_path)
        else:
            save_path = self._get_model_dir(model_name)
        
        # 配置yt-dlp选项
        ydl_opts = self.download_options.copy()
        ydl_opts['outtmpl'] = str(save_path / '%(title)s_%(id)s.%(ext)s')
        
        # 配置代理
        if self.proxies:
            ydl_opts['proxy'] = self.proxies['http']
        
        # 执行下载
        result = {
            'success': False,
            'url': url,
            'title': title,
            'model': model_name,
            'save_path': str(save_path),
            'filename': None,
            'file_path': None,
            'error': None,
            'file_size': 0
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 获取视频信息（不下载）
                info = ydl.extract_info(url, download=False)
                
                # 格式化文件名
                safe_title = self._clean_title(info.get('title', title))
                video_id = info.get('id', 'unknown')
                ext = info.get('ext', 'mp4')
                filename = f"{safe_title}_{video_id}.{ext}"
                file_path = save_path / filename
                
                # 检查文件是否已存在
                if file_path.exists():
                    logger.info(f"文件已存在，跳过下载: {file_path}")
                    result.update({
                        'success': True,
                        'filename': filename,
                        'file_path': str(file_path),
                        'file_size': file_path.stat().st_size,
                        'message': '文件已存在'
                    })
                    return result
                
                # 实际下载
                info = ydl.extract_info(url, download=True)
                
                # 获取下载后的文件路径
                downloaded_file = ydl.prepare_filename(info)
                
                if os.path.exists(downloaded_file):
                    result.update({
                        'success': True,
                        'filename': os.path.basename(downloaded_file),
                        'file_path': downloaded_file,
                        'file_size': os.path.getsize(downloaded_file),
                        'message': '下载成功'
                    })
                    logger.info(f"视频下载成功: {downloaded_file}")
                else:
                    raise Exception("下载完成但文件不存在")
                    
        except Exception as e:
            error_msg = str(e)
            result['error'] = error_msg
            logger.error(f"视频下载失败: {url}, 错误: {error_msg}")
            
            # 检查是否是会员内容
            if 'premium' in error_msg.lower() or 'login' in error_msg.lower():
                result['message'] = '需要会员登录或Cookie配置'
            elif 'geo' in error_msg.lower() or 'region' in error_msg.lower():
                result['message'] = '地区限制，可能需要代理'
            else:
                result['message'] = f'下载失败: {error_msg}'
        
        return result
    
    def download_multiple_videos(self, urls: List[str], save_dir: Optional[str] = None) -> List[Dict]:
        """
        批量下载视频
        
        Args:
            urls: Pornhub视频URL列表
            save_dir: 指定保存目录
            
        Returns:
            下载结果列表
        """
        results = []
        
        for i, url in enumerate(urls, 1):
            logger.info(f"下载进度: {i}/{len(urls)} - {url}")
            
            try:
                result = self.download_single_video(url, save_dir)
                results.append(result)
                
                # 添加索引信息
                result['index'] = i
                result['total'] = len(urls)
                
            except Exception as e:
                error_result = {
                    'success': False,
                    'url': url,
                    'error': str(e),
                    'message': f'批量下载异常: {str(e)}',
                    'index': i,
                    'total': len(urls)
                }
                results.append(error_result)
                logger.error(f"批量下载异常: {url}, 错误: {e}")
        
        return results
    
    def get_video_info_only(self, url: str) -> Dict:
        """
        仅获取视频信息，不下载
        
        Args:
            url: Pornhub视频URL
            
        Returns:
            视频信息字典
        """
        ydl_opts = {
            'simulate': True,  # 仅模拟，不下载
            'quiet': True,
            'no_warnings': True,
        }
        
        if self.proxies:
            ydl_opts['proxy'] = self.proxies['http']
        
        if self.cookies_file:
            ydl_opts['cookiefile'] = self.cookies_file
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'success': True,
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'description': info.get('description'),
                    'duration': info.get('duration'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'formats': info.get('formats', []),
                    'thumbnail': info.get('thumbnail'),
                    'webpage_url': info.get('webpage_url'),
                    'is_live': info.get('is_live', False),
                    'was_live': info.get('was_live', False)
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'获取视频信息失败: {str(e)}'
            }


# 便捷函数
def download_pronhub_video(url: str, save_dir: Optional[str] = None, config: Optional[Dict] = None) -> Dict:
    """
    下载单个Pornhub视频的便捷函数
    
    Args:
        url: Pornhub视频URL
        save_dir: 保存目录（可选）
        config: 配置字典（可选）
        
    Returns:
        下载结果
    """
    downloader = PornhubDownloader(config)
    return downloader.download_single_video(url, save_dir)


def download_pronhub_urls(urls: List[str], save_dir: Optional[str] = None, config: Optional[Dict] = None) -> List[Dict]:
    """
    批量下载Pornhub视频的便捷函数
    
    Args:
        urls: Pornhub视频URL列表
        save_dir: 保存目录（可选）
        config: 配置字典（可选）
        
    Returns:
        下载结果列表
    """
    downloader = PornhubDownloader(config)
    return downloader.download_multiple_videos(urls, save_dir)


def get_pronhub_video_info(url: str, config: Optional[Dict] = None) -> Dict:
    """
    获取Pornhub视频信息的便捷函数
    
    Args:
        url: Pornhub视频URL
        config: 配置字典（可选）
        
    Returns:
        视频信息
    """
    downloader = PornhubDownloader(config)
    return downloader.get_video_info_only(url)


def download_model_complete_directory(model_url: str, model_name: str, 
                                 base_save_dir: Optional[str] = None, 
                                 config: Optional[Dict] = None,
                                 max_videos: Optional[int] = None,
                                 progress_callback: Optional[callable] = None) -> Dict:
    """
    完整下载模特目录的所有视频
    
    Args:
        model_url: 模特页面URL
        model_name: 模特名称
        base_save_dir: 基础保存目录（可选）
        config: 配置字典（可选）
        max_videos: 最大下载数量限制（可选）
        progress_callback: 进度回调函数（可选）
        
    Returns:
        下载结果字典，包含统计信息
    """
    logger.info(f"开始完整下载模特目录: {model_name}")
    logger.info(f"模特URL: {model_url}")
    
    downloader = PornhubDownloader(config)
    
    # 确定保存目录
    if base_save_dir:
        save_dir = Path(base_save_dir) / f"[Channel] {model_name}"
    else:
        save_dir = downloader._get_model_dir(model_name)
    
    ensure_dir_exists(save_dir)
    
    result = {
        'success': False,
        'model_name': model_name,
        'model_url': model_url,
        'save_dir': str(save_dir),
        'total_videos': 0,
        'successful_downloads': 0,
        'failed_downloads': 0,
        'skipped_downloads': 0,
        'total_size': 0,
        'download_details': [],
        'errors': [],
        'start_time': None,
        'end_time': None
    }
    
    try:
        from datetime import datetime
        result['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if progress_callback:
            progress_callback(f"开始获取 {model_name} 的视频列表...")
        
        # 获取模特的所有视频URL
        video_urls = _get_model_all_videos(model_url, config)
        
        if not video_urls:
            result['errors'].append("无法获取模特视频列表")
            result['message'] = "无法获取模特视频列表"
            return result
        
        # 应用数量限制
        if max_videos and len(video_urls) > max_videos:
            video_urls = video_urls[:max_videos]
            if progress_callback:
                progress_callback(f"限制下载数量为: {max_videos}")
        
        result['total_videos'] = len(video_urls)
        
        if progress_callback:
            progress_callback(f"找到 {len(video_urls)} 个视频，开始下载...")
        
        # 批量下载
        for i, (title, url) in enumerate(video_urls, 1):
            try:
                if progress_callback:
                    progress_callback(f"下载进度: {i}/{len(video_urls)} - {title[:50]}...")
                
                # 检查文件是否已存在
                safe_title = downloader._clean_title(title)
                potential_files = list(save_dir.glob(f"{safe_title}_*.*"))
                
                if potential_files:
                    result['skipped_downloads'] += 1
                    if progress_callback:
                        progress_callback(f"跳过已存在: {title[:50]}...")
                    result['download_details'].append({
                        'title': title,
                        'url': url,
                        'status': 'skipped',
                        'reason': 'file_exists'
                    })
                    continue
                
                # 下载视频
                download_result = downloader.download_single_video(url, str(save_dir))
                
                if download_result['success']:
                    result['successful_downloads'] += 1
                    result['total_size'] += download_result.get('file_size', 0)
                    if progress_callback:
                        progress_callback(f"✅ 下载成功: {title[:50]}...")
                    result['download_details'].append({
                        'title': title,
                        'url': url,
                        'status': 'success',
                        'file_path': download_result.get('file_path'),
                        'file_size': download_result.get('file_size', 0)
                    })
                else:
                    result['failed_downloads'] += 1
                    error_msg = download_result.get('message', download_result.get('error', 'Unknown error'))
                    result['errors'].append(f"{title}: {error_msg}")
                    if progress_callback:
                        progress_callback(f"❌ 下载失败: {title[:50]}... - {error_msg}")
                    result['download_details'].append({
                        'title': title,
                        'url': url,
                        'status': 'failed',
                        'error': error_msg
                    })
                    
            except Exception as e:
                result['failed_downloads'] += 1
                error_msg = str(e)
                result['errors'].append(f"处理视频时异常: {error_msg}")
                if progress_callback:
                    progress_callback(f"❌ 处理异常: {error_msg}")
        
        result['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 判断整体成功
        result['success'] = result['successful_downloads'] > 0
        result['message'] = f"下载完成: 成功 {result['successful_downloads']}, 失败 {result['failed_downloads']}, 跳过 {result['skipped_downloads']}"
        
        return result
        
    except Exception as e:
        result['errors'].append(f"批量下载异常: {str(e)}")
        result['message'] = f"批量下载失败: {str(e)}"
        return result


def _get_model_all_videos(model_url: str, config: Optional[Dict] = None) -> List[Tuple[str, str]]:
    """
    获取模特的所有视频URL和标题
    
    Args:
        model_url: 模特页面URL
        config: 配置字典（可选）
        
    Returns:
        (标题, URL) 元组的列表
    """
    try:
        from core.modules.pronhub.pronhub import fetch_with_requests_pronhub
        
        logger.info(f"获取模特视频列表: {model_url}")
        
        # 使用现有的抓取函数获取视频列表
        online_set, title_to_url = fetch_with_requests_pronhub(
            model_url, logger, -1, config or {}, None, ""
        )
        
        # 转换为 (标题, URL) 元组列表
        video_list = []
        for title in online_set:
            url = title_to_url.get(title, "")
            if url:
                video_list.append((title, url))
        
        logger.info(f"获取到 {len(video_list)} 个视频")
        return video_list
        
    except Exception as e:
        logger.error(f"获取模特视频列表失败: {e}")
        return []


def batch_download_models(models_info: List[Tuple[str, str, str]], 
                       base_save_dir: Optional[str] = None,
                       config: Optional[Dict] = None,
                       max_videos_per_model: Optional[int] = None,
                       progress_callback: Optional[callable] = None) -> Dict:
    """
    批量下载多个模特的完整目录
    
    Args:
        models_info: [(model_name, model_url, save_dir)] 的列表
        base_save_dir: 基础保存目录（可选）
        config: 配置字典（可选）
        max_videos_per_model: 每个模特的最大下载数量（可选）
        progress_callback: 进度回调函数（可选）
        
    Returns:
        批量下载结果
    """
    logger.info(f"开始批量下载 {len(models_info)} 个模特的目录")
    
    results = {
        'success': False,
        'total_models': len(models_info),
        'successful_models': 0,
        'failed_models': 0,
        'total_videos': 0,
        'total_downloaded': 0,
        'total_size': 0,
        'model_results': [],
        'start_time': None,
        'end_time': None
    }
    
    try:
        from datetime import datetime
        results['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for i, (model_name, model_url, custom_save_dir) in enumerate(models_info, 1):
            try:
                if progress_callback:
                    progress_callback(f"处理模特 {i}/{len(models_info)}: {model_name}")
                
                # 确定保存目录
                save_dir = custom_save_dir or base_save_dir
                
                # 下载单个模特的完整目录
                model_result = download_model_complete_directory(
                    model_url=model_url,
                    model_name=model_name,
                    base_save_dir=save_dir,
                    config=config,
                    max_videos=max_videos_per_model,
                    progress_callback=lambda msg: progress_callback(f"  {msg}") if progress_callback else None
                )
                
                results['model_results'].append(model_result)
                
                if model_result['success']:
                    results['successful_models'] += 1
                    results['total_videos'] += model_result['total_videos']
                    results['total_downloaded'] += model_result['successful_downloads']
                    results['total_size'] += model_result['total_size']
                else:
                    results['failed_models'] += 1
                    
            except Exception as e:
                results['failed_models'] += 1
                error_msg = str(e)
                results['model_results'].append({
                    'model_name': model_name,
                    'success': False,
                    'error': error_msg,
                    'message': f"模特处理异常: {error_msg}"
                })
                if progress_callback:
                    progress_callback(f"❌ 模特 {model_name} 处理失败: {error_msg}")
        
        results['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        results['success'] = results['successful_models'] > 0
        
        return results
        
    except Exception as e:
        results['success'] = False
        results['error'] = f"批量下载异常: {str(e)}"
        return results


# 命令行测试接口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python downloader.py <pornhub_url> [save_dir]")
        sys.exit(1)
    
    url = sys.argv[1]
    save_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = download_pronhub_video(url, save_dir)
    
    if result['success']:
        print(f"下载成功: {result['file_path']}")
        print(f"文件大小: {result['file_size'] / (1024*1024):.2f} MB")
    else:
        print(f"下载失败: {result['message']}")
        sys.exit(1)