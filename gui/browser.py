import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import yaml

class BrowserTab:
    """内置浏览器标签页类"""
    
    def __init__(self, parent):
        """初始化浏览器标签页"""
        self.parent = parent
        self.browser_available = False
        self.browser = None
        
        # 创建主框架
        self.frame = ttk.Frame(parent, padding="10")
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # 地址栏框架
        url_frame = ttk.Frame(self.frame)
        url_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 地址输入框
        self.url_var = tk.StringVar(value="https://www.google.com")
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=50)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # 导航按钮
        ttk.Button(url_frame, text="前往", command=self.browser_go).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(url_frame, text="刷新", command=self.browser_refresh).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(url_frame, text="返回", command=self.browser_back).pack(side=tk.LEFT)
        
        # 浏览器内容区域
        self.browser_frame = ttk.Frame(self.frame)
        self.browser_frame.pack(fill=tk.BOTH, expand=True)
        
        # 初始化浏览器
        self.init_browser()
    
    def load_config(self):
        """加载配置文件"""
        try:
            with open("config.yaml", "r", encoding="utf-8") as f:
                config_text = f.read()
                config_text = config_text.replace('\\', '\\\\')
                return yaml.safe_load(config_text)
        except Exception as e:
            messagebox.showerror("错误", f"配置文件加载失败: {e}")
            return {}
    
    def init_browser(self):
        """初始化浏览器组件"""
        # 尝试使用tkinterweb库
        try:
            from tkinterweb import HtmlFrame
            self.browser = HtmlFrame(self.browser_frame)
            self.browser.pack(fill=tk.BOTH, expand=True)
            # 加载配置，设置代理
            self.setup_proxy()
            self.browser.load_website("https://www.google.com")
            self.browser_available = True
        except ImportError:
            # 如果没有安装tkinterweb，显示提示信息
            self.browser_available = False
            ttk.Label(self.browser_frame, text="内置浏览器需要安装 tkinterweb 库", font=("SimHei", 12)).pack(pady=20)
            ttk.Label(self.browser_frame, text="请运行: pip install tkinterweb", font=("SimHei", 10)).pack(pady=5)
            ttk.Button(self.browser_frame, text="使用系统浏览器打开", command=self.open_system_browser).pack(pady=10)
    
    def setup_proxy(self):
        """设置浏览器代理"""
        try:
            # 加载配置
            config = self.load_config()
            proxy_config = config.get("network", {}).get("proxy", {})
            
            # 如果启用了代理
            if proxy_config.get("enabled", False):
                http_proxy = proxy_config.get("http", "")
                https_proxy = proxy_config.get("https", "")
                
                if http_proxy:
                    # 设置tkinterweb的代理
                    if hasattr(self.browser, 'set_proxy'):
                        self.browser.set_proxy(http_proxy)
                        # 尝试设置HTTPS代理（如果tkinterweb支持）
                        if hasattr(self.browser, 'set_https_proxy'):
                            self.browser.set_https_proxy(https_proxy if https_proxy else http_proxy)
        except Exception as e:
            print(f"设置代理失败: {e}")
    
    def browser_go(self):
        """浏览器前往指定地址"""
        url = self.url_var.get().strip()
        if url:
            if self.browser_available:
                try:
                    # 重新设置代理，确保使用最新配置
                    self.setup_proxy()
                    print(f"尝试加载 URL: {url}")
                    # 尝试加载网页
                    self.browser.load_website(url)
                    print("网页加载成功")
                except Exception as e:
                    print(f"加载网页失败: {e}")
                    messagebox.showerror("错误", f"加载网页失败: {e}")
                    # 如果失败，尝试使用系统浏览器
                    self.open_system_browser(url)
            else:
                self.open_system_browser(url)
    
    def browser_refresh(self):
        """浏览器刷新当前页面"""
        if self.browser_available:
            try:
                self.browser.reload()
            except Exception as e:
                messagebox.showerror("错误", f"刷新页面失败: {e}")
    
    def browser_back(self):
        """浏览器返回上一页"""
        if self.browser_available:
            try:
                self.browser.back()
            except Exception as e:
                messagebox.showerror("错误", f"返回上一页失败: {e}")
    
    def open_system_browser(self, url=None):
        """使用系统默认浏览器打开网页"""
        if not url:
            url = self.url_var.get().strip()
        if url:
            try:
                webbrowser.open(url)
            except Exception as e:
                messagebox.showerror("错误", f"打开浏览器失败: {e}")

class BrowserWindow:
    """浏览器窗口类"""
    
    def __init__(self, parent=None, url="https://www.google.com"):
        """初始化浏览器窗口"""
        # 创建浏览器窗口
        self.window = tk.Toplevel(parent)
        self.window.title("内置浏览器")
        self.window.geometry("1000x700")
        self.window.minsize(800, 600)
        
        # 创建浏览器标签
        self.browser_tab = ttk.Frame(self.window)
        self.browser_tab.pack(fill=tk.BOTH, expand=True)
        
        # 初始化浏览器
        self.browser = BrowserTab(self.browser_tab)
        
        # 设置初始URL
        self.browser.url_var.set(url)
        
        # 当窗口关闭时，确保资源被释放
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def show(self):
        """显示浏览器窗口"""
        self.window.deiconify()  # 显示窗口，而不是启动新的主循环
    
    def on_close(self):
        """窗口关闭时的处理"""
        try:
            # 可以在这里添加清理代码
            self.window.destroy()
        except Exception as e:
            print(f"关闭窗口时出错: {e}")

# 测试函数
def test_browser():
    """测试浏览器"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    browser = BrowserWindow(root)
    browser.show()