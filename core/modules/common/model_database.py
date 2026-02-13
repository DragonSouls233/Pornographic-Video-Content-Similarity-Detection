"""
模特数据数据库管理模块
提供SQLite数据库存储替代JSON文件存储
"""

import sqlite3
import json
import os
import sys
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path


class ModelDatabase:
    """模特数据库管理器"""
    
    def __init__(self, db_path: str = "models.db"):
        # 确保路径在EXE环境中正确工作
        if getattr(sys, 'frozen', False):
            # 打包为EXE时，使用可执行文件所在目录
            base_path = os.path.dirname(sys.executable)
        else:
            # 开发环境时，使用传入路径或当前工作目录
            base_path = os.getcwd()
            
        self.db_path = os.path.join(base_path, db_path)
        self.logger = logging.getLogger(__name__)
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 模特基本信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    module TEXT DEFAULT 'PORN',
                    country TEXT DEFAULT '欧美',
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 模特统计信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_stats (
                    model_id INTEGER PRIMARY KEY,
                    local_video_count INTEGER DEFAULT 0,
                    online_video_count INTEGER DEFAULT 0,
                    missing_video_count INTEGER DEFAULT 0,
                    last_sync TIMESTAMP,
                    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
                )
            ''')
            
            # 视频记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT,
                    source TEXT DEFAULT 'online',
                    is_missing BOOLEAN DEFAULT 0,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
                )
            ''')

            # 旧版黑名单表（已存在于数据库中）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    reason TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引优化查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_models_name ON models(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_models_module ON models(module)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_models_url ON models(url)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_model_id ON videos(model_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_title ON videos(title)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_blacklist_url ON blacklist(url)')


            
            conn.commit()
            conn.close()
            
            self.logger.info(f"数据库初始化完成: {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"数据库初始化失败: {e}")
            raise
    
    def migrate_from_json(self, json_path: str = "models.json"):
        """从JSON文件迁移数据到数据库"""
        try:
            if not os.path.exists(json_path):
                self.logger.info("JSON文件不存在，跳过迁移")
                return
            
            with open(json_path, 'r', encoding='utf-8') as f:
                models_data = json.load(f)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            migrated_count = 0
            for model_name, model_info in models_data.items():
                try:
                    if isinstance(model_info, dict):
                        url = model_info.get('url', '')
                        module = model_info.get('module', 'PORN')
                    else:
                        url = model_info
                        module = 'PORN'
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO models (name, url, module)
                        VALUES (?, ?, ?)
                    ''', (model_name, url, module))
                    
                    migrated_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"迁移模特 '{model_name}' 失败: {e}")
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"成功从JSON迁移 {migrated_count} 个模特到数据库")
            
        except Exception as e:
            self.logger.error(f"JSON迁移失败: {e}")
            raise
    
    def add_model(self, name: str, url: str, module: str = "PORN", country: str = "欧美") -> bool:
        """添加模特"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 如果URL在黑名单中，标记为invalid
            status_to_use = 'active'
            if url and self._is_url_blacklisted(url):
                status_to_use = 'invalid'
            else:
                try:
                    cursor.execute('SELECT status FROM models WHERE name = ?', (name,))
                    existing = cursor.fetchone()
                    if existing and existing[0]:
                        status_to_use = existing[0]
                except Exception:
                    pass
            
            cursor.execute('''
                INSERT OR REPLACE INTO models (name, url, module, country, status, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (name, url, module, country, status_to_use))
            
            # 如果是新插入，初始化统计数据
            if cursor.rowcount > 0:
                model_id = cursor.lastrowid
                cursor.execute('''
                    INSERT OR IGNORE INTO model_stats (model_id)
                    VALUES (?)
                ''', (model_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"添加模特: {name} ({module})")
            return True
            
        except Exception as e:
            self.logger.error(f"添加模特失败: {e}")
            return False

    
    def get_model(self, name: str) -> Optional[Dict]:
        """获取单个模特信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT m.*, s.local_video_count, s.online_video_count, 
                       s.missing_video_count, s.last_sync
                FROM models m
                LEFT JOIN model_stats s ON m.id = s.model_id
                WHERE m.name = ?
            ''', (name,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            self.logger.error(f"获取模特信息失败: {e}")
            return None
    
    def load_models(self) -> Dict[str, str]:
        """加载所有模特，返回 {name: url} 格式的字典（兼容JSON接口）"""
        try:
            # 应用URL黑名单与状态过滤
            self.apply_blacklist_to_models()
            models = self.get_all_models(exclude_blacklisted=True)
            return {model['name']: model['url'] for model in models if model.get('url')}
        except Exception as e:
            self.logger.error(f"加载模特数据失败: {e}")
            return {}


    def get_all_models(self, module: str = None, status: str = None, exclude_blacklisted: bool = False) -> List[Dict]:
        """获取所有模特信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT m.*, s.local_video_count, s.online_video_count, 
                       s.missing_video_count, s.last_sync
                FROM models m
                LEFT JOIN model_stats s ON m.id = s.model_id
            '''
            
            conditions = []
            params = []
            
            if module:
                conditions.append("m.module = ?")
                params.append(module)
            
            if status:
                conditions.append("m.status = ?")
                params.append(status)
            elif exclude_blacklisted:
                conditions.append("m.status = 'active'")

            if exclude_blacklisted:
                conditions.append("m.url NOT IN (SELECT url FROM blacklist)")

            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY m.name"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"获取模特列表失败: {e}")
            return []

    
    def update_model_stats(self, model_name: str, local_count: int = None, 
                          online_count: int = None, missing_count: int = None):
        """更新模特统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取模特ID
            cursor.execute('SELECT id FROM models WHERE name = ?', (model_name,))
            result = cursor.fetchone()
            
            if not result:
                self.logger.warning(f"模特不存在: {model_name}")
                return
            
            model_id = result[0]
            
            # 更新统计数据
            updates = []
            params = []
            
            if local_count is not None:
                updates.append("local_video_count = ?")
                params.append(local_count)
            
            if online_count is not None:
                updates.append("online_video_count = ?")
                params.append(online_count)
            
            if missing_count is not None:
                updates.append("missing_video_count = ?")
                params.append(missing_count)
            
            updates.append("last_sync = CURRENT_TIMESTAMP")
            
            if updates:
                params.append(model_id)
                query = f"UPDATE model_stats SET {', '.join(updates)} WHERE model_id = ?"
                cursor.execute(query, params)
                
                # 如果没有记录，插入新记录
                if cursor.rowcount == 0:
                    insert_params = [model_id]
                    if local_count is not None:
                        insert_params.append(local_count)
                    else:
                        insert_params.append(0)
                        
                    if online_count is not None:
                        insert_params.append(online_count)
                    else:
                        insert_params.append(0)
                        
                    if missing_count is not None:
                        insert_params.append(missing_count)
                    else:
                        insert_params.append(0)
                    
                    cursor.execute('''
                        INSERT INTO model_stats 
                        (model_id, local_video_count, online_video_count, missing_video_count, last_sync)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', insert_params)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"更新模特统计失败: {e}")
    
    def delete_model(self, name: str) -> bool:
        """删除模特"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM models WHERE name = ?', (name,))
            deleted = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            
            if deleted:
                self.logger.info(f"删除模特: {name}")
            else:
                self.logger.warning(f"模特不存在: {name}")
                
            return deleted
            
        except Exception as e:
            self.logger.error(f"删除模特失败: {e}")
            return False
    
    def search_models(self, keyword: str, module: str = None, exclude_blacklisted: bool = False) -> List[Dict]:
        """搜索模特"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT m.*, s.local_video_count, s.online_video_count, 
                       s.missing_video_count, s.last_sync
                FROM models m
                LEFT JOIN model_stats s ON m.id = s.model_id
                WHERE m.name LIKE ?
            '''
            
            params = [f"%{keyword}%"]
            
            if module:
                query += " AND m.module = ?"
                params.append(module)

            if exclude_blacklisted:
                query += " AND m.status = 'active' AND m.url NOT IN (SELECT url FROM blacklist)"

            
            query += " ORDER BY m.name"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"搜索模特失败: {e}")
            return []

    
    def get_statistics(self) -> Dict:
        """获取整体统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 总模特数
            cursor.execute('SELECT COUNT(*) FROM models')
            total_models = cursor.fetchone()[0]
            
            # 各模块统计
            cursor.execute('''
                SELECT module, COUNT(*) as count
                FROM models
                GROUP BY module
            ''')
            module_stats = dict(cursor.fetchall())
            
            # 状态统计
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM models
                GROUP BY status
            ''')
            status_stats = dict(cursor.fetchall())

            # 黑名单统计
            cursor.execute("SELECT COUNT(*) FROM blacklist")
            blacklist_count = cursor.fetchone()[0]

            
            # 最近同步时间
            cursor.execute('''
                SELECT MAX(last_sync) as last_sync
                FROM model_stats
            ''')
            last_sync = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_models': total_models,
                'module_distribution': module_stats,
                'status_distribution': status_stats,
                'blacklist_count': blacklist_count,
                'last_sync': last_sync
            }
            
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {}

    def get_blacklisted_urls(self) -> List[str]:
        """获取黑名单URL列表（旧表 blacklist）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT url FROM blacklist')
            rows = cursor.fetchall()
            conn.close()
            return [r[0] for r in rows]
        except Exception as e:
            self.logger.error(f"获取黑名单失败: {e}")
            return []

    def add_blacklisted_url(self, url: str, name: str = "", reason: str = "") -> bool:
        """添加黑名单URL到旧表（自动去重）"""
        if not url:
            return False
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # 去重：如果已存在同URL则忽略
            cursor.execute('SELECT 1 FROM blacklist WHERE url = ?', (url,))
            if cursor.fetchone():
                conn.close()
                return True
            cursor.execute('''
                INSERT INTO blacklist (name, url, reason, added_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (name or '', url, reason or ''))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"添加黑名单失败: {e}")
            return False

    def apply_blacklist_to_models(self) -> int:
        """将黑名单URL同步到模型状态，返回更新数量"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE models
                SET status = 'invalid', updated_at = CURRENT_TIMESTAMP
                WHERE url IN (SELECT url FROM blacklist)
                  AND status != 'invalid'
            ''')
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            if affected:
                self.logger.info(f"已标记 {affected} 条黑名单URL为 invalid")
            return affected
        except Exception as e:
            self.logger.error(f"应用黑名单失败: {e}")
            return 0

    def get_duplicate_urls(self) -> List[Tuple[str, int]]:
        """获取重复URL列表及其数量"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT url, COUNT(*) as cnt
                FROM models
                WHERE url IS NOT NULL AND TRIM(url) != ''
                GROUP BY url
                HAVING cnt > 1
            ''')
            rows = cursor.fetchall()
            conn.close()
            return rows
        except Exception as e:
            self.logger.error(f"获取重复URL失败: {e}")
            return []

    def _is_url_blacklisted(self, url: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM blacklist WHERE url = ?', (url,))
            hit = cursor.fetchone()
            conn.close()
            return hit is not None
        except Exception:
            return False





# 数据库适配器，兼容现有JSON接口
class DatabaseModelAdapter:
    """数据库适配器，提供与JSON相同的接口

    重要：GUI/脚本在保存时经常只传 name/url/module。
    如果直接调用 `ModelDatabase.add_model()` 并使用默认 `country='欧美'`，
    会把你在数据库里维护好的 country 覆盖掉。
    这里统一做“保留已有 country/module”的保护。
    """
    
    def __init__(self, db_path: str = "models.db"):
        self.db = ModelDatabase(db_path)
        self.logger = logging.getLogger(__name__)
    
    def load_models(self) -> Dict[str, str]:
        """加载模特数据（兼容JSON接口）"""
        try:
            models = self.db.get_all_models()
            return {model['name']: model['url'] for model in models}
        except Exception as e:
            self.logger.error(f"加载模特数据失败: {e}")
            return {}

    def save_models(self, models_dict: Dict[str, str]):
        """保存模特数据（兼容JSON接口）

        注意：此接口只提供 url，因此会尽量保留数据库中已有的 module/country。
        """
        try:
            for name, url in models_dict.items():
                # 尝试保留已有字段
                existing = self.db.get_model(name) or {}
                module = existing.get('module', 'PORN')
                country = existing.get('country', '欧美')
                self.db.add_model(name, url, module, country)
        except Exception as e:
            self.logger.error(f"保存模特数据失败: {e}")

    def add_model(self, name: str, url: str, module: str = "PORN", country: str = None):
        """添加/更新单个模特（默认不覆盖已存在的 country）"""
        try:
            existing = self.db.get_model(name) or {}

            # module：如果调用方没显式提供，则保留旧值
            module_to_use = module or existing.get('module', 'PORN')

            # country：如果调用方没显式提供，则保留旧值
            if country is None:
                country_to_use = existing.get('country', '欧美')
            else:
                country_to_use = country

            return self.db.add_model(name, url, module_to_use, country_to_use)
        except Exception as e:
            self.logger.error(f"添加/更新模特失败: {e}")
            return False
    
    def remove_model(self, name: str) -> bool:
        """删除模特"""
        return self.db.delete_model(name)
    
    def get_model_info(self, name: str) -> Optional[Dict]:
        """获取模特详细信息"""
        return self.db.get_model(name)


# 工厂函数
def create_model_database(db_path: str = "models.db", 
                         migrate_from_json: bool = True) -> DatabaseModelAdapter:
    """创建模特数据库实例"""
    adapter = DatabaseModelAdapter(db_path)
    
    # 自动迁移JSON数据
    if migrate_from_json:
        json_path = db_path.replace('.db', '.json')
        adapter.db.migrate_from_json(json_path)
    
    return adapter


# 使用示例和测试
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建数据库实例
    db_adapter = create_model_database("test_models.db")
    
    # 测试基本操作
    print("=== 数据库测试 ===")
    
    # 添加测试数据
    db_adapter.add_model("Test Model 1", "https://example.com/model1", "PORN")
    db_adapter.add_model("Test Model 2", "https://example.com/model2", "JAVDB")
    
    # 查询数据
    models = db_adapter.load_models()
    print(f"加载模特数量: {len(models)}")
    
    # 获取详细信息
    model_info = db_adapter.get_model_info("Test Model 1")
    if model_info:
        print(f"模特信息: {model_info}")
    
    # 搜索功能
    search_results = db_adapter.db.search_models("Test")
    print(f"搜索结果: {len(search_results)} 个")
    
    # 统计信息
    stats = db_adapter.db.get_statistics()
    print(f"统计信息: {stats}")