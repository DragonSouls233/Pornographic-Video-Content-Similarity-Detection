"""
Chrome 版本检测模块 - 自动检测本地 Chrome 版本并匹配合适的 ChromeDriver
"""

import os
import re
import subprocess
import logging
import platform
from typing import Optional, Tuple
from pathlib import Path

# 导入 webdriver_manager 相关组件
try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False


class ChromeVersionManager:
    """Chrome 版本管理器 - 检测本地 Chrome 版本并匹配合适的 ChromeDriver"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.system = platform.system()
        
    @staticmethod
    def get_local_chrome_version() -> Optional[str]:
        """
        获取本地安装的 Chrome 浏览器版本
        
        Returns:
            Chrome 版本号 (如 "120.0.6099.130")，如果未找到返回 None
        """
        system = platform.system()
        
        try:
            if system == "Windows":
                return ChromeVersionManager._get_chrome_version_windows()
            elif system == "Darwin":  # macOS
                return ChromeVersionManager._get_chrome_version_macos()
            else:  # Linux
                return ChromeVersionManager._get_chrome_version_linux()
        except Exception as e:
            logging.getLogger(__name__).warning(f"获取 Chrome 版本失败: {e}")
            return None
    
    @staticmethod
    def _get_chrome_version_windows() -> Optional[str]:
        """Windows 系统获取 Chrome 版本"""
        try:
            # 方法1: 通过注册表查询
            import winreg
            
            # 尝试多个可能的注册表路径
            reg_paths = [
                (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Google\Chrome\BLBeacon"),
                (winreg.HKEY_CURRENT_USER, r"Software\Chromium\BLBeacon"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Chromium\BLBeacon"),
            ]
            
            for hkey, path in reg_paths:
                try:
                    with winreg.OpenKey(hkey, path) as key:
                        version, _ = winreg.QueryValueEx(key, "version")
                        if version:
                            return version
                except (WindowsError, OSError):
                    continue
            
            # 方法2: 通过 Chrome 可执行文件获取版本
            chrome_paths = [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            ]
            
            for chrome_path in chrome_paths:
                if os.path.exists(chrome_path):
                    # 使用 PowerShell 获取文件版本
                    try:
                        result = subprocess.run(
                            ["powershell", "-Command", 
                             f"(Get-ItemProperty '{chrome_path}').VersionInfo.FileVersion"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if result.returncode == 0:
                            version = result.stdout.strip()
                            if version:
                                return version
                    except Exception:
                        pass
                    
                    # 备用方法：使用 wmic
                    try:
                        result = subprocess.run(
                            ["wmic", "datafile", "where", f"name='{chrome_path.replace('\\', '\\\\')}'", 
                             "get", "Version", "/value"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if result.returncode == 0:
                            match = re.search(r'Version=(\S+)', result.stdout)
                            if match:
                                return match.group(1)
                    except Exception:
                        pass
            
            # 方法3: 尝试运行 chrome --version
            try:
                result = subprocess.run(
                    ["chrome", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
                    if match:
                        return match.group(1)
            except Exception:
                pass
                
        except Exception as e:
            logging.getLogger(__name__).debug(f"Windows Chrome 版本检测失败: {e}")
        
        return None
    
    @staticmethod
    def _get_chrome_version_macos() -> Optional[str]:
        """macOS 系统获取 Chrome 版本"""
        try:
            # 方法1: 通过 Info.plist 读取
            plist_paths = [
                "/Applications/Google Chrome.app/Contents/Info.plist",
                "/Applications/Chromium.app/Contents/Info.plist",
                os.path.expanduser("~/Applications/Google Chrome.app/Contents/Info.plist"),
            ]
            
            for plist_path in plist_paths:
                if os.path.exists(plist_path):
                    try:
                        result = subprocess.run(
                            ["defaults", "read", plist_path.replace("/Contents/Info.plist", ""), "CFBundleShortVersionString"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if result.returncode == 0:
                            version = result.stdout.strip()
                            if version:
                                return version
                    except Exception:
                        pass
            
            # 方法2: 运行 chrome --version
            try:
                result = subprocess.run(
                    ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
                    if match:
                        return match.group(1)
            except Exception:
                pass
                
        except Exception as e:
            logging.getLogger(__name__).debug(f"macOS Chrome 版本检测失败: {e}")
        
        return None
    
    @staticmethod
    def _get_chrome_version_linux() -> Optional[str]:
        """Linux 系统获取 Chrome 版本"""
        try:
            # 尝试多个可能的 Chrome 可执行文件
            chrome_commands = [
                ["google-chrome", "--version"],
                ["google-chrome-stable", "--version"],
                ["chromium", "--version"],
                ["chromium-browser", "--version"],
                ["/usr/bin/google-chrome", "--version"],
                ["/usr/bin/chromium", "--version"],
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
                        match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
                        if match:
                            return match.group(1)
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
                    
        except Exception as e:
            logging.getLogger(__name__).debug(f"Linux Chrome 版本检测失败: {e}")
        
        return None
    
    @staticmethod
    def get_major_version(version: str) -> Optional[int]:
        """
        从完整版本号中提取主版本号
        
        Args:
            version: 完整版本号 (如 "120.0.6099.130")
            
        Returns:
            主版本号 (如 120)，如果解析失败返回 None
        """
        if not version:
            return None
        
        match = re.match(r'(\d+)', version)
        if match:
            return int(match.group(1))
        return None
    
    def get_matching_chromedriver(self, chrome_version: Optional[str] = None) -> str:
        """
        获取匹配 Chrome 版本的 ChromeDriver 路径
        
        Args:
            chrome_version: Chrome 版本号，如果为 None 则自动检测
            
        Returns:
            ChromeDriver 可执行文件路径
        """
        if not WEBDRIVER_MANAGER_AVAILABLE:
            raise ImportError("webdriver-manager 未安装，无法自动下载 ChromeDriver")
        
        # 如果未提供版本，自动检测
        if not chrome_version:
            chrome_version = self.get_local_chrome_version()
        
        if chrome_version:
            major_version = self.get_major_version(chrome_version)
            self.logger.info(f"检测到 Chrome 版本: {chrome_version} (主版本: {major_version})")
            
            try:
                # 使用 webdriver-manager 下载匹配版本的 ChromeDriver
                driver_path = ChromeDriverManager(
                    driver_version=chrome_version if major_version else None
                ).install()
                self.logger.info(f"✅ ChromeDriver 已准备: {driver_path}")
                return driver_path
            except Exception as e:
                self.logger.warning(f"下载匹配版本的 ChromeDriver 失败: {e}")
                self.logger.info("尝试下载最新版本的 ChromeDriver...")
        else:
            self.logger.warning("未检测到 Chrome 版本，将下载最新 ChromeDriver")
        
        # 回退到最新版本
        try:
            driver_path = ChromeDriverManager().install()
            self.logger.info(f"✅ 使用最新 ChromeDriver: {driver_path}")
            return driver_path
        except Exception as e:
            self.logger.error(f"下载 ChromeDriver 失败: {e}")
            raise
    
    def verify_chromedriver_compatibility(self, chromedriver_path: str, 
                                          chrome_version: Optional[str] = None) -> Tuple[bool, str]:
        """
        验证 ChromeDriver 与 Chrome 版本的兼容性
        
        Args:
            chromedriver_path: ChromeDriver 路径
            chrome_version: Chrome 版本号
            
        Returns:
            (是否兼容, 详细信息)
        """
        if not chrome_version:
            chrome_version = self.get_local_chrome_version()
        
        if not chrome_version:
            return False, "无法检测 Chrome 版本"
        
        chrome_major = self.get_major_version(chrome_version)
        
        # 尝试获取 ChromeDriver 版本
        try:
            result = subprocess.run(
                [chromedriver_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                driver_version_match = re.search(r'(\d+)\.', result.stdout)
                if driver_version_match:
                    driver_major = int(driver_version_match.group(1))
                    
                    if chrome_major == driver_major:
                        return True, f"版本匹配: Chrome {chrome_major} == ChromeDriver {driver_major}"
                    elif abs(chrome_major - driver_major) <= 1:
                        return True, f"版本兼容: Chrome {chrome_major} ~ ChromeDriver {driver_major}"
                    else:
                        return False, f"版本不匹配: Chrome {chrome_major} != ChromeDriver {driver_major}"
        except Exception as e:
            return False, f"无法验证 ChromeDriver 版本: {e}"
        
        return False, "无法获取 ChromeDriver 版本信息"


def get_chromedriver_path(config: dict = None) -> str:
    """
    获取 ChromeDriver 路径的便捷函数
    
    Args:
        config: 配置字典，可能包含 chromedriver_path 配置
        
    Returns:
        ChromeDriver 可执行文件路径
    """
    logger = logging.getLogger(__name__)
    
    # 检查配置中是否指定了路径
    if config:
        selenium_config = config.get('selenium', {})
        custom_path = selenium_config.get('chromedriver_path', '')
        if custom_path and os.path.exists(custom_path):
            logger.info(f"使用配置的 ChromeDriver: {custom_path}")
            return custom_path
    
    # 使用版本管理器自动获取
    manager = ChromeVersionManager()
    return manager.get_matching_chromedriver()


def check_chrome_installation() -> Tuple[bool, str]:
    """
    检查 Chrome 浏览器是否已安装
    
    Returns:
        (是否安装, 详细信息)
    """
    manager = ChromeVersionManager()
    version = manager.get_local_chrome_version()
    
    if version:
        return True, f"Chrome 已安装，版本: {version}"
    else:
        return False, "未检测到 Chrome 浏览器，请安装 Chrome 后再试"


# 测试代码
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s'
    )
    
    print("=" * 60)
    print("Chrome 版本检测测试")
    print("=" * 60)
    
    # 检查 Chrome 安装
    installed, msg = check_chrome_installation()
    print(f"\n{msg}")
    
    if installed:
        manager = ChromeVersionManager()
        
        # 获取 Chrome 版本
        chrome_version = manager.get_local_chrome_version()
        print(f"Chrome 版本: {chrome_version}")
        
        # 获取匹配的 ChromeDriver
        try:
            driver_path = manager.get_matching_chromedriver(chrome_version)
            print(f"ChromeDriver 路径: {driver_path}")
            
            # 验证兼容性
            compatible, compat_msg = manager.verify_chromedriver_compatibility(driver_path, chrome_version)
            print(f"兼容性检查: {compat_msg}")
        except Exception as e:
            print(f"获取 ChromeDriver 失败: {e}")
