#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""集成测试脚本"""

import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """测试导入"""
    try:
        logger.info("🔍 测试导入...")
        
        from core.modules.porn import (
            UnifiedDownloader,
            PornDownloader,
            PornHubDownloaderV3Fixed,
            download_porn_video,
            download_porn_videos
        )
        
        logger.info("✅ 成功导入所有PORN模块")
        logger.info(f"  - UnifiedDownloader: {UnifiedDownloader.__name__}")
        logger.info(f"  - PornDownloader: {PornDownloader.__name__}")
        logger.info(f"  - PornHubDownloaderV3Fixed: {PornHubDownloaderV3Fixed.__name__}")
        logger.info(f"  - download_porn_video: 便捷函数")
        logger.info(f"  - download_porn_videos: 便捷函数")
        
        return True
    except Exception as e:
        logger.error(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """测试配置"""
    try:
        logger.info("\n🔍 测试配置...")
        import yaml
        
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        download_config = config.get("download", {})
        
        logger.info("✅ 配置加载成功")
        logger.info(f"  - 默认版本: {download_config.get('default_version')}")
        logger.info(f"  - 自动降级: {download_config.get('enable_fallback')}")
        logger.info(f"  - 默认超时: {download_config.get('timeout')}秒")
        logger.info(f"  - 并发线程: {download_config.get('max_workers')}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 配置测试失败: {e}")
        return False

def test_gui():
    """测试GUI导入"""
    try:
        logger.info("\n🔍 测试GUI导入...")
        from gui.gui import ModelManagerGUI
        logger.info("✅ GUI模块导入成功")
        return True
    except Exception as e:
        logger.error(f"❌ GUI导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("集成测试 - V1/V3统一下载器")
    logger.info("=" * 60)
    
    results = []
    results.append(("导入测试", test_imports()))
    results.append(("配置测试", test_config()))
    results.append(("GUI测试", test_gui()))
    
    logger.info("\n" + "=" * 60)
    logger.info("测试结果总结")
    logger.info("=" * 60)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
    
    all_pass = all(r for _, r in results)
    
    if all_pass:
        logger.info("\n✅ 所有测试通过！集成完成！")
        sys.exit(0)
    else:
        logger.info("\n❌ 部分测试失败，请检查")
        sys.exit(1)
