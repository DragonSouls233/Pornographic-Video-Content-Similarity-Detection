import os
import sys
import json
import yaml
import time
import random
import re
import logging
import traceback
import socket
from datetime import datetime
from pathlib import Path
from typing import Set, List, Tuple, Dict, Optional

# 路径工具函数 - 修复打包后的路径问题
def get_app_path():
    """
    获取应用程序路径
    打包后返回可执行文件所在目录，开发环境返回项目根目录

    注意：`common.py` 位于 `core/modules/common/`，需要回溯到项目根目录，
    否则会错误读取 `core/config.yaml` 并生成简化默认配置。
    """
    if getattr(sys, 'frozen', False):
        # 打包后的环境
        return os.path.dirname(sys.executable)
    else:
        # 开发环境 - 返回项目根目录（core/modules/common -> project_root）
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def get_config_path(filename):
    """
    获取配置文件路径
    确保配置文件保存在正确位置
    """
    app_path = get_app_path()
    return os.path.join(app_path, filename)


# --- 日志配置 ---
def setup_logging(log_dir: str, config_name: str = "main"):
    """配置日志系统，返回日志器"""
    Path(log_dir).mkdir(exist_ok=True)
    
    # 创建国家日志目录
    countries_dir = os.path.join(log_dir, "countries")
    Path(countries_dir).mkdir(exist_ok=True)
    
    # 主日志文件
    main_log_file = os.path.join(log_dir, f"sync_{datetime.now().strftime('%Y%m%d')}.log")
    
    # 缺失视频专用日志文件
    missing_log_file = os.path.join(log_dir, f"missing_{datetime.now().strftime('%Y%m%d')}.log")
    
    # 使用根日志器，这样GUI的QueueHandler也能捕获到日志
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 避免重复添加处理器
    if not logger.handlers:
        # 添加文件处理器
        file_handler = logging.FileHandler(main_log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', '%Y-%m-%d %H:%M:%S'))
        logger.addHandler(file_handler)
        
        # 添加控制台处理器
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', '%Y-%m-%d %H:%M:%S'))
        logger.addHandler(stream_handler)
    
    # 创建专门记录缺失视频的日志器
    missing_logger = logging.getLogger('missing_logger')
    missing_logger.setLevel(logging.INFO)
    
    # 避免重复添加处理器
    if not missing_logger.handlers:
        missing_handler = logging.FileHandler(missing_log_file, encoding='utf-8')
        missing_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
        missing_logger.addHandler(missing_handler)
    
    return logger, missing_logger, countries_dir

# --- 配置加载 ---
def load_config(config_path: str = "config.yaml") -> dict:
    """加载YAML配置文件，如果不存在则自动创建默认配置"""
    try:
        # 使用正确的路径
        if not os.path.isabs(config_path):
            config_path = get_config_path(config_path)
        
        # 在开发环境中，优先检查根目录是否存在配置文件
        if not getattr(sys, 'frozen', False):  # 开发环境
            root_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), config_path.split('/')[-1])
            if os.path.exists(root_config_path):
                config_path = root_config_path

        if not os.path.exists(config_path):
            # 自动生成默认配置文件
            default_config = {
                "local_roots": ["F:\\作品"],
                "output_dir": "output",
                "log_dir": "log",
                "video_extensions": ["mp4", "avi", "mov", "wmv", "flv", "mkv", "rmvb"],
                "filename_clean_patterns": [
                    r"(?i)\[.*?\]",
                    r"(?i)\(.*?\)",
                    r"(?i)\{.*?\}"
                ],
                "scraper": "selenium",
                "max_pages": -1,
                "delay_between_pages": {
                    "min": 2.0,
                    "max": 3.5
                },
                "retry_on_fail": 2,
                "proxy": {
                    "enabled": False,
                    "http": "",
                    "https": ""
                }
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False)
            print(f"配置文件不存在，已自动创建默认配置文件: {config_path}")
            return default_config
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_text = f.read()
            config_text = config_text.replace('\\', '\\\\')
            return yaml.safe_load(config_text)
    except Exception as e:
        print(f"配置文件加载失败: {e}")
        sys.exit(1)

def load_models(model_path: str = "models.json", use_database: bool = True) -> dict:
    """加载模特配置，支持数据库和JSON两种模式
    
    Args:
        model_path: JSON文件路径（当use_database=False时使用）
        use_database: 是否使用数据库模式
    
    Returns:
        dict: {"模特名": "URL"} 格式的字典
    """
    if use_database:
        try:
            # 使用数据库模式
            from .model_database import ModelDatabase
            db = ModelDatabase('models.db')
            models_dict = db.load_models()
            
            # 安全使用logger（如果已初始化）
            try:
                logger.debug(f"从数据库加载了 {len(models_dict)} 个模特")
            except NameError:
                pass  # logger未初始化，静默忽略
            
            return models_dict
        except Exception as e:
            # 安全使用logger（如果已初始化）
            try:
                logger.warning(f"数据库加载失败，回退到JSON模式: {e}")
            except NameError:
                pass  # logger未初始化，静默忽略
            # 回退到JSON模式
            pass
    
    # JSON模式（原有逻辑）
    try:
        # 使用正确的路径
        if not os.path.isabs(model_path):
            model_path = get_config_path(model_path)

        if not os.path.exists(model_path):
            # 自动生成空的模特配置文件
            with open(model_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            print(f"模特配置文件不存在，已自动创建空文件: {model_path}")
            return {}

        with open(model_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # 检查是否是schema格式，如果是，尝试获取examples中的模特数据
            if 'examples' in data and len(data['examples']) > 0:
                example = data['examples'][0]
                if 'models' in example:
                    data = example['models']
            # 检查是否是嵌套格式，如 {"models": {"模特名": "URL"}}
            elif 'models' in data:
                data = data['models']
            
            # 兼容新格式：将 {"模特名": {"module": "...", "url": "..."}} 转换为 {"模特名": "url"}
            result = {}
            for model_name, model_info in data.items():
                if isinstance(model_info, dict):
                    # 新格式：提取URL
                    result[model_name] = model_info.get("url", "")
                else:
                    # 旧格式：直接使用
                    result[model_name] = model_info
            
            return result
    except Exception as e:
        print(f"模特配置文件加载失败: {e}")
        sys.exit(1)

# --- 缓存管理 --- 
# 导入智能缓存模块
from .smart_cache import SmartCache, create_smart_cache

# 导入数据库存储模块
from .database_storage import create_database_cache_adapter

# 导入异步下载器模块
from .async_downloader import AsyncDownloadEngine, AsyncDownloaderAdapter

# 全局智能缓存实例（延迟初始化）
_smart_cache_instance: SmartCache = None

def get_cache_dir(config: dict) -> str:
    """获取缓存目录路径"""
    # 确保output目录存在
    output_dir = config['output_dir']
    Path(output_dir).mkdir(exist_ok=True)
    
    # 然后创建缓存目录
    cache_dir = os.path.join(output_dir, 'cache')
    Path(cache_dir).mkdir(exist_ok=True)
    return cache_dir

def get_model_cache_path(cache_dir: str, model_name: str) -> str:
    """获取模特缓存文件路径"""
    # 生成安全的文件名
    safe_model_name = re.sub(r'[^\w\-]', '_', model_name)
    return os.path.join(cache_dir, f"{safe_model_name}.json")

def get_smart_cache(cache_dir: str = None, config: dict = None) -> SmartCache:
    """
    获取智能缓存实例（单例模式）
    支持JSON文件存储和数据库存储两种方式
    
    Args:
        cache_dir: 缓存目录
        config: 配置字典
        
    Returns:
        SmartCache 实例（可能是数据库适配器）
    """
    global _smart_cache_instance
    if _smart_cache_instance is None:
        if cache_dir is None:
            cache_dir = 'output/cache'
        
        # 检查是否启用数据库存储
        cache_config = config.get('cache', {}) if config else {}
        use_database = cache_config.get('use_database', False)
        
        if use_database:
            # 使用数据库存储
            db_path = cache_config.get('database_path', 'output/cache.db')
            _smart_cache_instance = create_database_cache_adapter(db_path, config)
            logging.getLogger(__name__).info(f"使用数据库存储: {db_path}")
        else:
            # 使用传统的JSON文件存储
            _smart_cache_instance = create_smart_cache(cache_dir, config)
            logging.getLogger(__name__).info(f"使用JSON文件存储: {cache_dir}")
    
    return _smart_cache_instance

def load_cache(cache_path: str) -> Set[str]:
    """加载缓存文件（兼容旧版本）"""
    if not os.path.exists(cache_path):
        return set()
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 优先使用新的 videos 结构
            if 'videos' in data and data['videos']:
                return set(data['videos'].keys())
            # 兼容旧版本
            return set(data.get('video_titles', []))
    except Exception as e:
        logging.warning(f"加载缓存失败: {e}")
        return set()

def save_cache(cache_path: str, video_titles: Set[str], model_name: str, url: str):
    """保存缓存文件（兼容旧版本）"""
    try:
        data = {
            'model_name': model_name,
            'url': url,
            'video_titles': list(video_titles),
            'videos': {title: {'url': '', 'page': 0, 'timestamp': datetime.now().isoformat()} 
                      for title in video_titles},
            'last_updated': datetime.now().isoformat()
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"保存缓存失败: {e}")

# --- 本地文件处理（支持多层文件夹）---
def clean_filename(name: str, patterns: List[str]) -> str:
    """清理文件名中的干扰项"""
    original_name = name
    
    for pat in patterns:
        try:
            name = re.sub(pat, '', name, flags=re.IGNORECASE)
        except re.error as e:
            logging.debug(f"正则表达式错误 '{pat}': {e}")
            # 尝试不带标志的正则表达式
            try:
                name = re.sub(pat, '', name)
            except:
                pass
    
    cleaned = name.strip()
    
    # 移除多余的空格和分隔符
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'[_\-\.]+', ' ', cleaned)
    cleaned = cleaned.strip(' _-.')
    
    # 移除常见的视频标识
    # 先移除文件名开头的[模特名]前缀
    cleaned = re.sub(r'^\[.*?\]\s*', '', cleaned)
    # 再移除末尾的哈希值或其他标识
    cleaned = re.sub(r'\s*\([^\)]*?\)\s*$', '', cleaned)
    
    # 全面的字符统一处理
    # 1. 全角转半角
    full_to_half = {}
    for i in range(0xFF01, 0xFF5F + 1):
        full_to_half[chr(i)] = chr(i - 0xFEE0)
    # 特殊处理空格
    full_to_half['　'] = ' '
    # 应用全角转半角
    cleaned = ''.join([full_to_half.get(c, c) for c in cleaned])
    
    # 2. 特殊字符统一
    # 统一处理破折号：将所有类型的破折号转换为标准的hyphen
    cleaned = re.sub(r'[\u2013\u2014\u2015]', '-', cleaned)
    # 统一处理引号：将所有类型的引号转换为标准的单引号
    cleaned = re.sub(r'[\u2018\u2019\u201c\u201d]', "'", cleaned)
    # 统一处理省略号：将所有类型的省略号转换为标准的三个点
    cleaned = re.sub(r'[\u2026]', '...', cleaned)
    # 统一处理斜杠：将全角斜杠转换为半角斜杠
    cleaned = re.sub(r'[\uFF0F]', '/', cleaned)
    
    # 3. 空格和分隔符标准化
    # 统一处理空格：将多个连续空格替换为单个空格
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # 移除分辨率和视频质量标识
    cleaned = re.sub(r'\d{3,4}[xp]\d{3,4}', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\d{3,4}p', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(hd|fhd|uhd|4k|fullhd)\b', '', cleaned, flags=re.IGNORECASE)
    # 移除多余的空格和分隔符
    cleaned = re.sub(r'[\s_\-\.]+', ' ', cleaned)
    cleaned = cleaned.strip(' _-.')
    
    if original_name != cleaned:
        logging.debug(f"清理文件名: '{original_name}' -> '{cleaned}'")
    
    return cleaned.strip()

def extract_local_videos(folder: str, video_exts: Set[str], 
                        clean_patterns: List[str]) -> Set[str]:
    """
    提取本地视频文件，支持多层文件夹结构
    递归扫描子文件夹中的所有视频文件
    """
    videos = set()

    # 支持多路径（自动模式合并路径使用 ; 分隔）
    folders = [folder]
    if folder and not os.path.exists(folder) and ';' in folder:
        folders = [p.strip() for p in folder.split(';') if p.strip()]

    for path in folders:
        if not path or not os.path.exists(path):
            continue

        # 递归扫描所有子目录
        for root_dir, _, files in os.walk(path):
            for file in files:
                name, ext = os.path.splitext(file)

                if ext.lower() in video_exts:
                    cleaned = clean_filename(name, clean_patterns)
                    if cleaned:
                        videos.add(cleaned)
                    else:
                        # 如果清理后为空，使用原始名称
                        cleaned_name = name.strip()
                        cleaned_name = re.sub(r'[\[\]\(\)].*?[\[\]\(\)]', '', cleaned_name)
                        videos.add(cleaned_name)

    return videos


def extract_local_folders(folder: str) -> Set[str]:
    """
    提取本地文件夹名称，支持多层文件夹结构
    递归扫描子文件夹，提取文件夹名称作为视频标题
    """
    folders = set()

    # 支持多路径（自动模式合并路径使用 ; 分隔）
    folder_list = [folder]
    if folder and not os.path.exists(folder) and ';' in folder:
        folder_list = [p.strip() for p in folder.split(';') if p.strip()]

    for path in folder_list:
        if not path or not os.path.exists(path):
            continue

        # 递归扫描所有子目录
        for root_dir, subdirs, _ in os.walk(path):
            for subdir in subdirs:
                # 清理文件夹名称
                cleaned = subdir.strip()
                # 移除日期前缀（如果有），如 [2026-01-27]
                cleaned = re.sub(r'^\[\d{4}-\d{2}-\d{2}\]', '', cleaned)
                # 移除多余的空格
                cleaned = cleaned.strip()
                if cleaned:
                    folders.add(cleaned)

    return folders


def test_proxy_connection(proxy_config: dict, timeout: int = 5, logger=None) -> bool:
    """
    测试代理连接是否可用
    
    Args:
        proxy_config: 代理配置字典
        timeout: 连接超时时间（秒）
        logger: 日志记录器
        
    Returns:
        bool: 代理是否可用
    """
    if not proxy_config.get('enabled', False):
        # 未启用代理，直接返回 True
        return True
    
    # 尝试从不同位置获取代理主机和端口
    host = proxy_config.get('host', '')
    port = proxy_config.get('port', '')
    
    # 如果没有直接的 host 和 port，尝试从 http 代理 URL 中解析
    if not host or not port:
        http_proxy = proxy_config.get('http', '')
        if http_proxy:
            # 解析代理 URL，例如: http://127.0.0.1:10808 或 socks5://127.0.0.1:10808
            import re
            match = re.match(r'(?:https?|socks5?)://([^:]+):(\d+)', http_proxy)
            if match:
                host = match.group(1)
                port = match.group(2)
    
    if not host or not port:
        if logger:
            logger.warning("⚠️  代理配置不完整，无法进行连接测试")
        return True  # 配置不完整时不阻止程序运行
    
    try:
        port = int(port)
        if logger:
            logger.info(f"🔍 测试代理连接: {host}:{port}")
        
        # 创建 socket 连接测试
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            if logger:
                logger.info(f"✅ 代理连接测试成功: {host}:{port}")
            return True
        else:
            if logger:
                logger.error(f"❌ 代理连接失败: {host}:{port} (错误码: {result})")
            return False
            
    except socket.timeout:
        if logger:
            logger.error(f"❌ 代理连接超时: {host}:{port}")
        return False
    except socket.gaierror as e:
        if logger:
            logger.error(f"❌ 代理主机名解析失败: {host} ({e})")
        return False
    except ValueError as e:
        if logger:
            logger.error(f"❌ 代理端口格式错误: {port} ({e})")
        return False
    except Exception as e:
        if logger:
            logger.error(f"❌ 代理连接测试异常: {e}")
        return False


def record_missing_videos(model_name: str, url: str, missing_titles: List[Tuple[str, str]], 
                         missing_logger, logger, local_count=0, online_count=0, template_type="simple"):
    """记录缺失视频到专用日志文件
    
    Args:
        model_name: 模特名称
        url: 模特链接
        missing_titles: 缺失视频列表 [(标题, URL)]
        missing_logger: 缺失日志记录器
        logger: 主日志记录器
        local_count: 本地视频数量
        online_count: 在线视频数量
        template_type: 日志模板类型 ("simple" | "detailed")
    """
    if not missing_titles and not online_count:
        return
    
    if template_type == "simple":
        _record_missing_simple(model_name, url, missing_titles, missing_logger, logger, local_count, online_count)
    elif template_type == "detailed":
        _record_missing_detailed(model_name, url, missing_titles, missing_logger, logger, local_count, online_count)
    else:
        # 默认使用简单模板
        _record_missing_simple(model_name, url, missing_titles, missing_logger, logger, local_count, online_count)


def _record_missing_simple(model_name: str, url: str, missing_titles: List[Tuple[str, str]], 
                         missing_logger, logger, local_count=0, online_count=0):
    """简单模板：只记录标题和链接"""
    missing_logger.info("=" * 60)
    missing_logger.info(f"模特: {model_name}")
    missing_logger.info(f"链接: {url}")
    if online_count > 0:
        missing_logger.info(f"缺失视频数量: {len(missing_titles)}")
        missing_logger.info(f"总视频数量: {online_count} | 本地视频: {local_count} | 缺失视频: {len(missing_titles)}")
    else:
        missing_logger.info(f"缺失视频数量: {len(missing_titles)}")
    missing_logger.info("-" * 40)
    
    for i, (title, video_url) in enumerate(missing_titles, 1):
        if video_url:
            missing_logger.info(f"{i:3d}. {title}")
            missing_logger.info(f"    链接: {video_url}")
        else:
            missing_logger.info(f"{i:3d}. {title}")
    
    missing_logger.info("=" * 60 + "\n")
    logger.warning(f"  🔴 缺失 {len(missing_titles)} 个视频，已记录到缺失日志")


def _record_missing_detailed(model_name: str, url: str, missing_titles: List[Tuple[str, str]], 
                         missing_logger, logger, local_count=0, online_count=0):
    """详细模板：记录更多信息包括统计和格式化输出"""
    from datetime import datetime
    
    missing_logger.info("=" * 80)
    missing_logger.info(f"缺失视频报告 - {model_name}")
    missing_logger.info("=" * 80)
    missing_logger.info(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    missing_logger.info(f"模特链接: {url}")
    missing_logger.info("")
    
    # 统计信息
    missing_logger.info("📊 统计信息:")
    missing_logger.info(f"  • 在线视频总数: {online_count}")
    missing_logger.info(f"  • 本地已有视频: {local_count}")
    missing_logger.info(f"  • 缺失视频数量: {len(missing_titles)}")
    missing_logger.info(f"  • 完整度: {((online_count - len(missing_titles)) / online_count * 100):.1f}% ({online_count - len(missing_titles)}/{online_count})")
    missing_logger.info("")
    
    if missing_titles:
        missing_logger.info("📋 缺失视频列表:")
        missing_logger.info("-" * 80)
        
        for i, (title, video_url) in enumerate(missing_titles, 1):
            missing_logger.info(f"{i:3d}. 标题: {title}")
            if video_url:
                missing_logger.info(f"    链接: {video_url}")
            else:
                missing_logger.info(f"    链接: [未获取到链接]")
            
            # 每10个视频添加一个分隔线
            if i % 10 == 0 and i > 0:
                missing_logger.info("-" * 40)
        
        missing_logger.info("-" * 80)
        
        # 下载建议
        missing_logger.info("")
        missing_logger.info("💡 下载建议:")
        missing_logger.info(f"  • 可以使用以下命令批量下载:")
        missing_logger.info(f"    python -c \"")
        missing_logger.info(f"    from core.modules.porn.downloader import download_model_complete_directory;")
        missing_logger.info(f"    download_model_complete_directory('{url}', '{model_name}')")
        missing_logger.info(f"    \"")
        missing_logger.info("")
        missing_logger.info("  • 或者在GUI中选择'完整下载模特目录'功能")
    else:
        missing_logger.info("✅ 视频完整度: 100% - 无缺失视频")
    
    missing_logger.info("")
    missing_logger.info("=" * 80)
    missing_logger.info("报告结束")
    missing_logger.info("=" * 80 + "\n")
    
    if missing_titles:
        logger.warning(f"  🔴 缺失 {len(missing_titles)} 个视频，已记录到缺失日志（详细模板）")
    else:
        logger.info(f"  ✅ 模特 {model_name} 视频完整，无缺失")


# --- 全局配置访问函数 ---
def get_config():
    """获取全局配置"""
    return load_config()

def get_session():
    """获取全局会话对象"""
    import requests
    config = get_config()
    session = requests.Session()
    
    # 配置代理
    if config.get('network', {}).get('proxy', {}).get('enabled', False):
        proxy_config = config['network']['proxy']
        proxy_url = f"{proxy_config.get('http', 'socks5://127.0.0.1:10808')}"
        session.proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
    
    # 配置请求头
    headers = config.get('network', {}).get('headers', {})
    if headers:
        session.headers.update(headers)
    
    return session

def ensure_dir_exists(dir_path):
    """确保目录存在"""
    Path(dir_path).mkdir(parents=True, exist_ok=True)
