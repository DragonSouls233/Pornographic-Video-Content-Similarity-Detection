import os
import sys
import json
import time
import random
import re
import logging
import traceback
import threading
from datetime import datetime
from pathlib import Path
from typing import Set, List, Tuple, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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

# 查重缓存模块
from core.modules.common.dup_cache import DupCacheStore, DupCacheEntry, compute_remote_signature
from core.modules.common.dup_cache_probe import probe_remote_signature, compute_local_signature_from_files, check_url_available, compute_remote_signature_from_titles




# 导入配置验证模块
from core.modules.common.config_validator import validate_config_file, print_validation_report

# 导入ChromeDriver管理模块
from core.modules.common.chrome_driver_manager import check_and_setup_chromedriver

# 导入增强版代理检查模块
from core.modules.common.enhanced_proxy_checker import EnhancedProxyTester, print_comprehensive_report

from core.modules.common.smart_cache import SmartCache
from core.modules.common.model_database import ModelDatabase


from core.modules.porn.porn import (
    fetch_with_requests_porn,
    scan_porn_models
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
    local_folder_full: str = ""  # 本地目录完整路径
    source: str = "local"  # 数据来源：local/online/cache


class ModelProcessor:
    """模特处理器 - 支持多线程并发处理"""
    
    def __init__(self, config: dict, module_type: int, logger: logging.Logger, 
                 missing_logger: logging.Logger, countries_dir: str, 
                 smart_cache: SmartCache, db: ModelDatabase = None, running_flag=None):
        """
        初始化模特处理器
        
        Args:
            config: 配置字典
            module_type: 模块类型 (1=PORN, 2=JAVDB, 3=AUTO)
            logger: 主日志记录器
            missing_logger: 缺失视频日志记录器
            countries_dir: 国家分类目录
            smart_cache: 智能缓存实例
            db: 数据库实例
            running_flag: 运行标志
        """
        self.config = config
        self.module_type = module_type
        self.logger = logger
        self.missing_logger = missing_logger
        self.countries_dir = countries_dir
        self.smart_cache = smart_cache
        self.db = db if db else ModelDatabase()
        self.running_flag = running_flag

        # 线程本地存储，每个线程有自己的 Selenium 实例
        self._thread_local = threading.local()

        # 统计信息
        self.processed_count = 0
        self.error_count = 0
        self._stats_lock = threading.Lock()

    def _get_selenium_instance(self) -> Optional['SeleniumHelper']:
        """获取当前线程的 Selenium 实例（线程安全，复用实例）"""
        # 检查当前线程是否已有 Selenium 实例
        if hasattr(self._thread_local, 'selenium_instance'):
            return self._thread_local.selenium_instance

        # 创建新的 Selenium 实例
        try:
            from core.modules.common.selenium_helper import SeleniumHelper
            selenium = SeleniumHelper(self.config)
            selenium.driver = selenium.setup_driver()
            self._thread_local.selenium_instance = selenium
            self.logger.debug(f"为新线程创建 Selenium 实例")
            return selenium
        except Exception as e:
            self.logger.error(f"创建 Selenium 实例失败: {e}")
            return None

    def _cleanup_selenium_instance(self):
        """清理当前线程的 Selenium 实例"""
        if hasattr(self._thread_local, 'selenium_instance') and self._thread_local.selenium_instance:
            try:
                self._thread_local.selenium_instance.close()
                delattr(self._thread_local, 'selenium_instance')
                self.logger.debug(f"清理 Selenium 实例")
            except Exception as e:
                self.logger.error(f"清理 Selenium 实例失败: {e}")
    
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

        # 国家信息：优先使用数据库中维护的 country（避免默认值不一致/被覆盖）
        if not country or str(country).strip() in ("未知", "未知国家"):
            try:
                info = self.db.get_model(model_name) or {}
                db_country = info.get('country')
                if db_country and str(db_country).strip():
                    country = str(db_country).strip()
            except Exception:
                pass

        
        # 检查是否需要停止
        if self._should_stop():
            return ModelResult(
                model_name=model_name,
                success=False,
                error_message="用户请求停止",
                local_folder_full=original_dir
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

            # 统一标题归一化（降低误判）
            comparison_cfg = self.config.get('comparison', {})
            def _normalize_title(title: str) -> str:
                t = (title or '').strip()
                if not t:
                    return ''
                if not comparison_cfg.get('case_sensitive', False):
                    t = t.lower()
                if comparison_cfg.get('strip_punctuation', True):
                    t = re.sub(r'[\W_]+', '', t, flags=re.UNICODE)
                t = re.sub(r'\s+', '', t)
                return t

            def _normalize_set(titles):
                return {n for n in (_normalize_title(t) for t in titles) if n}
            
            # 获取模特URL

            models = load_models()
            url = models.get(model_name)
            if not url:
                self.logger.error(f"[线程-{thread_id}] {model_name}: 配置中未找到URL")
                self.logger.warning(f"[线程-{thread_id}] 提示: 请在models.json或数据库中添加模特 '{model_name}' 的配置")
                self.logger.warning(f"[线程-{thread_id}] 当前已配置的模特: {list(models.keys())}")
                self._update_stats(False)
                return ModelResult(
                    model_name=model_name,
                    success=False,
                    error_message=f"未找到URL，请添加模特配置",
                    local_count=len(local_set),
                    country=country,
                    local_folder=original_dir,
                    local_folder_full=folder
                )

            # 计算模块类型（用于缓存键）
            if self.module_type == 1 or (self.module_type == 3 and '[Channel]' in original_dir):
                module_name = "PORN"
            elif self.module_type == 2:
                module_name = "JAVDB"
            else:
                module_name = "JAVDB" if 'javdb' in url.lower() else "PORN"

            # 读取该模特的专属黑名单URL
            blacklisted_urls = set()
            try:
                blacklisted_urls = set(self.db.get_blacklisted_urls_by_model(model_name))
            except Exception:
                pass


            # 初始化查重缓存
            cache_ctrl = self.config.get('cache', {})

            cache_db_path = cache_ctrl.get('dup_cache_path', 'output/dup_cache.db')
            cache_store = DupCacheStore(cache_db_path)
            cache_key = cache_store.build_cache_key(model_name, module_name, url)
            cache_entry = cache_store.get(cache_key)

            # 缓存过期判定
            expire_hours = cache_ctrl.get('dup_cache_expire_hours', None)
            if expire_hours is None:
                expire_days = cache_ctrl.get('expiration_days', 7)
                expire_hours = expire_days * 24 if isinstance(expire_days, (int, float)) else 0
            if cache_entry and expire_hours and expire_hours > 0 and cache_entry.checked_at:
                try:
                    checked_at = datetime.fromisoformat(cache_entry.checked_at)
                    if (datetime.now() - checked_at).total_seconds() > expire_hours * 3600:
                        self.logger.info(f"[线程-{thread_id}] {model_name}: 查重缓存已过期，执行完整查重")
                        cache_entry = None
                except Exception:
                    pass

            # 缓存管理：支持强制刷新/按模特清理
            force_refresh = cache_ctrl.get('dup_cache_force_refresh', False)
            force_refresh_models = cache_ctrl.get('dup_cache_force_refresh_models', []) or []
            clear_models = cache_ctrl.get('dup_cache_clear_models', []) or []

            if force_refresh or model_name in force_refresh_models or model_name in clear_models:
                cache_store.clear(model_name)
                cache_entry = None
                self.logger.info(f"[线程-{thread_id}] {model_name}: 已清理查重缓存，执行完整查重")


            # 轻量远端探测（用于判断远端是否变化）
            remote_signature = ""
            probe_titles = []
            proxies = None
            headers = None
            try:
                # 代理配置

                proxy_cfg = self.config.get('network', {}).get('proxy', {})
                if proxy_cfg.get('enabled'):
                    ptype = proxy_cfg.get('type', 'socks5')
                    host = proxy_cfg.get('host', '')
                    port = proxy_cfg.get('port', '')
                    if host and port:
                        proxy_url = f"{ptype}://{host}:{port}"
                        proxies = {"http": proxy_url, "https": proxy_url}

                headers = self.config.get('network', {}).get('headers', None)
                remote_signature, probe_titles = probe_remote_signature(url, headers=headers, proxies=proxies)
            except Exception as e:
                self.logger.warning(f"[线程-{thread_id}] {model_name}: 远端轻量探测失败，将回退完整抓取 ({e})")

            # 如果缓存命中且远端未变化，则走快速路径
            if cache_entry and remote_signature and cache_entry.remote_signature == remote_signature:
                # 获取已下载的视频（用于判定补齐）
                downloaded_videos = set()
                if self.smart_cache and self.smart_cache.enabled:
                    cache_data = self.smart_cache.load(model_name)
                    missing_data = cache_data.get('missing_videos', {})
                    for title, info in missing_data.items():
                        if info.get('status') == 'downloaded':
                            downloaded_videos.add(title)

                local_set_with_downloaded = local_set | downloaded_videos

                # 严格补齐判定：缺失标题必须有可用链接
                def _is_valid_url(url_value):
                    return isinstance(url_value, str) and url_value.strip().startswith(("http://", "https://"))

                cached_missing_with_urls_raw = list(cache_entry.missing_with_urls or [])
                blacklisted_titles = set()
                if blacklisted_urls and cached_missing_with_urls_raw:
                    blacklisted_titles = {t for t, u in cached_missing_with_urls_raw if u in blacklisted_urls}
                    cached_missing_with_urls_raw = [(t, u) for t, u in cached_missing_with_urls_raw if u not in blacklisted_urls]

                cached_missing_titles = set(cache_entry.missing_titles or []) - blacklisted_titles
                cached_missing_with_urls = [(t, u) for t, u in cached_missing_with_urls_raw if _is_valid_url(u)]

                local_norm = _normalize_set(local_set_with_downloaded)
                cached_missing_norm = {_normalize_title(t) for t in cached_missing_titles if _normalize_title(t)}
                cached_missing_with_urls_norm = {_normalize_title(t) for t, _ in cached_missing_with_urls if _normalize_title(t)}
                invalid_or_no_url_norm = cached_missing_norm - cached_missing_with_urls_norm

                remaining_missing_norm = (cached_missing_with_urls_norm - local_norm) | invalid_or_no_url_norm

                # 严格链接可用性校验：仅在“已补齐”时触发
                url_check_enabled = cache_ctrl.get('dup_cache_url_check_enabled', True)
                url_check_timeout = cache_ctrl.get('dup_cache_url_check_timeout', 8)
                url_check_max = cache_ctrl.get('dup_cache_url_check_max', 0)
                if url_check_enabled and not remaining_missing_norm and cached_missing_with_urls:
                    to_check = cached_missing_with_urls
                    if isinstance(url_check_max, int) and url_check_max > 0:
                        to_check = cached_missing_with_urls[:url_check_max]
                    invalid_due_to_url = set()
                    for title, video_url in to_check:
                        if not check_url_available(video_url, headers=headers, proxies=proxies, timeout=url_check_timeout):
                            invalid_due_to_url.add(_normalize_title(title))
                    if invalid_due_to_url:
                        remaining_missing_norm |= invalid_due_to_url
                        invalid_or_no_url_norm |= invalid_due_to_url

                missing_with_urls = [(t, u) for t, u in cached_missing_with_urls if _normalize_title(t) in remaining_missing_norm]

                effective_local_count = len(local_set_with_downloaded)
                missing_titles_sorted = sorted([t for t in cached_missing_titles if _normalize_title(t) in remaining_missing_norm])


                # 更新缓存（本地签名/缺失结果）
                local_signature = compute_local_signature_from_files(folder, list(local_set))
                cache_entry.local_changed = 1 if cache_entry.local_signature and cache_entry.local_signature != local_signature else 0
                cache_entry.remote_changed = 0
                cache_entry.local_signature = local_signature
                cache_entry.local_count = effective_local_count
                cache_entry.online_count = cache_entry.online_count or len(cached_missing_titles)
                cache_entry.missing_titles = missing_titles_sorted
                cache_entry.missing_with_urls = missing_with_urls
                invalid_titles_sorted = sorted([t for t in cached_missing_titles if _normalize_title(t) in invalid_or_no_url_norm])
                cache_entry.invalid_titles = invalid_titles_sorted

                if remote_signature:
                    cache_entry.remote_signature = remote_signature
                cache_store.upsert(cache_entry)


                self._update_stats(True)
                return ModelResult(
                    model_name=model_name,
                    success=True,
                    local_count=effective_local_count,
                    online_count=cache_entry.online_count,
                    new_videos_count=0,
                    missing_count=len(missing_titles_sorted),
                    missing_titles=missing_titles_sorted,
                    missing_with_urls=missing_with_urls,

                    url=url,
                    local_folder=original_dir,
                    local_folder_full=folder,
                    country=country,
                    source="cache"
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
                        error_message="用户请求停止",
                        local_folder_full=original_dir
                    )
                
                try:
                    # 获取当前线程的 Selenium 实例（如果使用 Selenium）
                    selenium = self._get_selenium_instance() if (self.config.get('use_selenium', False) or self.config.get('scraper', '') == 'selenium') else None

                    # 根据模块类型选择抓取函数，传入智能缓存和 Selenium 实例
                    if self.module_type == 1 or (self.module_type == 3 and '[Channel]' in original_dir):
                        online_set, title_to_url = fetch_with_requests_porn(
                            url, self.logger, max_pages, self.config,
                            self.smart_cache, model_name, selenium
                        )
                    else:
                        online_set, title_to_url = fetch_with_requests_javdb(
                            url, self.logger, max_pages, self.config,
                            self.smart_cache, model_name, selenium
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
                    local_folder_full=folder,
                    url=url
                )
            
            # 获取已缓存的标题
            cached_titles = self.smart_cache.get_cached_titles(model_name) if self.smart_cache else set()
            cached_norm = _normalize_set(cached_titles)
            
            # 获取之前已下载的视频（从缓存中标记为downloaded的视频）
            # 这样后续运行时，已下载的视频不会再出现在缺失列表中
            downloaded_videos = set()
            if self.smart_cache and self.smart_cache.enabled:
                # 直接读取缓存数据中的missing_videos，筛选status='downloaded'的
                cache_data = self.smart_cache.load(model_name)
                missing_data = cache_data.get('missing_videos', {})
                for title, info in missing_data.items():
                    if info.get('status') == 'downloaded':
                        downloaded_videos.add(title)
            
            # 合并本地视频和已下载视频
            local_set_with_downloaded = local_set | downloaded_videos
            local_norm = _normalize_set(local_set_with_downloaded)
            
            # 补全缓存中的URL映射，避免增量模式下出现空链接
            resolved_title_to_url = dict(title_to_url)
            if self.smart_cache and self.smart_cache.enabled:
                for title in online_set:
                    if not resolved_title_to_url.get(title):
                        cached_url = self.smart_cache.get_video_url(model_name, title)
                        if cached_url:
                            resolved_title_to_url[title] = cached_url

            # 过滤专属黑名单URL
            if blacklisted_urls:
                blacklisted_titles = {t for t, u in resolved_title_to_url.items() if u in blacklisted_urls}
                if blacklisted_titles:
                    online_set = online_set - blacklisted_titles
                    for t in blacklisted_titles:
                        resolved_title_to_url.pop(t, None)
                    self.logger.info(f"[线程-{thread_id}] {model_name}: 专属黑名单已忽略 {len(blacklisted_titles)} 条URL")

            online_norm = _normalize_set(online_set)

            # 重新计算新增视频（排除黑名单，使用归一化）
            new_norm = online_norm - cached_norm
            new_videos = {t for t in online_set if _normalize_title(t) in new_norm}

            # 对比找出缺失视频（使用归一化）
            missing_norm = online_norm - local_norm
            missing_titles = [t for t in online_set if _normalize_title(t) in missing_norm]
            missing = set(missing_titles)
            
            def _is_valid_url(url_value):
                return isinstance(url_value, str) and url_value.strip().startswith(("http://", "https://"))

            
            # 过滤无连接的内容
            missing_with_urls = [
                (title, resolved_title_to_url.get(title, ""))
                for title in missing_titles
                if _is_valid_url(resolved_title_to_url.get(title, ""))
            ]

            
            # 记录原始本地数量和实际用于对比的数量
            original_local_count = len(local_set)
            effective_local_count = len(local_set_with_downloaded)
            
            self.logger.info(f"[线程-{thread_id}] {model_name}: 在线 {len(online_set)} | 新视频 {len(new_videos)} | 本地 {original_local_count} | 已下载{len(downloaded_videos)} | 有效本地 {effective_local_count} | 缺失 {len(missing)}")
            
            # 更新查重缓存（完整抓取后）
            try:
                remote_sig_full = compute_remote_signature(list(online_set), len(online_set))
                remote_sig_probe_fallback = compute_remote_signature_from_titles(list(online_set))
                remote_sig_probe = remote_signature or remote_sig_probe_fallback
                local_sig = compute_local_signature_from_files(folder, list(local_set))
                local_changed = 1 if cache_entry and cache_entry.local_signature and cache_entry.local_signature != local_sig else 0
                remote_changed = 1 if cache_entry and cache_entry.remote_signature and remote_sig_probe and cache_entry.remote_signature != remote_sig_probe else 0
                cache_entry = DupCacheEntry(
                    cache_key=cache_key,
                    model_name=model_name,
                    module=module_name,
                    url=url,
                    remote_signature=remote_sig_probe,
                    remote_signature_full=remote_sig_full,
                    local_signature=local_sig,
                    online_count=len(online_set),
                    local_count=effective_local_count,
                    missing_titles=sorted(list(missing)),
                    missing_with_urls=missing_with_urls,
                    invalid_titles=[t for t in sorted(online_set) if not _is_valid_url(resolved_title_to_url.get(t, ""))],
                    local_changed=local_changed,
                    remote_changed=remote_changed
                )
                cache_store.upsert(cache_entry)
            except Exception as e:
                self.logger.warning(f"[线程-{thread_id}] {model_name}: 缓存写入失败: {e}")


            
            self._update_stats(True)
            
            # 构建结果
            result = ModelResult(
                model_name=model_name,
                success=True,
                local_count=effective_local_count,  # 使用有效的本地视频数量（包含已下载的）
                online_count=len(online_set),
                new_videos_count=len(new_videos),
                missing_count=len(missing),
                missing_titles=sorted(list(missing)),
                missing_with_urls=missing_with_urls,
                url=url,
                local_folder=original_dir,
                local_folder_full=folder,
                country=country,
                source="online" if online_set else "local"
            )
            
            # 如果有缺失视频，记录到日志
            if missing:
                sorted_missing = sorted(list(missing))
                
                # 过滤无连接的内容，并记录过滤数量
                filtered_count = len(sorted_missing) - len(missing_with_urls)
                if filtered_count > 0:
                    self.logger.warning(
                        f"[线程-{thread_id}] {model_name}: 过滤 {filtered_count} 条无效链接（未获取到URL）"
                    )
                
                # 线程安全的日志记录
                with threading.Lock():
                    # 获取日志模板类型
                    template_type = self.config.get('porn', {}).get('missing_log_template', 'simple')
                    record_missing_videos(
                        model_name, url, missing_with_urls,
                        self.missing_logger, self.logger,
                        local_count=len(local_set), online_count=len(online_set),
                        template_type=template_type
                    )
                
                # 保存国家-模特的详细报告
                country_model_dir = os.path.join(self.countries_dir, country, model_name)
                Path(country_model_dir).mkdir(parents=True, exist_ok=True)
                
                # 创建缺失视频目录
                missing_dir = os.path.join(country_model_dir, "缺失")
                Path(missing_dir).mkdir(exist_ok=True)
                
                country_model_report = os.path.join(
                    country_model_dir,
                    f"{model_name}_report_{datetime.now().strftime('%Y%m%d')}.txt"
                )
                
                with threading.Lock():
                    # 生成报告文件
                    with open(country_model_report, 'w', encoding='utf-8') as f:
                        f.write("=" * 60 + "\n")
                        f.write(f"模特: {model_name}\n")
                        f.write(f"国家: {country}\n")
                        f.write(f"链接: {url}\n")
                        f.write(f"本地目录: {original_dir}\n")
                        f.write(f"完整路径: {folder}\n")
                        f.write(f"统计: 在线 {len(online_set)} 个 | 新视频 {len(new_videos)} 个 | 本地 {len(local_set)} 个 | 缺失 {len(missing)} 个\n")
                        f.write(f"处理模块: {'PORN' if self.module_type == 1 or ('[Channel]' in original_dir and self.module_type == 3) else 'JAVDB'}\n")
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
                    
                    # 如果有缺失视频，生成缺失视频链接文件（缺失目录：只保留URL）
                    if missing and missing_with_urls:
                        missing_links_file = os.path.join(missing_dir, f"{model_name}_缺失链接_{datetime.now().strftime('%Y%m%d')}.txt")
                        with open(missing_links_file, 'w', encoding='utf-8') as f:
                            # 按你的要求：缺失目录里的TXT仅输出URL（一行一个），不写标题/统计/注释
                            urls = []
                            for _, video_url in missing_with_urls:
                                if video_url and str(video_url).strip():
                                    urls.append(str(video_url).strip())

                            # 去重但保持顺序
                            seen = set()
                            for u in urls:
                                if u in seen:
                                    continue
                                seen.add(u)
                                f.write(u + "\n")

                        self.logger.info(f"[线程-{thread_id}] {model_name}: 📁 缺失链接已保存（URL-only）")
                        
                        # 更新智能缓存中的缺失视频列表（用于后续只更新）
                        if self.smart_cache and self.smart_cache.enabled:
                            self.smart_cache.update_missing_videos(model_name, missing_with_urls)
                
                # 生成模特级链接校验报告
                links_report_file = os.path.join(
                    country_model_dir,
                    f"{model_name}_链接报告_{datetime.now().strftime('%Y%m%d')}.txt"
                )
                valid_links = [
                    (title, resolved_title_to_url.get(title, ""))
                    for title in sorted(online_set)
                    if _is_valid_url(resolved_title_to_url.get(title, ""))
                ]
                invalid_titles = [
                    title for title in sorted(online_set)
                    if not _is_valid_url(resolved_title_to_url.get(title, ""))
                ]
                local_titles = sorted(local_set)
                downloaded_only = sorted(downloaded_videos - local_set)
                
                with open(links_report_file, 'w', encoding='utf-8') as f:
                    f.write("=" * 70 + "\n")
                    f.write(f"模特链接校验报告 - {model_name}\n")
                    f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"模特链接: {url}\n")
                    f.write("=" * 70 + "\n\n")
                    f.write("统计信息:\n")
                    f.write(f"- 在线视频总数: {len(online_set)}\n")
                    f.write(f"- 有效链接数量: {len(valid_links)}\n")
                    f.write(f"- 无效/缺失链接数量: {len(invalid_titles)}\n")
                    f.write(f"- 本地视频数量: {len(local_set)}\n")
                    f.write(f"- 已下载视频数量: {len(downloaded_videos)}\n")
                    f.write(f"- 本地对比视频总数(本地+已下载): {len(local_set_with_downloaded)}\n")
                    f.write("\n")
                    
                    f.write("本地对比视频标记:\n")
                    f.write("-" * 40 + "\n")
                    for title in local_titles:
                        f.write(f"[本地] {title}\n")
                    for title in downloaded_only:
                        f.write(f"[已下载] {title}\n")
                    f.write("\n")
                    
                    f.write("有效链接列表:\n")
                    f.write("-" * 40 + "\n")
                    for i, (title, video_url) in enumerate(valid_links, 1):
                        f.write(f"{i:3d}. {title}\n")
                        f.write(f"    链接: {video_url}\n")
                    f.write("\n")
                    
                    if invalid_titles:
                        f.write("无效/缺失链接列表:\n")
                        f.write("-" * 40 + "\n")
                        for i, title in enumerate(invalid_titles, 1):
                            f.write(f"{i:3d}. {title}\n")
                        f.write("\n")
                
                self.logger.info(f"[线程-{thread_id}] {model_name}: 📁 链接校验报告已保存")
                
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
                local_folder=original_dir,
                local_folder_full=folder,
                source="local"
            )


def process_models_multithreaded(
    local_matches: List[Tuple],
    config: dict,
    module_type: int,
    logger: logging.Logger,
    missing_logger: logging.Logger,
    countries_dir: str,
    smart_cache: SmartCache,
    db: ModelDatabase = None,
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
        db: 数据库实例
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
        countries_dir, smart_cache, db, running_flag
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
            f.write(f"运行模块: {'PORN' if module_type == 1 else 'JAVDB' if module_type == 2 else '自动模式'}\n")
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
                "running_module": "PORN" if module_type == 1 else "JAVDB" if module_type == 2 else "AUTO",
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
        module_arg: 模块类型参数，可选值: "auto", "porn", "javdb"
        local_dirs: 本地目录路径列表，如果提供则覆盖配置文件中的设置
        scraper: 抓取工具，可选值: "selenium", "playwright", "drissionpage", "zendriver"
        running_flag: 运行标志，用于控制程序是否继续运行
    """
    # 初始化日志器（提前初始化以便错误处理）
    logger = logging.getLogger(__name__)
    
    # 🚨 修复：添加参数验证和安全初始化
    try:
        # 验证module_arg参数
        valid_modules = ["auto", "porn", "javdb"]
        if module_arg not in valid_modules:
            raise ValueError(f"无效的模块参数: {module_arg}，有效选项: {valid_modules}")
        
        # 验证scraper参数
        valid_scrapers = ["selenium"]
        if scraper not in valid_scrapers:
            raise ValueError(f"无效的抓取工具参数: {scraper}，有效选项: {valid_scrapers}")
        
        # 确保local_dirs是列表类型
        if local_dirs is not None and not isinstance(local_dirs, list):
            raise TypeError(f"local_dirs必须是列表类型，当前类型: {type(local_dirs)}")
    
    except Exception as param_error:
        logger.error(f"参数验证失败: {param_error}")
        raise
    
    try:
        # 模块选择
        if module_arg == "porn":
            module_type = 1
        elif module_arg == "javdb":
            module_type = 2
        else:  # auto
            module_type = 3
        
        # 加载配置
        config = load_config()
        models = load_models()
        
        # 配置验证（新增）
        logger.info("🔍 正在验证配置文件...")
        validation_result = validate_config_file("config.yaml")
        if not validation_result.valid:
            logger.error("❌ 配置验证失败，程序无法继续运行")
            print_validation_report(validation_result)
            logger.error("\n请修复上述配置问题后重新运行程序")
            logger.error("💡 提示：可以运行 'python -m core.modules.common.config_validator' 单独验证配置")
            sys.exit(1)
        elif validation_result.warnings:
            logger.warning(f"⚠️  配置验证发现 {len(validation_result.warnings)} 个警告:")
            for warning in validation_result.warnings:
                logger.warning(f"  - {warning}")
        else:
            logger.info("✅ 配置验证通过")
        
        # ChromeDriver检查（新增）
        if config.get('use_selenium', False) or config.get('scraper', '') == 'selenium':
            logger.info("\n🔍 正在检查ChromeDriver...")
            driver_success, driver_message = check_and_setup_chromedriver(config)
            if driver_success:
                logger.info(f"✅ {driver_message}")
            else:
                logger.warning(f"⚠️  ChromeDriver检查失败: {driver_message}")
                logger.warning("💡 程序将继续运行，但在使用Selenium时可能会出现问题")
        
        # 如果提供了本地目录，则覆盖配置
        if local_dirs:
            config['local_roots'] = local_dirs
        
        # 如果提供了抓取工具，则覆盖配置
        config['scraper'] = scraper
        
        # 设置日志
        logger, missing_logger, countries_dir = setup_logging(config['log_dir'])
        
        # 初始化数据库
        db = ModelDatabase('models.db')
        
        # 获取多线程配置

        multithreading_config = config.get('multithreading', {})
        use_multithreading = multithreading_config.get('enabled', True)
        max_workers = multithreading_config.get('max_workers', 3)
        
        logger.info("🚀 启动批量模特视频同步检查系统（多线程优化版本）")
        logger.info("=" * 60)
        logger.info(f"配置文件: config.yaml")
        logger.info(f"模特数量: {len(models)}")
        
        # 显示多目录配置信息
        local_roots = config['local_roots']
        logger.info(f"本地目录数量: {len(local_roots)}")
        for i, root in enumerate(local_roots, 1):
            logger.info(f"  目录 {i}: {root}")
        
        logger.info(f"输出目录: {config['output_dir']}")
        logger.info(f"抓取工具: {config.get('scraper', 'selenium')}")
        logger.info(f"最大翻页: {config.get('max_pages', '无限制')}")
        logger.info(f"运行模块: {'PORN' if module_type == 1 else 'JAVDB' if module_type == 2 else '自动模式'}")
        logger.info(f"多线程模式: {'启用' if use_multithreading else '禁用'} ({max_workers} 工作线程)")
        logger.info("=" * 60)
        
        # 代理连接预检（增强版）
        proxy_config = config.get('network', {}).get('proxy', {})
        if not proxy_config:
            proxy_config = config.get('proxy', {})
        
        if proxy_config.get('enabled', False):
            logger.info("\n🔍 检测到已启用代理，正在进行全面连接测试...")
            
            proxy_type = proxy_config.get('type', 'http')
            proxy_host = proxy_config.get('host', '127.0.0.1')
            proxy_port = proxy_config.get('port', '10808')
            logger.info(f"   代理类型: {proxy_type}")
            logger.info(f"   代理地址: {proxy_host}:{proxy_port}")
            
            # 使用增强版代理检查
            tester = EnhancedProxyTester(proxy_config, timeout=15)
            check_result = tester.comprehensive_check()
            
            # 打印详细报告
            print_comprehensive_report(check_result)
            
            if not check_result.overall_success:
                logger.error("\n" + "=" * 60)
                logger.error("❌ 代理连接检查失败！")
                logger.error("=" * 60)
                logger.error("\n检测到的问题：")
                # 正确访问ComprehensiveProxyCheck的属性
                test_results = [
                    ("基础TCP连接", check_result.basic_connectivity.success, check_result.basic_connectivity.error_message),
                    ("HTTP访问", check_result.http_access.success, check_result.http_access.error_message),
                    ("HTTPS访问", check_result.https_access.success, check_result.https_access.error_message)
                ]
                
                # 添加目标网站测试结果
                for target_result in check_result.target_websites:
                    test_results.append((
                        f"目标网站({target_result.host})", 
                        target_result.success, 
                        target_result.error_message
                    ))
                
                for test_name, status, message in test_results:
                    if not status:
                        logger.error(f"  • {test_name}: {message}")
                
                logger.error("\n可能的解决方案：")
                logger.error("  1. 检查代理服务是否正在运行")
                logger.error("  2. 验证代理地址和端口配置")
                logger.error("  3. 确认代理认证信息（如有）")
                logger.error("  4. 检查防火墙设置")
                logger.error("  5. 尝试禁用代理使用直连")
                logger.error("=" * 60)
                
                # 代理检查失败：默认自动继续（避免反复卡住），仅记录告警
                ask_on_fail = config.get('network', {}).get('proxy', {}).get('ask_on_fail', False)
                if ask_on_fail and sys.stdin and sys.stdin.isatty():
                    try:
                        user_input = input("\n是否继续运行程序？(y/N): ").strip().lower()
                        if user_input not in ['y', 'yes']:
                            logger.info("用户选择退出程序")
                            sys.exit(1)
                    except (RuntimeError, EOFError):
                        logger.info("\n⚠️  无法获取用户输入，程序将自动继续运行")
                else:
                    logger.info("\n⚠️  代理检查未通过，程序将自动继续运行（如需询问请在config开启 network.proxy.ask_on_fail: true）")
                    logger.info("提示：代理检查失败时仍可继续，但可能出现网络/证书问题")
            else:
                logger.info("✅ 代理连接检查通过，继续执行...\n")
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
            local_matches = scan_porn_models(
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
            # 自动模式：同时扫描PORN和JAVDB格式
            logger.info("🔄 自动模式 - 同时扫描PORN和JAVDB格式目录")
            
            # 分别扫描两种格式
            porn_matches = scan_porn_models(
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
            
            # 合并结果并去重
            seen_models = set()
            local_matches = []
            
            # 优先处理PORN格式的结果
            for match in porn_matches:
                model_name, folder, original_dir, country = match
                if model_name not in seen_models:
                    seen_models.add(model_name)
                    local_matches.append(match)
                    logger.debug(f"  添加PORN格式模特: {model_name}")
            
            # 处理JAVDB格式的结果，避免重复
            for match in javdb_matches:
                model_name, folder, original_dir, country = match
                if model_name not in seen_models:
                    seen_models.add(model_name)
                    local_matches.append(match)
                    logger.debug(f"  添加JAVDB格式模特: {model_name}")
                else:
                    # 如果模特已在PORN结果中，合并目录信息
                    for i, existing_match in enumerate(local_matches):
                        if existing_match[0] == model_name:
                            # 合并目录路径
                            combined_folder = f"{existing_match[1]};{folder}"
                            combined_original = f"{existing_match[2]};{original_dir}"
                            local_matches[i] = (model_name, combined_folder, combined_original, existing_match[3])
                            logger.debug(f"  合并模特目录信息: {model_name}")
                            break
            
            logger.info(f"自动模式 - 合并后共找到 {len(local_matches)} 个匹配的本地模特目录")
            logger.info(f"  PORN格式: {len(porn_matches)} 个")
            logger.info(f"  JAVDB格式: {len(javdb_matches)} 个")
            logger.info(f"  去重后: {len(seen_models)} 个唯一模特")
        
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
                smart_cache, db, running_flag
            )
        else:
            # 单线程模式（用于调试或只有一个模特的情况）
            logger.info("\n使用单线程模式处理...")
            processor = ModelProcessor(
                config, module_type, logger, missing_logger,
                countries_dir, smart_cache, db, running_flag
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
    import argparse
    
    parser = argparse.ArgumentParser(description='模特查重管理系统')
    parser.add_argument('--version', '-v', action='version', version='模特查重管理系统 v1.0')
    
    # 解析参数但不强制使用
    try:
        args = parser.parse_args()
    except SystemExit:
        # 如果用户请求帮助，正常退出
        sys.exit(0)
    
    main()
    
    # ==================== 修复的对比逻辑 ====================
    def _fixed_process_single_model(self, model_info: tuple, thread_id: int = 0) -> ModelResult:
        """
        修复版单个模特处理函数 - 确保下载后对比逻辑正确
        """
        model_name, folder, url, country, original_dir = model_info
        
        try:
            self.logger.info(f"[线程-{thread_id}] 开始处理模特: {model_name}")
            
            # 提取本地视频
            local_videos = extract_local_videos(folder, self.config['video_extensions'])
            local_set = {v[0] for v in local_videos}  # 只取标题
            
            # 获取在线视频
            online_set, title_to_url = self._fetch_online_videos(model_name, url, thread_id)
            
            if not online_set:
                error_msg = "无法获取在线视频列表"
                self.logger.error(f"[线程-{thread_id}] {model_name}: {error_msg}")
                return ModelResult(
                    model_name=model_name,
                    success=False,
                    error_message=error_msg,
                    url=url,
                    local_folder=original_dir,
                    local_folder_full=folder,
                    country=country
                )
            
            # 获取已缓存的标题
            cached_titles = self.smart_cache.get_cached_titles(model_name)
            new_videos = online_set - cached_titles
            
            # 修复关键：正确获取已下载的视频
            downloaded_videos = self._get_downloaded_videos_correctly(model_name)
            
            # 修复关键：正确合并本地和已下载视频
            local_set_with_downloaded = local_set | downloaded_videos
            
            # 修复关键：正确的对比逻辑
            missing = online_set - local_set_with_downloaded
            
            # 记录详细信息
            original_local_count = len(local_set)
            effective_local_count = len(local_set_with_downloaded)
            downloaded_count = len(downloaded_videos)
            
            self.logger.info(f"[线程-{thread_id}] {model_name}: "
                           f"在线 {len(online_set)} | "
                           f"新视频 {len(new_videos)} | "
                           f"本地 {original_local_count} | "
                           f"已下载 {downloaded_count} | "
                           f"有效本地 {effective_local_count} | "
                           f"缺失 {len(missing)}")
            
            # 构建结果
            result = ModelResult(
                model_name=model_name,
                success=True,
                local_count=effective_local_count,
                online_count=len(online_set),
                new_videos_count=len(new_videos),
                missing_count=len(missing),
                missing_titles=sorted(list(missing)),
                missing_with_urls=[(title, title_to_url.get(title, "")) for title in missing],
                url=url,
                local_folder=original_dir,
                local_folder_full=folder,
                country=country
            )
            
            # 更新缓存
            if self.smart_cache and self.smart_cache.enabled:
                self.smart_cache.add_videos(model_name, [(title, title_to_url.get(title, ""), 1) for title in online_set])
                # 更新缺失视频列表
                missing_data = {title: {"status": "missing", "url": title_to_url.get(title, "")} for title in missing}
                self.smart_cache.update_missing_videos(model_name, missing_data)
            
            return result
            
        except Exception as e:
            error_msg = f"处理模特失败: {str(e)}"
            self.logger.error(f"[线程-{thread_id}] {model_name}: {error_msg}")
            return ModelResult(
                model_name=model_name,
                success=False,
                error_message=error_msg,
                url=url,
                local_folder=original_dir,
                local_folder_full=folder,
                country=country
            )
    
    def _get_downloaded_videos_correctly(self, model_name: str) -> set:
        """
        正确获取已下载的视频集合
        """
        downloaded_videos = set()
        
        if self.smart_cache and self.smart_cache.enabled:
            try:
                # 从缓存中获取缺失视频数据
                cache_data = self.smart_cache.load(model_name)
                missing_data = cache_data.get('missing_videos', {})
                
                # 筛选出已下载的视频
                for title, info in missing_data.items():
                    if info.get('status') == 'downloaded':
                        downloaded_videos.add(title)
                        
                self.logger.debug(f"从缓存获取到 {len(downloaded_videos)} 个已下载视频")
                
            except Exception as e:
                self.logger.warning(f"获取已下载视频时出错: {e}")
        
        return downloaded_videos
    
    def _fetch_online_videos(self, model_name: str, url: str, thread_id: int) -> tuple:
        """
        获取在线视频列表
        """
        try:
            if self.module_type == 1:  # PORN
                online_set, title_to_url = fetch_with_requests_porn(
                    url, self.config, self.smart_cache, model_name, thread_id
                )
            elif self.module_type == 2:  # JAVDB
                online_set, title_to_url = fetch_with_requests_javdb(
                    url, self.config, self.smart_cache, model_name, thread_id
                )
            else:  # AUTO
                # 自动检测模块类型
                if 'javdb' in url.lower():
                    online_set, title_to_url = fetch_with_requests_javdb(
                        url, self.config, self.smart_cache, model_name, thread_id
                    )
                else:
                    online_set, title_to_url = fetch_with_requests_porn(
                        url, self.config, self.smart_cache, model_name, thread_id
                    )
            
            return online_set, title_to_url
            
        except Exception as e:
            self.logger.error(f"[线程-{thread_id}] 获取在线视频失败: {e}")
            return set(), {}

