import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

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
    
    def init_browser(self):
        """初始化浏览器组件"""
        # 尝试使用tkinterweb库
        try:
            from tkinterweb import HtmlFrame
            self.browser = HtmlFrame(self.browser_frame)
            self.browser.pack(fill=tk.BOTH, expand=True)
            self.browser.load_website("https://www.google.com")
            self.browser_available = True
        except ImportError:
            # 如果没有安装tkinterweb，显示提示信息
            self.browser_available = False
            ttk.Label(self.browser_frame, text="内置浏览器需要安装 tkinterweb 库", font=("SimHei", 12)).pack(pady=20)
            ttk.Label(self.browser_frame, text="请运行: pip install tkinterweb", font=("SimHei", 10)).pack(pady=5)
            ttk.Button(self.browser_frame, text="使用系统浏览器打开", command=self.open_system_browser).pack(pady=10)
    
    def browser_go(self):
        """浏览器前往指定地址"""
        url = self.url_var.get().strip()
        if url:
            if self.browser_available:
                try:
                    self.browser.load_website(url)
                except Exception as e:
                    messagebox.showerror("错误", f"加载网页失败: {e}")
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