"""
代理连接测试脚本
用于测试代理配置是否正确
"""

import sys
import os
import io

# 设置标准输出编码为 UTF-8（解决 Windows 控制台乱码）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.modules.common.common import load_config, test_proxy_connection
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    """测试代理连接"""
    print("\n" + "=" * 60)
    print("代理连接测试工具")
    print("=" * 60 + "\n")
    
    try:
        # 加载配置
        logger.info("📄 加载配置文件...")
        config = load_config('config.yaml')
        
        # 获取代理配置
        proxy_config = config.get('network', {}).get('proxy', {})
        if not proxy_config:
            # 兼容旧版配置
            proxy_config = config.get('proxy', {})
        
        if not proxy_config:
            logger.error("❌ 配置文件中没有找到代理配置")
            return 1
        
        # 显示代理配置
        print("\n当前代理配置：")
        print("-" * 40)
        print(f"启用状态: {'✅ 已启用' if proxy_config.get('enabled', False) else '❌ 未启用'}")
        print(f"代理类型: {proxy_config.get('type', 'N/A')}")
        print(f"主机地址: {proxy_config.get('host', 'N/A')}")
        print(f"端口号:   {proxy_config.get('port', 'N/A')}")
        print(f"HTTP代理: {proxy_config.get('http', 'N/A')}")
        print(f"HTTPS代理: {proxy_config.get('https', 'N/A')}")
        print("-" * 40 + "\n")
        
        if not proxy_config.get('enabled', False):
            logger.info("ℹ️  代理未启用，无需测试")
            return 0
        
        # 测试代理连接
        logger.info("🔍 开始测试代理连接...")
        result = test_proxy_connection(proxy_config, timeout=10, logger=logger)
        
        print("\n" + "=" * 60)
        if result:
            print("✅ 测试结果: 代理连接成功！")
            print("=" * 60)
            print("\n✨ 你的代理配置正确，可以正常使用系统。")
            return 0
        else:
            print("❌ 测试结果: 代理连接失败！")
            print("=" * 60)
            print("\n请检查以下问题：")
            print("  1. 代理工具（如 v2rayN、Clash 等）是否已启动")
            print("  2. 代理配置是否正确（主机地址和端口）")
            print("  3. 代理工具是否已成功连接到服务器")
            print("  4. 防火墙是否阻止了代理连接")
            print("\n💡 解决方法：")
            print("  • 启动代理工具并确保连接成功")
            print("  • 在 config.yaml 中修改代理配置")
            print("  • 或者在 config.yaml 中设置 proxy.enabled: false 禁用代理")
            return 1
            
    except FileNotFoundError:
        logger.error("❌ 配置文件 config.yaml 不存在")
        return 1
    except Exception as e:
        logger.error(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
