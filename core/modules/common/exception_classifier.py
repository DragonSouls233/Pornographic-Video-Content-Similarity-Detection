# -*- coding: utf-8 -*-
"""
异常分类器
区分系统错误、数据缺失和链接错误等不同类型的异常
"""

import re
from typing import Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass


class ExceptionType(Enum):
    """异常类型枚举"""
    SYSTEM_ERROR = "系统错误"
    DATA_MISSING = "数据缺失"
    LINK_ERROR = "链接错误"
    NETWORK_ERROR = "网络错误"
    PERMISSION_ERROR = "权限错误"
    UNKNOWN_ERROR = "未知错误"


class ExceptionSeverity(Enum):
    """异常严重程度"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    CRITICAL = "严重"


@dataclass
class ExceptionClassification:
    """异常分类结果"""
    exception_type: ExceptionType
    severity: ExceptionSeverity
    description: str
    suggestion: str
    is_retryable: bool
    auto_continue: bool = True


class ExceptionClassifier:
    """异常分类器"""
    
    def __init__(self):
        """初始化分类规则"""
        self.rules = self._init_classification_rules()
    
    def _init_classification_rules(self) -> Dict[str, ExceptionClassification]:
        """初始化分类规则"""
        rules = {}
        
        # 网络相关错误
        network_patterns = [
            r"connection.*timeout|timeout.*connection",
            r"connection.*refused|connection.*reset",
            r"network.*unreachable|network.*error",
            r"requests\.exceptions\.Timeout",
            r"requests\.exceptions\.ConnectionError"
        ]
        
        for pattern in network_patterns:
            rules[pattern] = ExceptionClassification(
                exception_type=ExceptionType.NETWORK_ERROR,
                severity=ExceptionSeverity.MEDIUM,
                description="网络连接错误",
                suggestion="检查网络连接和代理设置",
                is_retryable=True,
                auto_continue=True
            )
        
        # 链接相关错误
        link_patterns = [
            r"404.*not found|not found.*404",
            r"page.*not found|not.*found.*page",
            r"url.*invalid|invalid.*url",
            r"link.*missing|missing.*link",
            r"链接.*缺失|缺失.*链接",
            r"在线标题正确.*链接缺失|标题正确.*链接错误"
        ]
        
        for pattern in link_patterns:
            rules[pattern] = ExceptionClassification(
                exception_type=ExceptionType.LINK_ERROR,
                severity=ExceptionSeverity.MEDIUM,
                description="链接缺失或错误",
                suggestion="检查模特页面URL，可能需要更新",
                is_retryable=False,
                auto_continue=True
            )
        
        # 数据缺失相关错误
        data_missing_patterns = [
            r"no.*data|data.*missing",
            r"empty.*response|response.*empty",
            r"no.*content|content.*missing",
            r"标题.*缺失|缺失.*标题",
            r"数据.*缺失|缺失.*数据"
        ]
        
        for pattern in data_missing_patterns:
            rules[pattern] = ExceptionClassification(
                exception_type=ExceptionType.DATA_MISSING,
                severity=ExceptionSeverity.LOW,
                description="模特数据缺失",
                suggestion="检查模特页面结构，可能需要更新抓取规则",
                is_retryable=True,
                auto_continue=True
            )
        
        # 权限相关错误
        permission_patterns = [
            r"403.*forbidden|forbidden.*403",
            r"401.*unauthorized|unauthorized.*401",
            r"permission.*denied|denied.*permission",
            r"access.*denied|denied.*access"
        ]
        
        for pattern in permission_patterns:
            rules[pattern] = ExceptionClassification(
                exception_type=ExceptionType.PERMISSION_ERROR,
                severity=ExceptionSeverity.HIGH,
                description="访问权限问题",
                suggestion="检查代理设置或会员权限",
                is_retryable=True,
                auto_continue=True
            )
        
        # 系统相关错误
        system_patterns = [
            r"selenium.*error|error.*selenium",
            r"driver.*error|error.*driver",
            r"browser.*error|error.*browser",
            r"memory.*error|error.*memory",
            r"disk.*full|full.*disk",
            r"file.*not.*found|not.*found.*file",
            r"import.*error|error.*import"
        ]
        
        for pattern in system_patterns:
            rules[pattern] = ExceptionClassification(
                exception_type=ExceptionType.SYSTEM_ERROR,
                severity=ExceptionSeverity.HIGH,
                description="系统环境错误",
                suggestion="检查系统环境和依赖",
                is_retryable=False,
                auto_continue=True
            )
        
        return rules
    
    def classify_exception(self, error_message: str, error_type: Optional[str] = None) -> ExceptionClassification:
        """
        分类异常
        
        Args:
            error_message: 错误消息
            error_type: 错误类型（可选）
            
        Returns:
            ExceptionClassification: 分类结果
        """
        # 统一转为小写进行匹配
        error_lower = str(error_message).lower()
        
        # 检查每个规则
        for pattern, classification in self.rules.items():
            if re.search(pattern, error_lower):
                return classification
        
        # 特殊情况处理
        if error_type:
            error_type_lower = str(error_type).lower()
            if "timeout" in error_type_lower:
                return ExceptionClassification(
                    exception_type=ExceptionType.NETWORK_ERROR,
                    severity=ExceptionSeverity.MEDIUM,
                    description="请求超时",
                    suggestion="增加超时时间或检查网络",
                    is_retryable=True,
                    auto_continue=True
                )
            elif "connection" in error_type_lower:
                return ExceptionClassification(
                    exception_type=ExceptionType.NETWORK_ERROR,
                    severity=ExceptionSeverity.MEDIUM,
                    description="连接错误",
                    suggestion="检查网络连接",
                    is_retryable=True,
                    auto_continue=True
                )
        
        # 默认分类为未知错误
        return ExceptionClassification(
            exception_type=ExceptionType.UNKNOWN_ERROR,
            severity=ExceptionSeverity.MEDIUM,
            description="未知错误类型",
            suggestion="检查具体错误信息",
            is_retryable=True,
            auto_continue=True
        )
    
    def classify_model_result(self, model_result) -> Dict[str, any]:
        """
        对模特处理结果进行分类
        
        Args:
            model_result: ModelResult对象
            
        Returns:
            Dict: 包含分类信息的字典
        """
        classification = {
            "exception_type": None,
            "severity": None,
            "description": None,
            "suggestion": None,
            "is_retryable": True,
            "auto_continue": True,
            "category": "正常"
        }
        
        if not model_result.success:
            # 处理失败的模特
            exception_info = self.classify_exception(model_result.error_message)
            classification.update({
                "exception_type": exception_info.exception_type.value,
                "severity": exception_info.severity.value,
                "description": exception_info.description,
                "suggestion": exception_info.suggestion,
                "is_retryable": exception_info.is_retryable,
                "auto_continue": exception_info.auto_continue,
                "category": "处理失败"
            })
        elif model_result.missing_count > 0:
            # 有缺失视频的情况
            missing_with_urls = getattr(model_result, 'missing_with_urls', [])
            
            if len(missing_with_urls) < model_result.missing_count:
                # 有缺失但没有链接的情况
                classification.update({
                    "exception_type": ExceptionType.LINK_ERROR.value,
                    "severity": ExceptionSeverity.MEDIUM.value,
                    "description": "在线标题正确但链接缺失/错误",
                    "suggestion": "需要更新链接或重新抓取页面",
                    "is_retryable": True,
                    "auto_continue": True,
                    "category": "链接缺失"
                })
            else:
                # 有链接的情况，认为是正常的数据缺失
                classification.update({
                    "exception_type": ExceptionType.DATA_MISSING.value,
                    "severity": ExceptionSeverity.LOW.value,
                    "description": "数据缺失（有链接）",
                    "suggestion": "正常情况，可以下载",
                    "is_retryable": True,
                    "auto_continue": True,
                    "category": "数据缺失"
                })
        
        return classification
    
    def should_auto_continue(self, error_message: str, error_type: Optional[str] = None) -> bool:
        """
        判断是否应该自动继续
        
        Args:
            error_message: 错误消息
            error_type: 错误类型
            
        Returns:
            bool: 是否自动继续
        """
        classification = self.classify_exception(error_message, error_type)
        return classification.auto_continue
    
    def get_retry_suggestion(self, error_message: str, error_type: Optional[str] = None) -> str:
        """
        获取重试建议
        
        Args:
            error_message: 错误消息
            error_type: 错误类型
            
        Returns:
            str: 重试建议
        """
        classification = self.classify_exception(error_message, error_type)
        return classification.suggestion


# 全局实例
_exception_classifier = None


def get_exception_classifier() -> ExceptionClassifier:
    """获取异常分类器实例（单例）"""
    global _exception_classifier
    if _exception_classifier is None:
        _exception_classifier = ExceptionClassifier()
    return _exception_classifier


def classify_exception(error_message: str, error_type: Optional[str] = None) -> ExceptionClassification:
    """分类异常（全局接口）"""
    classifier = get_exception_classifier()
    return classifier.classify_exception(error_message, error_type)


def should_auto_continue(error_message: str, error_type: Optional[str] = None) -> bool:
    """判断是否应该自动继续（全局接口）"""
    classifier = get_exception_classifier()
    return classifier.should_auto_continue(error_message, error_type)


if __name__ == "__main__":
    # 测试
    classifier = ExceptionClassifier()
    
    test_cases = [
        "Connection timeout after 30 seconds",
        "404 Not Found - page does not exist",
        "在线标题正确但链接缺失",
        "403 Forbidden - access denied",
        "Selenium WebDriver error",
        "Unknown error occurred"
    ]
    
    for error in test_cases:
        result = classifier.classify_exception(error)
        print(f"错误: {error}")
        print(f"类型: {result.exception_type.value}")
        print(f"严重: {result.severity.value}")
        print(f"描述: {result.description}")
        print(f"建议: {result.suggestion}")
        print(f"自动继续: {result.auto_continue}")
        print("-" * 50)