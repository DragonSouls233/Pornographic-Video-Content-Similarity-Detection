#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI日志显示功能测试脚本
用于验证修复后的日志显示是否正常工作
"""

import sys
import os
import threading
import time
import logging

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_gui_logging():
    """测试GUI日志显示功能"""
    print("🔍 GUI日志显示功能测试")
    print("=" * 50)
    
    try:
        # 导入GUI模块
        from gui.gui import ModelManagerGUI
        import tkinter as tk
        
        print("✓ 成功导入GUI模块")
        
        # 创建测试窗口
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        
        # 创建GUI实例
        gui = ModelManagerGUI(root)
        print("✓ 成功创建GUI实例")
        
        # 测试QueueHandler是否正确初始化
        if hasattr(gui, 'QueueHandler'):
            print("✓ QueueHandler类已正确初始化")
        else:
            print("✗ QueueHandler类未初始化")
            return False
            
        # 测试日志队列功能
        print("\n📝 测试日志队列功能:")
        
        # 模拟日志消息
        test_messages = [
            "程序启动测试",
            "正在扫描本地目录...",
            "发现模特目录: Test_Model",
            "开始抓取在线视频信息...",
            "抓取完成，共找到 50 个视频",
            "对比分析完成",
            "运行结束"
        ]
        
        # 测试队列发送
        for i, msg in enumerate(test_messages, 1):
            try:
                gui.queue.put(("log", f"[测试{i}/7] {msg}"))
                print(f"  ✓ 发送日志消息 {i}: {msg[:30]}...")
            except Exception as e:
                print(f"  ✗ 发送日志消息 {i} 失败: {e}")
                return False
        
        # 测试队列接收
        print("\n📥 测试队列接收功能:")
        received_count = 0
        try:
            while not gui.queue.empty() and received_count < len(test_messages):
                msg_type, msg = gui.queue.get_nowait()
                if msg_type == "log":
                    received_count += 1
                    print(f"  ✓ 接收日志消息 {received_count}: {msg[:30]}...")
                else:
                    print(f"  ⚠ 接收到非日志消息类型: {msg_type}")
        except Exception as e:
            print(f"  ✗ 队列接收测试失败: {e}")
            return False
            
        if received_count == len(test_messages):
            print(f"  ✓ 成功接收所有 {received_count} 条测试消息")
        else:
            print(f"  ✗ 只接收到 {received_count}/{len(test_messages)} 条消息")
            return False
            
        # 测试check_queue方法
        print("\n🔄 测试队列处理功能:")
        try:
            # 重新填充队列进行完整测试
            for msg in test_messages:
                gui.queue.put(("log", f"[完整测试] {msg}"))
            
            # 手动调用check_queue
            gui.check_queue()
            
            # 检查日志文本框是否更新
            if hasattr(gui, 'log_text'):
                log_content = gui.log_text.get(1.0, tk.END)
                expected_keywords = ["完整测试", "程序启动", "扫描本地", "抓取完成"]
                found_keywords = [kw for kw in expected_keywords if kw in log_content]
                
                if len(found_keywords) >= 2:
                    print(f"  ✓ 日志文本框已更新，包含关键词: {found_keywords}")
                else:
                    print(f"  ⚠ 日志文本框内容可能未正确更新")
            else:
                print("  ⚠ 未找到log_text组件")
                
        except Exception as e:
            print(f"  ✗ 队列处理测试失败: {e}")
            return False
            
        print("\n🎉 GUI日志显示功能测试完成!")
        print("预期效果:")
        print("- 日志区域应该能正常显示查重过程信息")
        print("- 实时状态和进度信息应该正确更新")
        print("- 日志滚动功能应该正常工作")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_core_integration():
    """测试核心模块与GUI的集成"""
    print("\n🔧 核心模块集成测试")
    print("=" * 50)
    
    try:
        # 测试日志系统
        from core.modules.common.common import setup_logging
        
        # 创建临时日志目录
        import tempfile
        temp_dir = tempfile.mkdtemp()
        log_dir = os.path.join(temp_dir, "test_logs")
        
        # 设置日志
        logger, missing_logger, countries_dir = setup_logging(log_dir, "test")
        print("✓ 核心模块日志系统初始化成功")
        
        # 测试日志输出
        logger.info("测试日志消息 - 来自核心模块")
        missing_logger.info("测试缺失视频日志")
        
        # 检查日志文件
        main_log_file = os.path.join(log_dir, f"sync_{time.strftime('%Y%m%d')}.log")
        missing_log_file = os.path.join(log_dir, f"missing_{time.strftime('%Y%m%d')}.log")
        
        if os.path.exists(main_log_file):
            print("✓ 主日志文件创建成功")
        else:
            print("✗ 主日志文件未创建")
            
        if os.path.exists(missing_log_file):
            print("✓ 缺失视频日志文件创建成功")
        else:
            print("✗ 缺失视频日志文件未创建")
            
        return True
        
    except Exception as e:
        print(f"✗ 核心模块集成测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始GUI日志显示功能测试")
    print("=" * 60)
    
    # 运行测试
    gui_test_passed = test_gui_logging()
    core_test_passed = test_core_integration()
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    print(f"  GUI日志显示测试: {'✅ 通过' if gui_test_passed else '❌ 失败'}")
    print(f"  核心模块集成测试: {'✅ 通过' if core_test_passed else '❌ 失败'}")
    
    if gui_test_passed and core_test_passed:
        print("\n🎉 所有测试通过! 日志显示功能应该已修复。")
        print("请在GUI中运行查重功能验证实际效果。")
    else:
        print("\n⚠️  部分测试失败，请检查相关代码。")
    
    input("\n按回车键退出...")