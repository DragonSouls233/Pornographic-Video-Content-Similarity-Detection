import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import yaml
import time

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
            # 检查代理是否支持
            config = self.load_config()
            proxy_config = config.get("network", {}).get("proxy", {})
            
            if proxy_config.get("enabled", False):
                # 显示提示信息
                messagebox.showinfo("提示", "当前版本的tkinterweb不支持代理设置，将使用系统浏览器打开以测试代理。")
                # 直接使用系统浏览器
                self.open_system_browser("https://www.google.com")
            else:
                # 没有启用代理，尝试使用内置浏览器
                self.browser.load_website("https://www.google.com")
            self.browser_available = True
        except ImportError:
            # 如果没有安装tkinterweb，显示一个简单的浏览器界面
            self.browser_available = False
            # 创建一个简单的文本框来显示代理信息
            info_frame = ttk.Frame(self.browser_frame)
            info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            ttk.Label(info_frame, text="代理测试浏览器", font=("SimHei", 14, "bold")).pack(pady=10)
            ttk.Label(info_frame, text="当前代理配置:", font=("SimHei", 12)).pack(pady=5, anchor=tk.W)
            
            # 加载配置，显示代理信息
            config = self.load_config()
            proxy_config = config.get("network", {}).get("proxy", {})
            
            proxy_info = f"启用: {proxy_config.get('enabled', False)}\n"
            proxy_info += f"类型: {proxy_config.get('type', 'http')}\n"
            proxy_info += f"主机: {proxy_config.get('host', '127.0.0.1')}\n"
            proxy_info += f"端口: {proxy_config.get('port', '10808')}\n"
            proxy_info += f"HTTP代理: {proxy_config.get('http', '')}\n"
            proxy_info += f"HTTPS代理: {proxy_config.get('https', '')}\n"
            
            info_text = tk.Text(info_frame, width=80, height=15, wrap=tk.WORD)
            info_text.pack(fill=tk.BOTH, expand=True, pady=10)
            info_text.insert(tk.END, proxy_info)
            info_text.config(state=tk.DISABLED)
            
            ttk.Label(info_frame, text="测试代理是否成功:", font=("SimHei", 12)).pack(pady=5, anchor=tk.W)
            ttk.Label(info_frame, text="1. 确保v2rayN等代理工具已启动并连接", font=("SimHei", 10)).pack(pady=2, anchor=tk.W)
            ttk.Label(info_frame, text="2. 在代理设置中配置正确的代理信息", font=("SimHei", 10)).pack(pady=2, anchor=tk.W)
            ttk.Label(info_frame, text="3. 点击'测试代理连接'按钮测试连接", font=("SimHei", 10)).pack(pady=2, anchor=tk.W)
            ttk.Label(info_frame, text="4. 如果测试成功，说明代理配置正确", font=("SimHei", 10)).pack(pady=2, anchor=tk.W)
    
    def setup_proxy(self):
        """设置浏览器代理"""
        try:
            # 加载配置
            config = self.load_config()
            proxy_config = config.get("network", {}).get("proxy", {})
            
            print(f"代理配置: {proxy_config}")
            
            # 如果启用了代理
            if proxy_config.get("enabled", False):
                http_proxy = proxy_config.get("http", "")
                https_proxy = proxy_config.get("https", "")
                
                print(f"HTTP代理: {http_proxy}")
                print(f"HTTPS代理: {https_proxy}")
                
                if http_proxy:
                    # 尝试设置tkinterweb的代理（不同版本的API可能不同）
                    print(f"尝试设置代理: {http_proxy}")
                    
                    # 方法1: 直接设置代理属性
                    if hasattr(self.browser, 'proxy'):
                        self.browser.proxy = http_proxy
                        print("使用属性设置代理成功")
                    # 方法2: 使用set_proxy方法
                    elif hasattr(self.browser, 'set_proxy'):
                        try:
                            self.browser.set_proxy(http_proxy)
                            print("使用set_proxy方法设置代理成功")
                        except Exception as e:
                            print(f"set_proxy方法调用失败: {e}")
                    # 方法3: 检查是否有其他代理相关属性
                    elif hasattr(self.browser, '_proxy'):
                        self.browser._proxy = http_proxy
                        print("使用_proxy属性设置代理成功")
                    # 方法4: 检查是否有network属性
                    elif hasattr(self.browser, 'network'):
                        try:
                            self.browser.network.set_proxy(http_proxy)
                            print("使用network.set_proxy设置代理成功")
                        except Exception as e:
                            print(f"network.set_proxy失败: {e}")
                    else:
                        print("tkinterweb不支持代理设置")
                        # 显示提示信息
                        messagebox.showinfo("提示", "当前版本的tkinterweb不支持代理设置，将使用系统默认网络连接。")
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
                    start_time = time.time()
                    self.browser.load_website(url)
                    end_time = time.time()
                    print(f"网页加载成功，耗时: {end_time - start_time:.2f}秒")
                    
                    # 检查是否加载成功
                    try:
                        page_title = self.browser.get_title()
                        print(f"页面标题: {page_title}")
                        if "Oops" in page_title or "Error" in page_title or "找不到页面" in page_title:
                            print("页面加载失败，显示错误信息")
                            # 尝试使用系统浏览器
                            messagebox.showinfo("提示", "内置浏览器加载失败，尝试使用系统浏览器打开。")
                            self.open_system_browser(url)
                    except Exception as e:
                        print(f"获取页面标题失败: {e}")
                        
                except Exception as e:
                    print(f"加载网页失败: {e}")
                    # 如果失败，显示提示信息
                    messagebox.showinfo("提示", f"加载网页失败，尝试使用系统浏览器打开。\n错误: {e}")
                    self.open_system_browser(url)
            else:
                # 如果tkinterweb不可用，显示提示信息并使用系统浏览器
                messagebox.showinfo("提示", "内置浏览器不可用，尝试使用系统浏览器打开。")
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