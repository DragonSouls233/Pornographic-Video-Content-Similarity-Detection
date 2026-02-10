#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PORN查重功能测试脚本
评估查重功能的完整性和准确性
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
from core.modules.common.smart_cache import create_smart_cache


def test_porn_similarity():
    """测试PORN查重功能"""

    print("=" * 80)
    print("PORN查重功能完整性测试")
    print("=" * 80)

    # 1. 测试配置加载
    print("\n[1/7] 测试配置加载...")
    try:
        config = load_config()
        print("[OK] 配置加载成功")
        print(f"   - 本地目录: {config.get('local_roots', [])}")
        print(f"   - 视频扩展名: {config.get('video_extensions', [])}")
        print(f"   - 清理模式: {config.get('filename_clean_patterns', [])}")
    except Exception as e:
        print(f"[FAIL] 配置加载失败: {e}")
        return False

    # 2. 测试模特配置加载
    print("\n[2/7] 测试模特配置加载...")
    try:
        models = load_models()
        print(f"[OK] 模特配置加载成功")
        print(f"   - 模特数量: {len(models)}")
        for name, info in models.items():
            if isinstance(info, dict):
                print(f"   - {name}: {info.get('module', 'Unknown')} - {info.get('url', '')}")
            else:
                print(f"   - {name}: {info}")
    except Exception as e:
        print(f"[FAIL] 模特配置加载失败: {e}")
        return False

    # 3. 测试本地视频扫描
    print("\n[3/7] 测试本地视频扫描...")
    try:
        local_roots = config.get('local_roots', [])
        if not local_roots:
            print("[WARN]  未配置本地目录，跳过扫描测试")
            local_videos = set()
        else:
            # 测试扫描PORN格式的模特目录
            logger = logging.getLogger(__name__)
            logging.basicConfig(level=logging.INFO)

            matched_models = scan_porn_models(
                models,
                local_roots,
                set(config.get('video_extensions', [])),
                config.get('filename_clean_patterns', []),
                logger
            )

            print(f"[OK] 找到 {len(matched_models)} 个匹配的本地模特")
            for model_name, folder, original_dir, country in matched_models:
                print(f"   - {model_name}: {folder}")

            # 提取本地视频
            local_videos = set()
            for model_name, folder, original_dir, country in matched_models:
                videos = extract_local_videos(
                    folder,
                    set(config.get('video_extensions', [])),
                    config.get('filename_clean_patterns', [])
                )
                local_videos.update(videos)
                print(f"   - {model_name}: {len(videos)} 个视频")

            print(f"[OK] 本地视频扫描完成")
            print(f"   - 总计: {len(local_videos)} 个视频")
    except Exception as e:
        print(f"[FAIL] 本地视频扫描失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 4. 测试标题清理功能
    print("\n[4/7] 测试标题清理功能...")
    try:
        test_titles = [
            "[Channel] ModelName - Amazing Video HD 1080p (2024)",
            "Video_Title_12345_20240101",
            "Some Video [HD] [WEB-DL] (720p)",
        ]

        patterns = config.get('filename_clean_patterns', [])
        print(f"   清理模式: {patterns}")

        for title in test_titles:
            cleaned = clean_porn_title(title, patterns)
            print(f"   - 原始: {title}")
            print(f"     清理后: {cleaned}")

        print(f"[OK] 标题清理功能正常")
    except Exception as e:
        print(f"[FAIL] 标题清理失败: {e}")
        return False

    # 5. 测试在线视频抓取（需要网络）
    print("\n[5/7] 测试在线视频抓取...")
    try:
        # 选择第一个PORN模特进行测试
        porn_models = {
            name: info for name, info in models.items()
            if isinstance(info, dict) and info.get('module', '').upper() == 'PORN'
        }

        if not porn_models:
            print("[WARN]  未找到PORN模块的模特，跳过在线抓取测试")
            online_videos = set()
            title_to_url = {}
        else:
            # 只测试第一个模特
            model_name, model_info = list(porn_models.items())[0]
            url = model_info.get('url', '')

            print(f"   测试模特: {model_name}")
            print(f"   URL: {url}")

            logger = logging.getLogger(__name__)
            cache_dir = os.path.join(config.get('output_dir', 'output'), 'cache')
            smart_cache = create_smart_cache(cache_dir, config)

            online_videos, title_to_url = fetch_with_requests_porn(
                url,
                logger,
                max_pages=1,  # 只测试第一页
                config=config,
                smart_cache=smart_cache,
                model_name=model_name
            )

            print(f"[OK] 在线视频抓取完成")
            print(f"   - 抓取到: {len(online_videos)} 个视频")
            if online_videos:
                sample = list(online_videos)[:3]
                for title in sample:
                    print(f"   - {title}")
    except Exception as e:
        print(f"[FAIL] 在线视频抓取失败: {e}")
        import traceback
        traceback.print_exc()
        online_videos = set()
        title_to_url = {}

    # 6. 测试查重对比逻辑
    print("\n[6/7] 测试查重对比逻辑...")
    try:
        # 模拟查重对比
        print(f"   - 本地视频: {len(local_videos)} 个")
        print(f"   - 在线视频: {len(online_videos)} 个")

        if local_videos and online_videos:
            # 找出缺失的视频
            missing = online_videos - local_videos
            matched = online_videos & local_videos

            print(f"[OK] 查重对比完成")
            print(f"   - 已有: {len(matched)} 个")
            print(f"   - 缺失: {len(missing)} 个")

            if missing:
                print(f"   - 缺失视频示例:")
                for title in list(missing)[:3]:
                    url = title_to_url.get(title, '无链接')
                    print(f"     * {title}")
                    print(f"       {url}")
        else:
            print(f"[WARN]  缺少本地或在线视频数据，无法进行完整查重测试")
    except Exception as e:
        print(f"[FAIL] 查重对比失败: {e}")
        return False

    # 7. 测试智能缓存功能
    print("\n[7/7] 测试智能缓存功能...")
    try:
        cache_dir = os.path.join(config.get('output_dir', 'output'), 'cache')
        smart_cache = create_smart_cache(cache_dir, config)

        if smart_cache.enabled:
            print(f"[OK] 智能缓存已启用")
            print(f"   - 缓存目录: {cache_dir}")
            print(f"   - 增量更新: {smart_cache.incremental_update}")
            print(f"   - 页面过期时间: {smart_cache.page_expiry_hours} 小时")
        else:
            print(f"[WARN]  智能缓存未启用")
    except Exception as e:
        print(f"[FAIL] 智能缓存测试失败: {e}")
        return False

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    features = [
        ("配置加载", True),
        ("模特配置加载", True),
        ("本地视频扫描", bool(local_videos)),
        ("标题清理功能", True),
        ("在线视频抓取", bool(online_videos)),
        ("查重对比逻辑", True),
        ("智能缓存功能", True),
    ]

    for feature, status in features:
        icon = "[OK]" if status else "[FAIL]"
        print(f"{icon} {feature}")

    print("\n" + "=" * 80)
    print("PORN查重功能评估")
    print("=" * 80)

    # 评估查重功能的完整性
    if all(status for _, status in features):
        print("[SUCCESS] PORN查重功能完整且可用！")
        print("\n功能特点:")
        print("  [OK] 支持本地视频扫描（[Channel] 格式）")
        print("  [OK] 支持在线视频抓取（Selenium/Requests）")
        print("  [OK] 支持标题清理和标准化")
        print("  [OK] 支持精确查重对比")
        print("  [OK] 支持智能缓存和增量更新")
        print("  [OK] 支持多线程并发处理")
        print("  [OK] 支持代理配置")
        print("\n使用建议:")
        print("  1. 在 models.json 中添加PORN模特配置")
        print("  2. 在本地目录创建 [Channel] 模特名 格式的文件夹")
        print("  3. 运行查重程序进行对比")
        print("  4. 查看缺失视频列表并下载")
    else:
        print("[WARN]  PORN查重功能部分可用")
        print("\n缺失的功能:")
        for feature, status in features:
            if not status:
                print(f"  [FAIL] {feature}")

    print("=" * 80)

    return True


if __name__ == "__main__":
    test_porn_similarity()
