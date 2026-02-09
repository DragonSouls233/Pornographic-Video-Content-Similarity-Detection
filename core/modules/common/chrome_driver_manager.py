"""
ChromeDriver自动检测和管理模块
自动检测Chrome版本并下载匹配的ChromeDriver
"""

import os
import re
import sys
import json
import platform
import subprocess
import urllib.request
from typing import Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ChromeVersionDetector:
    """Chrome浏览器版本检测器"""
    
    @staticmethod
    def detect_chrome_version() -> Optional[str]:
        """
        检测系统中安装的Chrome版本
        
        Returns:
            str: Chrome版本号，如 "120.0.6099.109"
            None: 未检测到Chrome
        """
        system = platform.system()
        
        try:
            if system == "Windows":
                return ChromeVersionDetector._detect_windows_chrome()
            elif system == "Darwin":  # macOS
                return ChromeVersionDetector._detect_mac_chrome()
            elif system == "Linux":
                return ChromeVersionDetector._detect_linux_chrome()
            else:
                logger.warning(f"不支持的操作系统: {system}")
                return None
                
        except Exception as e:
            logger.error(f"检测Chrome版本失败: {e}")
            return None
    
    @staticmethod
    def _detect_windows_chrome() -> Optional[str]:
        """Windows系统Chrome版本检测"""
        # 常见Chrome安装路径
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
            r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe",
            r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"
        ]
        
        for chrome_path in chrome_paths:
            # 展开环境变量
            expanded_path = os.path.expandvars(chrome_path)
            if os.path.exists(expanded_path):
                try:
                    # 获取文件版本信息
                    version = ChromeVersionDetector._get_file_version_windows(expanded_path)
                    if version:
                        logger.info(f"检测到Windows Chrome版本: {version}")
                        return version
                except Exception as e:
                    logger.debug(f"获取{expanded_path}版本信息失败: {e}")
                    continue
        
        # 尝试通过注册表检测
        try:
            version = ChromeVersionDetector._get_chrome_version_from_registry()
            if version:
                logger.info(f"通过注册表检测到Chrome版本: {version}")
                return version
        except Exception as e:
            logger.debug(f"注册表检测失败: {e}")
        
        # 尝试命令行方式
        try:
            result = subprocess.run(
                ['chrome', '--version'], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version_match = re.search(r'Google Chrome (\d+\.\d+\.\d+\.\d+)', result.stdout)
                if version_match:
                    version = version_match.group(1)
                    logger.info(f"通过命令行检测到Chrome版本: {version}")
                    return version
        except Exception as e:
            logger.debug(f"命令行检测失败: {e}")
        
        return None
    
    @staticmethod
    def _detect_mac_chrome() -> Optional[str]:
        """macOS系统Chrome版本检测"""
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
        
        for chrome_path in chrome_paths:
            expanded_path = os.path.expanduser(chrome_path)
            if os.path.exists(expanded_path):
                try:
                    result = subprocess.run(
                        [expanded_path, '--version'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        version_match = re.search(r'Google Chrome (\d+\.\d+\.\d+\.\d+)', result.stdout)
                        if version_match:
                            version = version_match.group(1)
                            logger.info(f"检测到macOS Chrome版本: {version}")
                            return version
                except Exception as e:
                    logger.debug(f"检测{expanded_path}版本失败: {e}")
                    continue
        
        return None
    
    @staticmethod
    def _detect_linux_chrome() -> Optional[str]:
        """Linux系统Chrome版本检测"""
        chrome_commands = [
            ['google-chrome', '--version'],
            ['google-chrome-stable', '--version'],
            ['chromium-browser', '--version'],
            ['chromium', '--version']
        ]
        
        for cmd in chrome_commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    # 支持多种版本输出格式
                    patterns = [
                        r'Google Chrome (\d+\.\d+\.\d+\.\d+)',
                        r'Chromium (\d+\.\d+\.\d+\.\d+)'
                    ]
                    
                    for pattern in patterns:
                        version_match = re.search(pattern, result.stdout)
                        if version_match:
                            version = version_match.group(1)
                            logger.info(f"检测到Linux Chrome/Chromium版本: {version}")
                            return version
            except Exception as e:
                logger.debug(f"执行{cmd}失败: {e}")
                continue
        
        return None
    
    @staticmethod
    def _get_file_version_windows(filepath: str) -> Optional[str]:
        """获取Windows文件版本信息"""
        try:
            import win32api
            info = win32api.GetFileVersionInfo(filepath, "\\")
            ms = info['FileVersionMS']
            ls = info['FileVersionLS']
            version = f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
            return version
        except ImportError:
            # 如果没有pywin32，尝试其他方法
            logger.debug("pywin32未安装，使用备用方法")
            return ChromeVersionDetector._get_version_via_wmic(filepath)
        except Exception as e:
            logger.debug(f"获取文件版本失败: {e}")
            return None
    
    @staticmethod
    def _get_version_via_wmic(filepath: str) -> Optional[str]:
        """通过WMIC获取文件版本"""
        try:
            cmd = ['wmic', 'datafile', 'where', f'name="{filepath}"', 'get', 'Version', '/value']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version_match = re.search(r'Version=(.+)', result.stdout)
                if version_match:
                    return version_match.group(1).strip()
        except Exception:
            pass
        return None
    
    @staticmethod
    def _get_chrome_version_from_registry() -> Optional[str]:
        """从Windows注册表获取Chrome版本"""
        try:
            import winreg
            # Chrome主版本在注册表中的位置
            reg_paths = [
                (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Google\Chrome\BLBeacon"),
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
            ]
            
            for hkey, subkey in reg_paths:
                try:
                    with winreg.OpenKey(hkey, subkey) as key:
                        version, _ = winreg.QueryValueEx(key, "version")
                        if version:
                            return version
                except (FileNotFoundError, OSError):
                    continue
                    
        except ImportError:
            logger.debug("无法访问注册表")
        except Exception as e:
            logger.debug(f"注册表查询失败: {e}")
        
        return None


class ChromeDriverManager:
    """ChromeDriver管理器"""
    
    # ChromeDriver下载镜像源
    DRIVER_MIRRORS = [
        "https://chromedriver.storage.googleapis.com",  # 官方源
        "https://npmmirror.com/mirrors/chromedriver",   # 阿里云镜像
        "https://cdn.npmmirror.com/binaries/chromedriver"  # npmmirror镜像
    ]
    
    def __init__(self, driver_dir: str = "drivers"):
        self.driver_dir = Path(driver_dir)
        self.driver_dir.mkdir(exist_ok=True)
        self.current_system = platform.system().lower()
    
    def get_driver_path(self) -> Path:
        """获取ChromeDriver路径"""
        if self.current_system == "windows":
            return self.driver_dir / "chromedriver.exe"
        else:
            return self.driver_dir / "chromedriver"
    
    def is_driver_installed(self) -> bool:
        """检查ChromeDriver是否已安装"""
        driver_path = self.get_driver_path()
        return driver_path.exists() and os.access(driver_path, os.X_OK)
    
    def get_installed_driver_version(self) -> Optional[str]:
        """获取已安装的ChromeDriver版本"""
        if not self.is_driver_installed():
            return None
        
        try:
            driver_path = self.get_driver_path()
            result = subprocess.run(
                [str(driver_path), '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version_match = re.search(r'ChromeDriver (\d+\.\d+\.\d+\.\d+)', result.stdout)
                if version_match:
                    return version_match.group(1)
        except Exception as e:
            logger.debug(f"获取ChromeDriver版本失败: {e}")
        
        return None
    
    def download_matching_driver(self, chrome_version: str) -> bool:
        """
        下载与Chrome版本匹配的ChromeDriver
        
        Args:
            chrome_version: Chrome版本号
            
        Returns:
            bool: 下载是否成功
        """
        try:
            # 提取主版本号
            major_version = chrome_version.split('.')[0]
            logger.info(f"正在为Chrome {chrome_version} (主版本 {major_version}) 下载匹配的ChromeDriver...")
            
            # 构造下载URL
            download_url = self._construct_download_url(major_version)
            if not download_url:
                logger.error("无法构造有效的下载URL")
                return False
            
            # 下载文件
            driver_path = self.get_driver_path()
            temp_path = driver_path.with_suffix('.tmp')
            
            # 如果临时文件已存在，先删除
            if temp_path.exists():
                temp_path.unlink()
            
            logger.info(f"正在下载: {download_url}")
            urllib.request.urlretrieve(download_url, temp_path)
            
            # 解压文件（如果是zip格式）
            if temp_path.suffix.lower() == '.zip':
                self._extract_zip(temp_path, driver_path)
                temp_path.unlink()
            else:
                # 直接重命名
                temp_path.rename(driver_path)
            
            # 设置执行权限（非Windows系统）
            if self.current_system != "windows":
                driver_path.chmod(0o755)
            
            logger.info(f"ChromeDriver下载完成: {driver_path}")
            return True
            
        except Exception as e:
            logger.error(f"下载ChromeDriver失败: {e}")
            return False
    
    def _construct_download_url(self, major_version: str) -> Optional[str]:
        """构造ChromeDriver下载URL"""
        # 获取最新版本号
        version = self._get_latest_driver_version(major_version)
        if not version:
            return None
        
        # 确定平台后缀
        platform_suffix = self._get_platform_suffix()
        if not platform_suffix:
            return None
        
        filename = f"chromedriver_{platform_suffix}.zip"
        
        # 尝试不同镜像源
        for mirror in self.DRIVER_MIRRORS:
            url = f"{mirror}/{version}/{filename}"
            if self._test_url_accessible(url):
                logger.info(f"使用镜像源: {mirror}")
                return url
        
        return None
    
    def _get_latest_driver_version(self, major_version: str) -> Optional[str]:
        """获取指定主版本的最新ChromeDriver版本"""
        version_url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
        
        try:
            with urllib.request.urlopen(version_url, timeout=10) as response:
                version = response.read().decode().strip()
                logger.info(f"找到ChromeDriver版本: {version}")
                return version
        except Exception as e:
            logger.debug(f"获取版本信息失败: {e}")
            # 尝试获取最新版本
            return self._get_latest_stable_version()
    
    def _get_latest_stable_version(self) -> Optional[str]:
        """获取最新的稳定版本"""
        try:
            version_url = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"
            with urllib.request.urlopen(version_url, timeout=10) as response:
                version = response.read().decode().strip()
                logger.info(f"使用最新稳定版本: {version}")
                return version
        except Exception as e:
            logger.error(f"无法获取ChromeDriver版本: {e}")
            return None
    
    def _get_platform_suffix(self) -> Optional[str]:
        """获取平台对应的文件后缀"""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "windows":
            return "win32" if machine == "amd64" else "win32"
        elif system == "darwin":
            if "arm" in machine:
                return "mac_arm64"
            else:
                return "mac64"
        elif system == "linux":
            if "arm" in machine:
                return "linux_arm64"
            else:
                return "linux64"
        else:
            logger.error(f"不支持的平台: {system}")
            return None
    
    def _test_url_accessible(self, url: str) -> bool:
        """测试URL是否可访问"""
        try:
            request = urllib.request.Request(url, method='HEAD')
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False
    
    def _extract_zip(self, zip_path: Path, extract_to: Path):
        """解压zip文件"""
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 查找chromedriver文件
            for member in zip_ref.namelist():
                if 'chromedriver' in member and not member.endswith('/'):
                    # 提取文件
                    zip_ref.extract(member, self.driver_dir)
                    extracted_path = self.driver_dir / member
                    # 重命名为目标文件名
                    if extracted_path != extract_to:
                        extracted_path.rename(extract_to)
                    break


def check_and_setup_chromedriver(config: dict = None) -> Tuple[bool, str]:
    """
    检查并设置ChromeDriver
    
    Args:
        config: 配置字典（可选）
        
    Returns:
        Tuple[bool, str]: (是否成功, 信息)
    """
    logger.info("🔍 开始ChromeDriver检查...")
    
    # 检测Chrome版本
    chrome_version = ChromeVersionDetector.detect_chrome_version()
    if not chrome_version:
        return False, "未检测到Chrome浏览器，请确保已安装Chrome"
    
    logger.info(f"✅ 检测到Chrome版本: {chrome_version}")
    
    # 初始化ChromeDriver管理器
    driver_manager = ChromeDriverManager("drivers")
    
    # 检查已安装的ChromeDriver
    installed_version = driver_manager.get_installed_driver_version()
    if installed_version:
        logger.info(f"✅ 已安装ChromeDriver版本: {installed_version}")
        
        # 检查版本是否匹配
        chrome_major = chrome_version.split('.')[0]
        driver_major = installed_version.split('.')[0]
        
        if chrome_major == driver_major:
            logger.info("✅ Chrome和ChromeDriver版本匹配")
            return True, f"ChromeDriver {installed_version} 已就绪"
        else:
            logger.warning(f"⚠️  版本不匹配 - Chrome: {chrome_major}, ChromeDriver: {driver_major}")
    
    # 需要下载匹配的ChromeDriver
    logger.info("📥 正在下载匹配的ChromeDriver...")
    if driver_manager.download_matching_driver(chrome_version):
        new_version = driver_manager.get_installed_driver_version()
        return True, f"ChromeDriver {new_version} 下载完成并已就绪"
    else:
        return False, "ChromeDriver下载失败"


# 便捷函数
def quick_check() -> bool:
    """快速检查ChromeDriver状态"""
    success, message = check_and_setup_chromedriver()
    logger.info(message)
    return success


if __name__ == "__main__":
    # 命令行测试
    import logging
    logging.basicConfig(level=logging.INFO)
    
    success, message = check_and_setup_chromedriver()
    print(f"\n{'✅' if success else '❌'} {message}")
    sys.exit(0 if success else 1)