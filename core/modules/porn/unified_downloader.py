# -*- coding: utf-8 -*-
"""
统一下载器调度模块
整合V1（yt-dlp）和V3（Selenium+CDP）两个版本
支持版本选择、自动降级、进度回调等功能
"""

import logging
from typing import Dict, Optional, Callable

from .downloader import PornDownloader
from .downloader_v3_fixed import PornHubDownloaderV3Fixed

logger = logging.getLogger(__name__)


class UnifiedDownloader:
    """统一的PORN下载器
    
    支持两个版本：
    - V1-Standard: 基于yt-dlp的完整下载（默认）
    - V3-Advanced: 基于Selenium+CDP的网络捕获
    
    支持特性：
    1. 版本选择（v1/v3/auto）
    2. 自动降级（V1失败自动切V3）
    3. 进度回调
    4. 统一接口
    """
    
    # 版本常量
    VERSION_V1 = "v1"
    VERSION_V3 = "v3"
    VERSION_AUTO = "auto"
    
    def __init__(self, 
                 config: Optional[Dict] = None,
                 version: str = "auto",
                 enable_fallback: bool = True,
                 progress_callback: Optional[Callable] = None):
        """
        初始化统一下载器
        
        Args:
            config: 配置字典
            version: 版本选择 - "v1"、"v3"、"auto"（默认自动）
            enable_fallback: 是否启用自动降级（V1失败→V3）
            progress_callback: 进度回调函数，签名: callback(progress_dict)
        """
        self.config = config or {}
        self.version = version
        self.enable_fallback = enable_fallback
        self.progress_callback = progress_callback
        
        # 初始化两个版本的下载器
        self.downloader_v1 = None
        self.downloader_v3 = None
        self.current_version = None
        
        # 初始化V1
        try:
            self.downloader_v1 = PornDownloader(
                config=self.config,
                progress_callback=self._wrap_callback("V1-Standard")
            )
            logger.info("✅ V1-Standard下载器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ V1-Standard初始化失败: {str(e)[:100]}")
        
        # 初始化V3
        try:
            self.downloader_v3 = PornHubDownloaderV3Fixed(
                config=self.config
            )
            logger.info("✅ V3-Advanced下载器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ V3-Advanced初始化失败: {str(e)[:100]}")
    
    def _wrap_callback(self, version_tag: str) -> Callable:
        """包装进度回调，添加版本标签"""
        def wrapper(info: Dict):
            if self.progress_callback:
                info['_version'] = version_tag
                self.progress_callback(info)
        return wrapper
    
    def select_version(self, url: str) -> str:
        """
        根据配置选择合适的版本
        
        Args:
            url: 视频URL
            
        Returns:
            选择的版本: "v1" 或 "v3"
        """
        if self.version == self.VERSION_AUTO:
            # 自动模式：优先V1（更稳定）
            if self.downloader_v1:
                return self.VERSION_V1
            elif self.downloader_v3:
                logger.warning("V1不可用，自动切换到V3")
                return self.VERSION_V3
            else:
                raise RuntimeError("没有可用的下载器")
        
        elif self.version == self.VERSION_V1:
            if not self.downloader_v1:
                raise RuntimeError("V1下载器未初始化")
            return self.VERSION_V1
        
        elif self.version == self.VERSION_V3:
            if not self.downloader_v3:
                raise RuntimeError("V3下载器未初始化")
            return self.VERSION_V3
        
        else:
            raise ValueError(f"未知的版本: {self.version}")
    
    def download_video(self, 
                      url: str, 
                      save_dir: Optional[str] = None) -> Dict:
        """
        下载单个视频（统一接口）
        
        Args:
            url: 视频URL
            save_dir: 保存目录
            
        Returns:
            结果字典
        """
        result = {
            'success': False,
            'url': url,
            'file_path': None,
            'error': None,
            'message': None,
            'version': None
        }
        
        try:
            # 选择版本
            version = self.select_version(url)
            logger.info(f"📥 [统一下载器] 选择版本: {version.upper()}")
            result['version'] = version
            self.current_version = version
            
            # 执行下载
            if version == self.VERSION_V1:
                logger.info(f"🔄 V1-Standard开始下载...")
                result = self.downloader_v1.download_video(url, save_dir)
                result['version'] = self.VERSION_V1
                
                # 如果失败且启用降级，尝试V3
                if not result.get('success') and self.enable_fallback and self.downloader_v3:
                    logger.warning(f"⚠️ V1失败，尝试降级到V3...")
                    result = self.downloader_v3.download_video(url, save_dir)
                    result['version'] = self.VERSION_V3
            
            elif version == self.VERSION_V3:
                logger.info(f"🔄 V3-Advanced开始下载...")
                result = self.downloader_v3.download_video(url, save_dir)
                result['version'] = self.VERSION_V3
            
            return result
        
        except Exception as e:
            result['error'] = str(e)
            result['message'] = f'异常: {str(e)[:100]}'
            logger.error(f"❌ 下载异常: {e}", exc_info=True)
            return result
    
    def download_multiple_videos(self, 
                                urls: list, 
                                save_dir: Optional[str] = None) -> list:
        """
        下载多个视频
        
        Args:
            urls: 视频URL列表
            save_dir: 保存目录
            
        Returns:
            结果列表
        """
        results = []
        for i, url in enumerate(urls, 1):
            logger.info(f"下载 {i}/{len(urls)}: {url[:80]}")
            result = self.download_video(url, save_dir)
            results.append(result)
        
        return results
    
    def download_model_videos(self,
                             model_url: str,
                             model_name: str,
                             base_save_dir: Optional[str] = None,
                             max_videos: Optional[int] = None) -> Dict:
        """
        下载模特的视频（针对V1的特殊功能）
        
        Args:
            model_url: 模特页面URL
            model_name: 模特名称
            base_save_dir: 基础保存目录
            max_videos: 最多下载视频数
            
        Returns:
            结果字典
        """
        # 这个功能只有V1支持，直接调用V1
        if not self.downloader_v1:
            return {
                'success': False,
                'error': 'V1下载器未初始化',
                'message': '模特视频下载需要V1-Standard支持'
            }
        
        logger.info(f"📥 [统一下载器] 下载模特视频: {model_name}")
        return self.downloader_v1.download_model_complete_directory(
            model_url=model_url,
            model_name=model_name,
            base_save_dir=base_save_dir,
            max_videos=max_videos,
            config=self.config
        )


# 便捷函数
def download_porn_video(url: str, 
                       save_dir: Optional[str] = None,
                       config: Optional[Dict] = None,
                       version: str = "auto") -> Dict:
    """
    便捷函数：下载单个视频
    
    Args:
        url: 视频URL
        save_dir: 保存目录
        config: 配置
        version: 版本选择
        
    Returns:
        结果字典
    """
    downloader = UnifiedDownloader(config=config, version=version)
    return downloader.download_video(url, save_dir)


def download_porn_videos(urls: list,
                        save_dir: Optional[str] = None,
                        config: Optional[Dict] = None,
                        version: str = "auto") -> list:
    """
    便捷函数：下载多个视频
    
    Args:
        urls: 视频URL列表
        save_dir: 保存目录
        config: 配置
        version: 版本选择
        
    Returns:
        结果列表
    """
    downloader = UnifiedDownloader(config=config, version=version)
    return downloader.download_multiple_videos(urls, save_dir)
