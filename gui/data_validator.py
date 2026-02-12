"""
数据验证模块
提供模特数据的格式验证和清理功能
"""

import re
import logging
from typing import Dict, List, Tuple, Any, Optional
from urllib.parse import urlparse
from datetime import datetime

class ModelDataValidator:
    """模特数据验证器"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        
        # 验证规则配置
        self.validation_config = {
            'name': {
                'required': True,
                'min_length': 1,
                'max_length': 100,
                'trim_whitespace': True,
                'normalize_case': True,
                'forbidden_chars': ['<', '>', '|', '"', "'"],
                'pattern': r'^[a-zA-Z0-9\u4e00-\u9fa5\s\-_.,()&[\]]+$',
                'error_messages': {
                    'required': '模特名称不能为空',
                    'too_short': '模特名称长度不能少于{min_length}个字符',
                    'too_long': '模特名称长度不能超过{max_length}个字符',
                    'invalid_chars': '模特名称包含不允许的字符: {forbidden_chars}',
                    'invalid_format': '模特名称格式不正确'
                }
            },
            'url': {
                'required': True,
                'min_length': 10,
                'max_length': 1000,
                'trim_whitespace': True,
                'normalize_protocol': True,
                'valid_domains': [
                    'javdb.com', 'javlibrary.com', 'pornhub.com', 'xvideos.com',
                    'youporn.com', 'redtube.com', 'tube8.com', 'spankbang.com',
                    'eporner.com', 'xhamster.com', 'tnaflix.com', 'porn.com'
                ],
                'pattern': r'^https?://[^\s/$.?#].[^\s]*$',
                'error_messages': {
                    'required': 'URL不能为空',
                    'too_short': 'URL长度不能少于{min_length}个字符',
                    'too_long': 'URL长度不能超过{max_length}个字符',
                    'invalid_format': 'URL格式不正确',
                    'invalid_domain': '不在支持的域名列表中'
                }
            },
            'module': {
                'required': True,
                'allowed_values': ['PORN', 'JAVDB'],
                'case_sensitive': False,
                'auto_detect': True,
                'error_messages': {
                    'required': '模块类型不能为空',
                    'invalid_value': '模块类型必须是PORN或JAVDB'
                }
            },
            'country': {
                'required': False,
                'max_length': 50,
                'allowed_values': [
                    '日本', '韩国', '中国', '台湾', '香港', '美国', '欧洲', '泰国',
                    'Japan', 'Korea', 'China', 'Taiwan', 'Hong Kong', 'USA', 'Europe', 'Thailand'
                ],
                'error_messages': {
                    'too_long': '国家名称长度不能超过{max_length}个字符',
                    'invalid_value': '不支持的国家名称'
                }
            }
        }
    
    def validate_field(self, field_name: str, value: Any) -> Tuple[bool, Any, List[str]]:
        """
        验证单个字段
        
        Args:
            field_name: 字段名称
            value: 字段值
            
        Returns:
            (是否有效, 处理后的值, 错误信息列表)
        """
        config = self.validation_config.get(field_name, {})
        errors = []
        processed_value = value
        
        try:
            # 类型检查和转换
            if processed_value is None:
                processed_value = ''
            else:
                processed_value = str(processed_value)
            
            # 去除空白字符
            if config.get('trim_whitespace', False):
                processed_value = processed_value.strip()
            
            # 必填检查
            if config.get('required', False) and not processed_value:
                errors.append(config['error_messages']['required'])
                return False, processed_value, errors
            
            # 如果值为空且非必填，跳过后续检查
            if not processed_value:
                return True, processed_value, errors
            
            # 长度检查
            min_length = config.get('min_length')
            max_length = config.get('max_length')
            
            if min_length and len(processed_value) < min_length:
                errors.append(config['error_messages']['too_short'].format(min_length=min_length))
            
            if max_length and len(processed_value) > max_length:
                errors.append(config['error_messages']['too_long'].format(max_length=max_length))
            
            # 格式检查
            pattern = config.get('pattern')
            if pattern and not re.match(pattern, processed_value):
                errors.append(config['error_messages'].get('invalid_format', f'{field_name}格式不正确'))
            
            # 特殊检查
            if field_name == 'url':
                valid, processed_value, url_errors = self._validate_url(processed_value, config)
                errors.extend(url_errors)
                if not valid:
                    return False, processed_value, errors
            
            elif field_name == 'name':
                name_errors = self._validate_name(processed_value, config)
                errors.extend(name_errors)
            
            elif field_name == 'module':
                valid, processed_value, module_errors = self._validate_module(processed_value, config)
                errors.extend(module_errors)
                if not valid:
                    return False, processed_value, errors
            
            elif field_name == 'country':
                country_errors = self._validate_country(processed_value, config)
                errors.extend(country_errors)
            
            # 标准化处理
            if config.get('normalize_case', False):
                processed_value = self._normalize_case(processed_value)
            
            if config.get('normalize_protocol', False):
                processed_value = self._normalize_url_protocol(processed_value)
            
            return len(errors) == 0, processed_value, errors
            
        except Exception as e:
            self.logger.error(f"验证字段 {field_name} 时发生错误: {e}")
            errors.append(f"验证{field_name}时发生内部错误")
            return False, value, errors
    
    def _validate_url(self, url: str, config: Dict) -> Tuple[bool, str, List[str]]:
        """验证URL"""
        errors = []
        
        try:
            # 基本格式检查
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                errors.append('URL格式不正确，必须包含协议和域名')
                return False, url, errors
            
            # 协议检查
            if parsed.scheme not in ['http', 'https']:
                errors.append('URL必须使用http或https协议')
                return False, url, errors
            
            # 域名检查（可选）
            valid_domains = config.get('valid_domains', [])
            if valid_domains:
                domain_valid = False
                for valid_domain in valid_domains:
                    if valid_domain.lower() in parsed.netloc.lower():
                        domain_valid = True
                        break
                
                if not domain_valid:
                    errors.append(f'不在支持的域名列表中，支持的域名: {", ".join(valid_domains)}')
                    return False, url, errors
            
            return True, url, errors
            
        except Exception as e:
            errors.append(f'URL解析失败: {e}')
            return False, url, errors
    
    def _validate_name(self, name: str, config: Dict) -> List[str]:
        """验证模特名称"""
        errors = []
        
        # 禁用字符检查
        forbidden_chars = config.get('forbidden_chars', [])
        for char in forbidden_chars:
            if char in name:
                errors.append(f'模特名称不能包含字符: {char}')
        
        return errors
    
    def _validate_module(self, module: str, config: Dict) -> Tuple[bool, str, List[str]]:
        """验证模块类型"""
        errors = []
        allowed_values = config.get('allowed_values', [])
        
        # 大小写不敏感处理
        if not config.get('case_sensitive', True):
            module_upper = module.upper()
            for allowed in allowed_values:
                if module_upper == allowed.upper():
                    return True, allowed, []
        else:
            if module in allowed_values:
                return True, module, []
        
        # 自动检测
        if config.get('auto_detect', False):
            # 这里可以根据URL自动检测，但由于只有module字段，暂时返回错误
            pass
        
        errors.append(f'模块类型必须是以下之一: {", ".join(allowed_values)}')
        return False, module, errors
    
    def _validate_country(self, country: str, config: Dict) -> List[str]:
        """验证国家名称"""
        errors = []
        allowed_values = config.get('allowed_values', [])
        
        if allowed_values and country not in allowed_values:
            errors.append(f'国家名称必须是以下之一: {", ".join(allowed_values)}')
        
        return errors
    
    def _normalize_case(self, value: str) -> str:
        """标准化大小写"""
        # 特殊处理模特名称
        words = value.split()
        normalized_words = []
        
        for word in words:
            # 对于全大写的缩写，保持原样
            if word.isupper() and len(word) <= 4:
                normalized_words.append(word)
            # 对于其他情况，首字母大写
            else:
                normalized_words.append(word.capitalize())
        
        return ' '.join(normalized_words)
    
    def _normalize_url_protocol(self, url: str) -> str:
        """标准化URL协议"""
        if url.startswith('://'):
            return 'http' + url
        elif not url.startswith(('http://', 'https://')):
            return 'https://' + url
        return url
    
    def validate_model_data(self, model_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], Dict[str, List[str]]]:
        """
        验证完整的模特数据
        
        Args:
            model_data: 模特数据字典
            
        Returns:
            (是否全部有效, 处理后的数据, 各字段错误信息)
        """
        processed_data = {}
        all_errors = {}
        is_valid = True
        
        for field_name, field_value in model_data.items():
            valid, processed_value, errors = self.validate_field(field_name, field_value)
            
            processed_data[field_name] = processed_value
            
            if errors:
                all_errors[field_name] = errors
                is_valid = False
        
        # 检查必填字段是否都存在
        for field_name, config in self.validation_config.items():
            if config.get('required', False) and field_name not in model_data:
                all_errors[field_name] = [config['error_messages']['required']]
                is_valid = False
        
        return is_valid, processed_data, all_errors
    
    def auto_complete_data(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        自动补全数据
        
        Args:
            model_data: 原始数据
            
        Returns:
            补全后的数据
        """
        completed_data = model_data.copy()
        
        # 自动检测模块类型
        if 'url' in completed_data and 'module' not in completed_data:
            url = completed_data['url'].lower()
            if 'javdb' in url or 'javlibrary' in url:
                completed_data['module'] = 'JAVDB'
            else:
                completed_data['module'] = 'PORN'
        
        # 设置默认国家（如果有URL信息）
        if 'url' in completed_data and 'country' not in completed_data:
            url = completed_data['url'].lower()
            if any(site in url for site in ['javdb', 'javlibrary']):
                completed_data['country'] = '日本'
            elif '.cn' in url or any(site in url for site in ['youporn', 'xvideos']):
                completed_data['country'] = '中国'
            else:
                completed_data['country'] = '美国'
        
        # 添加时间戳
        if 'created_at' not in completed_data:
            completed_data['created_at'] = datetime.now().isoformat()
        
        completed_data['updated_at'] = datetime.now().isoformat()
        
        return completed_data
    
    def get_validation_summary(self, validation_results: List[Tuple[bool, Dict, Dict]]) -> Dict[str, Any]:
        """
        获取验证结果摘要
        
        Args:
            validation_results: 验证结果列表
            
        Returns:
            验证摘要
        """
        total_count = len(validation_results)
        valid_count = sum(1 for valid, _, _ in validation_results if valid)
        invalid_count = total_count - valid_count
        
        # 统计错误类型
        error_counts = {}
        all_field_errors = {}
        
        for valid, processed_data, errors in validation_results:
            if not valid and errors:
                for field, field_errors in errors.items():
                    if field not in all_field_errors:
                        all_field_errors[field] = []
                    all_field_errors[field].extend(field_errors)
        
        # 计算各字段的错误次数
        for field, errors in all_field_errors.items():
            error_counts[field] = len(errors)
        
        return {
            'total_count': total_count,
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'success_rate': (valid_count / total_count * 100) if total_count > 0 else 0,
            'error_counts': error_counts,
            'common_errors': dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5])
        }
    
    def generate_validation_report(self, validation_results: List[Tuple[bool, Dict, Dict]], 
                                 output_format: str = 'text') -> str:
        """
        生成验证报告
        
        Args:
            validation_results: 验证结果列表
            output_format: 输出格式 ('text', 'html', 'json')
            
        Returns:
            验证报告内容
        """
        summary = self.get_validation_summary(validation_results)
        
        if output_format == 'json':
            import json
            return json.dumps(summary, ensure_ascii=False, indent=2)
        
        elif output_format == 'html':
            html_report = f"""
            <html>
            <head><title>模特数据验证报告</title></head>
            <body>
            <h1>模特数据验证报告</h1>
            <h2>总体统计</h2>
            <p>总记录数: {summary['total_count']}</p>
            <p>有效记录: {summary['valid_count']}</p>
            <p>无效记录: {summary['invalid_count']}</p>
            <p>成功率: {summary['success_rate']:.2f}%</p>
            
            <h2>错误统计</h2>
            <ul>
            """
            
            for field, count in summary['common_errors'].items():
                html_report += f"<li>{field}: {count} 个错误</li>"
            
            html_report += "</ul></body></html>"
            return html_report
        
        else:  # text format
            text_report = f"""
模特数据验证报告
{'=' * 50}

总体统计:
- 总记录数: {summary['total_count']}
- 有效记录: {summary['valid_count']}
- 无效记录: {summary['invalid_count']}
- 成功率: {summary['success_rate']:.2f}%

错误统计:
"""
            
            for field, count in summary['common_errors'].items():
                text_report += f"- {field}: {count} 个错误\n"
            
            text_report += "\n详细错误信息:\n"
            text_report += "-" * 50 + "\n"
            
            for i, (valid, processed_data, errors) in enumerate(validation_results, 1):
                if not valid:
                    text_report += f"\n记录 {i}:\n"
                    for field, field_errors in errors.items():
                        for error in field_errors:
                            text_report += f"  - {field}: {error}\n"
            
            return text_report


class DataCleaner:
    """数据清理器"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def clean_model_name(self, name: str) -> str:
        """清理模特名称"""
        if not name:
            return name
        
        # 去除多余空格
        cleaned = re.sub(r'\s+', ' ', name.strip())
        
        # 去除特殊字符（保留基本标点）
        cleaned = re.sub(r'[<>"\'|]', '', cleaned)
        
        # 去除首尾的特殊字符
        cleaned = cleaned.strip(' ._-,')
        
        return cleaned
    
    def clean_url(self, url: str) -> str:
        """清理URL"""
        if not url:
            return url
        
        # 去除首尾空格
        cleaned = url.strip()
        
        # 确保有协议
        if not cleaned.startswith(('http://', 'https://')):
            cleaned = 'https://' + cleaned
        
        # 移除常见的垃圾参数
        parsed = urlparse(cleaned)
        # 可以在这里添加更多清理逻辑
        
        return cleaned
    
    def normalize_data(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化数据"""
        normalized = model_data.copy()
        
        # 清理名称
        if 'name' in normalized:
            normalized['name'] = self.clean_model_name(normalized['name'])
        
        # 清理URL
        if 'url' in normalized:
            normalized['url'] = self.clean_url(normalized['url'])
        
        # 标准化模块类型
        if 'module' in normalized:
            module = str(normalized['module']).upper().strip()
            if module in ['PORN', 'JAVDB']:
                normalized['module'] = module
            else:
                # 尝试自动检测
                url = normalized.get('url', '').lower()
                if 'javdb' in url or 'javlibrary' in url:
                    normalized['module'] = 'JAVDB'
                else:
                    normalized['module'] = 'PORN'
        
        return normalized