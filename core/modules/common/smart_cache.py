"""
智能缓存模块 - 支持增量更新和页级时间戳管理
减少重复抓取，提高抓取效率
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Set, Dict, List, Optional, Tuple, Any
from pathlib import Path
import re


class SmartCache:
    """
    智能缓存管理器
    
    功能特性：
    1. 页级时间戳 - 记录每页最后抓取时间
    2. 增量更新 - 只抓取新增页面
    3. 智能过期 - 根据配置自动判断缓存是否过期
    4. 线程安全 - 支持多线程并发访问
    """
    
    def __init__(self, cache_dir: str, config: dict = None):
        """
        初始化智能缓存管理器
        
        Args:
            cache_dir: 缓存目录路径
            config: 配置字典
        """
        self.cache_dir = cache_dir
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 线程锁，确保线程安全
        self._lock = threading.RLock()
        
        # 缓存配置
        cache_config = self.config.get('cache', {})
        self.enabled = cache_config.get('enabled', True)
        self.expiration_days = cache_config.get('expiration_days', 7)
        self.incremental_update = cache_config.get('incremental_update', True)
        self.page_expiry_hours = cache_config.get('page_expiry_hours', 24)
        
        # 确保缓存目录存在
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        
        # 内存中的缓存数据（减少磁盘IO）
        self._memory_cache: Dict[str, dict] = {}
    
    def _get_cache_path(self, model_name: str) -> str:
        """获取模特缓存文件路径"""
        safe_name = re.sub(r'[^\w\-]', '_', model_name)
        return os.path.join(self.cache_dir, f"{safe_name}.json")
    
    def _load_cache_file(self, cache_path: str) -> dict:
        """从文件加载缓存数据"""
        if not os.path.exists(cache_path):
            return self._create_empty_cache()
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 验证缓存结构
                if not self._validate_cache_structure(data):
                    self.logger.warning(f"缓存文件结构无效，创建新缓存: {cache_path}")
                    return self._create_empty_cache()
                return data
        except json.JSONDecodeError as e:
            self.logger.warning(f"缓存文件解析失败: {e}，创建新缓存")
            return self._create_empty_cache()
        except Exception as e:
            self.logger.error(f"加载缓存失败: {e}")
            return self._create_empty_cache()
    
    def _save_cache_file(self, cache_path: str, data: dict):
        """保存缓存数据到文件"""
        try:
            # 使用临时文件写入，然后重命名，避免写入中断导致文件损坏
            temp_path = f"{cache_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 原子重命名
            if os.path.exists(cache_path):
                os.replace(temp_path, cache_path)
            else:
                os.rename(temp_path, cache_path)
                
        except Exception as e:
            self.logger.error(f"保存缓存失败: {e}")
    
    def _create_empty_cache(self) -> dict:
        """创建空的缓存数据结构"""
        return {
            'version': '2.0',  # 缓存版本号
            'model_name': '',
            'url': '',
            'video_titles': [],  # 兼容旧版本
            'videos': {},  # 新的视频数据结构 {title: {url, page, timestamp}}
            'page_timestamps': {},  # 每页最后抓取时间 {page_num: timestamp}
            'last_page_fetched': 0,  # 最后抓取的页码
            'total_pages': 0,  # 总页数
            'last_updated': None,
            'created_at': datetime.now().isoformat(),
            'fetch_count': 0,  # 抓取次数统计
            'metadata': {
                'total_videos': 0,
                'last_incremental_update': None,
                'full_fetch_count': 0
            }
        }
    
    def _validate_cache_structure(self, data: dict) -> bool:
        """验证缓存数据结构是否有效"""
        required_fields = ['video_titles', 'videos', 'page_timestamps', 'last_updated']
        return all(field in data for field in required_fields)
    
    def load(self, model_name: str) -> dict:
        """
        加载模特缓存数据
        
        Args:
            model_name: 模特名称
            
        Returns:
            缓存数据字典
        """
        if not self.enabled:
            return self._create_empty_cache()
        
        with self._lock:
            # 先检查内存缓存
            if model_name in self._memory_cache:
                return self._memory_cache[model_name].copy()
            
            cache_path = self._get_cache_path(model_name)
            data = self._load_cache_file(cache_path)
            data['model_name'] = model_name
            
            # 迁移旧版本数据
            if 'videos' not in data:
                data['videos'] = {}
            if 'page_timestamps' not in data:
                data['page_timestamps'] = {}
            
            # 将旧格式视频标题迁移到新格式
            if data['video_titles'] and not data['videos']:
                for title in data['video_titles']:
                    data['videos'][title] = {
                        'url': '',
                        'page': 0,
                        'timestamp': data.get('last_updated') or datetime.now().isoformat()
                    }
            
            # 更新内存缓存
            self._memory_cache[model_name] = data.copy()
            
            return data
    
    def save(self, model_name: str, data: dict):
        """
        保存模特缓存数据
        
        Args:
            model_name: 模特名称
            data: 缓存数据字典
        """
        if not self.enabled:
            return
        
        with self._lock:
            cache_path = self._get_cache_path(model_name)
            
            # 确保metadata字段存在
            if 'metadata' not in data:
                data['metadata'] = {}
            
            # 更新元数据
            data['last_updated'] = datetime.now().isoformat()
            data['metadata']['total_videos'] = len(data.get('videos', {}))
            
            # 同步 video_titles（兼容旧版本）
            data['video_titles'] = list(data.get('videos', {}).keys())
            
            # 保存到文件
            self._save_cache_file(cache_path, data)
            
            # 更新内存缓存
            self._memory_cache[model_name] = data.copy()
            
            self.logger.debug(f"缓存已保存: {model_name} ({len(data['videos'])} 个视频)")
    
    def get_last_page(self, model_name: str) -> int:
        """
        获取模特最后抓取的页码
        
        Args:
            model_name: 模特名称
            
        Returns:
            最后抓取的页码，如果没有缓存返回 0
        """
        data = self.load(model_name)
        return data.get('last_page_fetched', 0)
    
    def should_update_page(self, model_name: str, page_num: int) -> bool:
        """
        判断某页是否需要更新
        
        Args:
            model_name: 模特名称
            page_num: 页码
            
        Returns:
            是否需要更新该页
        """
        if not self.enabled or not self.incremental_update:
            return True
        
        data = self.load(model_name)
        page_timestamps = data.get('page_timestamps', {})
        
        # 如果该页没有记录，需要更新
        if str(page_num) not in page_timestamps:
            return True
        
        # 检查是否过期
        last_fetch = page_timestamps[str(page_num)]
        try:
            last_fetch_time = datetime.fromisoformat(last_fetch)
            expiry_time = datetime.now() - timedelta(hours=self.page_expiry_hours)
            
            if last_fetch_time < expiry_time:
                self.logger.debug(f"页面 {page_num} 已过期，需要更新")
                return True
            else:
                self.logger.debug(f"页面 {page_num} 仍在有效期内，跳过")
                return False
        except Exception as e:
            self.logger.warning(f"解析时间戳失败: {e}")
            return True
    
    def update_page_timestamp(self, model_name: str, page_num: int):
        """
        更新某页的时间戳
        
        Args:
            model_name: 模特名称
            page_num: 页码
        """
        data = self.load(model_name)
        
        if 'page_timestamps' not in data:
            data['page_timestamps'] = {}
        
        data['page_timestamps'][str(page_num)] = datetime.now().isoformat()
        
        # 更新最后抓取页码
        if page_num > data.get('last_page_fetched', 0):
            data['last_page_fetched'] = page_num
        
        self.save(model_name, data)
    
    def add_videos(self, model_name: str, videos: List[Tuple[str, str, int]]):
        """
        添加视频到缓存
        
        Args:
            model_name: 模特名称
            videos: 视频列表 [(title, url, page_num), ...]
        """
        data = self.load(model_name)
        
        if 'videos' not in data:
            data['videos'] = {}
        
        current_time = datetime.now().isoformat()
        new_count = 0
        
        for title, url, page_num in videos:
            if title not in data['videos']:
                new_count += 1
            
            data['videos'][title] = {
                'url': url,
                'page': page_num,
                'timestamp': current_time
            }
        
        if new_count > 0:
            self.logger.debug(f"新增 {new_count} 个视频到缓存: {model_name}")
        
        self.save(model_name, data)
    
    def get_cached_titles(self, model_name: str) -> Set[str]:
        """
        获取已缓存的视频标题集合
        
        Args:
            model_name: 模特名称
            
        Returns:
            视频标题集合
        """
        data = self.load(model_name)
        return set(data.get('videos', {}).keys())
    
    def get_video_url(self, model_name: str, title: str) -> Optional[str]:
        """
        获取视频的 URL
        
        Args:
            model_name: 模特名称
            title: 视频标题
            
        Returns:
            视频 URL，如果不存在返回 None
        """
        data = self.load(model_name)
        video = data.get('videos', {}).get(title)
        return video.get('url') if video else None
    
    def is_cache_valid(self, model_name: str) -> bool:
        """
        检查缓存是否有效（未过期）
        
        Args:
            model_name: 模特名称
            
        Returns:
            缓存是否有效
        """
        if not self.enabled:
            return False
        
        data = self.load(model_name)
        last_updated = data.get('last_updated')
        
        if not last_updated:
            return False
        
        try:
            last_update_time = datetime.fromisoformat(last_updated)
            expiry_time = datetime.now() - timedelta(days=self.expiration_days)
            
            return last_update_time > expiry_time
        except Exception as e:
            self.logger.warning(f"检查缓存有效性失败: {e}")
            return False
    
    def get_cache_stats(self, model_name: str) -> dict:
        """
        获取缓存统计信息
        
        Args:
            model_name: 模特名称
            
        Returns:
            统计信息字典
        """
        data = self.load(model_name)
        
        return {
            'total_videos': len(data.get('videos', {})),
            'last_page_fetched': data.get('last_page_fetched', 0),
            'total_pages': data.get('total_pages', 0),
            'last_updated': data.get('last_updated'),
            'fetch_count': data.get('fetch_count', 0),
            'cached_pages': len(data.get('page_timestamps', {}))
        }
    
    def clear_cache(self, model_name: Optional[str] = None):
        """
        清除缓存
        
        Args:
            model_name: 模特名称，如果为 None 则清除所有缓存
        """
        with self._lock:
            if model_name:
                cache_path = self._get_cache_path(model_name)
                if os.path.exists(cache_path):
                    os.remove(cache_path)
                    self.logger.info(f"已清除缓存: {model_name}")
                
                if model_name in self._memory_cache:
                    del self._memory_cache[model_name]
            else:
                # 清除所有缓存
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.json'):
                        os.remove(os.path.join(self.cache_dir, filename))
                
                self._memory_cache.clear()
                self.logger.info("已清除所有缓存")
    
    def get_incremental_fetch_range(self, model_name: str, max_pages: int = -1) -> Tuple[int, int]:
        """
        获取增量抓取的范围
        
        Args:
            model_name: 模特名称
            max_pages: 最大页数限制
            
        Returns:
            (起始页码, 结束页码)
        """
        if not self.enabled or not self.incremental_update:
            return (1, max_pages if max_pages > 0 else 9999)
        
        data = self.load(model_name)
        last_page = data.get('last_page_fetched', 0)
        
        if last_page == 0:
            # 没有缓存，从第一页开始
            self.logger.info(f"{model_name}: 无缓存，执行完整抓取")
            return (1, max_pages if max_pages > 0 else 9999)
        
        # 检查前几页是否需要刷新（防止遗漏新发布的视频）
        pages_to_refresh = []
        check_pages = min(3, last_page)  # 检查前3页
        
        for page in range(1, check_pages + 1):
            if self.should_update_page(model_name, page):
                pages_to_refresh.append(page)
        
        if pages_to_refresh:
            self.logger.info(f"{model_name}: 检测到前 {len(pages_to_refresh)} 页需要刷新")
            return (1, max_pages if max_pages > 0 else 9999)
        
        # 从最后抓取的页码继续
        self.logger.info(f"{model_name}: 增量抓取，从第 {last_page + 1} 页开始")
        return (last_page + 1, max_pages if max_pages > 0 else 9999)
    
    def mark_full_fetch_completed(self, model_name: str, total_pages: int):
        """
        标记完整抓取完成
        
        Args:
            model_name: 模特名称
            total_pages: 总页数
        """
        data = self.load(model_name)
        
        data['total_pages'] = total_pages
        data['last_page_fetched'] = total_pages
        data['fetch_count'] = data.get('fetch_count', 0) + 1
        data['metadata']['full_fetch_count'] = data['metadata'].get('full_fetch_count', 0) + 1
        data['metadata']['last_incremental_update'] = datetime.now().isoformat()
        
        self.save(model_name, data)
    
    def update_missing_videos(self, model_name: str, missing_videos: List[Tuple[str, str]]):
        """
        更新缺失视频列表（用于后续只更新还缺失的视频）
        
        Args:
            model_name: 模特名称
            missing_videos: 缺失视频列表 [(title, url), ...]
        """
        data = self.load(model_name)
        
        if 'missing_videos' not in data:
            data['missing_videos'] = {}
        
        current_time = datetime.now().isoformat()
        
        for title, url in missing_videos:
            data['missing_videos'][title] = {
                'url': url,
                'last_missing': current_time,
                'status': 'missing'  # missing, downloaded
            }
        
        # 更新元数据
        if 'metadata' not in data:
            data['metadata'] = {}
        data['metadata']['last_missing_update'] = current_time
        data['metadata']['missing_count'] = len(data['missing_videos'])
        
        self.save(model_name, data)
        self.logger.info(f"已更新缺失视频列表: {model_name} ({len(missing_videos)} 个)")
    
    def get_missing_videos(self, model_name: str) -> List[Tuple[str, str]]:
        """
        获取当前缺失的视频列表（只返回状态为missing的视频）
        
        Args:
            model_name: 模特名称
            
        Returns:
            缺失视频列表 [(title, url), ...]
        """
        data = self.load(model_name)
        missing_data = data.get('missing_videos', {})
        
        result = []
        for title, info in missing_data.items():
            if info.get('status') == 'missing':
                result.append((title, info.get('url', '')))
        
        return result
    
    def mark_video_downloaded(self, model_name: str, title: str):
        """
        标记视频已下载（后续不再出现在缺失列表中）
        
        Args:
            model_name: 模特名称
            title: 视频标题
        """
        data = self.load(model_name)
        missing_data = data.get('missing_videos', {})
        
        if title in missing_data:
            missing_data[title]['status'] = 'downloaded'
            missing_data[title]['downloaded_at'] = datetime.now().isoformat()
            
            # 更新缺失数量
            missing_count = sum(1 for v in missing_data.values() if v.get('status') == 'missing')
            if 'metadata' not in data:
                data['metadata'] = {}
            data['metadata']['missing_count'] = missing_count
            
            self.save(model_name, data)
            self.logger.debug(f"已标记视频为已下载: {model_name} - {title}")


# 便捷函数
def create_smart_cache(cache_dir: str, config: dict = None) -> SmartCache:
    """
    创建智能缓存实例的工厂函数
    
    Args:
        cache_dir: 缓存目录
        config: 配置字典
        
    Returns:
        SmartCache 实例
    """
    return SmartCache(cache_dir, config)


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(message)s'
    )
    
    print("=" * 60)
    print("智能缓存系统测试")
    print("=" * 60)
    
    # 创建测试缓存
    test_config = {
        'cache': {
            'enabled': True,
            'expiration_days': 7,
            'incremental_update': True,
            'page_expiry_hours': 24
        }
    }
    
    cache = SmartCache('test_cache', test_config)
    
    # 测试添加视频
    test_videos = [
        ("Video 1", "http://example.com/1", 1),
        ("Video 2", "http://example.com/2", 1),
        ("Video 3", "http://example.com/3", 2),
    ]
    
    cache.add_videos("TestModel", test_videos)
    cache.update_page_timestamp("TestModel", 1)
    cache.update_page_timestamp("TestModel", 2)
    
    # 测试获取缓存
    titles = cache.get_cached_titles("TestModel")
    print(f"\n缓存的视频标题: {titles}")
    
    # 测试统计
    stats = cache.get_cache_stats("TestModel")
    print(f"\n缓存统计: {stats}")
    
    # 测试增量抓取范围
    start, end = cache.get_incremental_fetch_range("TestModel")
    print(f"\n增量抓取范围: 第 {start} 页 到 第 {end} 页")
    
    # 清理测试缓存
    cache.clear_cache("TestModel")
    print("\n测试完成，缓存已清理")
