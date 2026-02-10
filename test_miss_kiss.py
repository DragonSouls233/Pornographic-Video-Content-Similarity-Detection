#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Miss Kiss 模特查重测试
专门测试 https://cn.pornhub.com/model/miss-kiss/videos
"""

import os
import sys
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


def test_miss_kiss():
    """测试 Miss Kiss 模特查重"""

    print("=" * 80)
    print("Miss Kiss 模特查重测试")
    print("=" * 80)

    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)

    # 1. 加载配置
    print("\n[1] 加载配置...")
    config = load_config()
    print(f"    本地目录: {config.get('local_roots', [])}")
    print(f"    视频扩展名: {config.get('video_extensions', [])}")

    # 2. 加载模特配置
    print("\n[2] 加载模特配置...")

    # 直接读取原始JSON配置，保留module信息
    import json
    with open('models.json', 'r', encoding='utf-8') as f:
        models_raw = json.load(f)

    print(f"    模特数量: {len(models_raw)}")
    for name, info in models_raw.items():
        if isinstance(info, dict):
            print(f"    - {name}: {info.get('module')} - {info.get('url')}")

    # 3. 扫描本地视频
    print("\n[3] 扫描本地视频...")
    local_roots = config.get('local_roots', [])
    matched_models = scan_porn_models(
        models_raw,  # 使用原始配置
        local_roots,
        set(config.get('video_extensions', [])),
        config.get('filename_clean_patterns', []),
        logger
    )

    if not matched_models:
        print("    [FAIL] 未找到匹配的本地模特")
        return

    print(f"    找到 {len(matched_models)} 个匹配的本地模特")

    # 提取本地视频
    local_videos = set()
    for model_name, folder, original_dir, country in matched_models:
        print(f"\n    模特: {model_name}")
        print(f"    目录: {folder}")
        print(f"    原始目录名: {original_dir}")

        videos = extract_local_videos(
            folder,
            set(config.get('video_extensions', [])),
            config.get('filename_clean_patterns', [])
        )

        local_videos.update(videos)
        print(f"    本地视频数量: {len(videos)}")

        if videos:
            print(f"    本地视频列表:")
            for i, video in enumerate(list(videos)[:5], 1):
                print(f"      {i}. {video[:70]}...")

    print(f"\n    总计本地视频: {len(local_videos)} 个")

    # 4. 抓取在线视频
    print("\n[4] 抓取在线视频...")
    model_name, model_info = list(models_raw.items())[0]
    url = model_info.get('url', '')

    print(f"    模特: {model_name}")
    print(f"    URL: {url}")

    cache_dir = os.path.join(config.get('output_dir', 'output'), 'cache')
    smart_cache = create_smart_cache(cache_dir, config)

    try:
        online_videos, title_to_url = fetch_with_requests_porn(
            url,
            logger,
            max_pages=-1,  # 抓取所有页面
            config=config,
            smart_cache=smart_cache,
            model_name=model_name
        )

        print(f"    在线视频数量: {len(online_videos)}")

        if online_videos:
            print(f"\n    在线视频列表 (前10个):")
            for i, video in enumerate(list(online_videos)[:10], 1):
                print(f"      {i}. {video[:70]}...")
        else:
            print("    [FAIL] 未抓取到任何在线视频")
            return

    except Exception as e:
        print(f"    [FAIL] 抓取失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. 查重对比
    print("\n[5] 查重对比...")
    print(f"    本地视频: {len(local_videos)} 个")
    print(f"    在线视频: {len(online_videos)} 个")

    # 找出缺失的视频
    missing = online_videos - local_videos
    matched = online_videos & local_videos

    print(f"\n    已有视频: {len(matched)} 个")
    print(f"    缺失视频: {len(missing)} 个")

    if matched:
        print(f"\n    已有视频列表:")
        for i, video in enumerate(list(matched), 1):
            print(f"      {i}. {video[:70]}...")

    if missing:
        print(f"\n    缺失视频列表:")
        for i, video in enumerate(list(missing)[:10], 1):
            print(f"      {i}. {video[:70]}...")
            url = title_to_url.get(video, '无链接')
            print(f"         链接: {url}")

    # 6. 生成报告
    print("\n" + "=" * 80)
    print("查重报告")
    print("=" * 80)

    print(f"\n模特: {model_name}")
    print(f"在线视频总数: {len(online_videos)}")
    print(f"本地视频总数: {len(local_videos)}")
    print(f"已有视频: {len(matched)}")
    print(f"缺失视频: {len(missing)}")
    print(f"完整度: {(len(matched) / len(online_videos) * 100):.1f}%")

    if missing:
        print(f"\n建议:")
        print(f"  1. 下载 {len(missing)} 个缺失视频")
        print(f"  2. 保存到: {matched_models[0][1]}")
        print(f"  3. 使用下载功能批量下载")

    print("\n" + "=" * 80)

    return {
        'model_name': model_name,
        'local_count': len(local_videos),
        'online_count': len(online_videos),
        'matched_count': len(matched),
        'missing_count': len(missing),
        'missing_videos': list(missing),
        'title_to_url': title_to_url
    }


if __name__ == "__main__":
    test_miss_kiss()
