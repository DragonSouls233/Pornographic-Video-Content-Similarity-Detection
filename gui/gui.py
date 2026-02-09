import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import yaml
import os
import threading
import queue
import time
from datetime import datetime
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# 导入默认配置模板
try:
    from gui.config_template import DEFAULT_CONFIG
except ImportError:
    from config_template import DEFAULT_CONFIG

class ModelManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("模特查重管理系统")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # 设置图标
        try:
            # 尝试设置图标（如果有）
            pass
        except:
            pass
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建标签页
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 创建模特管理标签页
        self.model_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.model_tab, text="模特管理")
        
        # 创建运行控制标签页
        self.run_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.run_tab, text="运行控制")
        
        # 创建结果显示标签页
        self.result_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.result_tab, text="结果显示")
        
        # 创建浏览器/代理测试标签页（合并）
        self.browser_proxy_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.browser_proxy_tab, text="浏览器/代理测试")
        
        # 初始化各标签页
        self.init_model_tab()
        self.init_run_tab()
        self.init_result_tab()
        self.init_browser_proxy_tab()
        
        # 加载模特数据
        self.models = self.load_models()
        self.current_results = {}  # 初始化当前结果字典
        self.update_model_list()
        
        # 队列用于线程间通信
        self.queue = queue.Queue()
        self.running = False
        self.thread = None
        self.public_ip_var = tk.StringVar(value="000.000.000.000")
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="刷新数据", command=self.refresh_models)
        file_menu.add_command(label="导出数据", command=self.export_models)
        file_menu.add_command(label="导入数据", command=self.import_models)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        # 工具菜单
        tool_menu = tk.Menu(menubar, tearoff=0)
        tool_menu.add_command(label="打开配置文件", command=self.open_config)
        tool_menu.add_command(label="打开缓存目录", command=self.open_cache_dir)
        tool_menu.add_command(label="打开日志目录", command=self.open_log_dir)
        tool_menu.add_separator()
        tool_menu.add_command(label="打开独立浏览器", command=self.open_browser_window)
        menubar.add_cascade(label="工具", menu=tool_menu)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def init_model_tab(self):
        """初始化模特管理标签页"""
        # 创建主框架
        frame = ttk.Frame(self.model_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：模特列表
        list_frame = ttk.LabelFrame(frame, text="模特列表", padding="10")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 搜索框和模块筛选
        search_frame = ttk.Frame(list_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="搜索: ").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=25)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10))
        
        ttk.Label(search_frame, text="模块: ").pack(side=tk.LEFT)
        self.model_module_var = tk.StringVar(value="全部")
        module_combobox = ttk.Combobox(search_frame, textvariable=self.model_module_var, values=["全部", "PRONHUB", "JAVDB"], width=10, state="readonly")
        module_combobox.pack(side=tk.LEFT, padx=(5, 5))
        module_combobox.bind("<<ComboboxSelected>>", self.filter_models_by_module)
        
        ttk.Button(search_frame, text="搜索", command=self.search_models).pack(side=tk.RIGHT)
        
        # 列表视图
        columns = ("model_name", "module", "url")
        self.model_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # 设置列标题
        self.model_tree.heading("model_name", text="模特名称")
        self.model_tree.heading("module", text="模块")
        self.model_tree.heading("url", text="链接")
        
        # 设置列宽
        self.model_tree.column("model_name", width=180)
        self.model_tree.column("module", width=80)
        self.model_tree.column("url", width=320)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.model_tree.yview)
        self.model_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.model_tree.pack(fill=tk.BOTH, expand=True)
        
        # 右侧：操作面板
        action_frame = ttk.LabelFrame(frame, text="操作", padding="10", width=250)
        action_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 添加模特
        ttk.Button(action_frame, text="添加模特", command=self.add_model, width=20).pack(fill=tk.X, pady=5)
        
        # 编辑模特
        ttk.Button(action_frame, text="编辑模特", command=self.edit_model, width=20).pack(fill=tk.X, pady=5)
        
        # 删除模特
        ttk.Button(action_frame, text="删除模特", command=self.delete_model, width=20).pack(fill=tk.X, pady=5)
        
        # 分隔线
        ttk.Separator(action_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 下载功能
        ttk.Label(action_frame, text="下载功能", font=("Arial", 10, "bold")).pack(pady=5)
        ttk.Button(action_frame, text="下载选中模特完整目录", command=self.download_selected_models_complete, width=20).pack(fill=tk.X, pady=2)
        ttk.Button(action_frame, text="批量下载所有模特", command=self.download_all_models_complete, width=20).pack(fill=tk.X, pady=2)
        
        # 分隔线
        ttk.Separator(action_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 刷新列表
        ttk.Button(action_frame, text="刷新列表", command=self.refresh_models, width=20).pack(fill=tk.X, pady=5)
        
        # 模特数量统计
        self.model_count_var = tk.StringVar(value="模特数量: 0 (PRONHUB: 0, JAVDB: 0)")
        ttk.Label(action_frame, textvariable=self.model_count_var).pack(pady=10)
    
    def init_run_tab(self):
        """初始化运行控制标签页"""
        # 创建主框架
        frame = ttk.Frame(self.run_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 运行配置
        config_frame = ttk.LabelFrame(frame, text="运行配置", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 模块选择
        ttk.Label(config_frame, text="模块选择: ").pack(side=tk.LEFT)
        self.module_var = tk.StringVar(value="auto")
        module_combobox = ttk.Combobox(config_frame, textvariable=self.module_var, values=["auto", "pronhub", "javdb"], width=10)
        module_combobox.pack(side=tk.LEFT, padx=(5, 20))
        
        # 本地目录选择
        ttk.Label(config_frame, text="本地目录: ").pack(anchor=tk.W, pady=2)
        dir_frame = ttk.Frame(config_frame)
        dir_frame.pack(fill=tk.X, pady=2)
        
        # 目录列表
        self.dir_listbox = tk.Listbox(dir_frame, width=60, height=3)
        self.dir_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 滚动条
        scrollbar = ttk.Scrollbar(dir_frame, orient=tk.VERTICAL, command=self.dir_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.dir_listbox.configure(yscroll=scrollbar.set)
        
        # 按钮框架
        btn_frame = ttk.Frame(dir_frame, width=100)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        # 添加目录按钮
        ttk.Button(btn_frame, text="添加", command=self.add_local_dir, width=10).pack(fill=tk.X, pady=2)
        
        # 删除目录按钮
        ttk.Button(btn_frame, text="删除", command=self.remove_local_dir, width=10).pack(fill=tk.X, pady=2)
        
        # 加载保存的目录列表
        self.load_local_dirs()
        # 如果没有保存的目录，添加默认目录
        if self.dir_listbox.size() == 0:
            self.dir_listbox.insert(tk.END, "F:\\作品")
            self.save_local_dirs()
        
        # 抓取工具选择（固定为selenium）
        ttk.Label(config_frame, text="抓取工具: ").pack(side=tk.LEFT)
        self.scraper_var = tk.StringVar(value="selenium")
        scraper_combobox = ttk.Combobox(config_frame, textvariable=self.scraper_var, values=["selenium"], width=15, state="readonly")
        scraper_combobox.pack(side=tk.LEFT, padx=(5, 20))
        
        # 最大翻页
        ttk.Label(config_frame, text="最大翻页: ").pack(side=tk.LEFT)
        self.max_pages_var = tk.StringVar(value="-1")
        ttk.Entry(config_frame, textvariable=self.max_pages_var, width=10).pack(side=tk.LEFT, padx=(5, 20))
        
        # 延时设置
        ttk.Label(config_frame, text="页面间延时: ").pack(side=tk.LEFT)
        self.delay_var = tk.StringVar(value="2.0-3.5")
        ttk.Entry(config_frame, textvariable=self.delay_var, width=10).pack(side=tk.LEFT)
        
        # 运行按钮
        run_frame = ttk.Frame(frame)
        run_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.run_button = ttk.Button(run_frame, text="开始运行", command=self.start_run, width=20)
        self.run_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(run_frame, text="停止运行", command=self.stop_run, width=20, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT)
        
        # 进度显示
        progress_frame = ttk.LabelFrame(frame, text="运行进度", padding="10")
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        # 进度条
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # 状态信息
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(progress_frame, textvariable=self.status_var, font=("SimHei", 10)).pack(anchor=tk.W, pady=2)
        
        # 日志显示
        self.log_text = tk.Text(progress_frame, height=15, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(progress_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def init_result_tab(self):
        """初始化结果显示标签页"""
        # 创建主框架
        frame = ttk.Frame(self.result_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 结果统计
        stats_frame = ttk.LabelFrame(frame, text="结果统计", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 统计信息
        self.stats_vars = {
            "processed": tk.StringVar(value="成功处理: 0"),
            "failed": tk.StringVar(value="处理失败: 0"),
            "missing": tk.StringVar(value="发现缺失: 0")
        }
        
        for key, var in self.stats_vars.items():
            ttk.Label(stats_frame, textvariable=var).pack(side=tk.LEFT, padx=20)
        
        # 缺失视频列表
        result_frame = ttk.LabelFrame(frame, text="缺失视频", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # 列表视图
        columns = ("model", "title", "url")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings")
        
        # 设置列标题
        self.result_tree.heading("model", text="模特")
        self.result_tree.heading("title", text="视频标题")
        self.result_tree.heading("url", text="链接")
        
        # 设置列宽
        self.result_tree.column("model", width=150)
        self.result_tree.column("title", width=300)
        self.result_tree.column("url", width=400)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.result_tree.pack(fill=tk.BOTH, expand=True)
        
        # 操作按钮
        action_frame = ttk.Frame(result_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 下载按钮（PRONHUB专用）
        self.download_selected_btn = ttk.Button(action_frame, text="下载选中视频", command=self.download_selected_videos)
        self.download_selected_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.download_all_btn = ttk.Button(action_frame, text="下载所有缺失视频", command=self.download_all_missing_videos)
        self.download_all_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.download_complete_btn = ttk.Button(action_frame, text="完整下载模特目录", command=self.download_complete_model_directories)
        self.download_complete_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 绑定模块选择变化事件来控制下载按钮
        self.model_module_var.trace_add('write', self._update_download_buttons_state)
        
        # 导出按钮
        ttk.Button(action_frame, text="导出结果", command=self.export_results).pack(side=tk.RIGHT)
    
    def init_browser_proxy_tab(self):
        """初始化浏览器/代理测试标签页（合并）"""
        # 创建主框架
        frame = ttk.Frame(self.browser_proxy_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：浏览器功能
        browser_frame = ttk.LabelFrame(frame, text="浏览器", padding="10")
        browser_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 地址栏
        url_frame = ttk.Frame(browser_frame)
        url_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.browser_url_var = tk.StringVar(value="https://www.google.com")
        url_entry = ttk.Entry(url_frame, textvariable=self.browser_url_var, width=40)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(url_frame, text="前往", command=self.browser_go, width=8).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(url_frame, text="刷新", command=self.browser_refresh, width=8).pack(side=tk.LEFT)
        
        # 代理配置显示
        config_frame = ttk.LabelFrame(browser_frame, text="当前代理配置", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 加载并显示代理配置
        config = self.load_config()
        proxy_config = config.get("network", {}).get("proxy", {})
        
        self.proxy_info_text = tk.Text(config_frame, height=6, wrap=tk.WORD, font=("Consolas", 9))
        self.proxy_info_text.pack(fill=tk.X)
        self.proxy_info_text.insert(tk.END, f"状态: {'启用' if proxy_config.get('enabled', False) else '禁用'}\n")
        self.proxy_info_text.insert(tk.END, f"类型: {proxy_config.get('type', 'socks5').upper()}\n")
        self.proxy_info_text.insert(tk.END, f"主机: {proxy_config.get('host', '127.0.0.1')}\n")
        self.proxy_info_text.insert(tk.END, f"端口: {proxy_config.get('port', '10808')}\n")
        self.proxy_info_text.config(state=tk.DISABLED)
        
        # 浏览器测试结果区域
        result_frame = ttk.LabelFrame(browser_frame, text="测试结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.browser_result_text = tk.Text(result_frame, height=10, wrap=tk.WORD, font=("Consolas", 9))
        self.browser_result_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.browser_result_text.yview)
        self.browser_result_text.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 右侧：代理测试功能
        proxy_frame = ttk.LabelFrame(frame, text="代理测试", padding="10")
        proxy_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 测试设置
        test_setting_frame = ttk.Frame(proxy_frame)
        test_setting_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(test_setting_frame, text="测试URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.test_url_var = tk.StringVar(value="https://www.google.com")
        ttk.Entry(test_setting_frame, textvariable=self.test_url_var, width=35).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(test_setting_frame, text="超时(秒):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.timeout_var = tk.StringVar(value="10")
        ttk.Entry(test_setting_frame, textvariable=self.timeout_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 代理测试结果
        proxy_result_frame = ttk.LabelFrame(proxy_frame, text="代理测试结果", padding="10")
        proxy_result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.proxy_test_result_text = tk.Text(proxy_result_frame, height=12, wrap=tk.WORD, font=("Consolas", 9))
        self.proxy_test_result_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar2 = ttk.Scrollbar(proxy_result_frame, orient=tk.VERTICAL, command=self.proxy_test_result_text.yview)
        self.proxy_test_result_text.configure(yscroll=scrollbar2.set)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮框架
        button_frame = ttk.Frame(proxy_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="测试连接", command=self.test_proxy_connection, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="获取公网IP", command=self.refresh_public_ip, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空结果", command=self.clear_test_results, width=12).pack(side=tk.RIGHT, padx=5)
    
    def browser_go(self):
        """浏览器前往指定地址（使用系统浏览器测试代理）"""
        url = self.browser_url_var.get().strip()
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
                    import webbrowser
                    webbrowser.open(url)
                    
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
    
    def test_proxy_connection(self):
        """测试代理连接"""
        try:
            import requests
            
            # 获取测试设置
            url = self.test_url_var.get().strip()
            timeout = int(self.timeout_var.get().strip())
            
            # 清空结果
            self.proxy_test_result_text.delete(1.0, tk.END)
            self.proxy_test_result_text.insert(tk.END, f"开始测试代理连接...\n")
            self.proxy_test_result_text.insert(tk.END, f"测试URL: {url}\n")
            self.proxy_test_result_text.insert(tk.END, f"超时设置: {timeout}秒\n\n")
            
            # 加载配置
            config = self.load_config()
            proxy_config = config.get("network", {}).get("proxy", {})
            
            # 构建代理字典
            proxies = {}
            if proxy_config.get("enabled", False):
                proxy_type = proxy_config.get("type", "socks5")
                proxy_host = proxy_config.get("host", "").strip()
                proxy_port = proxy_config.get("port", "").strip()
                proxy_id = proxy_config.get("id", "").strip()
                proxy_password = proxy_config.get("password", "").strip()
                
                if proxy_host and proxy_port:
                    # 构建代理URL
                    if proxy_id and proxy_password:
                        proxy_url = f"{proxy_type}://{proxy_id}:{proxy_password}@{proxy_host}:{proxy_port}"
                    else:
                        proxy_url = f"{proxy_type}://{proxy_host}:{proxy_port}"
                    
                    proxies = {
                        "http": proxy_url,
                        "https": proxy_url
                    }
                    self.proxy_test_result_text.insert(tk.END, f"使用代理: {proxy_url}\n\n")
                else:
                    self.proxy_test_result_text.insert(tk.END, "警告: 代理已启用但未设置主机和端口\n\n")
            else:
                self.proxy_test_result_text.insert(tk.END, "未使用代理（直接连接）\n\n")
            
            # 测试连接
            start_time = time.time()
            response = requests.get(url, proxies=proxies, timeout=timeout, verify=False)
            end_time = time.time()
            
            # 显示结果
            self.proxy_test_result_text.insert(tk.END, f"测试成功!\n")
            self.proxy_test_result_text.insert(tk.END, f"响应状态码: {response.status_code}\n")
            self.proxy_test_result_text.insert(tk.END, f"响应时间: {end_time - start_time:.2f}秒\n")
            self.proxy_test_result_text.insert(tk.END, f"响应内容长度: {len(response.content)}字节\n\n")
            
            # 尝试获取页面标题
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, "html.parser")
                title = soup.title.string if soup.title else "无标题"
                self.proxy_test_result_text.insert(tk.END, f"页面标题: {title}\n")
            except ImportError:
                pass
            
            self.proxy_test_result_text.insert(tk.END, "\n代理连接测试通过！")
            
        except requests.exceptions.RequestException as e:
            self.proxy_test_result_text.insert(tk.END, f"测试失败: {e}\n")
            self.proxy_test_result_text.insert(tk.END, "\n代理连接测试失败，请检查代理设置！")
        except Exception as e:
            self.proxy_test_result_text.insert(tk.END, f"错误: {e}\n")
    
    def clear_test_results(self):
        """清空测试结果"""
        self.proxy_test_result_text.delete(1.0, tk.END)
    
    def generate_proxy_url(self, enabled, proxy_type, host, port, proxy_id, password):
        """生成代理URL"""
        if not enabled or not host or not port:
            return ""
        
        if proxy_id and password:
            if proxy_type == "socks5":
                return f"socks5://{proxy_id}:{password}@{host}:{port}"
            else:
                return f"http://{proxy_id}:{password}@{host}:{port}"
        else:
            if proxy_type == "socks5":
                return f"socks5://{host}:{port}"
            else:
                return f"http://{host}:{port}"
    
    def load_config(self):
        """加载配置文件"""
        try:
            if not os.path.exists("config.yaml"):
                # 如果配置文件不存在，生成默认配置文件
                with open("config.yaml", "w", encoding="utf-8") as f:
                    f.write(DEFAULT_CONFIG)
                messagebox.showinfo("提示", "配置文件不存在，已生成默认配置文件。")
            
            with open("config.yaml", "r", encoding="utf-8") as f:
                config_text = f.read()
                config_text = config_text.replace('\\', '\\\\')
                config = yaml.safe_load(config_text)
                
                # 检查配置文件结构是否完整
                if not config:
                    # 如果配置文件为空，生成默认配置文件
                    with open("config.yaml", "w", encoding="utf-8") as f:
                        f.write(DEFAULT_CONFIG)
                    messagebox.showinfo("提示", "配置文件结构不完整，已生成默认配置文件。")
                    config = yaml.safe_load(DEFAULT_CONFIG)
                
                return config
        except Exception as e:
            # 如果加载失败，生成默认配置文件
            with open("config.yaml", "w", encoding="utf-8") as f:
                f.write(DEFAULT_CONFIG)
            messagebox.showinfo("提示", f"配置文件加载失败: {e}\n已生成默认配置文件。")
            return yaml.safe_load(DEFAULT_CONFIG)
    
    def load_models(self):
        """加载模特数据"""
        try:
            # 检查文件是否存在，如果不存在则创建空文件
            if not os.path.exists("models.json"):
                # 自动生成空的models.json文件
                with open("models.json", "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("提示", "models.json文件不存在，已自动创建空文件")
                return {}
            
            # 文件存在，读取内容
            with open("models.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 兼容旧格式：如果models.json是简单字典，自动迁移为新格式
            # 新格式：每个模特包含 module 和 url 字段
            migrated = False
            new_data = {}
            
            for key, value in data.items():
                if isinstance(value, str):
                    # 旧格式：{model_name: url}
                    # 根据URL自动判断模块类型
                    module = "JAVDB" if "javdb" in value.lower() else "PRONHUB"
                    new_data[key] = {
                        "module": module,
                        "url": value
                    }
                    migrated = True
                elif isinstance(value, dict):
                    # 新格式：{model_name: {"module": "PRONHUB/JAVDB", "url": "..."}}
                    new_data[key] = value
            
            # 如果发生了迁移，保存新格式
            if migrated:
                self.models = new_data
                self.save_models()
                messagebox.showinfo("提示", "模特数据已自动迁移为新格式")
            else:
                self.models = new_data
            
            return self.models
        except Exception as e:
            messagebox.showerror("错误", f"加载模特数据失败: {e}")
            return {}
    
    def save_models(self):
        """保存模特数据"""
        try:
            with open("models.json", "w", encoding="utf-8") as f:
                json.dump(self.models, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存模特数据失败: {e}")
            return False
    
    def update_model_list(self):
        """更新模特列表"""
        # 清空现有列表
        for item in self.model_tree.get_children():
            self.model_tree.delete(item)
        
        # 统计各模块数量
        pronhub_count = 0
        javdb_count = 0
        
        # 添加模特数据
        for model_name, model_info in self.models.items():
            if isinstance(model_info, dict):
                module = model_info.get("module", "JAVDB")
                url = model_info.get("url", "")
                
                # 统计
                if module == "PRONHUB":
                    pronhub_count += 1
                else:
                    javdb_count += 1
                
                # 根据模块筛选显示
                selected_module = self.model_module_var.get()
                if selected_module == "全部" or selected_module == module:
                    self.model_tree.insert("", tk.END, values=(model_name, module, url))
        
        # 更新统计信息
        self.model_count_var.set(f"模特数量: {len(self.models)} (PRONHUB: {pronhub_count}, JAVDB: {javdb_count})")
    
    def filter_models_by_module(self, event=None):
        """根据模块筛选模特"""
        self.update_model_list()
    
    def search_models(self):
        """搜索模特"""
        search_term = self.search_var.get().lower()
        selected_module = self.model_module_var.get()
        
        # 清空现有列表
        for item in self.model_tree.get_children():
            self.model_tree.delete(item)
        
        # 添加匹配的模特
        for model_name, model_info in self.models.items():
            if isinstance(model_info, dict):
                module = model_info.get("module", "JAVDB")
                url = model_info.get("url", "")
                
                # 根据模块筛选
                if selected_module == "全部" or selected_module == module:
                    # 搜索匹配
                    if search_term in model_name.lower() or search_term in url.lower():
                        self.model_tree.insert("", tk.END, values=(model_name, module, url))
    
    def add_model(self):
        """添加模特"""
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("添加模特")
        dialog.geometry("500x240")
        dialog.resizable(False, False)
        
        # 居中显示
        dialog.update_idletasks()
        x = (self.root.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"500x240+{x}+{y}")
        
        # 创建框架
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 模特名称
        ttk.Label(frame, text="模特名称: ").grid(row=0, column=0, sticky=tk.W, pady=10)
        model_name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=model_name_var, width=40).grid(row=0, column=1, sticky=tk.W, pady=10)
        
        # 模块选择
        ttk.Label(frame, text="模块类型: ").grid(row=1, column=0, sticky=tk.W, pady=10)
        module_var = tk.StringVar(value="JAVDB")
        module_combobox = ttk.Combobox(frame, textvariable=module_var, values=["PRONHUB", "JAVDB"], width=37, state="readonly")
        module_combobox.grid(row=1, column=1, sticky=tk.W, pady=10)
        
        # 链接
        ttk.Label(frame, text="链接: ").grid(row=2, column=0, sticky=tk.W, pady=10)
        url_var = tk.StringVar()
        ttk.Entry(frame, textvariable=url_var, width=40).grid(row=2, column=1, sticky=tk.W, pady=10)
        
        # 按钮
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        def on_ok():
            model_name = model_name_var.get().strip()
            url = url_var.get().strip()
            module = module_var.get()
            
            if not model_name:
                messagebox.showerror("错误", "模特名称不能为空")
                return
            
            if not url:
                messagebox.showerror("错误", "链接不能为空")
                return
            
            # 检查URL是否与选择的模块匹配
            if module == "JAVDB" and "javdb" not in url.lower():
                if not messagebox.askyesno("警告", f"选择的模块是JAVDB，但链接中不包含'javdb'。\n\n确定要继续吗？"):
                    return
            elif module == "PRONHUB" and "javdb" in url.lower():
                if not messagebox.askyesno("警告", f"选择的模块是PRONHUB，但链接中包含'javdb'。\n\n确定要继续吗？"):
                    return
            
            # 添加到模型字典（新格式）
            self.models[model_name] = {
                "module": module,
                "url": url
            }
            
            # 保存并更新列表
            if self.save_models():
                self.update_model_list()
                dialog.destroy()
                messagebox.showinfo("成功", "模特添加成功")
        
        ttk.Button(button_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
        
        # 等待对话框关闭
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)
    
    def refresh_public_ip(self):
        """刷新公网IP"""
        try:
            import requests
            
            # 加载配置
            config = self.load_config()
            proxy_config = config.get("network", {}).get("proxy", {})
            
            # 构建代理字典
            proxies = {}
            if proxy_config.get("enabled", False):
                proxy_type = proxy_config.get("type", "socks5")
                proxy_host = proxy_config.get("host", "").strip()
                proxy_port = proxy_config.get("port", "").strip()
                proxy_id = proxy_config.get("id", "").strip()
                proxy_password = proxy_config.get("password", "").strip()
                
                if proxy_host and proxy_port:
                    # 构建代理URL
                    if proxy_id and proxy_password:
                        proxy_url = f"{proxy_type}://{proxy_id}:{proxy_password}@{proxy_host}:{proxy_port}"
                    else:
                        proxy_url = f"{proxy_type}://{proxy_host}:{proxy_port}"
                    
                    proxies = {
                        "http": proxy_url,
                        "https": proxy_url
                    }
            
            # 尝试获取公网IP
            response = requests.get("https://api.ipify.org", proxies=proxies, timeout=10, verify=False)
            if response.status_code == 200:
                public_ip = response.text.strip()
                self.public_ip_var.set(public_ip)
                # 更新配置文件
                import yaml
                with open("config.yaml", "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                config["network"]["proxy"]["public_ip"] = public_ip
                with open("config.yaml", "w", encoding="utf-8") as f:
                    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                messagebox.showinfo("成功", f"公网IP已更新: {public_ip}")
            else:
                messagebox.showerror("错误", "获取公网IP失败")
        except Exception as e:
            messagebox.showerror("错误", f"获取公网IP失败: {e}")
    
    def ping_test(self):
        """网络连接测试"""
        try:
            import requests
            import time
            
            # 加载配置
            config = self.load_config()
            proxy_config = config.get("proxy", {})
            
            # 构建代理字典
            proxies = {}
            proxy_url = ""
            if proxy_config.get("enabled", False):
                proxy_host = proxy_config.get("host", "").strip()
                proxy_port = proxy_config.get("port", "").strip()
                proxy_id = proxy_config.get("id", "").strip()
                proxy_password = proxy_config.get("password", "").strip()
                
                if proxy_host and proxy_port:
                    # 构建代理URL
                    if proxy_id and proxy_password:
                        proxy_url = f"http://{proxy_id}:{proxy_password}@{proxy_host}:{proxy_port}"
                    else:
                        proxy_url = f"http://{proxy_host}:{proxy_port}"
                    
                    proxies = {
                        "http": proxy_url,
                        "https": proxy_url
                    }
            
            # 测试目标
            test_urls = ["https://www.baidu.com", "https://www.google.com"]
            results = []
            
            for url in test_urls:
                try:
                    start_time = time.time()
                    response = requests.get(url, proxies=proxies, timeout=5)
                    end_time = time.time()
                    results.append(f"{url}: 成功 ({response.status_code}) - {end_time - start_time:.2f}秒")
                except Exception as e:
                    results.append(f"{url}: 失败 - {e}")
            
            # 显示测试结果
            result_text = "网络连接测试结果:\n\n"
            result_text += "\n".join(results)
            
            # 添加代理信息
            if proxies and proxy_url:
                result_text += f"\n\n使用代理: {proxy_url}"
            else:
                result_text += "\n\n未使用代理（直接连接）"
            
            messagebox.showinfo("网络连接测试", result_text)
        except Exception as e:
            messagebox.showerror("错误", f"网络连接测试失败: {e}")
    
    def edit_model(self):
        """编辑模特"""
        # 获取选中的项
        selected_items = self.model_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请选择要编辑的模特")
            return
        
        # 获取选中项的数据
        item = selected_items[0]
        model_name, module, url = self.model_tree.item(item, "values")
        
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("编辑模特")
        dialog.geometry("500x240")
        dialog.resizable(False, False)
        
        # 居中显示
        dialog.update_idletasks()
        x = (self.root.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"500x240+{x}+{y}")
        
        # 创建框架
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 模特名称
        ttk.Label(frame, text="模特名称: ").grid(row=0, column=0, sticky=tk.W, pady=10)
        model_name_var = tk.StringVar(value=model_name)
        ttk.Entry(frame, textvariable=model_name_var, width=40).grid(row=0, column=1, sticky=tk.W, pady=10)
        
        # 模块选择
        ttk.Label(frame, text="模块类型: ").grid(row=1, column=0, sticky=tk.W, pady=10)
        module_var = tk.StringVar(value=module)
        module_combobox = ttk.Combobox(frame, textvariable=module_var, values=["PRONHUB", "JAVDB"], width=37, state="readonly")
        module_combobox.grid(row=1, column=1, sticky=tk.W, pady=10)
        
        # 链接
        ttk.Label(frame, text="链接: ").grid(row=2, column=0, sticky=tk.W, pady=10)
        url_var = tk.StringVar(value=url)
        ttk.Entry(frame, textvariable=url_var, width=40).grid(row=2, column=1, sticky=tk.W, pady=10)
        
        # 按钮
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        def on_ok():
            new_model_name = model_name_var.get().strip()
            new_module = module_var.get()
            new_url = url_var.get().strip()
            
            if not new_model_name:
                messagebox.showerror("错误", "模特名称不能为空")
                return
            
            if not new_url:
                messagebox.showerror("错误", "链接不能为空")
                return
            
            # 检查URL是否与选择的模块匹配
            if new_module == "JAVDB" and "javdb" not in new_url.lower():
                if not messagebox.askyesno("警告", f"选择的模块是JAVDB，但链接中不包含'javdb'。\n\n确定要继续吗？"):
                    return
            elif new_module == "PRONHUB" and "javdb" in new_url.lower():
                if not messagebox.askyesno("警告", f"选择的模块是PRONHUB，但链接中包含'javdb'。\n\n确定要继续吗？"):
                    return
            
            # 更新模型字典
            if new_model_name != model_name:
                # 如果名称改变，删除旧的，添加新的
                del self.models[model_name]
                self.models[new_model_name] = {
                    "module": new_module,
                    "url": new_url
                }
            else:
                # 只更新链接和模块
                self.models[model_name] = {
                    "module": new_module,
                    "url": new_url
                }
            
            # 保存并更新列表
            if self.save_models():
                self.update_model_list()
                dialog.destroy()
                messagebox.showinfo("成功", "模特编辑成功")
        
        ttk.Button(button_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
        
        # 等待对话框关闭
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)
    
    def delete_model(self):
        """删除模特"""
        # 获取选中的项
        selected_items = self.model_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请选择要删除的模特")
            return
        
        # 获取选中项的数据
        item = selected_items[0]
        model_name, _ = self.model_tree.item(item, "values")
        
        # 确认删除
        if messagebox.askyesno("确认", f"确定要删除模特 '{model_name}' 吗？"):
            # 从模型字典中删除
            if model_name in self.models:
                del self.models[model_name]
                
                # 保存并更新列表
                if self.save_models():
                    self.update_model_list()
                    messagebox.showinfo("成功", "模特删除成功")
    
    def refresh_models(self):
        """刷新模特列表"""
        self.models = self.load_models()
        self.update_model_list()
        messagebox.showinfo("成功", "模特列表已刷新")
    
    def export_models(self):
        """导出模特数据"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            title="导出模特数据"
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self.models, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("成功", f"模特数据已导出到: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")
    
    def import_models(self):
        """导入模特数据"""
        file_path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            title="导入模特数据"
        )
        
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    imported_models = json.load(f)
                
                # 确认导入
                if messagebox.askyesno("确认", f"确定要导入 {len(imported_models)} 个模特吗？"):
                    # 合并数据
                    self.models.update(imported_models)
                    
                    # 保存并更新列表
                    if self.save_models():
                        self.update_model_list()
                        messagebox.showinfo("成功", f"已导入 {len(imported_models)} 个模特")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {e}")
    
    def start_run(self):
        """开始运行查重脚本"""
        # 更新按钮状态
        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 更新状态
        self.status_var.set("运行中...")
        self.progress_var.set(0)
        
        # 清空日志
        self.log_text.delete(1.0, tk.END)
        
        # 启动线程
        self.running = True
        self.thread = threading.Thread(target=self.run_script)
        self.thread.daemon = True
        self.thread.start()
        
        # 开始轮询队列
        self.root.after(100, self.check_queue)
    
    def stop_run(self):
        """停止运行"""
        self.running = False
        self.status_var.set("停止中...")
    
    def run_script(self):
        """在线程中运行查重脚本"""
        try:
            # 获取所有目录
            dirs = [self.dir_listbox.get(i) for i in range(self.dir_listbox.size())]
            if not dirs:
                messagebox.showinfo("提示", "请至少添加一个本地目录")
                return
            
            # 导入核心模块（使用动态导入方式）
            import sys
            import os
            import importlib.util
            import logging
            
            # 配置日志捕获
            class QueueHandler(logging.Handler):
                def emit(self, record):
                    msg = self.format(record)
                    self.queue.put(("log", msg))
            
            # 获取核心模块路径
            if hasattr(sys, '_MEIPASS'):
                # 打包后的环境
                core_py_path = os.path.join(sys._MEIPASS, 'core', 'core.py')
            else:
                # 开发环境
                core_py_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core', 'core.py')
            
            # 动态导入core模块
            spec = importlib.util.spec_from_file_location("core.core", core_py_path)
            if spec and spec.loader:
                core_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(core_module)
                
                # 替换core模块的日志处理器
                original_logger = logging.getLogger()
                original_handlers = original_logger.handlers.copy()
                
                # 创建队列处理器
                queue_handler = QueueHandler()
                queue_handler.setLevel(logging.INFO)
                queue_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', '%Y-%m-%d %H:%M:%S'))
                queue_handler.queue = self.queue
                queue_handler.running = self.running
                
                # 清空原有处理器并添加队列处理器
                for handler in original_handlers:
                    original_logger.removeHandler(handler)
                original_logger.addHandler(queue_handler)
                
                # 运行脚本
                try:
                    # 传递一个函数，用于检查运行状态
                    def check_running():
                        return self.running
                    results = core_module.main(self.module_var.get(), dirs, self.scraper_var.get(), check_running)
                    
                    # 发送结果数据到GUI
                    if results:
                        self.queue.put(("results", results))
                finally:
                    # 恢复原有日志处理器
                    original_logger.removeHandler(queue_handler)
                    for handler in original_handlers:
                        original_logger.addHandler(handler)
                
                # 发送完成消息
                self.queue.put(("completed", "运行完成"))
            else:
                raise Exception(f"无法找到核心模块: {core_py_path}")
        except Exception as e:
            self.queue.put(("error", str(e)))
        finally:
            # 确保线程结束后更新按钮状态
            self.queue.put(("completed", "运行完成"))
    
    def check_queue(self):
        """检查队列，处理线程消息"""
        try:
            while not self.queue.empty():
                msg_type, msg = self.queue.get_nowait()
                
                if msg_type == "status":
                    self.status_var.set(msg)
                elif msg_type == "log":
                    self.log_text.insert(tk.END, msg + "\n")
                    self.log_text.see(tk.END)
                elif msg_type == "progress":
                    self.progress_var.set(msg)
                elif msg_type == "results":
                    # 更新结果显示标签页
                    self.update_results_display(msg)
                elif msg_type == "completed":
                    self.status_var.set("运行完成")
                    self.progress_var.set(100)
                    self.run_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
                    messagebox.showinfo("成功", "查重脚本运行完成")
                elif msg_type == "error":
                    self.status_var.set("运行出错")
                    self.run_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
                    messagebox.showerror("错误", f"运行出错: {msg}")
        except queue.Empty:
            pass
        
        # 继续轮询，不管是否正在运行，确保所有日志都能被处理
        self.root.after(100, self.check_queue)
    
    def open_config(self):
        """打开配置界面"""
        self.show_config_dialog()
    
    def show_config_dialog(self):
        """显示配置对话框"""
        # 加载当前配置
        try:
            import yaml
            with open("config.yaml", "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            messagebox.showerror("错误", f"加载配置文件失败: {e}")
            return
        
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("配置设置")
        dialog.geometry("600x500")
        dialog.resizable(False, False)
        
        # 居中显示
        dialog.update_idletasks()
        x = (self.root.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"600x500+{x}+{y}")
        
        # 创建主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建笔记本（标签页）
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 基本设置标签页
        basic_frame = ttk.Frame(notebook, padding="10")
        notebook.add(basic_frame, text="基本设置")
        
        # 输出目录
        ttk.Label(basic_frame, text="输出目录: ").grid(row=0, column=0, sticky=tk.W, pady=5)
        output_dir_var = tk.StringVar(value=config.get("output_dir", "output"))
        ttk.Entry(basic_frame, textvariable=output_dir_var, width=40).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 日志目录
        ttk.Label(basic_frame, text="日志目录: ").grid(row=1, column=0, sticky=tk.W, pady=5)
        log_dir_var = tk.StringVar(value=config.get("log_dir", "log"))
        ttk.Entry(basic_frame, textvariable=log_dir_var, width=40).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 视频扩展名
        ttk.Label(basic_frame, text="视频扩展名: ").grid(row=2, column=0, sticky=tk.W, pady=5)
        video_exts_var = tk.StringVar(value=", ".join(config.get("video_extensions", ["mp4", "avi", "mov"])))
        ttk.Entry(basic_frame, textvariable=video_exts_var, width=40).grid(row=2, column=1, sticky=tk.W, pady=5)
        ttk.Label(basic_frame, text="（用逗号分隔）").grid(row=2, column=2, sticky=tk.W, pady=5)
        
        # 最大翻页
        ttk.Label(basic_frame, text="最大翻页: ").grid(row=3, column=0, sticky=tk.W, pady=5)
        max_pages_var = tk.StringVar(value=str(config.get("max_pages", -1)))
        ttk.Entry(basic_frame, textvariable=max_pages_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=5)
        ttk.Label(basic_frame, text="（-1表示无限制）").grid(row=3, column=2, sticky=tk.W, pady=5)
        
        # 延时设置
        ttk.Label(basic_frame, text="页面间延时: ").grid(row=4, column=0, sticky=tk.W, pady=5)
        delay_min_var = tk.StringVar(value=str(config.get("delay_between_pages", {}).get("min", 2.0)))
        delay_max_var = tk.StringVar(value=str(config.get("delay_between_pages", {}).get("max", 3.5)))
        ttk.Label(basic_frame, text="最小: ").grid(row=4, column=1, sticky=tk.W, pady=5)
        ttk.Entry(basic_frame, textvariable=delay_min_var, width=8).grid(row=4, column=1, sticky=tk.W, padx=(40, 0), pady=5)
        ttk.Label(basic_frame, text="最大: ").grid(row=4, column=1, sticky=tk.W, padx=(120, 0), pady=5)
        ttk.Entry(basic_frame, textvariable=delay_max_var, width=8).grid(row=4, column=1, sticky=tk.W, padx=(160, 0), pady=5)
        
        # 重试次数
        ttk.Label(basic_frame, text="失败重试次数: ").grid(row=5, column=0, sticky=tk.W, pady=5)
        retry_var = tk.StringVar(value=str(config.get("retry_on_fail", 2)))
        ttk.Entry(basic_frame, textvariable=retry_var, width=10).grid(row=5, column=1, sticky=tk.W, pady=5)
        
        # 性能设置标签页
        perf_frame = ttk.Frame(notebook, padding="10")
        notebook.add(perf_frame, text="性能设置")
        
        # 多线程配置
        multithreading_config = config.get("multithreading", {})
        
        # 多线程启用复选框
        mt_enabled_var = tk.BooleanVar(value=multithreading_config.get("enabled", True))
        ttk.Checkbutton(perf_frame, text="启用多线程", variable=mt_enabled_var).grid(row=0, column=0, sticky=tk.W, pady=10)
        
        # 工作线程数
        ttk.Label(perf_frame, text="工作线程数: ").grid(row=1, column=0, sticky=tk.W, pady=5)
        mt_workers_var = tk.StringVar(value=str(multithreading_config.get("max_workers", 3)))
        ttk.Entry(perf_frame, textvariable=mt_workers_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Label(perf_frame, text="（建议3-5个）").grid(row=1, column=2, sticky=tk.W, pady=5)
        
        # 代理设置标签页
        proxy_frame = ttk.Frame(notebook, padding="10")
        notebook.add(proxy_frame, text="代理设置")
        
        # 代理启用复选框
        proxy_enabled_var = tk.BooleanVar(value=config.get("network", {}).get("proxy", {}).get("enabled", False))
        proxy_check = ttk.Checkbutton(proxy_frame, text="代理", variable=proxy_enabled_var)
        proxy_check.grid(row=0, column=0, sticky=tk.W, pady=10)
        
        # 代理类型选择
        ttk.Label(proxy_frame, text="类型: ").grid(row=0, column=1, sticky=tk.W, pady=5)
        proxy_type_var = tk.StringVar(value=config.get("network", {}).get("proxy", {}).get("type", "socks5"))
        proxy_type_frame = ttk.Frame(proxy_frame)
        proxy_type_frame.grid(row=0, column=2, sticky=tk.W, pady=5)
        ttk.Radiobutton(proxy_type_frame, text="HTTP", value="http", variable=proxy_type_var).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(proxy_type_frame, text="SOCKS5", value="socks5", variable=proxy_type_var).pack(side=tk.LEFT, padx=5)
        
        # 代理服务器设置
        proxy_frame.grid_columnconfigure(0, weight=1)
        proxy_frame.grid_columnconfigure(1, weight=1)
        proxy_frame.grid_columnconfigure(2, weight=1)
        
        ttk.Label(proxy_frame, text="主机: ").grid(row=1, column=0, sticky=tk.W, pady=5)
        proxy_host_var = tk.StringVar(value=config.get("network", {}).get("proxy", {}).get("host", "127.0.0.1"))
        ttk.Entry(proxy_frame, textvariable=proxy_host_var, width=20).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(proxy_frame, text="端口: ").grid(row=1, column=2, sticky=tk.W, pady=5)
        proxy_port_var = tk.StringVar(value=config.get("network", {}).get("proxy", {}).get("port", "10808"))
        ttk.Entry(proxy_frame, textvariable=proxy_port_var, width=10).grid(row=1, column=3, sticky=tk.W, pady=5)
        
        # 账号密码设置
        ttk.Radiobutton(proxy_frame, text="账号/密码", value=1).grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(proxy_frame, text="ID: ").grid(row=2, column=1, sticky=tk.W, pady=5)
        proxy_id_var = tk.StringVar(value=config.get("network", {}).get("proxy", {}).get("id", ""))
        ttk.Entry(proxy_frame, textvariable=proxy_id_var, width=20).grid(row=2, column=2, sticky=tk.W, pady=5)
        
        ttk.Label(proxy_frame, text="Password: ").grid(row=3, column=1, sticky=tk.W, pady=5)
        proxy_password_var = tk.StringVar(value=config.get("network", {}).get("proxy", {}).get("password", ""))
        ttk.Entry(proxy_frame, textvariable=proxy_password_var, width=20, show="*").grid(row=3, column=2, sticky=tk.W, pady=5)
        
        # 下载限速选项
        download_limit_var = tk.BooleanVar(value=config.get("network", {}).get("proxy", {}).get("download_limit", False))
        ttk.Checkbutton(proxy_frame, text="下载限速", variable=download_limit_var).grid(row=4, column=0, sticky=tk.W, pady=5)
        
        # 绕过DPI选项
        bypass_dpi_var = tk.BooleanVar(value=config.get("network", {}).get("proxy", {}).get("bypass_dpi", False))
        ttk.Checkbutton(proxy_frame, text="绕过DPI", variable=bypass_dpi_var).grid(row=5, column=0, sticky=tk.W, pady=5)
        
        # 公网IP显示
        ttk.Label(proxy_frame, text="IP 公共: ").grid(row=6, column=0, sticky=tk.W, pady=10)
        self.public_ip_var = tk.StringVar(value=config.get("network", {}).get("proxy", {}).get("public_ip", "000.000.000.000"))
        ttk.Entry(proxy_frame, textvariable=self.public_ip_var, width=20, state="readonly").grid(row=6, column=1, sticky=tk.W, pady=10)
        
        # 刷新IP按钮
        ttk.Button(proxy_frame, text="刷新", command=self.refresh_public_ip).grid(row=6, column=2, sticky=tk.W, pady=10)
        
        # PING测试按钮
        ttk.Button(proxy_frame, text="PING测试", command=self.ping_test).grid(row=7, column=0, columnspan=4, pady=10)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame, padding="10")
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 保存按钮
        def save_config():
            try:
                # 更新配置
                config["output_dir"] = output_dir_var.get().strip()
                config["log_dir"] = log_dir_var.get().strip()
                config["video_extensions"] = [ext.strip() for ext in video_exts_var.get().split(",") if ext.strip()]
                config["max_pages"] = int(max_pages_var.get())
                config["delay_between_pages"] = {
                    "min": float(delay_min_var.get()),
                    "max": float(delay_max_var.get())
                }
                config["retry_on_fail"] = int(retry_var.get())
                
                # 保存多线程配置
                if "multithreading" not in config:
                    config["multithreading"] = {}
                config["multithreading"]["enabled"] = mt_enabled_var.get()
                config["multithreading"]["max_workers"] = int(mt_workers_var.get())
                
                # 确保 network 键存在
                if "network" not in config:
                    config["network"] = {}
                # 保存代理配置
                config["network"]["proxy"] = {
                    "enabled": proxy_enabled_var.get(),
                    "type": proxy_type_var.get(),
                    "host": proxy_host_var.get().strip(),
                    "port": proxy_port_var.get().strip(),
                    "id": proxy_id_var.get().strip(),
                    "password": proxy_password_var.get().strip(),
                    "download_limit": download_limit_var.get(),
                    "bypass_dpi": bypass_dpi_var.get(),
                    "public_ip": self.public_ip_var.get().strip(),
                    "http": self.generate_proxy_url(proxy_enabled_var.get(), proxy_type_var.get(), proxy_host_var.get().strip(), proxy_port_var.get().strip(), proxy_id_var.get().strip(), proxy_password_var.get().strip()),
                    "https": self.generate_proxy_url(proxy_enabled_var.get(), proxy_type_var.get(), proxy_host_var.get().strip(), proxy_port_var.get().strip(), proxy_id_var.get().strip(), proxy_password_var.get().strip())
                }
                
                # 保存配置 - 使用默认模板，保留注释
                # 1. 加载默认配置模板
                default_config = yaml.safe_load(DEFAULT_CONFIG)
                
                # 2. 更新默认配置中的字段
                def update_config(target, source):
                    for key, value in source.items():
                        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                            update_config(target[key], value)
                        else:
                            target[key] = value
                
                update_config(default_config, config)
                
                # 3. 生成带注释的配置文件
                # 读取默认模板的文本内容
                lines = DEFAULT_CONFIG.split('\n')
                output_lines = []
                current_path = []
                
                def get_value_from_config(path):
                    value = default_config
                    for key in path:
                        if isinstance(value, dict) and key in value:
                            value = value[key]
                        else:
                            return None
                    return value
                
                for line in lines:
                    stripped_line = line.strip()
                    
                    # 处理注释行
                    if stripped_line.startswith('#'):
                        output_lines.append(line)
                    # 处理空行
                    elif not stripped_line:
                        output_lines.append(line)
                    # 处理键值对
                    elif ':' in stripped_line and not stripped_line.endswith(':'):
                        parts = stripped_line.split(':', 1)
                        key = parts[0].strip()
                        # 检查当前路径
                        while current_path and not get_value_from_config(current_path + [key]):
                            current_path.pop()
                        # 获取值
                        value = get_value_from_config(current_path + [key])
                        if value is not None:
                            # 更新值
                            if isinstance(value, bool):
                                value_str = str(value).lower()
                            elif isinstance(value, list):
                                value_str = '[' + ', '.join(f'"{item}"' for item in value) + ']'
                            else:
                                value_str = str(value)
                            # 保留注释
                            comment_part = parts[1].split('#', 1) if '#' in parts[1] else ['', '']
                            if comment_part[1]:
                                output_lines.append(f"{parts[0]}: {value_str}  # {comment_part[1].strip()}")
                            else:
                                output_lines.append(f"{parts[0]}: {value_str}")
                        else:
                            output_lines.append(line)
                    # 处理字典键
                    elif stripped_line.endswith(':'):
                        key = stripped_line[:-1].strip()
                        # 检查当前路径
                        while current_path and not get_value_from_config(current_path + [key]):
                            current_path.pop()
                        # 检查是否存在该键
                        if get_value_from_config(current_path + [key]) is not None:
                            current_path.append(key)
                        output_lines.append(line)
                    # 处理列表项
                    elif stripped_line.startswith('- '):
                        # 检查当前路径
                        if current_path:
                            parent_value = get_value_from_config(current_path)
                            if isinstance(parent_value, list):
                                # 这里简化处理，直接保留原始行
                                output_lines.append(line)
                            else:
                                output_lines.append(line)
                        else:
                            output_lines.append(line)
                    else:
                        output_lines.append(line)
                
                # 4. 写入配置文件
                with open("config.yaml", "w", encoding="utf-8") as f:
                    f.write('\n'.join(output_lines))
                
                messagebox.showinfo("成功", "配置已保存")
                dialog.destroy()
            except Exception as e:
                # 如果复杂保存失败，使用简单方法保存
                try:
                    with open("config.yaml", "w", encoding="utf-8") as f:
                        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                    messagebox.showinfo("成功", "配置已保存")
                    dialog.destroy()
                except Exception as e2:
                    messagebox.showerror("错误", f"保存配置失败: {e}")
        
        ttk.Button(button_frame, text="保存", command=save_config, width=15).pack(side=tk.RIGHT, padx=10)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.RIGHT, padx=10)
        
        # 等待对话框关闭
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)
    
    def open_cache_dir(self):
        """打开缓存目录"""
        try:
            cache_dir = os.path.join("output", "cache")
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            os.startfile(cache_dir)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开缓存目录: {e}")
    
    def open_log_dir(self):
        """打开日志目录"""
        try:
            log_dir = "log"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            os.startfile(log_dir)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开日志目录: {e}")
    
    def update_results_display(self, results):
        """更新结果显示标签页"""
        try:
            # 存储当前结果供下载使用
            self.current_results = {result.model_name: result for result in results}
            
            # 清空现有结果
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
            
            # 统计信息
            processed_count = 0
            failed_count = 0
            missing_count = 0
            
            # 处理结果数据
            for result in results:
                if result.success:
                    processed_count += 1
                    # 添加缺失视频到列表
                    if hasattr(result, 'missing_with_urls') and result.missing_with_urls:
                        for title, url in result.missing_with_urls:
                            self.result_tree.insert("", tk.END, values=(result.model_name, title, url))
                            missing_count += 1
                else:
                    failed_count += 1
            
            # 更新统计信息
            self.stats_vars["processed"].set(f"成功处理: {processed_count}")
            self.stats_vars["failed"].set(f"处理失败: {failed_count}")
            self.stats_vars["missing"].set(f"发现缺失: {missing_count}")
            
            # 切换到结果显示标签页
            self.notebook.select(self.result_tab)
            
        except Exception as e:
            messagebox.showerror("错误", f"更新结果显示失败: {e}")
    
    def export_results(self):
        """导出结果"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            title="导出结果"
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"模特查重结果 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n")
                    
                    # 写入统计信息
                    for key, var in self.stats_vars.items():
                        f.write(var.get() + "\n")
                    f.write("=" * 80 + "\n")
                    
                    # 写入缺失视频
                    f.write("缺失视频列表:\n")
                    f.write("-" * 80 + "\n")
                    
                    for item in self.result_tree.get_children():
                        model, title, url = self.result_tree.item(item, "values")
                        f.write(f"模特: {model}\n")
                        f.write(f"标题: {title}\n")
                        f.write(f"链接: {url}\n")
                        f.write("-" * 80 + "\n")
                
                messagebox.showinfo("成功", f"结果已导出到: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
使用说明:

1. 模特管理:
   - 添加: 点击"添加模特"按钮，输入模特名称和链接
   - 编辑: 选择模特后点击"编辑模特"按钮
   - 删除: 选择模特后点击"删除模特"按钮
   - 搜索: 在搜索框中输入关键词，点击"搜索"按钮

2. 运行控制:
   - 开始运行: 点击"开始运行"按钮
   - 停止运行: 点击"停止运行"按钮
   - 配置: 可设置是否使用Selenium、最大翻页和页面间延时

3. 结果显示:
   - 查看统计信息和缺失视频列表
   - 点击"导出结果"按钮导出结果

4. 工具:
   - 打开配置文件: 编辑配置参数
   - 打开缓存目录: 查看缓存文件
   - 打开日志目录: 查看运行日志

注意:
- 运行前请确保网络连接正常
- 首次运行会创建必要的目录结构
- 缓存文件会保存在output/cache目录中
"""
        
        messagebox.showinfo("使用说明", help_text)
    
    def add_local_dir(self):
        """添加本地目录"""
        directory = filedialog.askdirectory(title="选择本地视频目录")
        if directory:
            # 检查目录是否已存在
            for i in range(self.dir_listbox.size()):
                if self.dir_listbox.get(i) == directory:
                    messagebox.showinfo("提示", "该目录已存在于列表中")
                    return
            # 添加到列表
            self.dir_listbox.insert(tk.END, directory)
            # 保存目录列表
            self.save_local_dirs()
    
    def save_local_dirs(self):
        """保存本地目录列表"""
        try:
            dirs = [self.dir_listbox.get(i) for i in range(self.dir_listbox.size())]
            with open("local_dirs.json", "w", encoding="utf-8") as f:
                json.dump(dirs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass
    
    def load_local_dirs(self):
        """加载本地目录列表"""
        try:
            if os.path.exists("local_dirs.json"):
                with open("local_dirs.json", "r", encoding="utf-8") as f:
                    dirs = json.load(f)
                    for directory in dirs:
                        self.dir_listbox.insert(tk.END, directory)
        except Exception as e:
            pass
    
    def remove_local_dir(self):
        """删除选中的本地目录"""
        selected = self.dir_listbox.curselection()
        if selected:
            self.dir_listbox.delete(selected)
            # 保存目录列表
            self.save_local_dirs()
    
    def show_about(self):
        """显示关于信息"""
        about_text = """
模特查重管理系统 v1.0

功能:
- 管理模特信息
- 自动查重视频
- 缓存已查询结果
- 导出运行结果

作者: dragonSoul
日期: 2026-01-25
"""
        
        messagebox.showinfo("关于", about_text)
    
    def _update_download_buttons_state(self, *args):
        """根据选择的模块更新下载按钮状态"""
        selected_module = self.model_module_var.get()
        
        # 如果选择JAVDB模块，禁用所有下载按钮
        if selected_module == "JAVDB":
            self.download_selected_btn.config(state=tk.DISABLED)
            self.download_all_btn.config(state=tk.DISABLED)
            self.download_complete_btn.config(state=tk.DISABLED)
        else:
            self.download_selected_btn.config(state=tk.NORMAL)
            self.download_all_btn.config(state=tk.NORMAL)
            self.download_complete_btn.config(state=tk.NORMAL)
    
    def download_selected_videos(self):
        """下载选中的缺失视频"""
        try:
            # 获取选中的项目
            selected_items = self.result_tree.selection()
            if not selected_items:
                messagebox.showwarning("提示", "请先选择要下载的视频")
                return
            
            # 收集下载信息
            download_items = []
            for item in selected_items:
                model, title, url = self.result_tree.item(item, "values")
                if url and url.strip():
                    download_items.append((model, title, url.strip()))
            
            if not download_items:
                messagebox.showwarning("提示", "选中的项目没有有效的下载链接")
                return
            
            # 确认下载
            if not messagebox.askyesno("确认下载", f"确定要下载选中的 {len(download_items)} 个视频吗？"):
                return
            
            # 开始下载
            self._download_videos(download_items)
            
        except Exception as e:
            messagebox.showerror("错误", f"下载失败: {e}")
    
    def download_all_missing_videos(self):
        """下载所有缺失视频"""
        try:
            # 收集所有缺失视频
            download_items = []
            for item in self.result_tree.get_children():
                model, title, url = self.result_tree.item(item, "values")
                if url and url.strip():
                    download_items.append((model, title, url.strip()))
            
            if not download_items:
                messagebox.showwarning("提示", "没有可下载的视频")
                return
            
            # 确认下载
            if not messagebox.askyesno("确认下载", f"确定要下载所有 {len(download_items)} 个缺失视频吗？\n注意：这可能需要很长时间！"):
                return
            
            # 开始下载
            self._download_videos(download_items)
            
        except Exception as e:
            messagebox.showerror("错误", f"下载失败: {e}")
    
    def _download_videos(self, download_items):
        """执行视频下载"""
        try:
            # 导入下载模块
            from core.modules.pronhub.downloader import PornhubDownloader
            import threading
            import queue
            import logging
            
            # 创建下载进度对话框
            progress_window = tk.Toplevel(self.root)
            progress_window.title("下载进度")
            progress_window.geometry("600x400")
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            # 进度显示
            ttk.Label(progress_window, text="下载进度:", font=("Arial", 12, "bold")).pack(pady=10)
            
            progress_text = tk.Text(progress_window, height=15, width=70)
            progress_scrollbar = ttk.Scrollbar(progress_window, orient=tk.VERTICAL, command=progress_text.yview)
            progress_text.configure(yscrollcommand=progress_scrollbar.set)
            
            progress_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
            progress_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
            
            # 进度队列
            progress_queue = queue.Queue()
            
            def download_worker():
                """下载工作线程"""
                try:
                    # 获取配置
                    config = self.load_config()
                    
                    # 设置日志
                    logger = logging.getLogger(__name__)
                    
                    # 创建下载器
                    downloader = PornhubDownloader(config)
                    
                    total_count = len(download_items)
                    for i, (model, title, url) in enumerate(download_items, 1):
                        try:
                            progress_queue.put(f"开始下载 ({i}/{total_count}): {title[:50]}...")
                            
                            # 确定保存目录（模特目录）
                            save_dir = None
                            # 查找模特的本地目录
                            for result_key, result_value in getattr(self, 'current_results', {}).items():
                                if hasattr(result_value, 'model_name') and result_value.model_name == model:
                                    if hasattr(result_value, 'local_folder_full') and result_value.local_folder_full:
                                        save_dir = result_value.local_folder_full
                                    break
                            
                            # 执行下载
                            result = downloader.download_single_video(url, save_dir)
                            
                            if result['success']:
                                progress_queue.put(f"✅ 下载成功: {title[:50]}... -> {result.get('file_path', 'N/A')}")
                            else:
                                progress_queue.put(f"❌ 下载失败: {title[:50]}... - {result.get('message', result.get('error', 'Unknown error'))}")
                            
                        except Exception as e:
                            progress_queue.put(f"❌ 下载异常: {title[:50]}... - {str(e)}")
                    
                    progress_queue.put("下载任务完成！")
                    
                except Exception as e:
                    progress_queue.put(f"下载器错误: {str(e)}")
                finally:
                    progress_queue.put("DOWNLOAD_COMPLETE")
            
            def update_progress():
                """更新进度显示"""
                try:
                    while True:
                        try:
                            message = progress_queue.get_nowait()
                            if message == "DOWNLOAD_COMPLETE":
                                ttk.Button(progress_window, text="关闭", command=progress_window.destroy).pack(pady=10)
                                break
                            else:
                                progress_text.insert(tk.END, message + "\n")
                                progress_text.see(tk.END)
                                progress_window.update()
                        except queue.Empty:
                            break
                    
                    # 继续检查进度
                    if progress_window.winfo_exists():
                        progress_window.after(100, update_progress)
                except:
                    pass
            
            # 启动下载线程
            download_thread = threading.Thread(target=download_worker, daemon=True)
            download_thread.start()
            
            # 启动进度更新
            update_progress()
            
            # 显示窗口
            progress_window.mainloop()
            
        except ImportError as e:
            messagebox.showerror("错误", f"下载模块导入失败: {e}\n\n请确保已安装所有依赖：\npip install yt-dlp requests beautifulsoup4 PyYAML")
        except Exception as e:
            messagebox.showerror("错误", f"下载失败: {e}\n\n请检查网络连接和代理设置")
    
    def download_complete_model_directories(self):
        """完整下载模特目录"""
        try:
            # 检查是否有结果数据
            if not hasattr(self, 'current_results') or not self.current_results:
                messagebox.showwarning("提示", "请先运行查重分析获取模特数据")
                return
            
            # 创建模特选择对话框
            dialog = tk.Toplevel(self.root)
            dialog.title("完整下载模特目录")
            dialog.geometry("500x400")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 说明
            ttk.Label(dialog, text="选择要完整下载的模特目录:", font=("Arial", 12, "bold")).pack(pady=10)
            ttk.Label(dialog, text="⚠️ 完整下载会下载该模特的所有视频，可能需要很长时间", foreground="red").pack(pady=5)
            
            # 模特列表框架
            list_frame = ttk.Frame(dialog)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 创建带滚动条的列表框
            scrollbar = ttk.Scrollbar(list_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            model_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar.set)
            model_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=model_listbox.yview)
            
            # 填充模特列表
            model_names = []
            for model_name, result in self.current_results.items():
                if result.success and result.url:
                    model_listbox.insert(tk.END, f"{model_name} (本地: {result.local_count}, 缺失: {result.missing_count})")
                    model_names.append(model_name)
            
            # 选项框架
            options_frame = ttk.Frame(dialog)
            options_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # 最大下载数量
            ttk.Label(options_frame, text="每个模特最大下载数量:").pack(side=tk.LEFT)
            max_videos_var = tk.StringVar(value="0")  # 0表示无限制
            max_videos_entry = ttk.Entry(options_frame, textvariable=max_videos_var, width=10)
            max_videos_entry.pack(side=tk.LEFT, padx=5)
            ttk.Label(options_frame, text="(0=无限制)").pack(side=tk.LEFT)
            
            # 按钮框架
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            def start_download():
                """开始下载"""
                selected_indices = model_listbox.curselection()
                if not selected_indices:
                    messagebox.showwarning("提示", "请选择至少一个模特")
                    return
                
                # 获取选择的模特
                selected_models = []
                for idx in selected_indices:
                    model_name = model_names[idx]
                    result = self.current_results[model_name]
                    if result.success and result.url:
                        selected_models.append((model_name, result.url, result.local_folder_full))
                
                # 获取最大下载数量
                try:
                    max_videos = int(max_videos_var.get()) if max_videos_var.get().strip() else 0
                except ValueError:
                    max_videos = 0
                
                # 确认下载
                total_videos_estimate = len(selected_models) * (max_videos if max_videos > 0 else 50)  # 估算
                confirm_msg = f"确定要完整下载 {len(selected_models)} 个模特的目录吗？\n"
                confirm_msg += f"预计下载大量视频（可能超过 {total_videos_estimate} 个）\n"
                confirm_msg += "这将消耗大量时间和存储空间！"
                
                if not messagebox.askyesno("确认下载", confirm_msg):
                    return
                
                # 关闭对话框
                dialog.destroy()
                
                # 开始下载
                self._download_complete_directories(selected_models, max_videos)
            
            ttk.Button(button_frame, text="开始下载", command=start_download).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
            
            # 居中显示
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"+{x}+{y}")
            
            dialog.mainloop()
            
        except Exception as e:
            messagebox.showerror("错误", f"打开模特选择对话框失败: {e}")
    
    def _download_complete_directories(self, models_info, max_videos_per_model=0):
        """执行完整目录下载"""
        try:
            # 导入批量下载函数
            from core.modules.pronhub.downloader import batch_download_models
            import threading
            import queue
            
            # 创建下载进度对话框
            progress_window = tk.Toplevel(self.root)
            progress_window.title("完整目录下载进度")
            progress_window.geometry("700x500")
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            # 进度显示
            ttk.Label(progress_window, text="完整目录下载进度:", font=("Arial", 12, "bold")).pack(pady=10)
            
            progress_text = tk.Text(progress_window, height=20, width=80)
            progress_scrollbar = ttk.Scrollbar(progress_window, orient=tk.VERTICAL, command=progress_text.yview)
            progress_text.configure(yscrollcommand=progress_scrollbar.set)
            
            progress_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
            progress_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
            
            # 进度队列
            progress_queue = queue.Queue()
            
            def download_worker():
                """下载工作线程"""
                try:
                    # 获取配置
                    config = self.load_config()
                    
                    def progress_callback(msg):
                        progress_queue.put(msg)
                    
                    # 执行批量下载
                    result = batch_download_models(
                        models_info=models_info,
                        base_save_dir=None,  # 使用默认输出目录
                        config=config,
                        max_videos_per_model=max_videos_per_model if max_videos_per_model > 0 else None,
                        progress_callback=progress_callback
                    )
                    
                    progress_queue.put("=" * 60)
                    progress_queue.put("批量下载完成！")
                    progress_queue.put(f"总模特数: {result['total_models']}")
                    progress_queue.put(f"成功模特数: {result['successful_models']}")
                    progress_queue.put(f"失败模特数: {result['failed_models']}")
                    progress_queue.put(f"总视频数: {result['total_videos']}")
                    progress_queue.put(f"已下载数: {result['total_downloaded']}")
                    progress_queue.put(f"总大小: {result['total_size'] / (1024*1024*1024):.2f} GB")
                    progress_queue.put("=" * 60)
                    
                    # 显示详细结果
                    for model_result in result.get('model_results', []):
                        model_name = model_result.get('model_name', 'Unknown')
                        if model_result.get('success'):
                            progress_queue.put(f"\n✅ {model_name}:")
                            progress_queue.put(f"  成功: {model_result.get('successful_downloads', 0)}")
                            progress_queue.put(f"  失败: {model_result.get('failed_downloads', 0)}")
                            progress_queue.put(f"  跳过: {model_result.get('skipped_downloads', 0)}")
                        else:
                            progress_queue.put(f"\n❌ {model_name}: {model_result.get('message', 'Unknown error')}")
                    
                    progress_queue.put("DOWNLOAD_COMPLETE")
                    
                except Exception as e:
                    progress_queue.put(f"批量下载器错误: {str(e)}")
                    progress_queue.put("DOWNLOAD_COMPLETE")
            
            def update_progress():
                """更新进度显示"""
                try:
                    while True:
                        try:
                            message = progress_queue.get_nowait()
                            if message == "DOWNLOAD_COMPLETE":
                                ttk.Button(progress_window, text="关闭", command=progress_window.destroy).pack(pady=10)
                                break
                            else:
                                progress_text.insert(tk.END, message + "\n")
                                progress_text.see(tk.END)
                                progress_window.update()
                        except queue.Empty:
                            break
                    
                    # 继续检查进度
                    if progress_window.winfo_exists():
                        progress_window.after(100, update_progress)
                except:
                    pass
            
            # 启动下载线程
            download_thread = threading.Thread(target=download_worker, daemon=True)
            download_thread.start()
            
            # 启动进度更新
            update_progress()
            
            # 显示窗口
            progress_window.mainloop()
            
        except ImportError as e:
            messagebox.showerror("错误", f"下载模块导入失败: {e}\n请确保已安装 yt-dlp: pip install yt-dlp")
        except Exception as e:
            messagebox.showerror("错误", f"完整目录下载失败: {e}")
    
    def download_selected_models_complete(self):
        """下载选中模特的完整目录"""
        try:
            # 获取选中的模特
            selected_items = self.model_tree.selection()
            if not selected_items:
                messagebox.showwarning("提示", "请先选择要下载的模特")
                return
            
            selected_models = []
            for item in selected_items:
                model_name = self.model_tree.item(item, "values")[0]
                url = self.model_tree.item(item, "values")[1]
                if url and url.strip():
                    selected_models.append((model_name, url.strip(), None))
            
            if not selected_models:
                messagebox.showwarning("提示", "选中的模特没有有效的URL")
                return
            
            # 询问最大下载数量
            max_videos_dialog = tk.Toplevel(self.root)
            max_videos_dialog.title("下载设置")
            max_videos_dialog.geometry("300x150")
            max_videos_dialog.transient(self.root)
            max_videos_dialog.grab_set()
            
            ttk.Label(max_videos_dialog, text="每个模特最大下载数量:", font=("Arial", 10)).pack(pady=20)
            
            max_videos_var = tk.StringVar(value="0")
            ttk.Entry(max_videos_dialog, textvariable=max_videos_var, width=10).pack(pady=10)
            ttk.Label(max_videos_dialog, text="(0=无限制)").pack()
            
            def confirm_download():
                try:
                    max_videos = int(max_videos_var.get()) if max_videos_var.get().strip() else 0
                    max_videos_dialog.destroy()
                    
                    # 确认下载
                    confirm_msg = f"确定要完整下载 {len(selected_models)} 个选中模特的目录吗？\n"
                    confirm_msg += "这将下载每个模特的所有视频！"
                    
                    if messagebox.askyesno("确认下载", confirm_msg):
                        self._download_complete_directories(selected_models, max_videos)
                except ValueError:
                    messagebox.showerror("错误", "请输入有效的数字")
            
            button_frame = ttk.Frame(max_videos_dialog)
            button_frame.pack(pady=20)
            ttk.Button(button_frame, text="确定", command=confirm_download).pack(side=tk.LEFT, padx=10)
            ttk.Button(button_frame, text="取消", command=max_videos_dialog.destroy).pack(side=tk.LEFT, padx=10)
            
            # 居中显示
            max_videos_dialog.update_idletasks()
            x = (max_videos_dialog.winfo_screenwidth() // 2) - (max_videos_dialog.winfo_width() // 2)
            y = (max_videos_dialog.winfo_screenheight() // 2) - (max_videos_dialog.winfo_height() // 2)
            max_videos_dialog.geometry(f"+{x}+{y}")
            
            max_videos_dialog.mainloop()
            
        except Exception as e:
            messagebox.showerror("错误", f"下载选中模特失败: {e}")
    
    def download_all_models_complete(self):
        """批量下载所有模特的完整目录"""
        try:
            # 获取所有模特
            all_models = []
            for item in self.model_tree.get_children():
                model_name = self.model_tree.item(item, "values")[0]
                url = self.model_tree.item(item, "values")[1]
                if url and url.strip():
                    all_models.append((model_name, url.strip(), None))
            
            if not all_models:
                messagebox.showwarning("提示", "没有可下载的模特")
                return
            
            # 询问最大下载数量
            max_videos_dialog = tk.Toplevel(self.root)
            max_videos_dialog.title("批量下载设置")
            max_videos_dialog.geometry("300x150")
            max_videos_dialog.transient(self.root)
            max_videos_dialog.grab_set()
            
            ttk.Label(max_videos_dialog, text="每个模特最大下载数量:", font=("Arial", 10)).pack(pady=20)
            
            max_videos_var = tk.StringVar(value="50")  # 默认限制50个
            ttk.Entry(max_videos_dialog, textvariable=max_videos_var, width=10).pack(pady=10)
            ttk.Label(max_videos_dialog, text="(0=无限制)").pack()
            
            def confirm_download():
                try:
                    max_videos = int(max_videos_var.get()) if max_videos_var.get().strip() else 0
                    max_videos_dialog.destroy()
                    
                    # 确认下载
                    confirm_msg = f"确定要批量下载所有 {len(all_models)} 个模特的完整目录吗？\n"
                    if max_videos > 0:
                        confirm_msg += f"每个模特最多下载 {max_videos} 个视频\n"
                    confirm_msg += "这将下载大量视频并消耗大量时间和存储空间！"
                    
                    if messagebox.askyesno("确认批量下载", confirm_msg):
                        self._download_complete_directories(all_models, max_videos)
                except ValueError:
                    messagebox.showerror("错误", "请输入有效的数字")
            
            button_frame = ttk.Frame(max_videos_dialog)
            button_frame.pack(pady=20)
            ttk.Button(button_frame, text="确定", command=confirm_download).pack(side=tk.LEFT, padx=10)
            ttk.Button(button_frame, text="取消", command=max_videos_dialog.destroy).pack(side=tk.LEFT, padx=10)
            
            # 居中显示
            max_videos_dialog.update_idletasks()
            x = (max_videos_dialog.winfo_screenwidth() // 2) - (max_videos_dialog.winfo_width() // 2)
            y = (max_videos_dialog.winfo_screenheight() // 2) - (max_videos_dialog.winfo_height() // 2)
            max_videos_dialog.geometry(f"+{x}+{y}")
            
            max_videos_dialog.mainloop()
            
        except Exception as e:
            messagebox.showerror("错误", f"批量下载所有模特失败: {e}")
    
    def open_browser_window(self):
        """打开独立的浏览器窗口"""
        # 切换到浏览器/代理测试标签页
        self.notebook.select(self.browser_proxy_tab)
        messagebox.showinfo("提示", "已切换到浏览器/代理测试标签页")

if __name__ == "__main__":
    root = tk.Tk()
    app = ModelManagerGUI(root)
    root.mainloop()
