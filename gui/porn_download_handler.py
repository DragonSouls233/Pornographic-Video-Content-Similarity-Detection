# -*- coding: utf-8 -*-
"""
PORN下载处理器 - 独立的下载管理模块
提供详细的错误处理和进度跟踪
"""
import requests
import logging
from typing import Dict, List, Tuple, Optional, Callable

logger = logging.getLogger(__name__)


class PornDownloadHandler:
    """PORN下载处理器，提供详细的错误处理和反馈"""
    
    def __init__(self, progress_callback: Optional[Callable] = None, 
                 log_callback: Optional[Callable] = None):
        """
        初始化下载处理器
        
        Args:
            progress_callback: 进度更新回调函数
            log_callback: 日志记录回调函数
        """
        self.progress_callback = progress_callback
        self.log_callback = log_callback
    
    def log(self, message: str):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message)
        else:
            logger.info(message)
    
    def execute_download(self, downloader, i: int, total_count: int, 
                        model: str, title: str, url: str, 
                        save_dir: Optional[str] = None) -> Dict:
        """
        执行单个视频下载，并提供详细的错误处理
        
        Returns:
            {
                'success': bool,
                'message': str,
                'downloaded_count': int,
                'file_path': str or None
            }
        """
        result = {
            'success': False,
            'message': '',
            'file_path': None
        }
        
        try:
            # 检查URL是否有效
            if not url or not url.strip():
                result['message'] = f"⚠️ 跳过: URL无效 - {title[:50]}"
                self.log(result['message'])
                return result
            
            # 更新进度
            if self.progress_callback:
                self.progress_callback({
                    'status': 'starting',
                    'current': i,
                    'total': total_count,
                    'title': title
                })
            
            self.log(f"开始下载 ({i}/{total_count}): {title[:50]}...")
            
            # 执行下载
            try:
                download_result = downloader.download_video(url, save_dir)
            except requests.exceptions.ConnectionError as e:
                result['message'] = f"❌ 下载失败 ({i}/{total_count}): {title[:50]}...\n原因: 网络连接错误\n解决: 请检查互联网连接"
                self.log(result['message'])
                return result
            except requests.exceptions.Timeout as e:
                result['message'] = f"❌ 下载失败 ({i}/{total_count}): {title[:50]}...\n原因: 请求超时\n解决: 请检查代理配置或网络速度"
                self.log(result['message'])
                return result
            except requests.exceptions.ProxyError as e:
                result['message'] = f"❌ 下载失败 ({i}/{total_count}): {title[:50]}...\n原因: 代理错误\n解决: 请检查代理地址和端口配置"
                self.log(result['message'])
                return result
            except ValueError as e:
                error_str = str(e).lower()
                if 'url' in error_str or 'protocol' in error_str:
                    result['message'] = f"❌ 下载失败 ({i}/{total_count}): {title[:50]}...\n原因: URL格式错误\n解决: 请检查URL是否有效"
                else:
                    result['message'] = f"❌ 下载失败 ({i}/{total_count}): {title[:50]}...\n原因: {error_str}\n解决: 请检查输入参数"
                self.log(result['message'])
                return result
            except Exception as e:
                error_str = str(e).lower()
                if '404' in error_str or 'not found' in error_str:
                    result['message'] = f"❌ 下载失败 ({i}/{total_count}): {title[:50]}...\n原因: 页面不存在 (404)\n解决: 模特页面可能已删除或URL过期，请更新URL"
                elif 'permission' in error_str or 'access' in error_str or 'forbidden' in error_str:
                    result['message'] = f"❌ 下载失败 ({i}/{total_count}): {title[:50]}...\n原因: 无权限或禁止访问\n解决: 此内容可能受地理位置限制或需要会员权限"
                elif 'proxy' in error_str or 'socks' in error_str:
                    result['message'] = f"❌ 下载失败 ({i}/{total_count}): {title[:50]}...\n原因: 代理配置错误\n解决: 请检查配置文件中的代理设置（主机、端口、认证）"
                elif 'ssl' in error_str or 'certificate' in error_str:
                    result['message'] = f"❌ 下载失败 ({i}/{total_count}): {title[:50]}...\n原因: SSL证书验证失败\n解决: 请更新CA证书或检查系统时间"
                else:
                    result['message'] = f"❌ 下载失败 ({i}/{total_count}): {title[:50]}...\n原因: {error_str[:80]}"
                self.log(result['message'])
                return result
            
            # 处理下载结果
            if download_result and download_result.get('success'):
                result['success'] = True
                result['file_path'] = download_result.get('file_path', 'N/A')
                result['message'] = f"✅ 下载成功: {title[:50]}...\n   保存路径: {result['file_path']}"
                self.log(result['message'])
                
                if self.progress_callback:
                    self.progress_callback({
                        'status': 'finished',
                        'current': i,
                        'total': total_count,
                        'title': title,
                        'file_path': result['file_path']
                    })
            else:
                error_msg = download_result.get('error', download_result.get('message', '未知错误'))
                result['message'] = f"❌ 下载失败: {title[:50]}...\n原因: {error_msg}"
                self.log(result['message'])
            
            return result
        
        except Exception as e:
            result['message'] = f"❌ 下载异常: {title[:50]}...\n原因: {str(e)[:100]}"
            self.log(result['message'])
            logger.exception(f"下载异常详情: {e}")
            return result


def create_error_tooltip_text(error_type: str) -> str:
    """
    为常见错误生成帮助文本
    """
    error_tips = {
        'network': """
        网络连接错误
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ✓ 检查互联网连接
        ✓ 检查防火墙设置
        ✓ 重启路由器/网络设备
        ✓ 尝试使用代理
        """,
        'proxy': """
        代理配置错误
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ✓ 检查代理地址和端口
        ✓ 验证代理认证信息
        ✓ 检查SOCKS5/HTTP协议设置
        ✓ 测试代理连接
        """,
        'url': """
        URL错误或页面不存在
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ✓ 验证URL格式正确
        ✓ 检查URL是否过期
        ✓ 确认模特页面仍然存在
        ✓ 使用浏览器测试该URL
        """,
        'permission': """
        权限不足或禁止访问
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ✓ 此内容可能受地理位置限制
        ✓ 可能需要会员身份
        ✓ 检查Cookie/认证信息
        ✓ 尝试使用不同地区的代理
        """
    }
    return error_tips.get(error_type, "未知错误，请检查日志")
