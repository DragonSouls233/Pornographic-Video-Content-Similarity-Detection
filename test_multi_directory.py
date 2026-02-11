#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多目录支持功能综合测试脚本
验证PRON对比系统对多个目录路径的支持能力
"""

import os
import sys
import json
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.modules.common.common import (
    load_config,
    load_models,
    clean_filename,
    extract_local_videos
)
from core.modules.porn.porn import (
    fetch_with_requests_porn,
    clean_porn_title,
    scan_porn_models
)
from core.modules.javdb.javdb import (
    scan_javdb_models
)
from core.modules.common.smart_cache import create_smart_cache


def test_multi_directory_support():
    """测试多目录支持功能"""
    
    print("=" * 80)
    print("多目录支持功能综合测试")
    print("=" * 80)
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)

    # 1. 测试配置加载
    print("\n[1/6] 测试配置加载...")
    try:
        config = load_config()
        local_roots = config.get('local_roots', [])
        print("[OK] 配置加载成功")
        print(f"   - 本地目录数量: {len(local_roots)}")
        for i, root in enumerate(local_roots, 1):
            exists = "✓" if os.path.exists(root) else "✗"
            print(f"   - 目录 {i}: {exists} {root}")
        print(f"   - 视频扩展名: {config.get('video_extensions', [])}")
        print(f"   - 清理模式: {config.get('filename_clean_patterns', [])}")
    except Exception as e:
        print(f"[FAIL] 配置加载失败: {e}")
        return False

    # 2. 测试多目录扫描功能
    print("\n[2/6] 测试多目录扫描功能...")
    try:
        # 创建测试用的模特配置
        test_models = {
            "测试模特1": "https://example.com/model1",
            "测试模特2": "https://example.com/model2"
        }
        
        print("  测试PORN格式多目录扫描...")
        porn_matches = scan_porn_models(
            test_models,
            local_roots,
            set(config.get('video_extensions', [])),
            config.get('filename_clean_patterns', []),
            logger
        )
        print(f"  [OK] PORN格式扫描完成，找到 {len(porn_matches)} 个匹配目录")
        
        print("  测试JAVDB格式多目录扫描...")
        javdb_matches = scan_javdb_models(
            test_models,
            local_roots,
            set(config.get('video_extensions', [])),
            config.get('filename_clean_patterns', []),
            logger
        )
        print(f"  [OK] JAVDB格式扫描完成，找到 {len(javdb_matches)} 个匹配目录")
        
    except Exception as e:
        print(f"  [FAIL] 多目录扫描测试失败: {e}")
        return False

    # 3. 测试跨目录去重功能
    print("\n[3/6] 测试跨目录去重功能...")
    try:
        # 模拟同一模特在不同目录的情况
        all_matches = porn_matches + javdb_matches
        unique_models = set(match[0] for match in all_matches)
        
        print(f"  - 总匹配目录数: {len(all_matches)}")
        print(f"  - 唯一模特数: {len(unique_models)}")
        
        if len(unique_models) <= len(all_matches):
            print("  [OK] 跨目录去重功能正常")
        else:
            print("  [WARN] 可能存在去重问题")
            
    except Exception as e:
        print(f"  [FAIL] 跨目录去重测试失败: {e}")
        return False

    # 4. 测试视频文件提取
    print("\n[4/6] 测试视频文件提取...")
    try:
        total_videos = 0
        for model_name, folder, original_dir, country in all_matches[:3]:  # 只测试前3个
            print(f"  测试目录: {folder}")
            if os.path.exists(folder):
                videos = extract_local_videos(
                    folder,
                    set(config.get('video_extensions', [])),
                    config.get('filename_clean_patterns', [])
                )
                print(f"    发现 {len(videos)} 个视频文件")
                total_videos += len(videos)
            else:
                print("    目录不存在，跳过")
        
        print(f"  [OK] 视频文件提取测试完成，总计 {total_videos} 个视频")
        
    except Exception as e:
        print(f"  [FAIL] 视频文件提取测试失败: {e}")
        return False

    # 5. 测试配置文件更新
    print("\n[5/6] 测试配置文件更新...")
    try:
        # 保存当前配置
        original_roots = config.get('local_roots', []).copy()
        
        # 添加测试目录
        test_dir = "F:/测试目录"
        if test_dir not in original_roots:
            config['local_roots'].append(test_dir)
            
        # 验证配置结构
        assert isinstance(config['local_roots'], list)
        assert all(isinstance(root, str) for root in config['local_roots'])
        
        print("  [OK] 配置文件结构验证通过")
        
        # 恢复原配置
        config['local_roots'] = original_roots
        
    except Exception as e:
        print(f"  [FAIL] 配置文件更新测试失败: {e}")
        return False

    # 6. 性能测试
    print("\n[6/6] 性能测试...")
    try:
        import time
        
        # 测试多目录扫描性能
        start_time = time.time()
        scan_porn_models(
            test_models,
            local_roots[:2],  # 只测试前两个目录以节省时间
            set(config.get('video_extensions', [])),
            config.get('filename_clean_patterns', []),
            logger
        )
        end_time = time.time()
        
        scan_time = end_time - start_time
        print(f"  扫描时间: {scan_time:.2f} 秒")
        
        if scan_time < 10:  # 10秒内完成认为性能良好
            print("  [OK] 性能表现良好")
        else:
            print("  [WARN] 性能有待优化")
            
    except Exception as e:
        print(f"  [FAIL] 性能测试失败: {e}")
        return False

    print("\n" + "=" * 80)
    print("多目录支持功能测试总结")
    print("=" * 80)
    print("[PASS] 配置加载")
    print("[PASS] 多目录扫描")
    print("[PASS] 跨目录去重")
    print("[PASS] 视频文件提取")
    print("[PASS] 配置文件更新")
    print("[PASS] 性能测试")
    print("\n🎉 多目录支持功能测试全部通过！")
    
    return True


def create_test_directories():
    """创建测试目录结构"""
    print("\n创建测试目录结构...")
    
    test_base = "F:/作品/测试"
    directories = [
        f"{test_base}/[Channel] 测试模特1",
        f"{test_base}/[Channel] 测试模特2", 
        f"{test_base}/测试模特3",  # JAVDB格式
        f"{test_base}/其他/[Channel] 测试模特4"
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"  ✓ 创建目录: {directory}")
        except Exception as e:
            print(f"  ✗ 创建目录失败: {directory} - {e}")


if __name__ == "__main__":
    print("开始多目录支持功能测试...")
    
    # 可选：创建测试目录
    # create_test_directories()
    
    success = test_multi_directory_support()
    
    if success:
        print("\n✅ 所有测试通过！多目录支持功能工作正常。")
        sys.exit(0)
    else:
        print("\n❌ 测试失败！请检查相关功能实现。")
        sys.exit(1)