# PORN module initialization

# 统一下载器（推荐使用）
from .unified_downloader import (
    UnifiedDownloader,
    download_porn_video,
    download_porn_videos
)

# V1-Standard下载器（直接使用）
from .downloader import (
    PornDownloader,
    download_porn_video as download_porn_video_v1,
    download_porn_urls as download_porn_urls_v1
)

# V3-Advanced下载器（直接使用）
from .downloader_v3_fixed import (
    PornHubDownloaderV3Fixed
)

__all__ = [
    'UnifiedDownloader',          # 推荐的统一调度器
    'download_porn_video',        # 统一便捷函数
    'download_porn_videos',       # 统一便捷函数
    'PornDownloader',             # V1原始类
    'download_porn_video_v1',     # V1直接函数
    'download_porn_urls_v1',      # V1直接函数
    'PornHubDownloaderV3Fixed',   # V3原始类
]