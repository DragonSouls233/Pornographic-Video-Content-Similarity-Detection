"""
增强版代理预检模块
提供全面的代理连接测试和诊断功能
"""

import socket
import time
import requests
import urllib.parse
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProxyTestResult:
    """代理测试结果数据类"""
    success: bool = False
    host: str = ""
    port: int = 0
    proxy_type: str = ""
    response_time: float = 0.0
    error_message: str = ""
    details: Dict = field(default_factory=dict)


@dataclass  
class ComprehensiveProxyCheck:
    """综合代理检查结果"""
    basic_connectivity: ProxyTestResult
    http_access: ProxyTestResult
    https_access: ProxyTestResult
    target_websites: List[ProxyTestResult] = field(default_factory=list)
    overall_success: bool = False
    recommendations: List[str] = field(default_factory=list)


class EnhancedProxyTester:
    """增强版代理测试器"""
    
    # 测试目标网站列表
    TEST_URLS = [
        "https://www.google.com",
        "https://www.github.com", 
        "https://httpbin.org/get",
        "https://api.ipify.org"
    ]
    
    def __init__(self, proxy_config: dict, timeout: int = 10):
        self.proxy_config = proxy_config
        self.timeout = timeout
        self.results = []
    
    def comprehensive_check(self) -> ComprehensiveProxyCheck:
        """执行全面的代理检查"""
        logger.info("🔍 开始全面代理检查...")
        
        # 1. 基础连接测试
        basic_result = self._test_basic_connectivity()
        
        # 2. HTTP访问测试
        http_result = self._test_http_access()
        
        # 3. HTTPS访问测试  
        https_result = self._test_https_access()
        
        # 4. 目标网站测试
        target_results = self._test_target_websites()
        
        # 5. 生成综合结果
        overall_success = all([
            basic_result.success,
            http_result.success or https_result.success,  # 至少一个协议成功
            len([r for r in target_results if r.success]) > 0  # 至少一个网站成功
        ])
        
        # 6. 生成建议
        recommendations = self._generate_recommendations(
            basic_result, http_result, https_result, target_results
        )
        
        return ComprehensiveProxyCheck(
            basic_connectivity=basic_result,
            http_access=http_result,
            https_access=https_result,
            target_websites=target_results,
            overall_success=overall_success,
            recommendations=recommendations
        )
    
    def _test_basic_connectivity(self) -> ProxyTestResult:
        """测试基础TCP连接"""
        logger.info("🔌 测试基础TCP连接...")
        
        host, port, proxy_type = self._extract_proxy_info()
        if not host or not port:
            return ProxyTestResult(
                success=False,
                error_message="代理配置不完整"
            )
        
        start_time = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            response_time = time.time() - start_time
            
            if result == 0:
                logger.info(f"✅ TCP连接成功: {host}:{port} ({response_time:.2f}s)")
                return ProxyTestResult(
                    success=True,
                    host=host,
                    port=port,
                    proxy_type=proxy_type,
                    response_time=response_time
                )
            else:
                logger.error(f"❌ TCP连接失败: {host}:{port} (错误码: {result})")
                return ProxyTestResult(
                    success=False,
                    host=host,
                    port=port,
                    proxy_type=proxy_type,
                    error_message=f"连接失败 (错误码: {result})"
                )
                
        except socket.timeout:
            response_time = time.time() - start_time
            logger.error(f"❌ TCP连接超时: {host}:{port}")
            return ProxyTestResult(
                success=False,
                host=host,
                port=port,
                proxy_type=proxy_type,
                error_message="连接超时",
                response_time=response_time
            )
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"❌ TCP连接异常: {e}")
            return ProxyTestResult(
                success=False,
                host=host,
                port=port,
                proxy_type=proxy_type,
                error_message=str(e),
                response_time=response_time
            )
    
    def _test_http_access(self) -> ProxyTestResult:
        """测试HTTP代理访问"""
        logger.info("🌐 测试HTTP代理访问...")
        
        proxies = self._build_proxy_dict()
        if not proxies or 'http' not in proxies:
            return ProxyTestResult(
                success=False,
                error_message="未配置HTTP代理"
            )
        
        try:
            start_time = time.time()
            response = requests.get(
                "http://httpbin.org/get",
                proxies=proxies,
                timeout=self.timeout,
                verify=False
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                logger.info(f"✅ HTTP代理访问成功 ({response_time:.2f}s)")
                return ProxyTestResult(
                    success=True,
                    response_time=response_time,
                    details={
                        'status_code': response.status_code,
                        'ip': response.json().get('origin', 'unknown')
                    }
                )
            else:
                logger.error(f"❌ HTTP代理访问失败: {response.status_code}")
                return ProxyTestResult(
                    success=False,
                    error_message=f"HTTP状态码: {response.status_code}"
                )
                
        except requests.exceptions.ProxyError as e:
            logger.error(f"❌ HTTP代理错误: {e}")
            return ProxyTestResult(
                success=False,
                error_message=f"代理错误: {str(e)[:100]}"
            )
        except requests.exceptions.Timeout:
            logger.error("❌ HTTP代理超时")
            return ProxyTestResult(
                success=False,
                error_message="请求超时"
            )
        except Exception as e:
            logger.error(f"❌ HTTP代理异常: {e}")
            return ProxyTestResult(
                success=False,
                error_message=str(e)
            )
    
    def _test_https_access(self) -> ProxyTestResult:
        """测试HTTPS代理访问"""
        logger.info("🔒 测试HTTPS代理访问...")
        
        proxies = self._build_proxy_dict()
        if not proxies:
            return ProxyTestResult(
                success=False,
                error_message="未配置代理"
            )
        
        try:
            start_time = time.time()
            response = requests.get(
                "https://httpbin.org/get",
                proxies=proxies,
                timeout=self.timeout,
                verify=False
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                logger.info(f"✅ HTTPS代理访问成功 ({response_time:.2f}s)")
                return ProxyTestResult(
                    success=True,
                    response_time=response_time,
                    details={
                        'status_code': response.status_code,
                        'ip': response.json().get('origin', 'unknown')
                    }
                )
            else:
                logger.error(f"❌ HTTPS代理访问失败: {response.status_code}")
                return ProxyTestResult(
                    success=False,
                    error_message=f"HTTPS状态码: {response.status_code}"
                )
                
        except requests.exceptions.ProxyError as e:
            logger.error(f"❌ HTTPS代理错误: {e}")
            return ProxyTestResult(
                success=False,
                error_message=f"代理错误: {str(e)[:100]}"
            )
        except requests.exceptions.Timeout:
            logger.error("❌ HTTPS代理超时")
            return ProxyTestResult(
                success=False,
                error_message="请求超时"
            )
        except Exception as e:
            logger.error(f"❌ HTTPS代理异常: {e}")
            return ProxyTestResult(
                success=False,
                error_message=str(e)
            )
    
    def _test_target_websites(self) -> List[ProxyTestResult]:
        """测试目标网站访问"""
        logger.info("🎯 测试目标网站访问...")
        
        results = []
        proxies = self._build_proxy_dict()
        
        if not proxies:
            # 如果没有代理配置，返回空结果
            return results
        
        for url in self.TEST_URLS:
            try:
                logger.info(f"  测试: {url}")
                start_time = time.time()
                response = requests.get(
                    url,
                    proxies=proxies,
                    timeout=self.timeout,
                    verify=False
                )
                response_time = time.time() - start_time
                
                result = ProxyTestResult(
                    success=response.status_code == 200,
                    host=urllib.parse.urlparse(url).netloc,
                    response_time=response_time,
                    details={'status_code': response.status_code}
                )
                
                if result.success:
                    logger.info(f"    ✅ 成功 ({response_time:.2f}s)")
                else:
                    logger.warning(f"    ⚠️  失败 (状态码: {response.status_code})")
                    result.error_message = f"状态码: {response.status_code}"
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"    ❌ 异常: {str(e)[:50]}")
                results.append(ProxyTestResult(
                    success=False,
                    host=urllib.parse.urlparse(url).netloc,
                    error_message=str(e)[:100]
                ))
        
        return results
    
    def _extract_proxy_info(self) -> Tuple[str, int, str]:
        """提取代理配置信息（兼容传入整份config或仅proxy段）"""

        # 兼容两种入参：
        # 1) 传入整份config：{'network': {'proxy': {...}}} 或 {'proxy': {...}}
        # 2) 直接传入proxy段：{'enabled': True, 'host': '127.0.0.1', 'port': '10808', ...}
        def _get_proxy_section(cfg: dict) -> dict:
            if not isinstance(cfg, dict):
                return {}

            # 如果本身就像proxy段（含host/port/http/https/type任一），直接使用
            if any(k in cfg for k in ('host', 'port', 'http', 'https', 'type')):
                return cfg

            # 否则尝试从整份config里取
            proxy_section = cfg.get('network', {}).get('proxy', {})
            if proxy_section:
                return proxy_section
            proxy_section = cfg.get('proxy', {})
            if proxy_section:
                return proxy_section

            return {}

        proxy_section = _get_proxy_section(self.proxy_config)

        host = proxy_section.get('host', '')
        port = proxy_section.get('port', '')
        proxy_type = proxy_section.get('type', '') or 'http'

        # 从URL中解析（如果host/port为空）
        if not host or not port:
            http_proxy = proxy_section.get('http', '') or proxy_section.get('https', '')
            if http_proxy:
                parsed = urllib.parse.urlparse(http_proxy)
                host = parsed.hostname or host
                port = parsed.port or port
                if parsed.scheme:
                    proxy_type = parsed.scheme

        try:
            port = int(port) if port else 0
        except (ValueError, TypeError):
            port = 0

        return host, port, proxy_type
    
    def _build_proxy_dict(self) -> Optional[Dict[str, str]]:
        """构建requests使用的代理字典"""
        host, port, proxy_type = self._extract_proxy_info()
        
        if not host or not port:
            return None
        
        proxy_url = f"{proxy_type}://{host}:{port}"
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def _generate_recommendations(self, basic: ProxyTestResult, http: ProxyTestResult, 
                                https: ProxyTestResult, targets: List[ProxyTestResult]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基础连接问题
        if not basic.success:
            recommendations.append("❌ 无法建立TCP连接，请检查:")
            recommendations.append("  • 代理服务是否正在运行")
            recommendations.append("  • 主机地址和端口是否正确")
            recommendations.append("  • 防火墙是否阻止连接")
            return recommendations
        
        # 协议支持问题
        if not http.success and not https.success:
            recommendations.append("❌ 代理不支持HTTP/HTTPS协议，请检查:")
            recommendations.append("  • 代理类型配置是否正确")
            recommendations.append("  • 代理是否支持所需的协议")
        
        # 目标网站访问问题
        successful_targets = len([t for t in targets if t.success])
        if successful_targets == 0:
            recommendations.append("❌ 无法访问目标网站，请检查:")
            recommendations.append("  • 代理是否能访问外网")
            recommendations.append("  • 目标网站是否被代理服务器屏蔽")
        elif successful_targets < len(targets):
            recommendations.append("⚠️  部分网站无法访问，可能是:")
            recommendations.append("  • 网站地区限制")
            recommendations.append("  • 代理服务器的访问策略限制")
        
        # 性能建议
        avg_response_time = sum([t.response_time for t in targets if t.success]) / max(successful_targets, 1)
        if avg_response_time > 5.0:
            recommendations.append("⚠️  代理响应较慢，建议:")
            recommendations.append("  • 选择延迟更低的代理服务器")
            recommendations.append("  • 检查网络带宽")
        
        if not recommendations:
            recommendations.append("✅ 代理配置良好，可以正常使用")
        
        return recommendations


def print_comprehensive_report(check_result: ComprehensiveProxyCheck):
    """打印综合检查报告（Windows控制台不支持emoji时自动降级输出）"""
    import sys

    def safe_print(text: str = "", end: str = "\n"):
        try:
            print(text, end=end)
        except UnicodeEncodeError:
            enc = getattr(sys.stdout, 'encoding', None) or 'utf-8'
            # 用replace避免崩溃（emoji会被替换成?）
            safe_text = str(text).encode(enc, errors='replace').decode(enc, errors='replace')
            print(safe_text, end=end)

    safe_print("\n" + "=" * 80)
    safe_print("🔍 代理连接综合检查报告")
    safe_print("=" * 80)

    # 总体状态
    status_icon = "✅" if check_result.overall_success else "❌"
    safe_print(f"\n总体状态: {status_icon} {'通过' if check_result.overall_success else '失败'}")

    # 基础连接
    basic = check_result.basic_connectivity
    icon = "✅" if basic.success else "❌"
    safe_print(f"\n🔌 基础TCP连接: {icon}")
    safe_print(f"  地址: {basic.host}:{basic.port} ({basic.proxy_type})")
    if basic.success:
        safe_print(f"  响应时间: {basic.response_time:.2f}秒")
    else:
        safe_print(f"  错误: {basic.error_message}")

    # HTTP访问
    http = check_result.http_access
    icon = "✅" if http.success else "❌"
    safe_print(f"\n🌐 HTTP访问: {icon}")
    if http.success:
        safe_print(f"  响应时间: {http.response_time:.2f}秒")
        ip = http.details.get('ip', 'unknown')
        safe_print(f"  出口IP: {ip}")
    else:
        safe_print(f"  错误: {http.error_message}")

    # HTTPS访问
    https = check_result.https_access
    icon = "✅" if https.success else "❌"
    safe_print(f"\n🔒 HTTPS访问: {icon}")
    if https.success:
        safe_print(f"  响应时间: {https.response_time:.2f}秒")
        ip = https.details.get('ip', 'unknown')
        safe_print(f"  出口IP: {ip}")
    else:
        safe_print(f"  错误: {https.error_message}")

    # 目标网站
    safe_print(f"\n🎯 目标网站测试:")
    for result in check_result.target_websites:
        icon = "✅" if result.success else "❌"
        status = "成功" if result.success else "失败"
        safe_print(f"  {icon} {result.host}: {status}", end="")
        if result.success:
            safe_print(f" ({result.response_time:.2f}s)")
        else:
            safe_print(f" - {result.error_message}")

    # 建议
    if check_result.recommendations:
        safe_print(f"\n💡 改进建议:")
        for recommendation in check_result.recommendations:
            safe_print(f"  {recommendation}")

    safe_print("\n" + "=" * 80)



# 便捷函数
def quick_proxy_check(proxy_config: dict) -> bool:
    """
    快速代理检查
    
    Args:
        proxy_config: 代理配置字典
        
    Returns:
        bool: 代理是否可用
    """
    tester = EnhancedProxyTester(proxy_config)
    result = tester.comprehensive_check()
    print_comprehensive_report(result)
    return result.overall_success


if __name__ == "__main__":
    # 命令行测试
    import sys
    import yaml
    
    # 从配置文件加载代理配置
    config_path = "config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        success = quick_proxy_check(config)
        sys.exit(0 if success else 1)
        
    except FileNotFoundError:
        print(f"❌ 配置文件不存在: {config_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)