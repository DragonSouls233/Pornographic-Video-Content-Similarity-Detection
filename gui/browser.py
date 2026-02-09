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
        # 创建一个功能更完整的代理测试界面
        self.browser_available = False
        
        # 创建主框架
        info_frame = ttk.Frame(self.browser_frame)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        ttk.Label(info_frame, text="🌐 代理测试浏览器", font=("SimHei", 14, "bold")).pack(pady=10)
        
        # 代理配置显示区域
        config_frame = ttk.LabelFrame(info_frame, text="当前代理配置", padding=10)
        config_frame.pack(fill=tk.X, pady=10)
        
        # 加载并显示代理配置
        config = self.load_config()
        proxy_config = config.get("network", {}).get("proxy", {})
        
        # 配置信息网格
        row = 0
        configs = [
            ("启用状态", "✅ 已启用" if proxy_config.get('enabled', False) else "❌ 未启用"),
            ("代理类型", proxy_config.get('type', 'socks5').upper()),
            ("主机地址", proxy_config.get('host', '127.0.0.1')),
            ("端口号", proxy_config.get('port', '10808')),
            ("HTTP代理", proxy_config.get('http', '未配置')),
            ("HTTPS代理", proxy_config.get('https', '未配置'))
        ]
        
        for label, value in configs:
            ttk.Label(config_frame, text=f"{label}:", font=("SimHei", 10, "bold")).grid(row=row, column=0, sticky=tk.W, padx=5, pady=3)
            ttk.Label(config_frame, text=str(value), font=("SimHei", 10)).grid(row=row, column=1, sticky=tk.W, padx=5, pady=3)
            row += 1
        
        # 测试结果显示区域
        result_frame = ttk.LabelFrame(info_frame, text="测试结果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.browser_result_text = tk.Text(result_frame, height=12, wrap=tk.WORD, font=("Consolas", 9))
        self.browser_result_text.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.browser_result_text.yview)
        self.browser_result_text.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 使用说明
        help_frame = ttk.LabelFrame(info_frame, text="💡 使用说明", padding=10)
        help_frame.pack(fill=tk.X, pady=10)
        
        instructions = [
            "1. 确保代理工具（如 v2rayN、Clash 等）已启动并连接成功",
            "2. 在【工具】→【打开配置文件】中配置正确的代理信息",
            "3. 点击上方【前往】按钮或【代理测试】标签页测试连接",
            "4. 测试成功后即可开始使用抓取功能"
        ]
        
        for inst in instructions:
            ttk.Label(help_frame, text=inst, font=("SimHei", 9)).pack(anchor=tk.W, pady=2)
    

    
    def browser_go(self):
        """浏览器前往指定地址（使用系统浏览器测试代理）"""
        url = self.url_var.get().strip()
        if url:
            try:
                # 显示测试信息
                self.browser_result_text.delete(1.0, tk.END)
                self.browser_result_text.insert(tk.END, f"📡 正在测试访问: {url}\n\n")
                
                # 使用requests测试代理连接
                config = self.load_config()
                proxy_config = config.get("network", {}).get("proxy", {})
                
                proxies = {}
                if proxy_config.get("enabled", False):
                    http_proxy = proxy_config.get("http", "")
                    https_proxy = proxy_config.get("https", "")
                    if http_proxy:
                        proxies["http"] = http_proxy
                        proxies["https"] = https_proxy
                    self.browser_result_text.insert(tk.END, f"✅ 使用代理: {http_proxy}\n\n")
                else:
                    self.browser_result_text.insert(tk.END, "⚠️  未启用代理，使用直接连接\n\n")
                
                self.browser_result_text.insert(tk.END, "⏳ 正在连接...\n")
                self.browser_result_text.update()
                
                import requests
                start_time = time.time()
                response = requests.get(url, proxies=proxies, timeout=15, verify=False)
                end_time = time.time()
                
                self.browser_result_text.insert(tk.END, f"\n✅ 连接成功!\n")
                self.browser_result_text.insert(tk.END, f"   状态码: {response.status_code}\n")
                self.browser_result_text.insert(tk.END, f"   响应时间: {end_time - start_time:.2f}秒\n")
                self.browser_result_text.insert(tk.END, f"   内容长度: {len(response.content)}字节\n\n")
                
                # 尝试获取页面标题
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.content, "html.parser")
                    title = soup.title.string if soup.title else "无标题"
                    self.browser_result_text.insert(tk.END, f"📄 页面标题: {title}\n\n")
                except:
                    pass
                
                # 询问是否在系统浏览器中打开
                if messagebox.askyesno("测试成功", f"代理连接测试成功！\n\n是否在系统浏览器中打开该网页？"):
                    self.open_system_browser(url)
                    
            except Exception as e:
                self.browser_result_text.delete(1.0, tk.END)
                self.browser_result_text.insert(tk.END, f"❌ 连接失败!\n\n")
                self.browser_result_text.insert(tk.END, f"错误信息: {str(e)}\n\n")
                self.browser_result_text.insert(tk.END, "💡 请检查:\n")
                self.browser_result_text.insert(tk.END, "   1. 代理工具是否已启动\n")
                self.browser_result_text.insert(tk.END, "   2. 代理配置是否正确\n")
                self.browser_result_text.insert(tk.END, "   3. 网络连接是否正常\n")
                messagebox.showerror("连接失败", f"代理连接测试失败!\n\n{str(e)}")
    
    def browser_refresh(self):
        """浏览器刷新当前页面"""
        # 重新测试当前URL
        self.browser_go()
    
    def browser_back(self):
        """浏览器返回（清空结果）"""
        self.browser_result_text.delete(1.0, tk.END)
        self.browser_result_text.insert(tk.END, "已清空测试结果\n")
    
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