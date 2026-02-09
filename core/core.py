import os
import sys
import json
import time
import random
import logging
import traceback
import threading
from datetime import datetime
from pathlib import Path
from typing import Set, List, Tuple, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

# 导入模块化的功能
from core.modules.common.common import (
    setup_logging,
    load_config,
    load_models,
    get_cache_dir,
    get_model_cache_path,
    load_cache,
    save_cache,
    extract_local_videos,
    extract_local_folders,
    record_missing_videos,
    test_proxy_connection,
    get_smart_cache
)

from core.modules.common.smart_cache import SmartCache

from core.modules.pronhub.pronhub import (
    fetch_with_requests_pronhub,
    scan_pronhub_models
)

from core.modules.javdb.javdb import (
    fetch_with_requests_javdb,
    scan_javdb_models
)


@dataclass
class ModelResult:
    """模特处理结果数据类"""
    model_name: str
    success: bool
    local_count: int = 0
    online_count: int = 0
    new_videos_count: int = 0
    missing_count: int = 0
    missing_titles: List[str] = field(default_factory=list)
    missing_with_urls: List[Tuple[str, str]] = field(default_factory=list)
    error_message: str = ""
    url: str = ""
    local_folder: str = ""
    country: str = ""


class ModelProcessor:
    """模特处理器 - 支持多线程并发处理"""
    
    def __init__(self, config: dict, module_type: int, logger: logging.Logger, 
                 missing_logger: logging.Logger, countries_dir: str, 
                 smart_cache: SmartCache, running_flag=None):
        """
        初始化模特处理器
        
        Args:
            config: 配置字典
            module_type: 模块类型 (1=PRONHUB, 2=JAVDB, 3=AUTO)
            logger: 主日志记录器
            missing_logger: 缺失视频日志记录器
            countries_dir: 国家分类目录
            smart_cache: 智能缓存实例
            running_flag: 运行标志
        """
        self.config = config
        self.module_type = module_type
        self.logger = logger
        self.missing_logger = missing_logger
        self.countries_dir = countries_dir
        self.smart_cache = smart_cache
        self.running_flag = running_flag
        
        # 线程本地存储，每个线程有自己的 Selenium 实例
        self._thread_local = threading.local()
        
        # 统计信息
        self.processed_count = 0
        self.error_count = 0
        self._stats_lock = threading.Lock()
    
    def _should_stop(self) -> bool:
        """检查是否应该停止处理"""
        if self.running_flag is None:
            return False
        
        if callable(self.running_flag):
            return not self.running_flag()
        return not self.running_flag
    
    def _update_stats(self, success: bool):
        """更新统计信息（线程安全）"""
        with self._stats_lock:
            if success:
                self.processed_count += 1
            else:
                self.error_count += 1
    
    def process_single_model(self, model_info: Tuple) -> ModelResult:
        """
        处理单个模特（供多线程调用）
        
        Args:
            model_info: (model_name, folder, original_dir, country) 元组
            
        Returns:
            ModelResult 处理结果
        """
        model_name, folder, original_dir, country = model_info
        
        # 检查是否需要停止
        if self._should_stop():
            return ModelResult(
                model_name=model_name,
                success=False,
                error_message="用户请求停止"
            )
        
        # 获取当前线程ID
        thread_id = threading.current_thread().ident
        self.logger.info(f"[线程-{thread_id}] 开始处理模特: {model_name} (国家: {country})")
        
        try:
            # 创建国家目录
            country_dir = os.path.join(self.countries_dir, country)
            Path(country_dir).mkdir(exist_ok=True)
            
            # 提取本地标题
            if self.module_type == 1 or (self.module_type == 3 and '[Channel]' in original_dir):
                local_set = extract_local_videos(
                    folder,
                    set(self.config['video_extensions']),
                    self.config['filename_clean_patterns']
                )
                self.logger.info(f"[线程-{thread_id}] {model_name}: 本地视频文件 {len(local_set)} 个")
            else:
                local_set = extract_local_folders(folder)
                self.logger.info(f"[线程-{thread_id}] {model_name}: 本地文件夹 {len(local_set)} 个")
            
            # 获取模特URL
            models = load_models()
            url = models.get(model_name)
            if not url:
                self.logger.error(f"[线程-{thread_id}] {model_name}: 配置中未找到URL")
                self._update_stats(False)
                return ModelResult(
                    model_name=model_name,
                    success=False,
                    error_message="未找到URL",
                    local_count=len(local_set),
                    country=country,
                    local_folder=original_dir
                )
            
            # 抓取在线视频标题（使用智能缓存）
            max_pages = self.config.get('max_pages', -1)
            max_retries = self.config.get('retry_on_fail', 2)
            
            online_set = set()
            title_to_url = {}
            
            for attempt in range(max_retries + 1):
                if self._should_stop():
                    return ModelResult(
                        model_name=model_name,
                        success=False,
                        error_message="用户请求停止"
                    )
                
                try:
                    # 根据模块类型选择抓取函数，传入智能缓存
                    if self.module_type == 1 or (self.module_type == 3 and '[Channel]' in original_dir):
                        online_set, title_to_url = fetch_with_requests_pronhub(
                            url, self.logger, max_pages, self.config,
                            self.smart_cache, model_name
                        )
                    else:
                        online_set, title_to_url = fetch_with_requests_javdb(
                            url, self.logger, max_pages, self.config,
                            self.smart_cache, model_name
                        )
                    
                    if online_set:
                        break
                    
                    if attempt < max_retries:
                        retry_delay = (attempt + 1) * 5
                        self.logger.warning(f"[线程-{thread_id}] {model_name}: 第 {attempt + 1} 次尝试失败，{retry_delay}秒后重试...")
                        time.sleep(retry_delay)
                        
                except Exception as e:
                    self.logger.error(f"[线程-{thread_id}] {model_name}: 抓取失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                    if attempt < max_retries:
                        time.sleep(5)
            
            if not online_set:
                self.logger.error(f"[线程-{thread_id}] {model_name}: 获取在线标题失败")
                self._update_stats(False)
                return ModelResult(
                    model_name=model_name,
                    success=False,
                    error_message="获取在线标题失败",
                    local_count=len(local_set),
                    country=country,
                    local_folder=original_dir,
                    url=url
                )
            
            # 获取已缓存的标题
            cached_titles = self.smart_cache.get_cached_titles(model_name)
            new_videos = online_set - cached_titles
            
            # 对比找出缺失视频
            missing = new_videos - local_set
            
            self.logger.info(f"[线程-{thread_id}] {model_name}: 在线 {len(online_set)} | 新视频 {len(new_videos)} | 本地 {len(local_set)} | 缺失 {len(missing)}")
            
            self._update_stats(True)
            
            # 构建结果
            result = ModelResult(
                model_name=model_name,
                success=True,
                local_count=len(local_set),
                online_count=len(online_set),
                new_videos_count=len(new_videos),
                missing_count=len(missing),
                missing_titles=sorted(list(missing)),
                missing_with_urls=[(title, title_to_url.get(title, "")) for title in missing],
                url=url,
                local_folder=original_dir,
                country=country
            )
            
            # 如果有缺失视频，记录到日志
            if missing:
                sorted_missing = sorted(list(missing))
                missing_with_urls = [(title, title_to_url.get(title, "")) for title in sorted_missing]
                
                # 线程安全的日志记录
                with threading.Lock():
                    record_missing_videos(
                        model_name, url, missing_with_urls,
                        self.missing_logger, self.logger,
                        local_count=len(local_set), online_count=len(online_set)
                    )
                
                # 保存国家-模特的详细报告
                country_model_dir = os.path.join(self.countries_dir, country, model_name)
                Path(country_model_dir).mkdir(parents=True, exist_ok=True)
                
                country_model_report = os.path.join(
                    country_model_dir,
                    f"{model_name}_report_{datetime.now().strftime('%Y%m%d')}.txt"
                )
                
                with threading.Lock():
                    with open(country_model_report, 'w', encoding='utf-8') as f:
                        f.write("=" * 60 + "\n")
                        f.write(f"模特: {model_name}\n")
                        f.write(f"国家: {country}\n")
                        f.write(f"链接: {url}\n")
                        f.write(f"本地目录: {original_dir}\n")
                        f.write(f"完整路径: {folder}\n")
                        f.write(f"统计: 在线 {len(online_set)} 个 | 新视频 {len(new_videos)} 个 | 本地 {len(local_set)} 个 | 缺失 {len(missing)} 个\n")
                        f.write(f"处理模块: {'PRONHUB' if self.module_type == 1 or ('[Channel]' in original_dir and self.module_type == 3) else 'JAVDB'}\n")
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
                
                self.logger.info(f"[线程-{thread_id}] {model_name}: 📁 报告已保存")
            
            return result
            
        except Exception as e:
            self.logger.error(f"[线程-{thread_id}] {model_name}: 处理异常: {e}")
            self._update_stats(False)
            return ModelResult(
                model_name=model_name,
                success=False,
                error_message=str(e),
                country=country,
                local_folder=original_dir
            )


def process_models_multithreaded(
    local_matches: List[Tuple],
    config: dict,
    module_type: int,
    logger: logging.Logger,
    missing_logger: logging.Logger,
    countries_dir: str,
    smart_cache: SmartCache,
    running_flag=None
) -> List[ModelResult]:
    """
    使用多线程并发处理模特
    
    Args:
        local_matches: 本地模特匹配列表
        config: 配置字典
        module_type: 模块类型
        logger: 主日志记录器
        missing_logger: 缺失视频日志记录器
        countries_dir: 国家分类目录
        smart_cache: 智能缓存实例
        running_flag: 运行标志
        
    Returns:
        ModelResult 列表
    """
    # 获取线程数配置
    max_workers = config.get('multithreading', {}).get('max_workers', 3)
    max_workers = min(max_workers, len(local_matches))  # 不超过模特数量
    
    logger.info(f"\n🚀 启动多线程处理，工作线程数: {max_workers}")
    logger.info(f"📊 总模特数: {len(local_matches)}")
    logger.info("=" * 60)
    
    # 创建处理器
    processor = ModelProcessor(
        config, module_type, logger, missing_logger,
        countries_dir, smart_cache, running_flag
    )
    
    results = []
    completed = 0
    failed = 0
    
    # 使用 ThreadPoolExecutor 并发处理
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ModelWorker") as executor:
        # 提交所有任务
        future_to_model = {
            executor.submit(processor.process_single_model, model_info): model_info
            for model_info in local_matches
        }
        
        # 处理完成的任务
        for future in as_completed(future_to_model):
            model_info = future_to_model[future]
            model_name = model_info[0]
            
            try:
                result = future.result()
                results.append(result)
                
                if result.success:
                    completed += 1
                    if result.missing_count > 0:
                        logger.info(f"✅ [{completed}/{len(local_matches)}] {model_name}: 发现 {result.missing_count} 个缺失")
                    else:
                        logger.info(f"✅ [{completed}/{len(local_matches)}] {model_name}: 无缺失")
                else:
                    failed += 1
                    logger.error(f"❌ [{completed + failed}/{len(local_matches)}] {model_name}: {result.error_message}")
                    
            except Exception as e:
                failed += 1
                logger.error(f"❌ [{completed + failed}/{len(local_matches)}] {model_name}: 任务异常 - {e}")
                results.append(ModelResult(
                    model_name=model_name,
                    success=False,
                    error_message=str(e)
                ))
            
            # 检查是否需要停止
            if running_flag is not None:
                should_stop = not running_flag() if callable(running_flag) else not running_flag
                if should_stop:
                    logger.info("⚠ 用户请求停止，取消剩余任务...")
                    # 取消未完成的任务
                    for f in future_to_model:
                        if not f.done():
                            f.cancel()
                    break
    
    logger.info(f"\n📊 多线程处理完成: 成功 {completed} | 失败 {failed} | 总计 {len(local_matches)}")
    
    return results


def generate_reports(all_missing: List[ModelResult], config: dict, 
                     module_type: int, processed_count: int, 
                     error_count: int, logger: logging.Logger):
    """生成报告文件"""
    
    logger.info("\n" + "=" * 60)
    logger.info("处理完成！")
    logger.info(f"✅ 成功处理: {processed_count} 个模特")
    logger.info(f"❌ 处理失败: {error_count} 个模特")
    logger.info(f"🔴 发现缺失: {len(all_missing)} 个模特有缺失视频")
    
    # 过滤出有缺失的模特
    missing_models = [r for r in all_missing if r.missing_count > 0]
    
    if missing_models:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. 生成TXT格式的缺失清单
        txt_path = os.path.join(config['output_dir'], f"missing_summary_{timestamp}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("缺失视频清单\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"运行模块: {'PRONHUB' if module_type == 1 else 'JAVDB' if module_type == 2 else '自动模式'}\n")
            f.write("=" * 60 + "\n\n")
            
            for result in missing_models:
                f.write(f"[{result.model_name}]\n")
                f.write(f"本地目录: {result.local_folder}\n")
                f.write(f"在线链接: {result.url}\n")
                f.write(f"统计: 本地 {result.local_count} 个 | 在线 {result.online_count} 个 | 新视频 {result.new_videos_count} 个 | 缺失 {result.missing_count} 个\n")
                f.write("-" * 50 + "\n")
                
                for i, (title, video_url) in enumerate(result.missing_with_urls, 1):
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
                "models_with_missing": len(missing_models),
                "running_module": "PRONHUB" if module_type == 1 else "JAVDB" if module_type == 2 else "AUTO",
                "missing_details": [
                    {
                        "model": r.model_name,
                        "url": r.url,
                        "local_folder": r.local_folder,
                        "local_count": r.local_count,
                        "online_count": r.online_count,
                        "new_videos_count": r.new_videos_count,
                        "missing_count": r.missing_count,
                        "missing_titles": r.missing_titles,
                        "missing_with_urls": r.missing_with_urls
                    }
                    for r in missing_models
                ]
            }, f, ensure_ascii=False, indent=2)
        
        # 3. 生成简化的当前缺失文件
        current_txt_path = os.path.join(config['output_dir'], "missing_current.txt")
        with open(current_txt_path, 'w', encoding='utf-8') as f:
            for result in missing_models:
                f.write(f"#{result.model_name}#{result.url}\n")
                for title in result.missing_titles:
                    f.write(f"{title}\n")
                f.write("\n")
        
        logger.info(f"📄 详细报告已保存: {txt_path}")
        logger.info(f"📄 JSON数据已保存: {json_path}")
        logger.info(f"📄 当前缺失清单: {current_txt_path}")
        
    else:
        logger.info("🎉 恭喜！所有模特的本地视频都完整无缺！")
    
    logger.info(f"📁 日志文件位置: {config['log_dir']}")
    logger.info("=" * 60)


# --- 主程序 ---
def main(module_arg="auto", local_dirs=None, scraper="selenium", running_flag=None):
    """主程序入口
    
    Args:
        module_arg: 模块类型参数，可选值: "auto", "pronhub", "javdb"
        local_dirs: 本地目录路径列表，如果提供则覆盖配置文件中的设置
        scraper: 抓取工具，可选值: "selenium", "playwright", "drissionpage", "zendriver"
        running_flag: 运行标志，用于控制程序是否继续运行
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
        if local_dirs:
            config['local_roots'] = local_dirs
        
        # 如果提供了抓取工具，则覆盖配置
        config['scraper'] = scraper
        
        # 设置日志
        logger, missing_logger, countries_dir = setup_logging(config['log_dir'])
        
        # 获取多线程配置
        multithreading_config = config.get('multithreading', {})
        use_multithreading = multithreading_config.get('enabled', True)
        max_workers = multithreading_config.get('max_workers', 3)
        
        logger.info("🚀 启动批量模特视频同步检查系统（多线程优化版本）")
        logger.info("=" * 60)
        logger.info(f"配置文件: config.yaml")
        logger.info(f"模特数量: {len(models)}")
        logger.info(f"本地目录: {config['local_roots']}")
        logger.info(f"输出目录: {config['output_dir']}")
        logger.info(f"抓取工具: {config.get('scraper', 'selenium')}")
        logger.info(f"最大翻页: {config.get('max_pages', '无限制')}")
        logger.info(f"运行模块: {'PRONHUB' if module_type == 1 else 'JAVDB' if module_type == 2 else '自动模式'}")
        logger.info(f"多线程模式: {'启用' if use_multithreading else '禁用'} ({max_workers} 工作线程)")
        logger.info("=" * 60)
        
        # 代理连接预检
        proxy_config = config.get('network', {}).get('proxy', {})
        if not proxy_config:
            proxy_config = config.get('proxy', {})
        
        if proxy_config.get('enabled', False):
            logger.info("\n🔍 检测到已启用代理，正在进行连接测试...")
            
            proxy_type = proxy_config.get('type', 'http')
            proxy_host = proxy_config.get('host', '127.0.0.1')
            proxy_port = proxy_config.get('port', '10808')
            logger.info(f"   代理类型: {proxy_type}")
            logger.info(f"   代理地址: {proxy_host}:{proxy_port}")
            
            if not test_proxy_connection(proxy_config, timeout=10, logger=logger):
                logger.error("\n" + "=" * 60)
                logger.error("❌ 代理连接失败！")
                logger.error("=" * 60)
                logger.error("\n请检查以下问题：")
                logger.error("  1. 代理工具（如 v2rayN、Clash 等）是否已启动")
                logger.error("  2. 代理配置是否正确（主机地址和端口）")
                logger.error("  3. 代理工具是否已成功连接到服务器")
                logger.error("  4. 防火墙是否阻止了代理连接")
                logger.error("\n💡 解决方法：")
                logger.error("  • 启动代理工具并确保连接成功")
                logger.error("  • 在 config.yaml 中修改代理配置")
                logger.error("  • 或者在 config.yaml 中设置 proxy.enabled: false 禁用代理")
                logger.error("\n程序已退出，请解决代理问题后重新运行。")
                logger.error("=" * 60)
                sys.exit(1)
            
            logger.info("✅ 代理连接测试通过，继续执行...\n")
        else:
            logger.info("\n📡 未启用代理，使用直接连接\n")
        
        # 创建输出目录
        Path(config['output_dir']).mkdir(exist_ok=True)
        
        # 获取缓存目录并初始化智能缓存
        cache_dir = get_cache_dir(config)
        logger.info(f"缓存目录: {cache_dir}")
        
        smart_cache = get_smart_cache(cache_dir, config)
        logger.info(f"智能缓存: {'启用' if smart_cache.enabled else '禁用'}")
        if smart_cache.enabled:
            logger.info(f"  - 增量更新: {'启用' if smart_cache.incremental_update else '禁用'}")
            logger.info(f"  - 页面过期时间: {smart_cache.page_expiry_hours} 小时")
        
        # 扫描本地模特目录
        local_matches = []
        if module_type == 1:
            local_matches = scan_pronhub_models(
                models,
                config['local_roots'],
                set(config['video_extensions']),
                config['filename_clean_patterns'],
                logger
            )
        elif module_type == 2:
            local_matches = scan_javdb_models(
                models,
                config['local_roots'],
                set(config['video_extensions']),
                config['filename_clean_patterns'],
                logger
            )
        else:
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
        
        # 使用多线程处理模特
        if use_multithreading and len(local_matches) > 1:
            results = process_models_multithreaded(
                local_matches, config, module_type,
                logger, missing_logger, countries_dir,
                smart_cache, running_flag
            )
        else:
            # 单线程模式（用于调试或只有一个模特的情况）
            logger.info("\n使用单线程模式处理...")
            processor = ModelProcessor(
                config, module_type, logger, missing_logger,
                countries_dir, smart_cache, running_flag
            )
            results = []
            for i, model_info in enumerate(local_matches, 1):
                logger.info(f"\n[{i}/{len(local_matches)}] 处理模特: {model_info[0]}")
                result = processor.process_single_model(model_info)
                results.append(result)
        
        # 统计结果
        processed_count = sum(1 for r in results if r.success)
        error_count = sum(1 for r in results if not r.success)
        
        # 生成报告
        generate_reports(results, config, module_type, processed_count, error_count, logger)
        
        # 返回结果供GUI使用
        return results
        
    except KeyboardInterrupt:
        logger.info("\n⚠ 用户中断程序执行")
        return []
    except Exception as e:
        logger.critical(f"❌ 程序执行错误: {e}")
        logger.critical(f"详细错误信息:\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
