#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整模特目录下载演示脚本
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.modules.pronhub.downloader import (
    download_model_complete_directory,
    batch_download_models,
    get_pronhub_video_info
)


def demo_single_model_download():
    """演示单个模特完整目录下载"""
    print("=" * 60)
    print("单个模特完整目录下载演示")
    print("=" * 60)
    
    # 示例模特信息（请替换为实际的模特URL和名称）
    model_url = "https://www.pornhub.com/model/your-model-name"
    model_name = "模特名称"
    
    def progress_callback(message):
        print(f"[进度] {message}")
    
    print(f"开始下载模特: {model_name}")
    print(f"模特URL: {model_url}")
    
    result = download_model_complete_directory(
        model_url=model_url,
        model_name=model_name,
        max_videos=5,  # 限制为5个视频用于演示
        progress_callback=progress_callback
    )
    
    print("\n下载结果:")
    print(f"成功: {result['success']}")
    print(f"总视频数: {result['total_videos']}")
    print(f"成功下载: {result['successful_downloads']}")
    print(f"下载失败: {result['failed_downloads']}")
    print(f"跳过已存在: {result['skipped_downloads']}")
    print(f"总大小: {result['total_size'] / (1024*1024):.2f} MB")
    
    if result['errors']:
        print("\n错误信息:")
        for error in result['errors']:
            print(f"  - {error}")


def demo_batch_download():
    """演示批量下载多个模特"""
    print("\n" + "=" * 60)
    print("批量模特目录下载演示")
    print("=" * 60)
    
    # 示例模特列表（请替换为实际的模特信息）
    models_info = [
        ("模特1", "https://www.pornhub.com/model/model1", None),
        ("模特2", "https://www.pornhub.com/model/model2", None),
    ]
    
    def progress_callback(message):
        print(f"[进度] {message}")
    
    print(f"开始批量下载 {len(models_info)} 个模特")
    
    result = batch_download_models(
        models_info=models_info,
        max_videos_per_model=3,  # 每个模特最多下载3个视频
        progress_callback=progress_callback
    )
    
    print("\n批量下载结果:")
    print(f"成功: {result['success']}")
    print(f"总模特数: {result['total_models']}")
    print(f"成功模特数: {result['successful_models']}")
    print(f"失败模特数: {result['failed_models']}")
    print(f"总视频数: {result['total_videos']}")
    print(f"已下载数: {result['total_downloaded']}")
    print(f"总大小: {result['total_size'] / (1024*1024):.2f} MB")
    
    if result.get('error'):
        print(f"\n批量下载错误: {result['error']}")


def demo_video_info():
    """演示获取视频信息"""
    print("\n" + "=" * 60)
    print("获取视频信息演示")
    print("=" * 60)
    
    # 示例视频URL（请替换为实际的视频URL）
    video_url = "https://www.pornhub.com/view_video.php?viewkey=example"
    
    print(f"获取视频信息: {video_url}")
    
    result = get_pronhub_video_info(video_url)
    
    print("\n视频信息:")
    print(f"获取成功: {result['success']}")
    
    if result['success']:
        print(f"标题: {result.get('title', 'N/A')}")
        print(f"时长: {result.get('duration', 'N/A')} 秒")
        print(f"观看次数: {result.get('view_count', 'N/A')}")
        print(f"点赞数: {result.get('like_count', 'N/A')}")
        print(f"上传者: {result.get('uploader', 'N/A')}")
        print(f"上传日期: {result.get('upload_date', 'N/A')}")
        print(f"缩略图: {result.get('thumbnail', 'N/A')}")
        print(f"可用格式数: {len(result.get('formats', []))}")
    else:
        print(f"错误: {result.get('message', 'Unknown error')}")


def main():
    """主函数"""
    print("模特完整目录下载功能演示")
    print("请先确保：")
    print("1. 已安装 yt-dlp: pip install yt-dlp")
    print("2. 配置文件中的代理设置（如需要）")
    print("3. 将示例URL替换为实际的模特URL")
    print()
    
    while True:
        print("\n请选择演示功能:")
        print("1. 单个模特完整目录下载")
        print("2. 批量模特目录下载")
        print("3. 获取视频信息")
        print("0. 退出")
        
        choice = input("\n请输入选项 (0-3): ").strip()
        
        if choice == "0":
            print("退出演示")
            break
        elif choice == "1":
            demo_single_model_download()
        elif choice == "2":
            demo_batch_download()
        elif choice == "3":
            demo_video_info()
        else:
            print("无效选项，请重新选择")


if __name__ == "__main__":
    main()