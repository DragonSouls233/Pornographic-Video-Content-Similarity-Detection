"""
数据迁移脚本
将models.json数据迁移到SQLite数据库
"""

import json
import sqlite3
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
logger = logging.getLogger(__name__)

def migrate_models_data():
    """迁移模特数据"""
    try:
        # 读取JSON数据
        logger.info("读取models.json文件...")
        with open('models.json', 'r', encoding='utf-8') as f:
            models_data = json.load(f)
        
        logger.info(f"发现 {len(models_data)} 个模特需要迁移")
        logger.info(f"原始数据: {models_data}")
        
        # 连接数据库
        logger.info("连接数据库...")
        conn = sqlite3.connect('models.db')
        cursor = conn.cursor()
        
        # 迁移数据
        migrated_count = 0
        failed_count = 0
        
        for model_name, model_info in models_data.items():
            try:
                # 解析模型信息
                if isinstance(model_info, dict):
                    url = model_info.get('url', '')
                    module = model_info.get('module', 'PORN')
                    country = model_info.get('country', '欧美')
                else:
                    url = model_info
                    module = 'PORN'
                    country = '欧美'
                
                logger.info(f"迁移模特: {model_name} | URL: {url} | 模块: {module}")
                
                # 插入数据库
                cursor.execute('''
                    INSERT OR REPLACE INTO models (name, url, module, country, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    model_name,
                    url,
                    module,
                    country,
                    'active',
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                
                # 同时插入统计记录
                cursor.execute('''
                    INSERT OR IGNORE INTO model_stats (model_id, local_video_count, online_video_count, missing_video_count)
                    VALUES ((SELECT id FROM models WHERE name = ?), 0, 0, 0)
                ''', (model_name,))
                
                migrated_count += 1
                logger.info(f"✅ 成功迁移: {model_name}")
                
            except Exception as e:
                logger.error(f"❌ 迁移失败 {model_name}: {e}")
                failed_count += 1
        
        # 提交事务
        conn.commit()
        conn.close()
        
        logger.info(f"迁移完成: 成功 {migrated_count} 个，失败 {failed_count} 个")
        return failed_count == 0
        
    except Exception as e:
        logger.error(f"迁移过程出错: {e}")
        return False

def verify_migration():
    """验证迁移结果"""
    try:
        logger.info("验证迁移结果...")
        
        # 连接数据库
        conn = sqlite3.connect('models.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询所有模特
        cursor.execute('SELECT * FROM models')
        db_models = cursor.fetchall()
        
        logger.info(f"数据库中模特数量: {len(db_models)}")
        
        for model in db_models:
            logger.info(f"  - {model['name']}: {model['url']} ({model['module']})")
        
        # 查询统计信息
        cursor.execute('''
            SELECT m.name, s.local_video_count, s.online_video_count, s.missing_video_count
            FROM models m
            LEFT JOIN model_stats s ON m.id = s.model_id
        ''')
        stats = cursor.fetchall()
        
        logger.info("统计信息:")
        for stat in stats:
            logger.info(f"  {stat['name']}: 本地{stat['local_video_count']} | 在线{stat['online_video_count']} | 缺失{stat['missing_video_count']}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"验证失败: {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("开始数据迁移")
    logger.info("=" * 50)
    
    # 执行迁移
    if migrate_models_data():
        logger.info("✅ 数据迁移成功")
        
        # 验证结果
        if verify_migration():
            logger.info("✅ 迁移验证通过")
        else:
            logger.error("❌ 迁移验证失败")
    else:
        logger.error("❌ 数据迁移失败")