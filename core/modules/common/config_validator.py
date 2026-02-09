"""
配置验证模块
提供全面的配置文件验证功能，确保系统配置的正确性和完整性
"""

import os
import re
import socket
import sys
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import yaml
import json

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class ValidationResult:
    """验证结果数据类"""
    def __init__(self, valid: bool = True, errors: List[str] = None, warnings: List[str] = None):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def add_error(self, error: str):
        self.valid = False
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        self.warnings.append(warning)
    
    def __bool__(self):
        return self.valid


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.result = ValidationResult()
    
    def validate_all(self) -> ValidationResult:
        """执行所有验证"""
        self._validate_basic_structure()
        self._validate_proxy_config()
        self._validate_directories()
        self._validate_models()
        self._validate_cache_settings()
        self._validate_network_settings()
        self._validate_multithreading()
        return self.result
    
    def _validate_basic_structure(self):
        """验证基本配置结构"""
        required_keys = ['local_roots', 'output_dir', 'log_dir']
        for key in required_keys:
            if key not in self.config:
                self.result.add_error(f"缺少必需配置项: {key}")
    
    def _validate_proxy_config(self):
        """验证代理配置"""
        # 检查网络代理配置
        network_proxy = self.config.get('network', {}).get('proxy', {})
        # 检查旧版代理配置（兼容性）
        legacy_proxy = self.config.get('proxy', {})
        
        # 优先使用网络配置中的代理
        proxy_config = network_proxy if network_proxy else legacy_proxy
        
        if proxy_config.get('enabled', False):
            # 验证代理主机
            host = proxy_config.get('host')
            if not host:
                self.result.add_error("代理已启用但未配置主机地址")
            elif not self._is_valid_hostname(host):
                self.result.add_warning(f"代理主机名格式可能不正确: {host}")
            
            # 验证代理端口
            port = proxy_config.get('port')
            if not port:
                self.result.add_error("代理已启用但未配置端口")
            elif not self._is_valid_port(port):
                self.result.add_error(f"代理端口无效: {port}")
            
            # 验证代理类型
            proxy_type = proxy_config.get('type', '').lower()
            valid_types = ['http', 'https', 'socks5', 'socks4']
            if proxy_type and proxy_type not in valid_types:
                self.result.add_warning(f"代理类型 '{proxy_type}' 可能不受支持")
    
    def _validate_directories(self):
        """验证目录配置"""
        local_roots = self.config.get('local_roots', [])
        
        # 处理不同格式的local_roots配置
        if isinstance(local_roots, dict):
            # 新格式: {porn: [...], jav: [...]}
            dirs_to_check = []
            for category_dirs in local_roots.values():
                if isinstance(category_dirs, list):
                    dirs_to_check.extend(category_dirs)
                else:
                    dirs_to_check.append(category_dirs)
        else:
            # 旧格式: 直接的目录列表
            dirs_to_check = local_roots if isinstance(local_roots, list) else [local_roots]
        
        if not dirs_to_check:
            self.result.add_warning("未配置任何本地视频目录")
            return
        
        for directory in dirs_to_check:
            if not directory:
                continue
                
            # 检查路径格式
            if not isinstance(directory, str):
                self.result.add_error(f"目录路径必须是字符串: {directory}")
                continue
            
            # 检查路径是否存在
            if not os.path.exists(directory):
                self.result.add_warning(f"配置的目录不存在: {directory}")
            elif not os.path.isdir(directory):
                self.result.add_error(f"配置路径不是目录: {directory}")
            else:
                # 检查目录权限
                if not os.access(directory, os.R_OK):
                    self.result.add_error(f"没有读取权限: {directory}")
    
    def _validate_models(self):
        """验证模特配置"""
        try:
            # 尝试加载models.json
            models_path = "models.json"
            if os.path.exists(models_path):
                with open(models_path, 'r', encoding='utf-8') as f:
                    models_data = json.load(f)
                
                if not models_data:
                    self.result.add_warning("models.json文件为空")
                elif not isinstance(models_data, dict):
                    self.result.add_error("models.json格式错误，应为对象")
                else:
                    # 验证每个模特配置
                    for model_name, model_info in models_data.items():
                        if not model_name or not isinstance(model_name, str):
                            self.result.add_error(f"模特名称无效: {model_name}")
                        
                        # 验证URL格式
                        url = None
                        if isinstance(model_info, str):
                            url = model_info
                        elif isinstance(model_info, dict):
                            url = model_info.get('url')
                        
                        if url:
                            if not self._is_valid_url(url):
                                self.result.add_warning(f"模特'{model_name}'的URL格式可能不正确: {url}")
                        else:
                            self.result.add_warning(f"模特'{model_name}'缺少URL配置")
            else:
                self.result.add_warning("未找到models.json文件")
                
        except json.JSONDecodeError as e:
            self.result.add_error(f"models.json文件格式错误: {e}")
        except Exception as e:
            self.result.add_error(f"读取models.json失败: {e}")
    
    def _validate_cache_settings(self):
        """验证缓存配置"""
        cache_config = self.config.get('cache', {})
        
        # 验证缓存目录
        cache_dir = cache_config.get('cache_dir', 'cache')
        if cache_dir:
            # 检查是否为相对路径
            if not os.path.isabs(cache_dir):
                # 相对路径，检查是否在输出目录下
                output_dir = self.config.get('output_dir', 'output')
                full_cache_path = os.path.join(output_dir, cache_dir)
                if not os.path.exists(full_cache_path):
                    try:
                        os.makedirs(full_cache_path, exist_ok=True)
                    except Exception as e:
                        self.result.add_warning(f"无法创建缓存目录: {e}")
        
        # 验证缓存大小限制
        max_size = cache_config.get('max_size_mb', -1)
        if max_size != -1 and (not isinstance(max_size, (int, float)) or max_size < 0):
            self.result.add_error("缓存大小限制必须是非负数")
        
        # 验证过期时间
        expiry_days = cache_config.get('expiration_days', 3650)
        if not isinstance(expiry_days, (int, float)) or expiry_days <= 0:
            self.result.add_error("缓存过期天数必须是正数")
    
    def _validate_network_settings(self):
        """验证网络配置"""
        network_config = self.config.get('network', {})
        
        # 验证超时设置
        timeout = network_config.get('timeout', 300)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            self.result.add_error("网络超时设置必须是正数")
        elif timeout < 30:
            self.result.add_warning("网络超时设置过短，可能导致连接不稳定")
        
        # 验证延迟设置
        delay_config = self.config.get('delay_between_pages', {})
        min_delay = delay_config.get('min', 2.0)
        max_delay = delay_config.get('max', 3.5)
        
        if not isinstance(min_delay, (int, float)) or min_delay < 0:
            self.result.add_error("最小延迟必须是非负数")
        if not isinstance(max_delay, (int, float)) or max_delay < 0:
            self.result.add_error("最大延迟必须是非负数")
        if min_delay > max_delay:
            self.result.add_error("最小延迟不能大于最大延迟")
    
    def _validate_multithreading(self):
        """验证多线程配置"""
        mt_config = self.config.get('multithreading', {})
        
        if not mt_config:
            return  # 多线程配置可选
        
        # 验证启用状态
        enabled = mt_config.get('enabled', True)
        if not isinstance(enabled, bool):
            self.result.add_error("多线程启用状态必须是布尔值")
        
        # 验证工作线程数
        max_workers = mt_config.get('max_workers', 3)
        if not isinstance(max_workers, int) or max_workers <= 0:
            self.result.add_error("工作线程数必须是正整数")
        elif max_workers > 10:
            self.result.add_warning("工作线程数过多可能导致系统资源耗尽")
    
    def _is_valid_hostname(self, hostname: str) -> bool:
        """验证主机名格式"""
        if not hostname:
            return False
        
        # IP地址格式
        try:
            socket.inet_aton(hostname)
            return True
        except socket.error:
            pass
        
        # 域名格式
        if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', hostname):
            return True
        
        return False
    
    def _is_valid_port(self, port) -> bool:
        """验证端口格式"""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False
    
    def _is_valid_url(self, url: str) -> bool:
        """验证URL格式"""
        if not url or not isinstance(url, str):
            return False
        
        # 基本URL格式检查
        url_pattern = re.compile(
            r'^https?://'  # http:// 或 https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # 域名
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # 可选端口
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))


def validate_config_file(config_path: str = "config.yaml") -> ValidationResult:
    """
    验证配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        ValidationResult: 验证结果
    """
    try:
        # 检查配置文件是否存在
        if not os.path.exists(config_path):
            result = ValidationResult(valid=False)
            result.add_error(f"配置文件不存在: {config_path}")
            return result
        
        # 加载配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config_text = f.read()
            # 处理Windows路径反斜杠问题
            config_text = config_text.replace('\\', '\\\\')
            config = yaml.safe_load(config_text)
        
        if not config:
            result = ValidationResult(valid=False)
            result.add_error("配置文件为空或格式错误")
            return result
        
        # 执行验证
        validator = ConfigValidator(config)
        return validator.validate_all()
        
    except yaml.YAMLError as e:
        result = ValidationResult(valid=False)
        result.add_error(f"YAML格式错误: {e}")
        return result
    except Exception as e:
        result = ValidationResult(valid=False)
        result.add_error(f"读取配置文件失败: {e}")
        return result


def print_validation_report(result: ValidationResult):
    """打印验证报告"""
    print("\n" + "="*60)
    print("配置验证报告")
    print("="*60)
    
    if result.valid:
        print("✅ 配置验证通过")
        if result.warnings:
            print(f"\n⚠️  发现 {len(result.warnings)} 个警告:")
            for i, warning in enumerate(result.warnings, 1):
                print(f"  {i}. {warning}")
    else:
        print("❌ 配置验证失败")
        print(f"\n错误 ({len(result.errors)} 个):")
        for i, error in enumerate(result.errors, 1):
            print(f"  {i}. {error}")
        
        if result.warnings:
            print(f"\n警告 ({len(result.warnings)} 个):")
            for i, warning in enumerate(result.warnings, 1):
                print(f"  {i}. {warning}")
    
    print("="*60)


# 便捷函数
def quick_validate() -> bool:
    """
    快速验证配置，返回是否通过
    
    Returns:
        bool: True表示配置有效，False表示存在问题
    """
    result = validate_config_file()
    if not result.valid:
        print_validation_report(result)
    return result.valid


if __name__ == "__main__":
    # 命令行测试
    import sys
    
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    result = validate_config_file(config_path)
    print_validation_report(result)
    
    # 返回适当的退出码
    sys.exit(0 if result.valid else 1)