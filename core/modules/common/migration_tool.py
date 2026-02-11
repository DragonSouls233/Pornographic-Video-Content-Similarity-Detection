"""
数据存储迁移工具
提供从JSON到数据库的平滑迁移方案
"""

import os
import json
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from .model_database import create_model_database
from .enhanced_config import create_config_manager


class StorageMigrationTool:
    """存储迁移工具"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.backup_dir = "migration_backups"
        Path(self.backup_dir).mkdir(exist_ok=True)
    
    def backup_current_data(self, json_files: List[str]) -> bool:
        """备份当前JSON数据"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder = os.path.join(self.backup_dir, f"backup_{timestamp}")
            Path(backup_folder).mkdir(exist_ok=True)
            
            for json_file in json_files:
                if os.path.exists(json_file):
                    backup_path = os.path.join(backup_folder, os.path.basename(json_file))
                    shutil.copy2(json_file, backup_path)
                    self.logger.info(f"备份文件: {json_file} -> {backup_path}")
            
            # 创建迁移记录
            migration_record = {
                "timestamp": timestamp,
                "files": json_files,
                "backup_location": backup_folder
            }
            
            record_path = os.path.join(backup_folder, "migration_record.json")
            with open(record_path, 'w', encoding='utf-8') as f:
                json.dump(migration_record, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"备份完成，位置: {backup_folder}")
            return True
            
        except Exception as e:
            self.logger.error(f"备份失败: {e}")
            return False
    
    def migrate_models_json_to_db(self, json_path: str = "models.json", 
                                db_path: str = "models.db") -> bool:
        """迁移models.json到数据库"""
        try:
            self.logger.info("开始迁移models.json到数据库...")
            
            # 创建数据库实例
            db_adapter = create_model_database(db_path, migrate_from_json=False)
            
            # 读取JSON数据
            if not os.path.exists(json_path):
                self.logger.warning(f"JSON文件不存在: {json_path}")
                return True
            
            with open(json_path, 'r', encoding='utf-8') as f:
                models_data = json.load(f)
            
            # 迁移数据
            migrated_count = 0
            failed_count = 0
            
            for model_name, model_info in models_data.items():
                try:
                    if isinstance(model_info, dict):
                        url = model_info.get('url', '')
                        module = model_info.get('module', 'PORN')
                        country = model_info.get('country', '欧美')
                    else:
                        url = model_info
                        module = 'PORN'
                        country = '欧美'
                    
                    if db_adapter.add_model(model_name, url, module, country):
                        migrated_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    self.logger.warning(f"迁移模特 '{model_name}' 失败: {e}")
                    failed_count += 1
            
            self.logger.info(f"迁移完成: 成功 {migrated_count} 个，失败 {failed_count} 个")
            return failed_count == 0
            
        except Exception as e:
            self.logger.error(f"迁移失败: {e}")
            return False
    
    def migrate_config_to_db(self, json_path: str = "config.yaml",
                           db_path: str = "config.db") -> bool:
        """迁移配置文件到数据库"""
        try:
            self.logger.info("开始迁移配置到数据库...")
            
            # 创建配置管理器
            config_manager = create_config_manager("database", db_path=db_path)
            
            # 读取配置文件
            if not os.path.exists(json_path):
                self.logger.warning(f"配置文件不存在: {json_path}")
                return True
            
            # 支持YAML和JSON格式
            if json_path.endswith('.yaml') or json_path.endswith('.yml'):
                import yaml
                with open(json_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
            else:
                with open(json_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            
            # 递归保存配置到数据库
            def save_config_recursive(data: dict, prefix: str = ""):
                for key, value in data.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    
                    if isinstance(value, dict):
                        save_config_recursive(value, full_key)
                    else:
                        config_manager.set(full_key, value)
            
            save_config_recursive(config_data)
            
            self.logger.info("配置迁移完成")
            return True
            
        except Exception as e:
            self.logger.error(f"配置迁移失败: {e}")
            return False
    
    def validate_migration(self, db_path: str, original_json_path: str) -> Dict[str, any]:
        """验证迁移结果"""
        try:
            validation_result = {
                "success": True,
                "errors": [],
                "statistics": {}
            }
            
            # 验证模型数据
            if "models" in db_path:
                db_adapter = create_model_database(db_path)
                db_models = db_adapter.load_models()
                
                # 读取原始JSON
                if os.path.exists(original_json_path):
                    with open(original_json_path, 'r', encoding='utf-8') as f:
                        json_models = json.load(f)
                    
                    # 比较数量
                    if len(db_models) != len(json_models):
                        validation_result["errors"].append(
                            f"数量不匹配: 数据库{len(db_models)} vs JSON{len(json_models)}"
                        )
                        validation_result["success"] = False
                    
                    # 比较内容
                    for name, url in json_models.items():
                        if name not in db_models:
                            validation_result["errors"].append(f"缺失模特: {name}")
                            validation_result["success"] = False
                        elif isinstance(url, dict) and db_models[name] != url.get('url', ''):
                            validation_result["errors"].append(f"URL不匹配: {name}")
                            validation_result["success"] = False
                        elif isinstance(url, str) and db_models[name] != url:
                            validation_result["errors"].append(f"URL不匹配: {name}")
                            validation_result["success"] = False
                
                validation_result["statistics"]["model_count"] = len(db_models)
            
            return validation_result
            
        except Exception as e:
            return {
                "success": False,
                "errors": [f"验证失败: {e}"],
                "statistics": {}
            }
    
    def rollback_migration(self, backup_folder: str) -> bool:
        """回滚迁移"""
        try:
            self.logger.info(f"开始回滚迁移: {backup_folder}")
            
            if not os.path.exists(backup_folder):
                self.logger.error("备份文件夹不存在")
                return False
            
            # 读取迁移记录
            record_path = os.path.join(backup_folder, "migration_record.json")
            if not os.path.exists(record_path):
                self.logger.error("迁移记录不存在")
                return False
            
            with open(record_path, 'r', encoding='utf-8') as f:
                record = json.load(f)
            
            # 恢复文件
            for original_file in record["files"]:
                backup_file = os.path.join(backup_folder, os.path.basename(original_file))
                if os.path.exists(backup_file):
                    shutil.copy2(backup_file, original_file)
                    self.logger.info(f"恢复文件: {backup_file} -> {original_file}")
            
            self.logger.info("回滚完成")
            return True
            
        except Exception as e:
            self.logger.error(f"回滚失败: {e}")
            return False


def interactive_migration_wizard():
    """交互式迁移向导"""
    
    import sys
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s | %(levelname)-8s | %(message)s')
    
    tool = StorageMigrationTool()
    
    print("=" * 60)
    print("数据存储迁移向导")
    print("=" * 60)
    
    # 检查当前状态
    json_files = ["models.json", "config.yaml"]
    existing_files = [f for f in json_files if os.path.exists(f)]
    
    if not existing_files:
        print("未找到需要迁移的JSON文件")
        return
    
    print(f"发现需要迁移的文件: {', '.join(existing_files)}")
    
    # 确认备份
    print("\n第一步: 创建备份")
    if not tool.backup_current_data(existing_files):
        print("❌ 备份失败，终止迁移")
        return
    
    backup_folder = sorted(os.listdir(tool.backup_dir))[-1]  # 最新的备份
    backup_path = os.path.join(tool.backup_dir, backup_folder)
    print(f"✅ 备份已完成: {backup_path}")
    
    # 执行迁移
    print("\n第二步: 执行迁移")
    
    success = True
    for json_file in existing_files:
        if json_file == "models.json":
            if not tool.migrate_models_json_to_db():
                success = False
                print("❌ 模特数据迁移失败")
            else:
                print("✅ 模特数据迁移完成")
                
        elif json_file == "config.yaml":
            if not tool.migrate_config_to_db():
                success = False
                print("❌ 配置数据迁移失败")
            else:
                print("✅ 配置数据迁移完成")
    
    # 验证结果
    print("\n第三步: 验证迁移结果")
    if success:
        validation = tool.validate_migration("models.db", "models.json")
        if validation["success"]:
            print("✅ 迁移验证通过")
            print(f"  模特数量: {validation['statistics'].get('model_count', 0)}")
        else:
            print("❌ 迁移验证失败:")
            for error in validation["errors"]:
                print(f"  - {error}")
            success = False
    
    # 完成或回滚
    if success:
        print("\n🎉 迁移成功完成！")
        print("\n建议后续操作:")
        print("1. 测试新系统功能是否正常")
        print("2. 确认无误后可删除备份文件")
        print("3. 更新相关代码引用")
    else:
        print("\n🔄 迁移失败，准备回滚...")
        if tool.rollback_migration(backup_path):
            print("✅ 已成功回滚到原始状态")
        else:
            print("❌ 回滚失败，请手动恢复备份")


# 使用示例
if __name__ == "__main__":
    interactive_migration_wizard()