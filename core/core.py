import os
import sys
import json
import time
import random
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Set, List, Tuple, Dict, Optional

# 导入模块化的功能
from modules.common.common import (
    setup_logging,
    load_config,
    load_models,
    get_cache_dir,
    get_model_cache_path,
    load_cache,
    save_cache,
    extract_local_videos,
    record_missing_videos
)

from modules.pronhub.pronhub import (
    fetch_with_requests_pronhub,
    scan_pronhub_models
)

from modules.javdb.javdb import (
    fetch_with_requests_javdb,
    scan_javdb_models
)

# --- 主程序 ---
def main(module_arg="auto", local_dir=None):
    """主程序入口
    
    Args:
        module_arg: 模块类型参数，可选值: "auto", "pronhub", "javdb"
        local_dir: 本地目录路径，如果提供则覆盖配置文件中的设置
    """
    try:
        # 模块选择
        if module_arg == "pronhub":
            module_type = 1
        elif module_arg == "javdb":
            module_type = 2
        else:  # auto
            module_type = 3
        
        # 加载配置
        config = load_config()
        models = load_models()
        
        # 如果提供了本地目录，则覆盖配置
        if local_dir:
            config['local_roots'] = [local_dir]
        
        # 设置日志
        logger, missing_logger, countries_dir = setup_logging(config['log_dir'])
        
        logger.info("🚀 启动批量模特视频同步检查系统（模块化版本）")
        logger.info("=" * 60)
        logger.info(f"配置文件: config.yaml")
        logger.info(f"模特数量: {len(models)}")
        logger.info(f"本地目录: {config['local_roots']}")
        logger.info(f"输出目录: {config['output_dir']}")
        logger.info(f"使用Selenium: {config.get('use_selenium', True)}")
        logger.info(f"最大翻页: {config.get('max_pages', '无限制')}")
        logger.info(f"运行模块: {'PRONHUB' if module_type == 1 else 'JAVDB' if module_type == 2 else '自动模式'}")
        logger.info("=" * 60)
        
        # 创建输出目录
        Path(config['output_dir']).mkdir(exist_ok=True)
        
        # 获取缓存目录
        cache_dir = get_cache_dir(config)
        logger.info(f"缓存目录: {cache_dir}")
        
        # 扫描本地模特目录
        local_matches = []
        if module_type == 1:
            # PRONHUB模块
            local_matches = scan_pronhub_models(
                models, 
                config['local_roots'], 
                set(config['video_extensions']), 
                config['filename_clean_patterns'],
                logger
            )
        elif module_type == 2:
            # JAVDB模块
            local_matches = scan_javdb_models(
                models, 
                config['local_roots'], 
                set(config['video_extensions']), 
                config['filename_clean_patterns'],
                logger
            )
        else:
            # 自动模式：同时扫描两种格式
            pronhub_matches = scan_pronhub_models(
                models, 
                config['local_roots'], 
                set(config['video_extensions']), 
                config['filename_clean_patterns'],
                logger
            )
            javdb_matches = scan_javdb_models(
                models, 
                config['local_roots'], 
                set(config['video_extensions']), 
                config['filename_clean_patterns'],
                logger
            )
            # 合并结果，去重
            seen_models = set()
            for match in pronhub_matches + javdb_matches:
                if match[0] not in seen_models:
                    seen_models.add(match[0])
                    local_matches.append(match)
            logger.info(f"自动模式 - 合并后共找到 {len(local_matches)} 个匹配的本地模特目录")
        
        if not local_matches:
            if module_type == 1:
                logger.error("❌ 未找到匹配的本地模特目录，程序退出")
                logger.info("提示: 确保本地目录包含以 '[Channel] 模特名' 格式命名的文件夹")
            elif module_type == 2:
                logger.error("❌ 未找到匹配的本地模特目录，程序退出")
                logger.info("提示: 确保本地目录包含以 '模特名' 格式命名的文件夹")
            else:
                logger.error("❌ 未找到匹配的本地模特目录，程序退出")
                logger.info("提示: 确保本地目录包含以 '[Channel] 模特名' 或 '模特名' 格式命名的文件夹")
            return
        
        all_missing = []
        processed_count = 0
        error_count = 0
        
        # 处理每个本地模特
        for i, (model_name, folder, original_dir, country) in enumerate(local_matches, 1):
            logger.info(f"\n[{i}/{len(local_matches)}] 处理模特: {model_name} (国家: {country})")
            logger.info(f"  本地目录: {original_dir}")
            logger.info(f"  完整路径: {folder}")
            
            # 创建国家目录
            country_dir = os.path.join(countries_dir, country)
            Path(country_dir).mkdir(exist_ok=True)
            
            # 提取本地视频（支持多层文件夹）
            local_set = extract_local_videos(
                folder, 
                set(config['video_extensions']), 
                config['filename_clean_patterns']
            )
            
            logger.info(f"  本地视频文件: {len(local_set)} 个")
            
            if local_set:
                sample = list(local_set)[:5]
                logger.info(f"  本地样本:")
                for idx, title in enumerate(sample, 1):
                    logger.info(f"    {idx}. {title[:80]}{'...' if len(title) > 80 else ''}")
            else:
                logger.warning(f"  ⚠ 本地目录中没有找到视频文件")
            
            # 获取模特URL
            url = models.get(model_name)
            if not url:
                logger.error(f"  ❌ 配置中未找到模特 '{model_name}' 的URL")
                error_count += 1
                continue
            
            logger.info(f"  在线链接: {url}")
            
            # 生成缓存路径并加载缓存
            cache_path = get_model_cache_path(cache_dir, model_name)
            cached_titles = load_cache(cache_path)
            logger.info(f"  缓存文件: {os.path.basename(cache_path)}")
            logger.info(f"  已缓存标题: {len(cached_titles)} 个")
            
            # 延时策略
            if i > 1 and config.get('delay_between_pages'):
                min_delay = config['delay_between_pages'].get('min', 2.0)
                max_delay = config['delay_between_pages'].get('max', 3.5)
                delay = random.uniform(min_delay, max_delay)
                logger.info(f"  ⏳ 随机延时 {delay:.1f} 秒")
                time.sleep(delay)
            
            # 抓取在线视频标题
            online_set = set()
            max_pages = config.get('max_pages', -1)
            
            max_retries = config.get('retry_on_fail', 2)
            online_set = set()
            title_to_url = {}
            new_videos = set()
            
            for attempt in range(max_retries + 1):
                try:
                    # 根据模块类型选择相应的抓取函数
                    if module_type == 1 or (module_type == 3 and '[Channel]' in original_dir):
                        # PRONHUB模块或自动模式下的PRONHUB格式目录
                        online_set, title_to_url = fetch_with_requests_pronhub(url, logger, max_pages, config)
                    else:
                        # JAVDB模块或自动模式下的JAVDB格式目录
                        online_set, title_to_url = fetch_with_requests_javdb(url, logger, max_pages, config)
                    
                    if online_set:
                        # 过滤出未缓存的新视频
                        new_videos = online_set - cached_titles
                        logger.info(f"  成功获取在线标题: {len(online_set)} 个")
                        logger.info(f"  新视频标题: {len(new_videos)} 个")
                        break
                    
                    if attempt < max_retries:
                        retry_delay = (attempt + 1) * 5
                        logger.warning(f"  第 {attempt + 1} 次尝试失败，{retry_delay}秒后重试...")
                        time.sleep(retry_delay)
                        
                except Exception as e:
                    logger.error(f"  抓取失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                    if attempt < max_retries:
                        time.sleep(5)
            
            if not online_set:
                logger.error(f"  ❌ 获取在线标题失败，跳过此模特")
                error_count += 1
                continue
            
            # 对比找出缺失视频（只检查新视频）
            missing = new_videos - local_set
            processed_count += 1
            
            # 更新缓存
            updated_titles = cached_titles.union(online_set)
            save_cache(cache_path, updated_titles, model_name, url)
            logger.info(f"  🔄 缓存已更新，共 {len(updated_titles)} 个标题")
            
            if missing:
                sorted_missing = sorted(list(missing))
                # 构建缺失视频列表，包含标题和链接
                missing_with_urls = []
                for title in sorted_missing:
                    video_url = title_to_url.get(title, "")
                    missing_with_urls.append((title, video_url))
                
                all_missing.append({
                    "model": model_name,
                    "url": url,
                    "local_folder": original_dir,
                    "local_count": len(local_set),
                    "online_count": len(online_set),
                    "new_videos_count": len(new_videos),
                    "missing_count": len(missing),
                    "missing_titles": sorted_missing,
                    "missing_with_urls": missing_with_urls
                })
                
                # 记录缺失视频
                record_missing_videos(model_name, url, missing_with_urls, missing_logger, logger, 
                                    local_count=len(local_set), online_count=len(online_set))
                
                logger.info(f"  🔴 发现 {len(missing)} 个缺失视频")
                logger.info(f"  📊 统计: 在线 {len(online_set)} 个 | 新视频 {len(new_videos)} 个 | 本地 {len(local_set)} 个 | 缺失 {len(missing)} 个")
                
                # 按照国家和模特结构保存日志
                country_model_dir = os.path.join(countries_dir, country, model_name)
                Path(country_model_dir).mkdir(exist_ok=True)
                
                # 保存国家-模特的详细报告
                country_model_report = os.path.join(country_model_dir, f"{model_name}_report_{datetime.now().strftime('%Y%m%d')}.txt")
                with open(country_model_report, 'w', encoding='utf-8') as f:
                    f.write("=" * 60 + "\n")
                    f.write(f"模特: {model_name}\n")
                    f.write(f"国家: {country}\n")
                    f.write(f"链接: {url}\n")
                    f.write(f"本地目录: {original_dir}\n")
                    f.write(f"完整路径: {folder}\n")
                    f.write(f"统计: 在线 {len(online_set)} 个 | 新视频 {len(new_videos)} 个 | 本地 {len(local_set)} 个 | 缺失 {len(missing)} 个\n")
                    f.write(f"处理模块: {'PRONHUB' if module_type == 1 or ('[Channel]' in original_dir and module_type == 3) else 'JAVDB'}\n")
                    f.write("=" * 60 + "\n\n")
                    
                    if missing:
                        f.write("缺失视频列表:\n")
                        f.write("-" * 40 + "\n")
                        for i, (title, video_url) in enumerate(missing_with_urls, 1):
                            f.write(f"{i:3d}. {title}\n")
                            if video_url:
                                f.write(f"    链接: {video_url}\n")
                        f.write("\n" + "=" * 60 + "\n")
                    else:
                        f.write("✅ 本地视频完整，无缺失\n")
                        f.write("\n" + "=" * 60 + "\n")
                
                logger.info(f"  📁 国家-模特报告已保存: {country_model_report}")
            else:
                logger.info("  ✅ 本地视频完整，无缺失")
        
        # 输出总结报告
        logger.info("\n" + "=" * 60)
        logger.info("处理完成！")
        logger.info(f"✅ 成功处理: {processed_count} 个模特")
        logger.info(f"❌ 处理失败: {error_count} 个模特")
        logger.info(f"🔴 发现缺失: {len(all_missing)} 个模特有缺失视频")
        
        # 如果有缺失，生成输出文件
        if all_missing:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 1. 生成TXT格式的缺失清单
            txt_path = os.path.join(config['output_dir'], f"missing_summary_{timestamp}.txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("缺失视频清单\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"运行模块: {'PRONHUB' if module_type == 1 else 'JAVDB' if module_type == 2 else '自动模式'}\n")
                f.write("=" * 60 + "\n\n")
                
                for item in all_missing:
                    f.write(f"[{item['model']}]\n")
                    f.write(f"本地目录: {item['local_folder']}\n")
                    f.write(f"在线链接: {item['url']}\n")
                    f.write(f"统计: 本地 {item['local_count']} 个 | 在线 {item['online_count']} 个 | 新视频 {item.get('new_videos_count', 0)} 个 | 缺失 {item['missing_count']} 个\n")
                    f.write("-" * 50 + "\n")
                    
                    for i, (title, video_url) in enumerate(item.get('missing_with_urls', []), 1):
                        f.write(f"{i:3d}. {title}\n")
                        if video_url:
                            f.write(f"    链接: {video_url}\n")
                    
                    f.write("\n" + "=" * 60 + "\n\n")
            
            # 2. 生成JSON格式的详细报告
            json_path = os.path.join(config['output_dir'], f"missing_detail_{timestamp}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "generated_at": datetime.now().isoformat(),
                    "total_models_processed": processed_count,
                    "models_with_missing": len(all_missing),
                    "running_module": "PRONHUB" if module_type == 1 else "JAVDB" if module_type == 2 else "AUTO",
                    "missing_details": all_missing
                }, f, ensure_ascii=False, indent=2)
            
            # 3. 生成简化的当前缺失文件
            current_txt_path = os.path.join(config['output_dir'], "missing_current.txt")
            with open(current_txt_path, 'w', encoding='utf-8') as f:
                for item in all_missing:
                    f.write(f"#{item['model']}#{item['url']}\n")
                    for title in item['missing_titles']:
                        f.write(f"{title}\n")
                    f.write("\n")
            
            logger.info(f"📄 详细报告已保存: {txt_path}")
            logger.info(f"📄 JSON数据已保存: {json_path}")
            logger.info(f"📄 当前缺失清单: {current_txt_path}")
            
        else:
            logger.info("🎉 恭喜！所有模特的本地视频都完整无缺！")
        
        logger.info(f"📁 日志文件位置: {config['log_dir']}")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\n⚠ 用户中断程序执行")
    except Exception as e:
        logger.critical(f"❌ 程序执行错误: {e}")
        logger.critical(f"详细错误信息:\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()