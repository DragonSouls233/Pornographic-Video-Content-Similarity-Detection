"""
快速测试脚本 - 验证所有修复是否正常工作
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_imports():
    """测试所有必需的模块是否可以导入"""
    print("=" * 60)
    print("测试模块导入...")
    print("=" * 60)
    
    modules = [
        ('beautifulsoup4', 'bs4'),
        ('requests', 'requests'),
        ('PyYAML', 'yaml'),
        ('lxml', 'lxml'),
        ('selenium', 'selenium'),
        ('webdriver_manager', 'webdriver_manager'),
        ('urllib3', 'urllib3'),
        ('certifi', 'certifi'),
        ('PySocks', 'socks'),
    ]
    
    success_count = 0
    fail_count = 0
    
    for display_name, import_name in modules:
        try:
            __import__(import_name)
            print(f"✅ {display_name:20s} - 已安装")
            success_count += 1
        except ImportError:
            print(f"❌ {display_name:20s} - 未安装")
            fail_count += 1
    
    print()
    print(f"成功: {success_count}, 失败: {fail_count}")
    print()
    
    return fail_count == 0


def test_config_loading():
    """测试配置文件加载"""
    print("=" * 60)
    print("测试配置文件加载...")
    print("=" * 60)
    
    try:
        from core.modules.common.common import load_config, load_models
        
        # 测试配置加载
        config = load_config('config.yaml')
        print(f"✅ 配置文件加载成功")
        print(f"   - 本地目录数: {len(config.get('local_roots', []))}")
        print(f"   - 代理启用: {config.get('network', {}).get('proxy', {}).get('enabled', False)}")
        print(f"   - 使用Selenium: {config.get('use_selenium', False)}")
        
        # 测试模特配置加载
        models = load_models('models.json')
        print(f"✅ 模特配置加载成功")
        print(f"   - 模特数量: {len(models)}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        print()
        return False


def test_selenium_helper():
    """测试 Selenium 助手"""
    print("=" * 60)
    print("测试 Selenium 助手...")
    print("=" * 60)
    
    try:
        from core.modules.common.selenium_helper import SeleniumHelper
        from core.modules.common.common import load_config
        
        config = load_config('config.yaml')
        
        print("✅ Selenium 助手模块导入成功")
        
        # 尝试创建实例（不实际启动浏览器）
        helper = SeleniumHelper(config)
        print("✅ Selenium 助手实例创建成功")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Selenium 助手测试失败: {e}")
        print()
        return False


def test_error_handler():
    """测试错误处理模块"""
    print("=" * 60)
    print("测试错误处理模块...")
    print("=" * 60)
    
    try:
        from core.modules.common.error_handler import (
            ErrorCollector,
            retry_on_exception,
            safe_execute
        )
        
        print("✅ 错误处理模块导入成功")
        
        # 测试错误收集器
        collector = ErrorCollector()
        collector.add_error('network', '测试网络错误')
        collector.add_error('parsing', '测试解析错误')
        
        stats = collector.get_statistics()
        print(f"✅ 错误收集器测试成功")
        print(f"   - 网络错误: {stats.get('network', 0)}")
        print(f"   - 解析错误: {stats.get('parsing', 0)}")
        
        # 测试重试装饰器
        @retry_on_exception(max_retries=2, retry_delay=0.1, exceptions=(ValueError,))
        def test_func():
            return "success"
        
        result = test_func()
        print(f"✅ 重试装饰器测试成功: {result}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ 错误处理模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_file_structure():
    """测试文件结构完整性"""
    print("=" * 60)
    print("测试文件结构...")
    print("=" * 60)
    
    required_files = [
        'requirements.txt',
        'config.yaml',
        'models.json',
        'local_dirs.json',
        'core/core.py',
        'core/modules/common/common.py',
        'core/modules/common/selenium_helper.py',
        'core/modules/common/error_handler.py',
        'core/modules/porn/porn.py',
        'core/modules/javdb/javdb.py',
        'gui/gui.py',
        'gui/browser.py',
        'gui/config_template.py',
        '打包脚本.bat',
        'build.sh',
        'README.md',
        'docs/INSTALL.md',
        'docs/README.md',
    ]
    
    success_count = 0
    fail_count = 0
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path:40s} - 存在")
            success_count += 1
        else:
            print(f"❌ {file_path:40s} - 不存在")
            fail_count += 1
    
    print()
    print(f"成功: {success_count}, 失败: {fail_count}")
    print()
    
    return fail_count == 0


def test_proxy_config():
    """测试代理配置"""
    print("=" * 60)
    print("测试代理配置...")
    print("=" * 60)
    
    try:
        from core.modules.common.common import load_config, test_proxy_connection
        
        config = load_config('config.yaml')
        proxy_config = config.get('network', {}).get('proxy', {})
        if not proxy_config:
            proxy_config = config.get('proxy', {})
        
        print(f"代理启用: {proxy_config.get('enabled', False)}")
        print(f"代理类型: {proxy_config.get('type', 'N/A')}")
        print(f"代理主机: {proxy_config.get('host', 'N/A')}")
        print(f"代理端口: {proxy_config.get('port', 'N/A')}")
        print(f"HTTP代理: {proxy_config.get('http', 'N/A')}")
        print(f"HTTPS代理: {proxy_config.get('https', 'N/A')}")
        
        if proxy_config.get('enabled', False):
            print("\n⚠️  代理已启用，正在测试连接...")
            
            # 创建一个简单的 logger 用于测试
            import logging
            test_logger = logging.getLogger('test_proxy')
            test_logger.setLevel(logging.INFO)
            
            # 测试代理连接
            result = test_proxy_connection(proxy_config, timeout=10, logger=test_logger)
            
            if result:
                print("✅ 代理连接测试成功")
            else:
                print("❌ 代理连接测试失败")
                print("💡 提示: 请确保代理工具正在运行")
                return False
        else:
            print("\nℹ️  代理未启用")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ 代理配置测试失败: {e}")
        print()
        return False


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "模特查重管理系统 - 测试套件" + " " * 16 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    tests = [
        ("模块导入", test_imports),
        ("配置加载", test_config_loading),
        ("文件结构", test_file_structure),
        ("Selenium 助手", test_selenium_helper),
        ("错误处理", test_error_handler),
        ("代理配置", test_proxy_config),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # 输出总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20s} - {status}")
    
    print()
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统已准备就绪。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查上述错误信息。")
        print("\n💡 提示：")
        print("   1. 确保已运行: pip install -r requirements.txt")
        print("   2. 检查配置文件是否存在和格式正确")
        print("   3. 如果 Selenium 测试失败，确保安装了 Chrome 浏览器")
        return 1


if __name__ == "__main__":
    sys.exit(main())
