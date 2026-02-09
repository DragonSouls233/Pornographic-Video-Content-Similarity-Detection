"""
错误处理和恢复模块
提供统一的异常处理、重试机制和错误恢复功能
"""

import logging
import time
import functools
from typing import Callable, Any, Optional, Tuple
from datetime import datetime


class RetryException(Exception):
    """重试异常基类"""
    pass


class NetworkException(RetryException):
    """网络相关异常"""
    pass


class ParsingException(Exception):
    """解析相关异常"""
    pass


class PermissionException(Exception):
    """权限相关异常"""
    pass


def retry_on_exception(
    max_retries: int = 3,
    retry_delay: float = 5.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple = (Exception,),
    logger: Optional[logging.Logger] = None
) -> Callable:
    """
    装饰器：在异常时自动重试
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 初始重试延迟（秒）
        backoff_factor: 延迟递增因子
        exceptions: 需要重试的异常类型元组
        logger: 日志记录器
    
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            _logger = logger or logging.getLogger(__name__)
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # 计算延迟时间
                        delay = retry_delay * (backoff_factor ** attempt)
                        
                        _logger.warning(
                            f"🔄 函数 {func.__name__} 执行失败 "
                            f"(尝试 {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        _logger.info(f"⏳ {delay:.1f} 秒后重试...")
                        
                        time.sleep(delay)
                    else:
                        _logger.error(
                            f"❌ 函数 {func.__name__} 达到最大重试次数 "
                            f"({max_retries + 1} 次)，放弃重试"
                        )
            
            # 所有重试都失败，抛出最后一个异常
            raise last_exception
        
        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    *args,
    default_return: Any = None,
    error_msg: str = "",
    logger: Optional[logging.Logger] = None,
    **kwargs
) -> Tuple[bool, Any]:
    """
    安全执行函数，捕获所有异常
    
    Args:
        func: 要执行的函数
        *args: 函数参数
        default_return: 出错时的默认返回值
        error_msg: 错误消息前缀
        logger: 日志记录器
        **kwargs: 函数关键字参数
    
    Returns:
        (是否成功, 返回值/默认值)
    """
    _logger = logger or logging.getLogger(__name__)
    
    try:
        result = func(*args, **kwargs)
        return True, result
        
    except NetworkException as e:
        _logger.error(f"🌐 网络错误 {error_msg}: {e}")
        return False, default_return
        
    except ParsingException as e:
        _logger.error(f"📄 解析错误 {error_msg}: {e}")
        return False, default_return
        
    except PermissionException as e:
        _logger.error(f"🔒 权限错误 {error_msg}: {e}")
        return False, default_return
        
    except Exception as e:
        _logger.error(f"❌ 未知错误 {error_msg}: {e}")
        _logger.debug(f"详细信息: {type(e).__name__}: {e}", exc_info=True)
        return False, default_return


class ErrorCollector:
    """错误收集器，用于统计和报告错误"""
    
    def __init__(self, alert_threshold: int = 10):
        """
        初始化错误收集器
        
        Args:
            alert_threshold: 错误告警阈值
        """
        self.errors = {
            'network': [],
            'parsing': [],
            'permission': [],
            'unknown': []
        }
        self.alert_threshold = alert_threshold
        self.logger = logging.getLogger(__name__)
    
    def add_error(self, error_type: str, message: str, details: str = ""):
        """
        添加错误记录
        
        Args:
            error_type: 错误类型 (network/parsing/permission/unknown)
            message: 错误消息
            details: 详细信息
        """
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'details': details
        }
        
        if error_type in self.errors:
            self.errors[error_type].append(error_record)
        else:
            self.errors['unknown'].append(error_record)
        
        # 检查是否达到告警阈值
        total_errors = sum(len(errors) for errors in self.errors.values())
        if total_errors >= self.alert_threshold:
            self.logger.warning(
                f"⚠️ 错误数量达到告警阈值 ({total_errors}/{self.alert_threshold})"
            )
    
    def get_statistics(self) -> dict:
        """
        获取错误统计信息
        
        Returns:
            错误统计字典
        """
        stats = {}
        for error_type, error_list in self.errors.items():
            stats[error_type] = len(error_list)
        stats['total'] = sum(stats.values())
        return stats
    
    def get_report(self) -> str:
        """
        生成错误报告
        
        Returns:
            格式化的错误报告字符串
        """
        stats = self.get_statistics()
        
        report = ["=" * 60]
        report.append("错误统计报告")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)
        report.append("")
        
        report.append("错误类型统计:")
        report.append(f"  网络错误: {stats.get('network', 0)} 次")
        report.append(f"  解析错误: {stats.get('parsing', 0)} 次")
        report.append(f"  权限错误: {stats.get('permission', 0)} 次")
        report.append(f"  未知错误: {stats.get('unknown', 0)} 次")
        report.append(f"  总计: {stats.get('total', 0)} 次")
        report.append("")
        
        # 详细错误列表
        for error_type, error_list in self.errors.items():
            if error_list:
                report.append(f"{error_type.upper()} 错误详情:")
                report.append("-" * 40)
                for i, error in enumerate(error_list, 1):
                    report.append(f"{i}. {error['timestamp']}")
                    report.append(f"   {error['message']}")
                    if error['details']:
                        report.append(f"   详情: {error['details']}")
                report.append("")
        
        report.append("=" * 60)
        return "\n".join(report)
    
    def clear(self):
        """清空错误记录"""
        for error_type in self.errors:
            self.errors[error_type].clear()


def handle_error_by_strategy(
    error: Exception,
    strategy: str,
    logger: Optional[logging.Logger] = None
) -> bool:
    """
    根据策略处理错误
    
    Args:
        error: 异常对象
        strategy: 处理策略 (continue/stop/retry/skip/warn)
        logger: 日志记录器
    
    Returns:
        是否继续执行
    """
    _logger = logger or logging.getLogger(__name__)
    
    if strategy == 'continue':
        _logger.warning(f"⚠️ 发生错误但继续执行: {error}")
        return True
        
    elif strategy == 'stop':
        _logger.error(f"❌ 发生错误，停止执行: {error}")
        return False
        
    elif strategy == 'retry':
        _logger.info(f"🔄 发生错误，将重试: {error}")
        return True
        
    elif strategy == 'skip':
        _logger.info(f"⏭️ 发生错误，跳过当前项: {error}")
        return True
        
    elif strategy == 'warn':
        _logger.warning(f"⚠️ 警告: {error}")
        return True
        
    else:
        _logger.warning(f"⚠️ 未知策略 '{strategy}'，默认继续执行")
        return True


# 预定义的重试装饰器
retry_on_network_error = functools.partial(
    retry_on_exception,
    exceptions=(NetworkException,),
    max_retries=3,
    retry_delay=5.0
)

retry_on_any_error = functools.partial(
    retry_on_exception,
    exceptions=(Exception,),
    max_retries=2,
    retry_delay=3.0
)
