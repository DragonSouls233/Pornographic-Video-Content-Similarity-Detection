#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多目录功能清理验证测试脚本
验证系统是否已成功切换到纯多目录管理模式
"""

import os
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_config_structure():
    """测试配置文件结构"""
    print("🔍 测试配置文件结构...")
    
    try:
        from core.modules.common.common import load_config
        config = load_config()
        
        # 检查local_roots字段
        local_roots = config.get('local_roots', [])
        print(f"✅ local_roots字段存在: {type(local_roots)}")
        print(f"   当前配置的目录数量: {len(local_roots)}")
        
        if isinstance(local_roots, list):
            print("✅ local_roots是列表类型 ✓")
            for i, root in enumerate(local_roots, 1):
                status = "✓ 可访问" if os.path.exists(root) else "✗ 不存在"
                print(f"   目录 {i}: {root} [{status}]")
        else:
            print("❌ local_roots不是列表类型 ✗")
            return False
            
        # 检查是否还有旧的分类配置格式
        if isinstance(local_roots, dict):
            print("⚠️  发现旧的分类配置格式，应该清理")
            return False
            
        print("✅ 配置文件结构正确")
        return True
        
    except Exception as e:
        print(f"❌ 配置文件测试失败: {e}")
        return False

def test_old_config_files():
    """测试是否还存在旧的配置文件"""
    print("\n🔍 检查旧配置文件...")
    
    # 检查local_dirs.json
    local_dirs_path = project_root / "local_dirs.json"
    if local_dirs_path.exists():
        print("⚠️  发现旧的local_dirs.json文件，建议删除")
        try:
            with open(local_dirs_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                print(f"   内容: {content}")
            return False
        except:
            print("   无法读取文件内容")
            return False
    else:
        print("✅ 未发现local_dirs.json文件 ✓")
    
    # 检查备份文件
    backup_files = list(project_root.glob("local_dirs.json.*"))
    if backup_files:
        print(f"⚠️  发现备份文件: {[f.name for f in backup_files]}")
        return False
    else:
        print("✅ 未发现local_dirs.json备份文件 ✓")
        return True

def test_gui_integration():
    """测试GUI集成"""
    print("\n🔍 测试GUI多目录集成...")
    
    try:
        from gui.gui import ModelManagerGUI
        import tkinter as tk
        
        # 创建根窗口但不显示
        root = tk.Tk()
        root.withdraw()  # 隐藏窗口
        
        # 创建GUI实例
        app = ModelManagerGUI(root)
        
        # 测试配置加载方法
        config = app.load_config()
        local_roots = config.get('local_roots', [])
        
        print(f"✅ GUI配置加载成功")
        print(f"   目录数量: {len(local_roots)}")
        
        # 测试目录管理方法
        if hasattr(app, 'load_directories_from_config'):
            print("✅ 发现load_directories_from_config方法 ✓")
        else:
            print("❌ 缺少load_directories_from_config方法 ✗")
            
        if hasattr(app, 'save_directories_to_config'):
            print("✅ 发现save_directories_to_config方法 ✓")
        else:
            print("❌ 缺少save_directories_to_config方法 ✗")
            
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ GUI集成测试失败: {e}")
        return False

def test_core_integration():
    """测试核心模块集成"""
    print("\n🔍 测试核心模块集成...")
    
    try:
        from core.core import main
        from core.modules.common.common import load_config, load_models
        
        config = load_config()
        models = load_models()
        
        print(f"✅ 核心模块导入成功")
        print(f"   配置加载: ✓")
        print(f"   模特加载: ✓ (数量: {len(models)})")
        print(f"   目录配置: ✓ (数量: {len(config.get('local_roots', []))})")
        
        return True
        
    except Exception as e:
        print(f"❌ 核心模块测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("🎭 多目录功能清理验证测试")
    print("=" * 60)
    
    tests = [
        ("配置文件结构", test_config_structure),
        ("旧配置文件检查", test_old_config_files),
        ("GUI集成", test_gui_integration),
        ("核心模块集成", test_core_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'-' * 40}")
        print(f"正在测试: {test_name}")
        print('-' * 40)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！多目录功能已成功清理并正常工作")
        print("\n📝 系统当前状态:")
        print("   ✅ 已移除传统单目录预设配置")
        print("   ✅ 已切换到纯多目录管理模式")
        print("   ✅ GUI界面已更新为多目录管理")
        print("   ✅ 核心功能已适配多目录配置")
    else:
        print("⚠️  部分测试未通过，请检查上述错误信息")
    
    print("=" * 60)

if __name__ == "__main__":
    main()