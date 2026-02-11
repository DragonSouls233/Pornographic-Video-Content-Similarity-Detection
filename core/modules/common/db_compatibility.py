"""
数据库兼容性层
确保新旧版本数据无缝兼容
"""

import os
import json
import sqlite3
import logging
from typing import Dict, List, Optional
from pathlib import Path


class DatabaseCompatibilityLayer:
    """数据库兼容性层"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._ensure_compatible_schema()
    
    def _ensure_compatible_schema(self):
        """确保数据库模式兼容"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查现有表结构
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            # 必需的表
            required_tables = {'models', 'model_stats', 'config_store'}
            
            # 创建缺失的表
            if 'models' not in existing_tables:
                self._create_models_table(cursor)
            
            if 'model_stats' not in existing_tables:
                self._create_model_stats_table(cursor)
            
            if 'config_store' not in existing_tables:
                self._create_config_table(cursor)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"确保数据库兼容性失败: {e}")
            raise
    
    def _create_models_table(self, cursor):
        """创建模特表"""
        cursor.execute('''
            CREATE TABLE models (
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
    
    def _create_model_stats_table(self, cursor):
        """创建统计表"""
        cursor.execute('''
            CREATE TABLE model_stats (
                model_id INTEGER PRIMARY KEY,
                local_video_count INTEGER DEFAULT 0,
                online_video_count INTEGER DEFAULT 0,
                missing_video_count INTEGER DEFAULT 0,
                last_sync TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES models(id)
            )
        ''')
    
    def _create_config_table(self, cursor):
        """创建配置表"""
        cursor.execute('''
            CREATE TABLE config_store (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def migrate_from_json_if_needed(self, json_path: str = None):
        """如有必要，从JSON迁移数据"""
        if json_path is None:
            # 自动寻找对应的JSON文件
            json_path = self.db_path.replace('.db', '.json')
        
        if not os.path.exists(json_path):
            return
        
        try:
            # 检查数据库是否已有数据
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM models")
            count = cursor.fetchone()[0]
            conn.close()
            
            if count > 0:
                self.logger.info("数据库已有数据，跳过JSON迁移")
                return
            
            # 执行迁移
            self.logger.info(f"从JSON文件迁移数据: {json_path}")
            self._perform_json_migration(json_path)
            
        except Exception as e:
            self.logger.error(f"JSON迁移失败: {e}")
    
    def _perform_json_migration(self, json_path: str):
        """执行JSON到数据库的迁移"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 迁移模特数据
            if isinstance(data, dict) and 'models' in data:
                models_data = data['models']
            else:
                models_data = data
            
            for name, info in models_data.items():
                if isinstance(info, dict):
                    url = info.get('url', '')
                    module = info.get('module', 'PORN')
                else:
                    url = info
                    module = 'PORN'
                
                cursor.execute('''
                    INSERT OR IGNORE INTO models (name, url, module)
                    VALUES (?, ?, ?)
                ''', (name, url, module))
            
            conn.commit()
            conn.close()
            
            self.logger.info("JSON数据迁移完成")
            
        except Exception as e:
            self.logger.error(f"执行JSON迁移时出错: {e}")
            raise


class VersionManager:
    """版本管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.current_version = "1.0.0"
        self._ensure_version_tracking()
    
    def _ensure_version_tracking(self):
        """确保版本跟踪表存在"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建版本表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    upgrade_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            ''')
            
            # 插入当前版本（如果不存在）
            cursor.execute('''
                INSERT OR IGNORE INTO app_versions (version, notes)
                VALUES (?, ?)
            ''', (self.current_version, "Initial version"))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"版本跟踪初始化失败: {e}")
    
    def record_upgrade(self, from_version: str, to_version: str, notes: str = ""):
        """记录版本升级"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO app_versions (version, notes)
                VALUES (?, ?)
            ''', (to_version, f"Upgrade from {from_version}. {notes}"))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"记录版本升级: {from_version} -> {to_version}")
            
        except Exception as e:
            self.logger.error(f"记录版本升级失败: {e}")
    
    def get_version_history(self) -> List[Dict]:
        """获取版本历史"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT version, upgrade_date, notes
                FROM app_versions
                ORDER BY upgrade_date DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"获取版本历史失败: {e}")
            return []


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 创建兼容性层
    compat_layer = DatabaseCompatibilityLayer("test_compat.db")
    
    # 检查并迁移JSON数据
    compat_layer.migrate_from_json_if_needed("models.json")
    
    # 版本管理
    version_manager = VersionManager("test_compat.db")
    version_manager.record_upgrade("0.9.0", "1.0.0", "数据库架构升级")
    
    # 查看版本历史
    history = version_manager.get_version_history()
    print("版本历史:")
    for record in history:
        print(f"  {record['version']} - {record['upgrade_date']}")