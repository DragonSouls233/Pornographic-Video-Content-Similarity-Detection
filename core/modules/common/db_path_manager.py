"""
数据库路径管理模块
智能处理开发环境和打包环境的数据库路径
"""

import os
import sys
import tempfile
from pathlib import Path
import logging


class DatabasePathManager:
    """数据库路径管理器"""
    
    def __init__(self, db_name: str = "models.db"):
        self.db_name = db_name
        self.logger = logging.getLogger(__name__)
    
    def get_runtime_path(self) -> str:
        """获取运行时数据库路径"""
        if getattr(sys, 'frozen', False):
            # 打包环境：EXE同目录
            exe_dir = os.path.dirname(sys.executable)
            db_path = os.path.join(exe_dir, self.db_name)
        else:
            # 开发环境：项目目录
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(project_dir, self.db_name)
        
        return db_path
    
    def ensure_database_exists(self, db_path: str = None) -> str:
        """确保数据库文件存在，必要时创建"""
        if db_path is None:
            db_path = self.get_runtime_path()
        
        db_dir = os.path.dirname(db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
        
        # 如果数据库不存在，创建它
        if not os.path.exists(db_path):
            self.logger.info(f"创建新数据库: {db_path}")
            # 这里可以调用数据库初始化函数
            self._initialize_database(db_path)
        
        return db_path
    
    def _initialize_database(self, db_path: str):
        """初始化数据库结构"""
        import sqlite3
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 创建必要的表结构
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    module TEXT DEFAULT 'PORN',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            self.logger.info("数据库初始化完成")
            
        except Exception as e:
            self.logger.error(f"数据库初始化失败: {e}")
            raise
    
    def get_backup_paths(self) -> dict:
        """获取备份相关路径"""
        runtime_path = self.get_runtime_path()
        
        return {
            'runtime': runtime_path,
            'backup_dir': os.path.join(os.path.dirname(runtime_path), 'backups'),
            'temp_dir': tempfile.gettempdir()
        }
    
    def copy_database_to_temp(self) -> str:
        """复制数据库到临时目录（用于测试）"""
        import shutil
        
        runtime_path = self.get_runtime_path()
        temp_path = os.path.join(tempfile.gettempdir(), f"temp_{self.db_name}")
        
        if os.path.exists(runtime_path):
            shutil.copy2(runtime_path, temp_path)
            self.logger.info(f"数据库已复制到临时目录: {temp_path}")
        
        return temp_path


# PyInstaller spec文件配置示例
PYINSTALLER_SPEC_TEMPLATE = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['gui/gui.py'],  # 主程序入口
    pathex=[],
    binaries=[],
    datas=[
        # 不需要包含数据库文件，因为它会在运行时创建
        # 但如果需要包含初始数据，可以这样添加：
        # ('initial_data.sql', '.'),
    ],
    hiddenimports=[
        'sqlite3',  # 确保包含SQLite支持
        'core.modules.common.model_database',
        'core.modules.common.enhanced_config'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='模特查重管理系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico'  # 如果有图标文件
)
"""

# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建路径管理器
    db_manager = DatabasePathManager("test.db")
    
    # 获取运行时路径
    db_path = db_manager.get_runtime_path()
    print(f"数据库路径: {db_path}")
    
    # 确保数据库存在
    actual_path = db_manager.ensure_database_exists()
    print(f"实际数据库路径: {actual_path}")
    
    # 获取备份路径信息
    backup_info = db_manager.get_backup_paths()
    print("备份路径信息:")
    for key, path in backup_info.items():
        print(f"  {key}: {path}")