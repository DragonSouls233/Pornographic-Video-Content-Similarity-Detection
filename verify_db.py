"""
数据库验证脚本
详细验证迁移后的数据完整性
"""

import sqlite3
import json

def detailed_verification():
    """详细验证数据库内容"""
    
    print("=" * 60)
    print("数据库详细验证")
    print("=" * 60)
    
    # 连接数据库
    conn = sqlite3.connect('models.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. 检查表结构
    print("\n1. 数据库表结构:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  - {table[0]}")
    
    # 2. 检查models表数据
    print("\n2. models表数据:")
    cursor.execute("SELECT * FROM models")
    models = cursor.fetchall()
    print(f"  总计: {len(models)} 个模特")
    
    for model in models:
        print(f"  ID: {model['id']}")
        print(f"  名称: {model['name']}")
        print(f"  URL: {model['url']}")
        print(f"  模块: {model['module']}")
        print(f"  国家: {model['country']}")
        print(f"  状态: {model['status']}")
        print(f"  创建时间: {model['created_at']}")
        print(f"  更新时间: {model['updated_at']}")
        print("  " + "-" * 40)
    
    # 3. 检查model_stats表数据
    print("\n3. model_stats表数据:")
    cursor.execute('''
        SELECT m.name, s.*
        FROM models m
        LEFT JOIN model_stats s ON m.id = s.model_id
    ''')
    stats = cursor.fetchall()
    
    for stat in stats:
        print(f"  模特: {stat['name']}")
        print(f"    本地视频数: {stat['local_video_count']}")
        print(f"    在线视频数: {stat['online_video_count']}")
        print(f"    缺失视频数: {stat['missing_video_count']}")
        print(f"    最后同步: {stat['last_sync']}")
        print("  " + "-" * 30)
    
    # 4. 与原始JSON对比
    print("\n4. 与原始JSON数据对比:")
    try:
        with open('models.json', 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        print(f"  原始JSON模特数: {len(original_data)}")
        print(f"  数据库模特数: {len(models)}")
        
        # 检查名称匹配
        db_names = {model['name'] for model in models}
        json_names = set(original_data.keys())
        
        if db_names == json_names:
            print("  ✅ 模特名称完全匹配")
        else:
            print("  ❌ 模特名称不匹配")
            print(f"    数据库独有: {db_names - json_names}")
            print(f"    JSON独有: {json_names - db_names}")
        
        # 检查URL匹配
        mismatch_count = 0
        for model in models:
            name = model['name']
            db_url = model['url']
            if name in original_data:
                json_info = original_data[name]
                if isinstance(json_info, dict):
                    json_url = json_info.get('url', '')
                else:
                    json_url = json_info
                
                if db_url != json_url:
                    print(f"  ❌ URL不匹配 - {name}:")
                    print(f"    数据库: {db_url}")
                    print(f"    JSON: {json_url}")
                    mismatch_count += 1
        
        if mismatch_count == 0:
            print("  ✅ 所有URL匹配")
            
    except Exception as e:
        print(f"  ❌ JSON对比失败: {e}")
    
    # 5. 性能测试
    print("\n5. 性能测试:")
    import time
    
    # 测试查询性能
    start_time = time.time()
    cursor.execute("SELECT * FROM models WHERE name = 'Miss Kiss'")
    result = cursor.fetchone()
    query_time = time.time() - start_time
    
    print(f"  单条查询耗时: {query_time:.6f} 秒")
    
    # 测试批量查询性能
    start_time = time.time()
    cursor.execute("SELECT * FROM models")
    all_results = cursor.fetchall()
    batch_time = time.time() - start_time
    
    print(f"  批量查询耗时: {batch_time:.6f} 秒")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)

if __name__ == "__main__":
    detailed_verification()