"""
数据库存储模块
提供SQLite数据库存储支持，替代JSON文件存储
"""

import sqlite3
import json
import threading
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseStorage:
    """数据库存储管理器"""
    
    def __init__(self, db_path: str, config: dict = None):
        """
        初始化数据库存储
        
        Args:
            db_path: 数据库文件路径
            config: 配置字典
        """
        self.db_path = Path(db_path)
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 确保数据库目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 初始化数据库
        self._initialize_database()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def _initialize_database(self):
        """初始化数据库表结构"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建模特信息表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS models (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建视频信息表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        url TEXT,
                        page_number INTEGER DEFAULT 0,
                        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE CASCADE,
                        UNIQUE(model_id, title)
                    )
                ''')
                
                # 创建缓存元数据表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cache_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_id INTEGER NOT NULL,
                        last_page_fetched INTEGER DEFAULT 0,
                        total_pages INTEGER DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        fetch_count INTEGER DEFAULT 0,
                        full_fetch_count INTEGER DEFAULT 0,
                        FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE CASCADE,
                        UNIQUE(model_id)
                    )
                ''')
                
                # 创建页面时间戳表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS page_timestamps (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_id INTEGER NOT NULL,
                        page_number INTEGER NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE CASCADE,
                        UNIQUE(model_id, page_number)
                    )
                ''')
                
                # 创建缺失视频表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS missing_videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        url TEXT,
                        last_missing TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'missing',  -- missing, downloaded
                        downloaded_at TIMESTAMP NULL,
                        FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE CASCADE,
                        UNIQUE(model_id, title)
                    )
                ''')
                
                # 创建索引优化查询性能
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_model_title ON videos(model_id, title)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_fetched_at ON videos(fetched_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_page_timestamps_model_page ON page_timestamps(model_id, page_number)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_missing_videos_model_status ON missing_videos(model_id, status)')
                
                conn.commit()
                self.logger.info(f"数据库初始化完成: {self.db_path}")
                
        except Exception as e:
            self.logger.error(f"数据库初始化失败: {e}")
            raise
    
    def add_or_update_model(self, model_name: str, url: str = "") -> int:
        """
        添加或更新模特信息
        
        Args:
            model_name: 模特名称
            url: 模特URL
            
        Returns:
            模特ID
        """
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 插入或更新模特信息
                    cursor.execute('''
                        INSERT INTO models (name, url, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(name) DO UPDATE SET
                            url = excluded.url,
                            updated_at = CURRENT_TIMESTAMP
                    ''', (model_name, url))
                    
                    # 获取插入的ID
                    model_id = cursor.lastrowid
                    if model_id is None:
                        # 如果是更新，需要查询ID
                        cursor.execute('SELECT id FROM models WHERE name = ?', (model_name,))
                        result = cursor.fetchone()
                        model_id = result['id'] if result else 0
                    
                    conn.commit()
                    return model_id
                    
            except Exception as e:
                self.logger.error(f"添加/更新模特失败: {e}")
                raise
    
    def add_videos(self, model_name: str, videos: List[Tuple[str, str, int]]) -> int:
        """
        添加视频信息
        
        Args:
            model_name: 模特名称
            videos: 视频列表 [(title, url, page_number), ...]
            
        Returns:
            新增视频数量
        """
        with self._lock:
            try:
                model_id = self.add_or_update_model(model_name)
                new_count = 0
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    for title, url, page_number in videos:
                        cursor.execute('''
                            INSERT INTO videos (model_id, title, url, page_number, fetched_at)
                            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                            ON CONFLICT(model_id, title) DO UPDATE SET
                                url = excluded.url,
                                page_number = excluded.page_number,
                                fetched_at = CURRENT_TIMESTAMP
                        ''', (model_id, title, url, page_number))
                        
                        # 如果是新插入的行，计数加1
                        if cursor.rowcount > 0:
                            new_count += 1
                    
                    # 更新缓存元数据
                    cursor.execute('''
                        INSERT INTO cache_metadata (model_id, last_updated)
                        VALUES (?, CURRENT_TIMESTAMP)
                        ON CONFLICT(model_id) DO UPDATE SET
                            last_updated = CURRENT_TIMESTAMP
                    ''', (model_id,))
                    
                    conn.commit()
                    self.logger.debug(f"添加了 {new_count} 个新视频到数据库")
                    return new_count
                    
            except Exception as e:
                self.logger.error(f"添加视频失败: {e}")
                raise
    
    def get_cached_titles(self, model_name: str) -> List[str]:
        """
        获取已缓存的视频标题
        
        Args:
            model_name: 模特名称
            
        Returns:
            视频标题列表
        """
        try:
            model_id = self._get_model_id(model_name)
            if not model_id:
                return []
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT title FROM videos WHERE model_id = ?
                ''', (model_id,))
                
                return [row['title'] for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"获取缓存标题失败: {e}")
            return []
    
    def get_video_url(self, model_name: str, title: str) -> Optional[str]:
        """
        获取视频URL
        
        Args:
            model_name: 模特名称
            title: 视频标题
            
        Returns:
            视频URL，如果不存在返回None
        """
        try:
            model_id = self._get_model_id(model_name)
            if not model_id:
                return None
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT url FROM videos WHERE model_id = ? AND title = ?
                ''', (model_id, title))
                
                result = cursor.fetchone()
                return result['url'] if result else None
                
        except Exception as e:
            self.logger.error(f"获取视频URL失败: {e}")
            return None
    
    def update_page_timestamp(self, model_name: str, page_number: int):
        """
        更新页面时间戳
        
        Args:
            model_name: 模特名称
            page_number: 页码
        """
        with self._lock:
            try:
                model_id = self.add_or_update_model(model_name)
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO page_timestamps (model_id, page_number, timestamp)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(model_id, page_number) DO UPDATE SET
                            timestamp = CURRENT_TIMESTAMP
                    ''', (model_id, page_number))
                    conn.commit()
                    
            except Exception as e:
                self.logger.error(f"更新页面时间戳失败: {e}")
    
    def should_update_page(self, model_name: str, page_number: int, expiry_hours: int = 24) -> bool:
        """
        判断页面是否需要更新
        
        Args:
            model_name: 模特名称
            page_number: 页码
            expiry_hours: 过期小时数
            
        Returns:
            是否需要更新
        """
        try:
            model_id = self._get_model_id(model_name)
            if not model_id:
                return True
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp FROM page_timestamps 
                    WHERE model_id = ? AND page_number = ?
                ''', (model_id, page_number))
                
                result = cursor.fetchone()
                if not result:
                    return True
                
                # 检查是否过期
                last_timestamp = datetime.fromisoformat(result['timestamp'])
                expiry_time = datetime.now() - timedelta(hours=expiry_hours)
                
                return last_timestamp < expiry_time
                
        except Exception as e:
            self.logger.warning(f"检查页面更新状态失败: {e}")
            return True
    
    def get_last_page_fetched(self, model_name: str) -> int:
        """
        获取最后抓取的页码
        
        Args:
            model_name: 模特名称
            
        Returns:
            最后抓取的页码
        """
        try:
            model_id = self._get_model_id(model_name)
            if not model_id:
                return 0
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT last_page_fetched FROM cache_metadata WHERE model_id = ?
                ''', (model_id,))
                
                result = cursor.fetchone()
                return result['last_page_fetched'] if result else 0
                
        except Exception as e:
            self.logger.error(f"获取最后抓取页码失败: {e}")
            return 0
    
    def update_cache_metadata(self, model_name: str, **kwargs):
        """
        更新缓存元数据
        
        Args:
            model_name: 模特名称
            **kwargs: 要更新的字段
        """
        with self._lock:
            try:
                model_id = self.add_or_update_model(model_name)
                
                # 构建更新SQL
                set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
                values = list(kwargs.values()) + [model_id]
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(f'''
                        INSERT INTO cache_metadata (model_id)
                        VALUES (?)
                        ON CONFLICT(model_id) DO UPDATE SET
                            {set_clause},
                            last_updated = CURRENT_TIMESTAMP
                    ''', values)
                    conn.commit()
                    
            except Exception as e:
                self.logger.error(f"更新缓存元数据失败: {e}")
    
    def update_missing_videos(self, model_name: str, missing_videos: List[Tuple[str, str]]):
        """
        更新缺失视频列表
        
        Args:
            model_name: 模特名称
            missing_videos: 缺失视频列表 [(title, url), ...]
        """
        with self._lock:
            try:
                model_id = self.add_or_update_model(model_name)
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 更新缺失视频状态
                    for title, url in missing_videos:
                        cursor.execute('''
                            INSERT INTO missing_videos (model_id, title, url, last_missing, status)
                            VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'missing')
                            ON CONFLICT(model_id, title) DO UPDATE SET
                                url = excluded.url,
                                last_missing = CURRENT_TIMESTAMP,
                                status = 'missing'
                        ''', (model_id, title, url))
                    
                    conn.commit()
                    self.logger.info(f"更新了 {len(missing_videos)} 个缺失视频")
                    
            except Exception as e:
                self.logger.error(f"更新缺失视频失败: {e}")
    
    def get_missing_videos(self, model_name: str) -> List[Tuple[str, str]]:
        """
        获取缺失视频列表
        
        Args:
            model_name: 模特名称
            
        Returns:
            缺失视频列表 [(title, url), ...]
        """
        try:
            model_id = self._get_model_id(model_name)
            if not model_id:
                return []
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT title, url FROM missing_videos 
                    WHERE model_id = ? AND status = 'missing'
                ''', (model_id,))
                
                return [(row['title'], row['url']) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"获取缺失视频失败: {e}")
            return []
    
    def mark_video_downloaded(self, model_name: str, title: str):
        """
        标记视频已下载
        
        Args:
            model_name: 模特名称
            title: 视频标题
        """
        with self._lock:
            try:
                model_id = self._get_model_id(model_name)
                if not model_id:
                    return
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE missing_videos 
                        SET status = 'downloaded', downloaded_at = CURRENT_TIMESTAMP
                        WHERE model_id = ? AND title = ?
                    ''', (model_id, title))
                    conn.commit()
                    
            except Exception as e:
                self.logger.error(f"标记视频已下载失败: {e}")
    
    def get_cache_stats(self, model_name: str) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Args:
            model_name: 模特名称
            
        Returns:
            统计信息字典
        """
        try:
            model_id = self._get_model_id(model_name)
            if not model_id:
                return {}
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取视频总数
                cursor.execute('SELECT COUNT(*) as video_count FROM videos WHERE model_id = ?', (model_id,))
                video_count = cursor.fetchone()['video_count']
                
                # 获取缓存元数据
                cursor.execute('''
                    SELECT last_page_fetched, total_pages, last_updated, fetch_count
                    FROM cache_metadata WHERE model_id = ?
                ''', (model_id,))
                metadata = cursor.fetchone()
                
                # 获取页面时间戳数量
                cursor.execute('SELECT COUNT(*) as page_count FROM page_timestamps WHERE model_id = ?', (model_id,))
                page_count = cursor.fetchone()['page_count']
                
                return {
                    'total_videos': video_count,
                    'last_page_fetched': metadata['last_page_fetched'] if metadata else 0,
                    'total_pages': metadata['total_pages'] if metadata else 0,
                    'last_updated': metadata['last_updated'] if metadata else None,
                    'fetch_count': metadata['fetch_count'] if metadata else 0,
                    'cached_pages': page_count
                }
                
        except Exception as e:
            self.logger.error(f"获取缓存统计失败: {e}")
            return {}
    
    def _get_model_id(self, model_name: str) -> Optional[int]:
        """获取模特ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM models WHERE name = ?', (model_name,))
                result = cursor.fetchone()
                return result['id'] if result else None
        except Exception:
            return None
    
    def clear_cache(self, model_name: Optional[str] = None):
        """
        清除缓存
        
        Args:
            model_name: 模特名称，如果为None则清除所有缓存
        """
        with self._lock:
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    if model_name:
                        model_id = self._get_model_id(model_name)
                        if model_id:
                            # 删除特定模特的缓存
                            cursor.execute('DELETE FROM videos WHERE model_id = ?', (model_id,))
                            cursor.execute('DELETE FROM cache_metadata WHERE model_id = ?', (model_id,))
                            cursor.execute('DELETE FROM page_timestamps WHERE model_id = ?', (model_id,))
                            cursor.execute('DELETE FROM missing_videos WHERE model_id = ?', (model_id,))
                            self.logger.info(f"已清除模特缓存: {model_name}")
                    else:
                        # 清除所有缓存
                        cursor.execute('DELETE FROM videos')
                        cursor.execute('DELETE FROM cache_metadata')
                        cursor.execute('DELETE FROM page_timestamps')
                        cursor.execute('DELETE FROM missing_videos')
                        cursor.execute('DELETE FROM models')
                        self.logger.info("已清除所有缓存")
                    
                    conn.commit()
                    
            except Exception as e:
                self.logger.error(f"清除缓存失败: {e}")


# 兼容性适配器 - 使数据库存储可以替代现有的SmartCache
class DatabaseCacheAdapter:
    """数据库缓存适配器，兼容SmartCache接口"""
    
    def __init__(self, db_storage: DatabaseStorage):
        self.db = db_storage
        self.enabled = True
        self.incremental_update = True
        self.page_expiry_hours = 24
    
    def load(self, model_name: str) -> dict:
        """加载缓存数据（兼容接口）"""
        # 从数据库获取数据并转换为SmartCache期望的格式
        titles = self.db.get_cached_titles(model_name)
        videos = {}
        for title in titles:
            url = self.db.get_video_url(model_name, title)
            videos[title] = {
                'url': url or '',
                'page': 0,  # 数据库中可能没有页码信息
                'timestamp': datetime.now().isoformat()
            }
        
        return {
            'video_titles': titles,
            'videos': videos,
            'page_timestamps': {},  # 需要额外查询
            'last_page_fetched': self.db.get_last_page_fetched(model_name),
            'last_updated': datetime.now().isoformat(),
            'model_name': model_name
        }
    
    def save(self, model_name: str, data: dict):
        """保存缓存数据（兼容接口）"""
        # 从SmartCache格式转换为数据库格式
        videos_data = []
        for title, video_info in data.get('videos', {}).items():
            videos_data.append((
                title,
                video_info.get('url', ''),
                video_info.get('page', 0)
            ))
        
        if videos_data:
            self.db.add_videos(model_name, videos_data)
    
    def add_videos(self, model_name: str, videos: List[Tuple[str, str, int]]):
        """添加视频（兼容接口）"""
        self.db.add_videos(model_name, videos)
    
    def get_cached_titles(self, model_name: str) -> set:
        """获取缓存标题（兼容接口）"""
        return set(self.db.get_cached_titles(model_name))
    
    def should_update_page(self, model_name: str, page_num: int) -> bool:
        """判断是否需要更新页面（兼容接口）"""
        return self.db.should_update_page(model_name, page_num, self.page_expiry_hours)
    
    def update_page_timestamp(self, model_name: str, page_num: int):
        """更新页面时间戳（兼容接口）"""
        self.db.update_page_timestamp(model_name, page_num)
    
    def get_last_page(self, model_name: str) -> int:
        """获取最后页面（兼容接口）"""
        return self.db.get_last_page_fetched(model_name)
    
    def get_cache_stats(self, model_name: str) -> dict:
        """获取缓存统计（兼容接口）"""
        return self.db.get_cache_stats(model_name)


# 工厂函数
def create_database_storage(db_path: str, config: dict = None) -> DatabaseStorage:
    """创建数据库存储实例"""
    return DatabaseStorage(db_path, config)


def create_database_cache_adapter(db_path: str, config: dict = None) -> DatabaseCacheAdapter:
    """创建数据库缓存适配器实例"""
    db_storage = DatabaseStorage(db_path, config)
    return DatabaseCacheAdapter(db_storage)