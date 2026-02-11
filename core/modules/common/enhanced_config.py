"""
增强版配置管理模块
支持多种存储后端的透明切换
"""

import os
import json
import yaml
import sqlite3
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from pathlib import Path


class ConfigStorage(ABC):
    """配置存储抽象基类"""
    
    @abstractmethod
    def load(self, key: str) -> Any:
        pass
    
    @abstractmethod
    def save(self, key: str, value: Any) -> bool:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def list_keys(self) -> list:
        pass


class JSONStorage(ConfigStorage):
    """JSON文件存储实现"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.logger = logging.getLogger(__name__)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """确保配置文件存在"""
        if not os.path.exists(self.file_path):
            Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    def _load_all(self) -> Dict:
        """加载所有配置"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _save_all(self, data: Dict) -> bool:
        """保存所有配置"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {e}")
            return False
    
    def load(self, key: str) -> Any:
        data = self._load_all()
        return data.get(key)
    
    def save(self, key: str, value: Any) -> bool:
        data = self._load_all()
        data[key] = value
        return self._save_all(data)
    
    def delete(self, key: str) -> bool:
        data = self._load_all()
        if key in data:
            del data[key]
            return self._save_all(data)
        return True
    
    def list_keys(self) -> list:
        data = self._load_all()
        return list(data.keys())


class DatabaseStorage(ConfigStorage):
    """数据库存储实现"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config_store (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"初始化数据库失败: {e}")
            raise
    
    def load(self, key: str) -> Any:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT value FROM config_store WHERE key = ?', (key,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
            return None
            
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            return None
    
    def save(self, key: str, value: Any) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO config_store (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, json.dumps(value, ensure_ascii=False)))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM config_store WHERE key = ?', (key,))
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"删除配置失败: {e}")
            return False
    
    def list_keys(self) -> list:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT key FROM config_store')
            results = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in results]
            
        except Exception as e:
            self.logger.error(f"列出配置键失败: {e}")
            return []


class HybridStorage(ConfigStorage):
    """混合存储：热数据用数据库，冷数据用JSON"""
    
    def __init__(self, db_path: str, json_path: str, hot_keys: set = None):
        self.db_storage = DatabaseStorage(db_path)
        self.json_storage = JSONStorage(json_path)
        self.hot_keys = hot_keys or {
            'models', 'recent_searches', 'session_data', 'cache_stats'
        }
        self.logger = logging.getLogger(__name__)
    
    def _is_hot_key(self, key: str) -> bool:
        """判断是否为热数据键"""
        return key in self.hot_keys or key.startswith('temp_') or key.startswith('cache_')
    
    def load(self, key: str) -> Any:
        # 优先从数据库加载热数据
        if self._is_hot_key(key):
            value = self.db_storage.load(key)
            if value is not None:
                return value
            # 如果数据库中没有，尝试从JSON加载
            return self.json_storage.load(key)
        else:
            # 冷数据从JSON加载
            return self.json_storage.load(key)
    
    def save(self, key: str, value: Any) -> bool:
        if self._is_hot_key(key):
            # 热数据保存到数据库
            return self.db_storage.save(key, value)
        else:
            # 冷数据保存到JSON
            return self.json_storage.save(key, value)
    
    def delete(self, key: str) -> bool:
        # 两个存储都删除
        success1 = self.db_storage.delete(key)
        success2 = self.json_storage.delete(key)
        return success1 and success2
    
    def list_keys(self) -> list:
        # 合并两个存储的键
        db_keys = set(self.db_storage.list_keys())
        json_keys = set(self.json_storage.list_keys())
        return list(db_keys | json_keys)


class ConfigManager:
    """配置管理器 - 统一接口"""
    
    def __init__(self, storage_backend: ConfigStorage):
        self.storage = storage_backend
        self.logger = logging.getLogger(__name__)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        value = self.storage.load(key)
        return value if value is not None else default
    
    def set(self, key: str, value: Any) -> bool:
        """设置配置值"""
        return self.storage.save(key, value)
    
    def delete(self, key: str) -> bool:
        """删除配置项"""
        return self.storage.delete(key)
    
    def exists(self, key: str) -> bool:
        """检查配置项是否存在"""
        return self.get(key) is not None
    
    def list_all(self) -> list:
        """列出所有配置键"""
        return self.storage.list_keys()
    
    def get_section(self, section: str) -> Dict:
        """获取配置节"""
        keys = [k for k in self.list_all() if k.startswith(f"{section}.")]
        result = {}
        for key in keys:
            result[key[len(section)+1:]] = self.get(key)
        return result
    
    def set_section(self, section: str, data: Dict) -> bool:
        """设置配置节"""
        success = True
        for key, value in data.items():
            full_key = f"{section}.{key}"
            if not self.set(full_key, value):
                success = False
        return success


# 工厂函数
def create_config_manager(storage_type: str = "json", **kwargs) -> ConfigManager:
    """创建配置管理器实例"""
    
    if storage_type == "json":
        file_path = kwargs.get("file_path", "config.json")
        storage = JSONStorage(file_path)
        
    elif storage_type == "database":
        db_path = kwargs.get("db_path", "config.db")
        storage = DatabaseStorage(db_path)
        
    elif storage_type == "hybrid":
        db_path = kwargs.get("db_path", "hot_config.db")
        json_path = kwargs.get("json_path", "cold_config.json")
        hot_keys = kwargs.get("hot_keys")
        storage = HybridStorage(db_path, json_path, hot_keys)
        
    else:
        raise ValueError(f"不支持的存储类型: {storage_type}")
    
    return ConfigManager(storage)


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    print("=== 配置管理器测试 ===")
    
    # 测试JSON存储
    print("\n1. JSON存储测试:")
    json_config = create_config_manager("json", file_path="test_config.json")
    
    json_config.set("models.TestModel", {"url": "https://example.com", "module": "PORN"})
    json_config.set("settings.proxy.enabled", True)
    
    print(f"模特配置: {json_config.get('models.TestModel')}")
    print(f"代理设置: {json_config.get('settings.proxy.enabled')}")
    
    # 测试数据库存储
    print("\n2. 数据库存储测试:")
    db_config = create_config_manager("database", db_path="test_config.db")
    
    db_config.set("user.preferences.theme", "dark")
    db_config.set("user.history.last_search", "2026-02-11")
    
    print(f"主题设置: {db_config.get('user.preferences.theme')}")
    print(f"最后搜索: {db_config.get('user.history.last_search')}")
    
    # 测试混合存储
    print("\n3. 混合存储测试:")
    hybrid_config = create_config_manager("hybrid", 
                                        db_path="hot.db", 
                                        json_path="cold.json",
                                        hot_keys={"cache_", "temp_", "session_"})
    
    # 热数据（数据库）
    hybrid_config.set("cache.models", ["Model1", "Model2"])
    hybrid_config.set("temp.search_results", {"count": 10})
    
    # 冷数据（JSON）
    hybrid_config.set("backup.models_list", ["Backup1", "Backup2"])
    
    print(f"缓存数据: {hybrid_config.get('cache.models')}")
    print(f"临时数据: {hybrid_config.get('temp.search_results')}")
    print(f"备份数据: {hybrid_config.get('backup.models_list')}")