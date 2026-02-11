"""
存储方案性能对比测试
比较JSON、SQLite、混合存储的性能差异
"""

import time
import json
import tempfile
import os
import logging
from typing import Dict, List
from pathlib import Path

# 导入我们的存储模块
from .model_database import DatabaseModelAdapter
from .enhanced_config import create_config_manager


def generate_test_data(count: int) -> Dict[str, Dict]:
    """生成测试数据"""
    test_data = {}
    for i in range(count):
        model_name = f"TestModel_{i:04d}"
        test_data[model_name] = {
            "url": f"https://example.com/model/{i}",
            "module": "PORN" if i % 2 == 0 else "JAVDB",
            "country": "欧美" if i % 3 == 0 else "日本",
            "status": "active"
        }
    return test_data


def benchmark_json_storage(data: Dict, iterations: int = 10) -> Dict[str, float]:
    """测试JSON存储性能"""
    print("测试JSON存储性能...")
    
    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False)
    temp_file.close()
    json_path = temp_file.name
    
    try:
        times = {
            'write': [],
            'read': [],
            'search': []
        }
        
        for _ in range(iterations):
            # 写入测试
            start_time = time.time()
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            write_time = time.time() - start_time
            times['write'].append(write_time)
            
            # 读取测试
            start_time = time.time()
            with open(json_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            read_time = time.time() - start_time
            times['read'].append(read_time)
            
            # 搜索测试
            start_time = time.time()
            search_results = {k: v for k, v in loaded_data.items() 
                            if 'TestModel_001' in k}
            search_time = time.time() - start_time
            times['search'].append(search_time)
        
        # 计算平均时间
        avg_times = {k: sum(v)/len(v) for k, v in times.items()}
        
        print(f"  写入平均时间: {avg_times['write']*1000:.2f} ms")
        print(f"  读取平均时间: {avg_times['read']*1000:.2f} ms")
        print(f"  搜索平均时间: {avg_times['search']*1000:.2f} ms")
        
        return avg_times
        
    finally:
        # 清理临时文件
        os.unlink(json_path)


def benchmark_database_storage(data: Dict, iterations: int = 10) -> Dict[str, float]:
    """测试数据库存储性能"""
    print("测试数据库存储性能...")
    
    # 创建临时数据库
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    db_path = temp_db.name
    
    try:
        # 初始化数据库
        db_adapter = DatabaseModelAdapter(db_path)
        
        times = {
            'write': [],
            'read': [],
            'search': []
        }
        
        for _ in range(iterations):
            # 写入测试
            start_time = time.time()
            for name, info in data.items():
                db_adapter.db.add_model(name, info['url'], info['module'])
            write_time = time.time() - start_time
            times['write'].append(write_time)
            
            # 读取测试
            start_time = time.time()
            loaded_data = db_adapter.load_models()
            read_time = time.time() - start_time
            times['read'].append(read_time)
            
            # 搜索测试
            start_time = time.time()
            search_results = db_adapter.db.search_models('TestModel_001')
            search_time = time.time() - start_time
            times['search'].append(search_time)
        
        # 计算平均时间
        avg_times = {k: sum(v)/len(v) for k, v in times.items()}
        
        print(f"  写入平均时间: {avg_times['write']*1000:.2f} ms")
        print(f"  读取平均时间: {avg_times['read']*1000:.2f} ms")
        print(f"  搜索平均时间: {avg_times['search']*1000:.2f} ms")
        
        return avg_times
        
    finally:
        # 清理临时数据库
        os.unlink(db_path)


def benchmark_hybrid_storage(data: Dict, iterations: int = 10) -> Dict[str, float]:
    """测试混合存储性能"""
    print("测试混合存储性能...")
    
    # 创建临时文件
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_json = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
    temp_db.close()
    temp_json.close()
    
    try:
        # 初始化混合存储
        config_manager = create_config_manager("hybrid",
                                             db_path=temp_db.name,
                                             json_path=temp_json.name,
                                             hot_keys={'cache_', 'temp_'})
        
        times = {
            'write': [],
            'read': [],
            'search': []
        }
        
        for _ in range(iterations):
            # 写入测试（热数据到数据库，冷数据到JSON）
            start_time = time.time()
            # 热数据
            config_manager.set("cache.models", data)
            # 冷数据
            config_manager.set("backup.models", data)
            write_time = time.time() - start_time
            times['write'].append(write_time)
            
            # 读取测试
            start_time = time.time()
            cache_data = config_manager.get("cache.models")
            backup_data = config_manager.get("backup.models")
            read_time = time.time() - start_time
            times['read'].append(read_time)
            
            # 搜索测试（模拟）
            start_time = time.time()
            # 混合存储的搜索需要分别查询
            cache_results = {k: v for k, v in cache_data.items() 
                           if 'TestModel_001' in k} if cache_data else {}
            search_time = time.time() - start_time
            times['search'].append(search_time)
        
        # 计算平均时间
        avg_times = {k: sum(v)/len(v) for k, v in times.items()}
        
        print(f"  写入平均时间: {avg_times['write']*1000:.2f} ms")
        print(f"  读取平均时间: {avg_times['read']*1000:.2f} ms")
        print(f"  搜索平均时间: {avg_times['search']*1000:.2f} ms")
        
        return avg_times
        
    finally:
        # 清理临时文件
        os.unlink(temp_db.name)
        os.unlink(temp_json.name)


def run_performance_comparison():
    """运行完整的性能对比测试"""
    
    # 配置日志
    logging.basicConfig(level=logging.WARNING)
    
    print("=" * 60)
    print("存储方案性能对比测试")
    print("=" * 60)
    
    # 测试不同数据量
    test_sizes = [100, 500, 1000, 2000]
    
    results = {}
    
    for size in test_sizes:
        print(f"\n测试数据量: {size} 条记录")
        print("-" * 40)
        
        # 生成测试数据
        test_data = generate_test_data(size)
        
        # 测试各种存储方案
        json_times = benchmark_json_storage(test_data)
        db_times = benchmark_database_storage(test_data)
        hybrid_times = benchmark_hybrid_storage(test_data)
        
        results[size] = {
            'json': json_times,
            'database': db_times,
            'hybrid': hybrid_times
        }
    
    # 输出汇总报告
    print("\n" + "=" * 60)
    print("性能对比汇总报告")
    print("=" * 60)
    
    print("\n写入性能对比 (ms):")
    print("数据量\tJSON\t数据库\t混合")
    for size in test_sizes:
        json_write = results[size]['json']['write'] * 1000
        db_write = results[size]['database']['write'] * 1000
        hybrid_write = results[size]['hybrid']['write'] * 1000
        print(f"{size}\t{json_write:.2f}\t{db_write:.2f}\t{hybrid_write:.2f}")
    
    print("\n读取性能对比 (ms):")
    print("数据量\tJSON\t数据库\t混合")
    for size in test_sizes:
        json_read = results[size]['json']['read'] * 1000
        db_read = results[size]['database']['read'] * 1000
        hybrid_read = results[size]['hybrid']['read'] * 1000
        print(f"{size}\t{json_read:.2f}\t{db_read:.2f}\t{hybrid_read:.2f}")
    
    print("\n搜索性能对比 (ms):")
    print("数据量\tJSON\t数据库\t混合")
    for size in test_sizes:
        json_search = results[size]['json']['search'] * 1000
        db_search = results[size]['database']['search'] * 1000
        hybrid_search = results[size]['hybrid']['search'] * 1000
        print(f"{size}\t{json_search:.2f}\t{db_search:.2f}\t{hybrid_search:.2f}")
    
    # 推荐建议
    print("\n" + "=" * 60)
    print("推荐建议")
    print("=" * 60)
    print("• 小型项目 (< 100条记录): 继续使用JSON，简单高效")
    print("• 中型项目 (100-1000条记录): 建议迁移到SQLite数据库")
    print("• 大型项目 (> 1000条记录): 强烈推荐使用数据库存储")
    print("• 高性能要求: 考虑混合存储方案")


if __name__ == "__main__":
    run_performance_comparison()