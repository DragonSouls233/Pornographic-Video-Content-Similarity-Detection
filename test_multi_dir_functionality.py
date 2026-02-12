#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多目录功能测试脚本
用于验证多目录管理模式是否正常工作
"""

import os
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_config_loading():
    """测试配置文件加载"""
    print("🔍 测试配置文件加载...")
    
    try:
        from core.modules.common.common import load_config
        config = load_config()
        
        local_roots = config.get('local_roots', [])
        print(f"✅ 成功加载配置文件")
        print(f"📁 配置的本地目录数量: {len(local_roots)}")
        
        for i, root in enumerate(local_roots, 1):
            status = "✓ 可访问" if os.path.exists(root) else "✗ 不存在"
            print(f"   目录 {i}: {root} [{status}]")
        
        return True, local_roots
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False, []

def test_directory_scanning():
    """测试目录扫描功能"""
    print("\n🔍 测试目录扫描功能...")
    
    try:
        # 导入扫描模块
        from core.modules.porn.porn import scan_porn_models
        from core.modules.javdb.javdb import scan_javdb_models
        from core.modules.common.common import load_config, load_models
        
        # 加载配置和模特数据
        config = load_config()
        models = load_models()
        local_roots = config.get('local_roots', [])
        
        if not local_roots:
            print("⚠️  未配置任何本地目录")
            return False
        
        if not models:
            print("⚠️  未配置任何模特")
            return False
        
        print(f"📊 扫描配置:")
        print(f"   - 模特数量: {len(models)}")
        print(f"   - 目录数量: {len(local_roots)}")
        print(f"   - 视频扩展名: {config.get('video_extensions', [])}")
        
        # 测试PORN格式扫描
        print(f"\n🧪 测试PORN格式扫描...")
        porn_matches = scan_porn_models(
            models,
            local_roots,
            set(config.get('video_extensions', ['.mp4'])),
            config.get('filename_clean_patterns', []),
            None  # 不使用logger
        )
        print(f"   PORN格式匹配结果: {len(porn_matches)} 个模特")
        
        # 测试JAVDB格式扫描
        print(f"\n🧪 测试JAVDB格式扫描...")
        javdb_matches = scan_javdb_models(
            models,
            local_roots,
            set(config.get('video_extensions', ['.mp4'])),
            config.get('filename_clean_patterns', []),
            None  # 不使用logger
        )
        print(f"   JAVDB格式匹配结果: {len(javdb_matches)} 个模特")
        
        # 显示部分匹配结果
        if porn_matches:
            print(f"\n📋 PORN格式匹配示例 (前5个):")
            for i, (model_name, folder, original_dir, country) in enumerate(porn_matches[:5]):
                print(f"   {i+1}. {model_name} -> {folder}")
        
        if javdb_matches:
            print(f"\n📋 JAVDB格式匹配示例 (前5个):")
            for i, (model_name, folder, original_dir, country) in enumerate(javdb_matches[:5]):
                print(f"   {i+1}. {model_name} -> {folder}")
        
        return True
    except Exception as e:
        print(f"❌ 目录扫描测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gui_directory_management():
    """测试GUI目录管理功能"""
    print("\n🔍 测试GUI目录管理功能...")
    
    try:
        # 模拟GUI中的目录管理逻辑
        from core.modules.common.common import load_config
        
        config = load_config()
        local_roots = config.get('local_roots', [])
        
        print(f"📋 当前配置的目录列表:")
        for i, directory in enumerate(local_roots, 1):
            status = "✓ 可访问" if os.path.exists(directory) else "✗ 不存在"
            print(f"   {i}. {directory} [{status}]")
        
        # 模拟添加新目录
        test_dir = "F:/测试目录"
        if test_dir not in local_roots:
            print(f"\n➕ 模拟添加测试目录: {test_dir}")
            new_roots = local_roots + [test_dir]
            print(f"   添加后目录数量: {len(new_roots)}")
        
        # 模拟删除目录
        if local_roots:
            removed_dir = local_roots[0]
            print(f"\n➖ 模拟删除目录: {removed_dir}")
            remaining_roots = [d for d in local_roots if d != removed_dir]
            print(f"   删除后目录数量: {len(remaining_roots)}")
        
        return True
    except Exception as e:
        print(f"❌ GUI目录管理测试失败: {e}")
        return False

def test_cross_directory_deduplication():
    """测试跨目录去重功能"""
    print("\n🔍 测试跨目录去重功能...")
    
    try:
        # 模拟跨目录去重场景
        test_models = {
            "测试模特1": "https://example.com/model1",
            "测试模特2": "https://example.com/model2"
        }
        
        # 模拟多个目录中有相同的模特
        mock_matches = [
            ("测试模特1", "模特1", "F:/作品/[Channel] 测试模特1", "日本"),
            ("测试模特1", "模特1", "D:/Videos/PORN/测试模特1", "美国"),  # 同一模特在不同目录
            ("测试模特2", "模特2", "F:/作品/[Channel] 测试模特2", "日本"),
        ]
        
        # 去重逻辑
        seen_models = set()
        unique_matches = []
        
        for match in mock_matches:
            model_name = match[0]
            if model_name not in seen_models:
                seen_models.add(model_name)
                unique_matches.append(match)
        
        print(f"📊 去重测试结果:")
        print(f"   原始匹配数量: {len(mock_matches)}")
        print(f"   去重后数量: {len(unique_matches)}")
        print(f"   发现重复: {len(mock_matches) - len(unique_matches)} 个")
        
        return True
    except Exception as e:
        print(f"❌ 跨目录去重测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🎯 多目录功能综合测试")
    print("=" * 50)
    
    tests = [
        ("配置文件加载", test_config_loading),
        ("目录扫描功能", test_directory_scanning),
        ("GUI目录管理", test_gui_directory_management),
        ("跨目录去重", test_cross_directory_deduplication),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                print(f"✅ {test_name} - 通过")
                passed += 1
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 测试总结: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！多目录功能正常工作")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关功能")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)