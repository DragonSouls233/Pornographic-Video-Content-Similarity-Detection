import os
import sys
import json
import yaml
import time
import random
import re
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Set, List, Tuple, Dict, Optional

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
    
    # 配置根日志器
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(main_log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # 创建专门记录缺失视频的日志器
    missing_logger = logging.getLogger('missing_logger')
    missing_logger.setLevel(logging.INFO)
    
    # 避免重复添加处理器
    if not missing_logger.handlers:
        missing_handler = logging.FileHandler(missing_log_file, encoding='utf-8')
        missing_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
        missing_logger.addHandler(missing_handler)
    
    return logging.getLogger(__name__), missing_logger, countries_dir

# --- 配置加载 ---
def load_config(config_path: str = "config.yaml") -> dict:
    """加载YAML配置文件，如果不存在则自动创建默认配置"""
    try:
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
                "use_selenium": True,
                "max_pages": -1,
                "delay_between_pages": {
                    "min": 2.0,
                    "max": 3.5
                },
                "retry_on_fail": 2
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

def load_models(model_path: str = "models.json") -> dict:
    """加载模特配置JSON文件，如果不存在则自动创建空文件"""
    try:
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
                    return example['models']
            # 检查是否是嵌套格式，如 {"models": {"模特名": "URL"}}
            elif 'models' in data:
                return data['models']
            # 如果不是schema格式，直接返回
            return data
    except Exception as e:
        print(f"模特配置文件加载失败: {e}")
        sys.exit(1)

# --- 缓存管理 --- 
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

def load_cache(cache_path: str) -> Set[str]:
    """加载缓存文件"""
    if not os.path.exists(cache_path):
        return set()
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get('video_titles', []))
    except Exception as e:
        logging.warning(f"加载缓存失败: {e}")
        return set()

def save_cache(cache_path: str, video_titles: Set[str], model_name: str, url: str):
    """保存缓存文件"""
    try:
        data = {
            'model_name': model_name,
            'url': url,
            'video_titles': list(video_titles),
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
    
    if not os.path.exists(folder):
        return videos
    
    # 递归扫描所有子目录
    for root_dir, _, files in os.walk(folder):
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

def record_missing_videos(model_name: str, url: str, missing_titles: List[Tuple[str, str]], 
                         missing_logger, logger, local_count=0, online_count=0):
    """记录缺失视频到专用日志文件"""
    if not missing_titles and not online_count:
        return
    
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
