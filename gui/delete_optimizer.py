"""
删除功能优化器
确保模特数据删除的完整性和一致性
"""

import sqlite3
import logging
import os
import sys
from typing import Tuple, Dict, Any, Optional
import time

class DeleteOperationResult:
    """删除操作结果"""
    def __init__(self):
        self.success = False
        self.deleted_from_memory = False
        self.deleted_from_database = False
        self.deleted_from_json = False
        self.error_message = ""
        self.affected_records = 0
        self.execution_time = 0.0
        self.cleanup_performed = []

class DeleteOptimizer:
    """删除操作优化器"""
    
    def __init__(self, db_path: str = "models.db", json_path: str = "models.json", logger=None):
        # 确保路径在EXE环境中正确工作
        if getattr(sys, 'frozen', False):
            # 打包为EXE时，使用可执行文件所在目录
            base_path = os.path.dirname(sys.executable)
        else:
            # 开发环境时，使用当前工作目录
            base_path = os.getcwd()
            
        self.db_path = os.path.join(base_path, db_path)
        self.json_path = os.path.join(base_path, json_path)
        self.logger = logger or logging.getLogger(__name__)
        
    def verify_model_existence(self, model_name: str) -> Dict[str, Any]:
        """验证模特是否存在于各个存储位置"""
        result = {
            'in_memory': False,
            'in_database': False,
            'in_json': False,
            'db_id': None,
            'db_stats_id': None,
            'video_count': 0
        }
        
        # 检查数据库
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查models表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='models'")
            models_exists = cursor.fetchone()
            if not models_exists:
                conn.close()
                return result
            
            # 检查models表
            cursor.execute("SELECT id FROM models WHERE name = ?", (model_name,))
            model_record = cursor.fetchone()
            if model_record:
                result['in_database'] = True
                result['db_id'] = model_record[0]
                
                # 检查model_stats表是否存在
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='model_stats'")
                stats_exists = cursor.fetchone()
                if stats_exists:
                    try:
                        cursor.execute("SELECT id FROM model_stats WHERE model_id = ?", (result['db_id'],))
                        stats_record = cursor.fetchone()
                        if stats_record:
                            result['db_stats_id'] = stats_record[0]
                    except sqlite3.OperationalError:
                        pass
                
                # 检查videos表是否存在
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='videos'")
                videos_exists = cursor.fetchone()
                if videos_exists:
                    try:
                        cursor.execute("SELECT COUNT(*) FROM videos WHERE model_id = ?", (result['db_id'],))
                        video_count = cursor.fetchone()
                        if video_count:
                            result['video_count'] = video_count[0]
                    except sqlite3.OperationalError:
                        pass
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"检查数据库中模特存在性失败: {e}")
        
        return result
    
    def safe_delete_from_database(self, model_name: str) -> Tuple[bool, int, str]:
        """安全地从数据库删除模特（包含级联删除检查）"""
        try:
            start_time = time.time()
            affected_records = 0
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 开始事务
            conn.execute("BEGIN TRANSACTION")
            
            try:
                # 获取模特ID
                cursor.execute("SELECT id FROM models WHERE name = ?", (model_name,))
                model_record = cursor.fetchone()
                if not model_record:
                    return False, 0, f"模特 '{model_name}' 在数据库中不存在"
                
                model_id = model_record[0]
                
                # 统计将要删除的记录（检查表是否存在）
                stats_count = 0
                videos_count = 0
                cache_count = 0
                pages_count = 0
                missing_count = 0
                
                # 检查并统计各表的记录数
                try:
                    cursor.execute("SELECT COUNT(*) FROM model_stats WHERE model_id = ?", (model_id,))
                    stats_count = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("SELECT COUNT(*) FROM videos WHERE model_id = ?", (model_id,))
                    videos_count = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("SELECT COUNT(*) FROM model_cache WHERE model_id = ?", (model_id,))
                    cache_count = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("SELECT COUNT(*) FROM model_pages WHERE model_id = ?", (model_id,))
                    pages_count = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("SELECT COUNT(*) FROM missing_videos WHERE model_id = ?", (model_id,))
                    missing_count = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    pass
                
                affected_records = 1 + stats_count + videos_count + cache_count + pages_count + missing_count
                
                # 执行删除（按外键依赖顺序，检查表是否存在）
                
                # 1. 先删除最底层的依赖数据
                try:
                    cursor.execute("DELETE FROM missing_videos WHERE model_id = ?", (model_id,))
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("DELETE FROM model_pages WHERE model_id = ?", (model_id,))
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("DELETE FROM model_cache WHERE model_id = ?", (model_id,))
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("DELETE FROM videos WHERE model_id = ?", (model_id,))
                except sqlite3.OperationalError:
                    pass
                
                try:
                    cursor.execute("DELETE FROM model_stats WHERE model_id = ?", (model_id,))
                except sqlite3.OperationalError:
                    pass
                
                # 2. 最后删除主记录
                cursor.execute("DELETE FROM models WHERE id = ?", (model_id,))
                
                # 提交事务
                conn.commit()
                
                execution_time = time.time() - start_time
                
                self.logger.info(f"数据库删除完成: {model_name}")
                self.logger.info(f"  - 删除了 {stats_count} 条统计记录")
                self.logger.info(f"  - 删除了 {videos_count} 条视频记录")
                self.logger.info(f"  - 删除了 {cache_count} 条缓存记录")
                self.logger.info(f"  - 删除了 {pages_count} 条页面记录")
                self.logger.info(f"  - 删除了 {missing_count} 条缺失记录")
                self.logger.info(f"  - 总共影响 {affected_records} 条记录")
                self.logger.info(f"  - 执行时间: {execution_time:.3f}秒")
                
                return True, affected_records, f"成功删除模特 '{model_name}' 及其所有相关数据"
                
            except Exception as e:
                # 回滚事务
                conn.rollback()
                raise e
                
        except Exception as e:
            self.logger.error(f"数据库删除失败: {e}")
            return False, 0, f"数据库删除失败: {e}"
            
        finally:
            if 'conn' in locals():
                conn.close()
    
    def safe_delete_from_json(self, model_name: str) -> Tuple[bool, str]:
        """安全地从JSON文件删除模特"""
        try:
            if not os.path.exists(self.json_path):
                return True, "JSON文件不存在，无需删除"
            
            import json
            
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if model_name not in data:
                return True, f"模特 '{model_name}' 不在JSON文件中"
            
            # 删除记录
            del data[model_name]
            
            # 保存回文件
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"JSON文件删除完成: {model_name}")
            return True, f"成功从JSON文件删除模特 '{model_name}'"
            
        except Exception as e:
            error_msg = f"JSON文件删除失败: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def cleanup_orphaned_records(self) -> int:
        """清理孤立的记录"""
        try:
            cleaned_count = 0
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # 清理各个表的孤立记录
            cleanup_queries = [
                ("model_stats", "DELETE FROM model_stats WHERE model_id NOT IN (SELECT id FROM models)"),
                ("videos", "DELETE FROM videos WHERE model_id NOT IN (SELECT id FROM models)"),
                ("model_cache", "DELETE FROM model_cache WHERE model_id NOT IN (SELECT id FROM models)"),
                ("model_pages", "DELETE FROM model_pages WHERE model_id NOT IN (SELECT id FROM models)"),
                ("missing_videos", "DELETE FROM missing_videos WHERE model_id NOT IN (SELECT id FROM models)")
            ]
            
            for table_name, query in cleanup_queries:
                if table_name in tables:
                    try:
                        cursor.execute(query)
                        cleaned_count += cursor.rowcount
                    except sqlite3.OperationalError as e:
                        self.logger.debug(f"清理表 {table_name} 失败: {e}")
            
            conn.commit()
            conn.close()
            
            if cleaned_count > 0:
                self.logger.info(f"清理孤立记录: {cleaned_count} 条")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"清理孤立记录失败: {e}")
            return 0
    
    def optimize_delete_operation(self, model_name: str, memory_dict: dict) -> DeleteOperationResult:
        """优化删除操作，确保数据完整性"""
        result = DeleteOperationResult()
        start_time = time.time()
        
        try:
            self.logger.info(f"开始删除模特: {model_name}")
            
            # 1. 验证模特存在性
            existence = self.verify_model_existence(model_name)
            self.logger.info(f"存在性检查: 内存={existence['in_memory']}, 数据库={existence['in_database']}, JSON={existence['in_json']}")
            
            # 2. 从内存删除
            if model_name in memory_dict:
                del memory_dict[model_name]
                result.deleted_from_memory = True
                result.cleanup_performed.append("从内存字典删除")
            else:
                result.cleanup_performed.append("内存中不存在该模特")
            
            # 3. 从数据库删除（最重要）
            if existence['in_database']:
                db_success, db_affected, db_message = self.safe_delete_from_database(model_name)
                if db_success:
                    result.deleted_from_database = True
                    result.affected_records += db_affected
                    result.cleanup_performed.append(f"从数据库删除（影响{db_affected}条记录）")
                else:
                    result.error_message = db_message
                    return result
            else:
                result.cleanup_performed.append("数据库中不存在该模特")
            
            # 4. 从JSON文件删除
            json_success, json_message = self.safe_delete_from_json(model_name)
            result.deleted_from_json = json_success
            result.cleanup_performed.append(json_message)
            
            # 5. 清理孤立记录
            orphaned_cleaned = self.cleanup_orphaned_records()
            if orphaned_cleaned > 0:
                result.cleanup_performed.append(f"清理了{orphaned_cleaned}条孤立记录")
            
            # 6. 执行数据库优化
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("VACUUM")
                cursor.execute("ANALYZE")
                conn.close()
                result.cleanup_performed.append("数据库优化完成")
            except Exception as e:
                self.logger.warning(f"数据库优化失败: {e}")
            
            # 计算结果
            result.success = True
            result.execution_time = time.time() - start_time
            
            self.logger.info(f"删除操作成功完成: {model_name}")
            self.logger.info(f"  - 总耗时: {result.execution_time:.3f}秒")
            self.logger.info(f"  - 清理项目: {'; '.join(result.cleanup_performed)}")
            
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.execution_time = time.time() - start_time
            self.logger.error(f"删除操作失败: {e}")
        
        return result
    
    def generate_delete_report(self, model_name: str, result: DeleteOperationResult) -> str:
        """生成删除报告"""
        report = f"""
模特删除操作报告
{'='*50}
模特名称: {model_name}
操作状态: {'成功' if result.success else '失败'}
执行时间: {result.execution_time:.3f}秒

删除详情:
- 内存删除: {'成功' if result.deleted_from_memory else '未执行'}
- 数据库删除: {'成功' if result.deleted_from_database else '未执行'}
- JSON删除: {'成功' if result.deleted_from_json else '未执行'}
- 影响记录: {result.affected_records}条

清理操作:
"""
        
        for i, cleanup in enumerate(result.cleanup_performed, 1):
            report += f"{i}. {cleanup}\n"
        
        if not result.success and result.error_message:
            report += f"\n错误信息:\n{result.error_message}"
        
        return report

# 全局删除优化器实例
_delete_optimizer = None

def get_delete_optimizer(db_path: str = "models.db", json_path: str = "models.json", logger=None) -> DeleteOptimizer:
    """获取删除优化器实例"""
    global _delete_optimizer
    if _delete_optimizer is None:
        _delete_optimizer = DeleteOptimizer(db_path, json_path, logger)
    return _delete_optimizer