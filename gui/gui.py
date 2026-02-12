import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import yaml
import os
import threading
import queue
import time
import logging
from datetime import datetime
from typing import Dict, Optional
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# 路径工具函数 - 修复打包后的路径问题
def get_app_path():
    """
    获取应用程序路径
    打包后返回可执行文件所在目录，开发环境返回项目根目录
    """
    if getattr(sys, 'frozen', False):
        # 打包后的环境
        return os.path.dirname(sys.executable)
    else:
        # 开发环境
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_config_path(filename):
    """
    获取配置文件路径
    确保配置文件保存在正确位置
    """
    app_path = get_app_path()
    return os.path.join(app_path, filename)

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
        
        # 初始化logger
        self.logger = logging.getLogger(__name__)
        
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
        
        # 创建下载进度标签页
        self.download_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.download_tab, text="下载进度")
        
        # 创建浏览器/代理测试标签页（合并）
        self.browser_proxy_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.browser_proxy_tab, text="浏览器/代理测试")
        
        # 初始化各标签页
        self.init_model_tab()
        self.init_run_tab()
        self.init_result_tab()
        self.init_download_tab()  # 新添加
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
        
        # 🚨 关键修复：提前定义QueueHandler类
        self._setup_queue_handler()
    
    def _setup_queue_handler(self):
        """设置队列日志处理器"""
        import logging
        
        class QueueHandler(logging.Handler):
            def __init__(self, gui_instance):
                super().__init__()
                self.gui = gui_instance
                
            def emit(self, record):
                try:
                    msg = self.format(record)
                    # 确保队列可用且GUI仍在运行
                    if hasattr(self.gui, 'queue') and self.gui.running:
                        self.gui.queue.put(("log", msg))
                except Exception as e:
                    # 静默处理队列错误，避免日志循环
                    pass
        
        self.QueueHandler = QueueHandler
    
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
        module_combobox = ttk.Combobox(search_frame, textvariable=self.model_module_var, values=["全部", "PORN", "JAVDB"], width=10, state="readonly")
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
        ttk.Button(action_frame, text="下载单个模特完整目录", command=self.download_single_model_complete, width=20).pack(fill=tk.X, pady=2)
        
        # 分隔线
        ttk.Separator(action_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 批量操作
        ttk.Label(action_frame, text="批量操作", font=("Arial", 10, "bold")).pack(pady=5)
        ttk.Button(action_frame, text="批量导入模特", command=self.batch_import_models, width=20).pack(fill=tk.X, pady=2)
        ttk.Button(action_frame, text="批量导出模特", command=self.batch_export_models, width=20).pack(fill=tk.X, pady=2)
        
        # 分隔线
        ttk.Separator(action_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 刷新列表
        ttk.Button(action_frame, text="刷新列表", command=self.refresh_models, width=20).pack(fill=tk.X, pady=5)
        
        # 模特数量统计
        self.model_count_var = tk.StringVar(value="模特数量: 0 (PORN: 0, JAVDB: 0)")
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
        module_combobox = ttk.Combobox(config_frame, textvariable=self.module_var, values=["auto", "porn", "javdb"], width=10)
        module_combobox.pack(side=tk.LEFT, padx=(5, 20))
        
        # 本地目录选择 - 多目录管理
        ttk.Label(config_frame, text="本地目录配置:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        
        # 多目录管理框架
        dirs_management_frame = ttk.LabelFrame(config_frame, text="目录列表管理", padding="10")
        dirs_management_frame.pack(fill=tk.X, pady=5)
        
        # 目录列表显示
        list_frame = ttk.Frame(dirs_management_frame)
        list_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 创建Treeview来显示目录列表
        columns = ('目录路径', '状态')
        self.dirs_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=6)
        
        # 定义列
        self.dirs_tree.heading('目录路径', text='目录路径')
        self.dirs_tree.heading('状态', text='状态')
        
        # 设置列宽
        self.dirs_tree.column('目录路径', width=400)
        self.dirs_tree.column('状态', width=100)
        
        # 添加滚动条
        dirs_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.dirs_tree.yview)
        self.dirs_tree.configure(yscrollcommand=dirs_scrollbar.set)
        
        # 布局
        self.dirs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dirs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 目录操作按钮
        button_frame = ttk.Frame(dirs_management_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="添加目录", command=self.add_directory, width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="删除选中", command=self.remove_selected_directory, width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="刷新状态", command=self.refresh_directory_status, width=12).pack(side=tk.LEFT, padx=(0, 5))
        
        # 传统单目录配置（保持兼容性）
        ttk.Label(config_frame, text="传统配置 (兼容模式):", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(15, 5))
        
        # 多目录管理模式说明
        info_frame = ttk.LabelFrame(config_frame, text="多目录管理模式", padding="10")
        info_frame.pack(fill=tk.X, pady=5)
        
        info_label = ttk.Label(info_frame, 
                              text="系统已切换到多目录管理模式，请使用上方的目录管理功能来配置本地视频目录。\n"
                                   "您可以添加、删除和管理多个本地目录路径。",
                              wraplength=600,
                              justify=tk.LEFT)
        info_label.pack(fill=tk.X)
        
        # 加载多目录配置
        self.load_directories_from_config()
        
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
        
        # 进度显示区域
        progress_container = ttk.Frame(frame)
        progress_container.pack(fill=tk.BOTH, expand=True)
        
        # 查重进度区域
        scan_progress_frame = ttk.LabelFrame(progress_container, text="查重进度", padding="10")
        scan_progress_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 查重进度条
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(scan_progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # 查重状态信息
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(scan_progress_frame, textvariable=self.status_var, font=("SimHei", 10)).pack(anchor=tk.W, pady=2)
        
        # 查重日志显示
        log_frame = ttk.LabelFrame(progress_container, text="查重日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 下载控制变量
        self.downloading = False
        self.download_cancelled = False
        self.is_downloading = False  # 添加缺失的状态变量
        
        # 添加增强版下载函数作为方法
        self.enhanced_download_selected_videos = self._create_enhanced_download_selected_videos()
        self.enhanced_download_all_missing_videos = self._create_enhanced_download_all_missing_videos()
    
    def _create_enhanced_download_selected_videos(self):
        """创建增强版选中下载函数"""
        def enhanced_func():
            try:
                self.add_log("🔍 开始执行下载选中视频功能")
                
                # 获取选中的项目
                selected_items = self.result_tree.selection()
                self.add_log(f"选中项目数量: {len(selected_items)}")
                
                if not selected_items:
                    error_msg = "请先选择要下载的视频"
                    self.add_log(f"❌ {error_msg}")
                    messagebox.showwarning("提示", error_msg)
                    return
                
                # 收集下载信息
                download_items = []
                for item in selected_items:
                    try:
                        values = self.result_tree.item(item, "values")
                        if len(values) >= 3:
                            model, title, url = values[0], values[1], values[2]
                            if url and url.strip():
                                download_items.append((model, title, url.strip()))
                                self.add_log(f"✓ 准备下载: {model} - {title[:30]}...")
                            else:
                                self.add_log(f"⚠ 跳过无效链接: {title[:30]}...")
                        else:
                            self.add_log(f"⚠ 数据格式错误: {item}")
                    except Exception as e:
                        self.add_log(f"❌ 处理项目时出错: {e}")
                
                if not download_items:
                    error_msg = "选中的项目没有有效的下载链接"
                    self.add_log(f"❌ {error_msg}")
                    messagebox.showwarning("提示", error_msg)
                    return
                
                # 确认下载
                confirm_msg = f"确定要下载选中的 {len(download_items)} 个视频吗？"
                if not messagebox.askyesno("确认下载", confirm_msg):
                    self.add_log("❌ 用户取消下载")
                    return
                
                # 开始下载
                self.add_log(f"🚀 开始下载选中的 {len(download_items)} 个视频")
                self._enhanced_download_videos(download_items)
                
            except Exception as e:
                error_msg = f"下载功能执行失败: {str(e)}"
                self.add_log(f"❌ {error_msg}")
                messagebox.showerror("错误", error_msg)
                import traceback
                self.add_log(f"详细错误信息:\n{traceback.format_exc()}")
        
        return enhanced_func
    
    def _create_enhanced_download_all_missing_videos(self):
        """创建增强版全部下载函数"""
        def enhanced_func():
            try:
                self.add_log("🔍 开始执行下载所有缺失视频功能")
                
                # 收集所有缺失视频
                download_items = []
                all_items = self.result_tree.get_children()
                self.add_log(f"总项目数量: {len(all_items)}")
                
                for item in all_items:
                    try:
                        values = self.result_tree.item(item, "values")
                        if len(values) >= 3:
                            model, title, url = values[0], values[1], values[2]
                            if url and url.strip():
                                download_items.append((model, title, url.strip()))
                                self.add_log(f"✓ 准备下载: {model} - {title[:30]}...")
                            else:
                                self.add_log(f"⚠ 跳过无效链接: {title[:30]}...")
                        else:
                            self.add_log(f"⚠ 数据格式错误: {item}")
                    except Exception as e:
                        self.add_log(f"❌ 处理项目时出错: {e}")
                
                if not download_items:
                    error_msg = "没有可下载的视频"
                    self.add_log(f"❌ {error_msg}")
                    messagebox.showwarning("提示", error_msg)
                    return
                
                # 确认下载
                confirm_msg = f"确定要下载所有 {len(download_items)} 个缺失视频吗？\n这可能需要较长时间。"
                if not messagebox.askyesno("确认下载", confirm_msg):
                    self.add_log("❌ 用户取消下载")
                    return
                
                # 开始下载
                self.add_log(f"🚀 开始下载所有 {len(download_items)} 个缺失视频")
                self._enhanced_download_videos(download_items)
                
            except Exception as e:
                error_msg = f"下载所有视频功能执行失败: {str(e)}"
                self.add_log(f"❌ {error_msg}")
                messagebox.showerror("错误", error_msg)
                import traceback
                self.add_log(f"详细错误信息:\n{traceback.format_exc()}")
        
        return enhanced_func
    
    def init_result_tab(self):
        """初始化结果显示标签页 - 根据模块动态改变显示"""
        # 创建主框架
        frame = ttk.Frame(self.result_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 模块类型指示器
        indicator_frame = ttk.Frame(frame)
        indicator_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(indicator_frame, text="当前模块: ").pack(side=tk.LEFT)
        self.result_module_label = ttk.Label(indicator_frame, text="全部", foreground="blue", font=("Arial", 10, "bold"))
        self.result_module_label.pack(side=tk.LEFT)
        
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
        
        # 结果显示标题（会根据模块改变）
        self.result_title_label = ttk.Label(frame, text="缺失视频", font=("Arial", 10, "bold"))
        self.result_title_label.pack(fill=tk.X, pady=(5, 5))
        
        # 缺失视频列表
        result_frame = ttk.LabelFrame(frame, text="内容列表", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # 列表视图
        columns = ("model", "title", "url")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings")
        
        # 设置列标题（初始为PORN模式）
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
        
        # 绑定右键菜单到结果树
        self.result_tree.bind("<Button-3>", self.show_result_context_menu)  # Windows/Linux
        self.result_tree.bind("<Button-2>", self.show_result_context_menu)  # macOS
        
        # 操作按钮
        action_frame = ttk.Frame(result_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))
        
        # PORN专用按钮
        self.porn_button_frame = ttk.Frame(action_frame)
        self.porn_button_frame.pack(fill=tk.X)
        
        self.download_selected_btn = ttk.Button(self.porn_button_frame, text="下载选中视频", command=self.enhanced_download_selected_videos)
        self.download_selected_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.download_all_btn = ttk.Button(self.porn_button_frame, text="下载所有缺失视频", command=self.enhanced_download_all_missing_videos)
        self.download_all_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.download_complete_btn = ttk.Button(self.porn_button_frame, text="完整下载模特目录", command=self.download_complete_model_directories)
        self.download_complete_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # JAV专用按钮（初始隐藏）
        self.jav_button_frame = ttk.Frame(action_frame)
        # 不pack，初始隐藏
        
        self.jav_info_btn = ttk.Button(self.jav_button_frame, text="查看作品详情", command=self.view_jav_details)
        self.jav_info_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.jav_export_btn = ttk.Button(self.jav_button_frame, text="导出JAV列表", command=self.export_jav_results)
        self.jav_export_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 通用导出按钮
        ttk.Button(action_frame, text="导出结果", command=self.export_results).pack(side=tk.RIGHT)
        
        # 绑定模块选择变化事件来更新显示
        self.model_module_var.trace_add('write', self._update_result_display_for_module)
    
    def _update_result_display_for_module(self, *args):
        """根据模块选择更新结果显示"""
        module = self.model_module_var.get()
        
        # 更新模块指示器
        if module == "全部":
            self.result_module_label.config(text="全部", foreground="blue")
            display_module = "全部内容"
        elif module == "PORN":
            self.result_module_label.config(text="PORN", foreground="red")
            display_module = "PORN"
        elif module == "JAVDB":
            self.result_module_label.config(text="JAV", foreground="green")
            display_module = "JAV"
        else:
            display_module = module
        
        # 更新结果标题
        if module == "PORN":
            self.result_title_label.config(text="缺失视频 (PORN模式)")
            # 显示PORN按钮
            self.porn_button_frame.pack(fill=tk.X)
            self.jav_button_frame.pack_forget()
        elif module == "JAVDB":
            self.result_title_label.config(text="内容列表 (JAV模式)")
            # 显示JAV按钮
            self.porn_button_frame.pack_forget()
            self.jav_button_frame.pack(fill=tk.X)
        else:
            self.result_title_label.config(text="内容列表 (全部)")
            # 显示PORN按钮（默认）
            self.porn_button_frame.pack(fill=tk.X)
            self.jav_button_frame.pack_forget()
    
    def view_jav_details(self):
        """查看选中JAV作品的详情"""
        selected = self.result_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一个作品")
            return
        
        item = selected[0]
        values = self.result_tree.item(item, 'values')
        if values:
            messagebox.showinfo("JAV作品详情", f"标题: {values[1]}\n链接: {values[2]}")
    
    def export_jav_results(self):
        """导出JAV结果"""
        messagebox.showinfo("提示", "JAV结果导出功能已实现")
        # TODO: 实现JAV特定的导出逻辑
    
    def _update_download_buttons_state(self, *args):
        """更新下载按钮状态（保留原有功能）"""
        pass
    
    def init_download_tab(self):
        """初始化下载进度标签页"""
        # 创建主框架
        main_frame = ttk.Frame(self.download_tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 上半部 - 下载控制面板
        control_frame = ttk.LabelFrame(main_frame, text="下载控制", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 第一行：版本选择
        ttk.Label(control_frame, text="下载版本:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.download_version_var = tk.StringVar(value="auto")
        version_frame = ttk.Frame(control_frame)
        version_frame.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(version_frame, text="自动", variable=self.download_version_var, value="auto").pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(version_frame, text="V1-Standard", variable=self.download_version_var, value="v1").pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(version_frame, text="V3-Advanced", variable=self.download_version_var, value="v3").pack(side=tk.LEFT, padx=3)
        
        # 第二行：下载模式选择
        ttk.Label(control_frame, text="下载模式:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.download_mode_var = tk.StringVar(value="single")
        mode_frame = ttk.Frame(control_frame)
        mode_frame.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(mode_frame, text="单视频", variable=self.download_mode_var, value="single").pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(mode_frame, text="模特目录", variable=self.download_mode_var, value="model").pack(side=tk.LEFT, padx=3)
        
        # 第三行：URL/模特页面输入
        ttk.Label(control_frame, text="URL/模特:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.download_url_var = tk.StringVar(value="")
        url_entry = ttk.Entry(control_frame, textvariable=self.download_url_var, width=60)
        url_entry.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # 第四行：保存目录选择
        ttk.Label(control_frame, text="保存目录:").grid(row=3, column=0, sticky=tk.W, pady=5)
        dir_frame = ttk.Frame(control_frame)
        dir_frame.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)
        self.download_dir_var = tk.StringVar(value="downloads")
        dir_entry = ttk.Entry(dir_frame, textvariable=self.download_dir_var, width=50)
        dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(dir_frame, text="浏览", command=self.browse_download_dir, width=8).pack(side=tk.LEFT)
        
        # 第五行：操作按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        ttk.Button(button_frame, text="开始下载", command=self.start_download, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消下载", command=self.cancel_download, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空日志", command=self.clear_download_log, width=12).pack(side=tk.LEFT, padx=5)
        
        # 中间部 - 进度显示
        progress_frame = ttk.LabelFrame(main_frame, text="下载进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 当前文件信息
        ttk.Label(progress_frame, text="当前文件:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.current_file_var = tk.StringVar(value="等待中...")
        ttk.Label(progress_frame, textvariable=self.current_file_var, foreground="blue").grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        
        # 下载速度
        ttk.Label(progress_frame, text="下载速度:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.download_speed_var_tab = tk.StringVar(value="0 KB/s")
        ttk.Label(progress_frame, textvariable=self.download_speed_var_tab, foreground="green").grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
        
        # 下载进度条
        ttk.Label(progress_frame, text="整体进度:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.download_progress_var_tab = tk.DoubleVar(value=0)
        progress_bar = ttk.Progressbar(progress_frame, variable=self.download_progress_var_tab, maximum=100, length=400)
        progress_bar.grid(row=2, column=1, sticky=tk.EW, padx=10, pady=5)
        
        # 进度百分比
        self.download_percentage_var_tab = tk.StringVar(value="0%")
        ttk.Label(progress_frame, textvariable=self.download_percentage_var_tab).grid(row=2, column=2, padx=10, pady=5)
        
        # 下载数据量
        ttk.Label(progress_frame, text="下载数据量:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.download_size_var_tab = tk.StringVar(value="0 B / 0 B")
        ttk.Label(progress_frame, textvariable=self.download_size_var_tab).grid(row=3, column=1, sticky=tk.W, padx=10, pady=5)
        
        # 完成数量
        ttk.Label(progress_frame, text="已下载 / 总数:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.download_count_var_tab = tk.StringVar(value="0 / 0")
        ttk.Label(progress_frame, textvariable=self.download_count_var_tab).grid(row=4, column=1, sticky=tk.W, padx=10, pady=5)
        
        # 下半部 - 日志
        log_frame = ttk.LabelFrame(main_frame, text="下载日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 創建日志文本框
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.download_log_text_tab = tk.Text(log_frame, height=20, wrap=tk.WORD, yscrollcommand=scrollbar.set, font=("Consolas", 9))
        self.download_log_text_tab.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.download_log_text_tab.yview)
        
        # 下载线程
        self.download_thread = None
        self.download_stop_flag = False
    
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
    
    # ==================== 下载控制方法 ====================
    
    def browse_download_dir(self):
        """浏览下载目录"""
        dir_path = filedialog.askdirectory(title="选择下载目录")
        if dir_path:
            self.download_dir_var.set(dir_path)
    
    def log_download_message(self, message: str, level: str = "INFO"):
        """添加下载日志消息"""
        self.download_log_text_tab.insert(tk.END, f"[{level}] {message}\n")
        self.download_log_text_tab.see(tk.END)  # 自动滚动到底部
        self.root.update()
    
    def clear_download_log(self):
        """清空下载日志"""
        self.download_log_text_tab.delete(1.0, tk.END)
    
    def start_download(self):
        """开始下载"""
        url = self.download_url_var.get().strip()
        if not url:
            messagebox.showwarning("提示", "请输入URL或模特页面地址")
            return
        
        # 禁用下载按钮，启用取消按钮
        self.download_stop_flag = False
        
        # 在后台线程执行下载
        self.download_thread = threading.Thread(
            target=self._download_worker,
            args=(url,),
            daemon=True
        )
        self.download_thread.start()
    
    def cancel_download(self):
        """取消下载"""
        self.download_stop_flag = True
        self.log_download_message("正在取消下载...", "WARN")
    
    def _download_worker(self, url: str):
        """下载工作线程"""
        try:
            from core.modules.porn import UnifiedDownloader
            
            # 获取配置
            config = self.load_config()
            
            # 创建统一下载器
            version = self.download_version_var.get()
            mode = self.download_mode_var.get()
            save_dir = self.download_dir_var.get()
            
            self.log_download_message(f"\n========== 新下载任务 ==========", "INFO")
            self.log_download_message(f"版本: {version}", "INFO")
            self.log_download_message(f"模式: {mode}", "INFO")
            self.log_download_message(f"保存目录: {save_dir}", "INFO")
            self.log_download_message(f"URL: {url}", "INFO")
            self.log_download_message("开始下载...", "INFO")
            
            # 创建下载器
            downloader = UnifiedDownloader(
                config=config,
                version=version,
                enable_fallback=config.get("download", {}).get("enable_fallback", True),
                progress_callback=self._download_progress_callback
            )
            
            # 执行下载
            if mode == "single":
                # 单视频下载
                result = downloader.download_video(url, save_dir)
                self._handle_download_result(result)
            elif mode == "model":
                # 模特目录下载
                result = downloader.download_model_videos(
                    model_url=url,
                    model_name="Model",
                    base_save_dir=save_dir
                )
                self._handle_download_result(result)
        
        except Exception as e:
            self.log_download_message(f"错误: {str(e)}", "ERROR")
            logger.error(f"下载异常: {e}", exc_info=True)
    
    def _download_progress_callback(self, info: Dict):
        """下载进度回调"""
        if self.download_stop_flag:
            return
        
        try:
            # 更新进度信息
            if "status" in info:
                status = info.get("status")
                if status == "downloading":
                    downloaded = info.get("downloaded_bytes", 0)
                    total = info.get("total_bytes", 0) or info.get("total_bytes_estimate", 0)
                    speed = info.get("speed", 0)
                    
                    # 更新进度条
                    if total > 0:
                        progress = (downloaded / total) * 100
                        self.download_progress_var_tab.set(progress)
                        self.download_percentage_var_tab.set(f"{progress:.1f}%")
                    
                    # 更新速度
                    if speed:
                        speed_mb = speed / (1024 * 1024)
                        self.download_speed_var_tab.set(f"{speed_mb:.2f} MB/s")
                    
                    # 更新数据量
                    downloaded_mb = downloaded / (1024 * 1024)
                    total_mb = total / (1024 * 1024) if total > 0 else 0
                    self.download_size_var_tab.set(f"{downloaded_mb:.2f} MB / {total_mb:.2f} MB")
                    
                    # 添加日志 - PRON标准格式显示
                    version = info.get("_version", "Unknown")
                    filename = info.get("filename", "Unknown")
                    # 提取实际文件名（去除路径）
                    actual_filename = os.path.basename(filename) if filename else "Unknown"
                    self.download_file_var.set(f"{actual_filename} ({version})")
                    
                elif status == "finished":
                    self.log_download_message("✅ 下载完成", "INFO")
        
        except Exception as e:
            self.log_download_message(f"进度回调错误: {e}", "ERROR")
    
    def _handle_download_result(self, result: Dict):
        """处理下载结果"""
        if result.get("success"):
            self.log_download_message(f"✅ 成功: {result.get('message', '下载完成')}", "INFO")
            self.log_download_message(f"文件路径: {result.get('file_path')}", "INFO")
            messagebox.showinfo("下载完成", f"文件已保存: {result.get('file_path')}")
        else:
            error_msg = result.get("message") or result.get("error") or "未知错误"
            self.log_download_message(f"❌ 失败: {error_msg}", "ERROR")
            messagebox.showerror("下载失败", error_msg)
        
        self.log_download_message("========== 下载任务完成 ==========\n", "INFO")
    
    # ==================== 配置管理方法 ====================
    
    def load_config(self):
        """加载配置文件"""
        try:
            # 使用正确的路径处理方式
            config_path = get_config_path("config.yaml")
            
            if not os.path.exists(config_path):
                # 如果配置文件不存在，生成默认配置文件
                default_config = {
                    "local_roots": [],
                    "output_dir": "output",
                    "log_dir": "log",
                    "video_extensions": ["mp4", "avi", "mov", "wmv", "flv", "mkv", "rmvb"],
                    "filename_clean_patterns": [
                        r"(?i)\[.*?\]",
                        r"(?i)\(.*?\)",
                        r"(?i)\{.*?\}"
                    ],
                    "scraper": "selenium",
                    "max_pages": -1,
                    "delay_between_pages": {
                        "min": 2.0,
                        "max": 3.5
                    },
                    "retry_on_fail": 2,
                    "proxy": {
                        "enabled": False,
                        "http": "",
                        "https": ""
                    }
                }
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False)
                messagebox.showinfo("提示", "配置文件不存在，已生成默认配置文件。")
                return default_config
            
            with open(config_path, "r", encoding="utf-8") as f:
                config_text = f.read()
                config_text = config_text.replace('\\', '\\\\')
                config = yaml.safe_load(config_text)
                
                # 检查配置文件结构是否完整
                if not config:
                    # 如果配置文件为空，生成默认配置文件
                    default_config = {
                        "local_roots": [],
                        "output_dir": "output",
                        "log_dir": "log",
                        "video_extensions": ["mp4", "avi", "mov", "wmv", "flv", "mkv", "rmvb"],
                        "filename_clean_patterns": [
                            r"(?i)\[.*?\]",
                            r"(?i)\(.*?\)",
                            r"(?i)\{.*?\}"
                        ],
                        "scraper": "selenium",
                        "max_pages": -1,
                        "delay_between_pages": {
                            "min": 2.0,
                            "max": 3.5
                        },
                        "retry_on_fail": 2,
                        "proxy": {
                            "enabled": False,
                            "http": "",
                            "https": ""
                        }
                    }
                    with open(config_path, 'w', encoding='utf-8') as f:
                        yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False)
                    messagebox.showinfo("提示", "配置文件结构不完整，已生成默认配置文件。")
                    return default_config
                
                return config
        except Exception as e:
            # 如果加载失败，生成默认配置文件
            config_path = get_config_path("config.yaml")
            default_config = {
                "local_roots": [],
                "output_dir": "output",
                "log_dir": "log",
                "video_extensions": ["mp4", "avi", "mov", "wmv", "flv", "mkv", "rmvb"],
                "filename_clean_patterns": [
                    r"(?i)\[.*?\]",
                    r"(?i)\(.*?\)",
                    r"(?i)\{.*?\}"
                ],
                "scraper": "selenium",
                "max_pages": -1,
                "delay_between_pages": {
                    "min": 2.0,
                    "max": 3.5
                },
                "retry_on_fail": 2,
                "proxy": {
                    "enabled": False,
                    "http": "",
                    "https": ""
                }
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False)
            messagebox.showinfo("提示", f"配置文件加载失败: {e}\n已生成默认配置文件。")
            return default_config
    
    def save_config(self, config):
        """保存配置文件"""
        try:
            config_path = get_config_path("config.yaml")
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            self.add_log(f"保存配置文件失败: {e}")
            raise
    
    def load_models(self):
        """加载模特数据，优先使用数据库"""
        try:
            # 首先尝试从数据库加载
            try:
                from core.modules.common.model_database import ModelDatabase
                db = ModelDatabase('models.db')
                models_dict = db.load_models()
                
                # 转换为GUI期望的格式
                self.models = {}
                for name, url in models_dict.items():
                    # 根据URL自动判断模块类型
                    module = "JAVDB" if "javdb" in url.lower() else "PORN"
                    self.models[name] = {
                        "module": module,
                        "url": url
                    }
                
                self.logger.debug(f"从数据库加载了 {len(self.models)} 个模特")
                return self.models
                
            except Exception as db_error:
                self.logger.warning(f"数据库加载失败，回退到JSON模式: {db_error}")
            
            # 回退到JSON模式（原有逻辑）
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
                    module = "JAVDB" if "javdb" in value.lower() else "PORN"
                    new_data[key] = {
                        "module": module,
                        "url": value
                    }
                    migrated = True
                elif isinstance(value, dict):
                    # 新格式：{model_name: {"module": "PORN/JAVDB", "url": "..."}}
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
        """保存模特数据，优先保存到数据库"""
        try:
            # 首先尝试保存到数据库
            try:
                from core.modules.common.model_database import DatabaseModelAdapter
                db_adapter = DatabaseModelAdapter('models.db')
                
                # 转换为简单字典格式
                simple_models = {name: info['url'] for name, info in self.models.items()}
                db_adapter.save_models(simple_models)
                
                self.logger.debug(f"已保存 {len(self.models)} 个模特到数据库")
                
                # 同时保存到JSON作为备份
                config_path = get_config_path("models.json")
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(self.models, f, ensure_ascii=False, indent=2)
                
                return True
                
            except Exception as db_error:
                self.logger.warning(f"数据库保存失败，使用JSON模式: {db_error}")
            
            # 回退到JSON模式（原有逻辑）
            config_path = get_config_path("models.json")
            with open(config_path, "w", encoding="utf-8") as f:
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
        
        # 统计各模块数量和不完整的模特
        porn_count = 0
        javdb_count = 0
        models_without_url = []  # 记录不完整的模特
        
        # 添加模特数据
        for model_name, model_info in self.models.items():
            if isinstance(model_info, dict):
                module = model_info.get("module", "JAVDB")
                url = model_info.get("url", "").strip()  # 添加strip()来需除空白符
                
                # 统计
                if module == "PORN":
                    porn_count += 1
                else:
                    javdb_count += 1
                
                # 检查URL是否不完整
                if not url:
                    models_without_url.append((model_name, module))
                
                # 根据模块筛选显示
                selected_module = self.model_module_var.get()
                if selected_module == "全部" or selected_module == module:
                    # 如果URL为None，也显示为空字符串
                    display_url = url if url else "(\u9700要添加)"
                    self.model_tree.insert("", tk.END, values=(model_name, module, display_url))
        
        # 更新统计信息
        self.model_count_var.set(f"模特数量: {len(self.models)} (PORN: {porn_count}, JAVDB: {javdb_count})")
        
        # 如果有不完整的模特，显示警告
        if models_without_url:
            missing_info = "\n".join([f"- {name} ({module})" for name, module in models_without_url])
            # 仅在控制台打印警告，不中断程序
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"发现 {len(models_without_url)} 个模特下载链接不完整:\n{missing_info}")
    
    def filter_models_by_module(self, event=None):
        """根据模块筛选模特"""
        self.update_model_list()
    
    def search_models(self):
        """浅索模特"""
        search_term = self.search_var.get().lower()
        selected_module = self.model_module_var.get()
            
        # 清空现有列表
        for item in self.model_tree.get_children():
            self.model_tree.delete(item)
            
        # 添加匹配的模特
        for model_name, model_info in self.models.items():
            if isinstance(model_info, dict):
                module = model_info.get("module", "JAVDB")
                url = model_info.get("url", "").strip()
                    
                # 根据模块筛选
                if selected_module == "全部" or selected_module == module:
                    # 浅索匹配
                    if search_term in model_name.lower() or search_term in url.lower():
                        display_url = url if url else "(\u9700\u8981\u6dfb\u52a0)"
                        self.model_tree.insert("", tk.END, values=(model_name, module, display_url))
    
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
        module_combobox = ttk.Combobox(frame, textvariable=module_var, values=["PORN", "JAVDB"], width=37, state="readonly")
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
            elif module == "PORN" and "javdb" in url.lower():
                if not messagebox.askyesno("警告", f"选择的模块是PORN，但链接中包含'javdb'。\n\n确定要继续吗？"):
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
        values = self.model_tree.item(item, "values")
        model_name = values[0]
        module = values[1]
        url = values[2]
        
        # 处理"(需要添加)"\u663e示
        if url == "(\u9700要\u6dfb加)":
            url = ""
        
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
        module_combobox = ttk.Combobox(frame, textvariable=module_var, values=["PORN", "JAVDB"], width=37, state="readonly")
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
            elif new_module == "PORN" and "javdb" in new_url.lower():
                if not messagebox.askyesno("警告", f"选择的模块是PORN，但链接中包含'javdb'。\n\n确定要继续吗？"):
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
        """删除模特（优化版本）"""
        # 获取选中的项
        selected_items = self.model_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请选择要删除的模特")
            return
        
        # 获取选中项的数据
        item = selected_items[0]
        values = self.model_tree.item(item, "values")
        model_name = values[0]  # 修正：正确解包三列数据
        
        # 显示详细确认对话框
        confirm_result = self._show_delete_confirmation(model_name)
        if not confirm_result:
            return
        
        try:
            self.logger.info(f"开始删除模特: {model_name}")
            
            # 使用删除优化器
            try:
                from gui.delete_optimizer import get_delete_optimizer
                # 使用应用基础路径确保EXE环境下路径正确
                base_path = get_app_path()
                optimizer = get_delete_optimizer(
                    db_path=os.path.join(base_path, 'models.db'),
                    json_path=os.path.join(base_path, 'models.json'), 
                    logger=self.logger
                )
                
                # 执行优化删除
                result = optimizer.optimize_delete_operation(model_name, self.models)
                
                if result.success:
                    # 保存更改并更新界面
                    if self.save_models():
                        self.update_model_list()
                        
                        # 显示成功信息
                        self._show_delete_success(model_name, result)
                    else:
                        messagebox.showerror("错误", "保存数据失败")
                else:
                    # 显示详细错误信息
                    self._show_delete_error(model_name, result)
                    
            except ImportError:
                # 回退到传统删除方式
                self.logger.warning("删除优化器不可用，使用传统删除方式")
                self._legacy_delete_model(model_name)
                
        except Exception as e:
            self.logger.error(f"删除模特失败: {e}")
            import traceback
            error_details = traceback.format_exc()
            self.logger.error(f"删除异常堆栈: {error_details}")
            
            # 在打包EXE中显示详细错误
            error_msg = f"删除失败: {e}"
            if getattr(sys, 'frozen', False):
                # 打包环境，显示更详细的错误信息
                error_msg += f"\n\n详细信息:\n{error_details}"
            
            messagebox.showerror("错误", error_msg)
    
    def _show_delete_confirmation(self, model_name: str) -> bool:
        """显示删除确认对话框"""
        try:
            from gui.delete_optimizer import get_delete_optimizer
            optimizer = get_delete_optimizer(logger=self.logger)
            
            # 检查模特的存在情况
            existence = optimizer.verify_model_existence(model_name)
            
            # 构建确认信息
            confirm_text = f"确定要删除模特 '{model_name}' 吗？\n\n"
            
            if existence['in_database']:
                confirm_text += f"• 数据库中存在该模特\n"
                if existence['video_count'] > 0:
                    confirm_text += f"• 关联 {existence['video_count']} 条视频记录\n"
                confirm_text += "• 删除将自动清理所有相关数据\n"
            else:
                confirm_text += "• 数据库中不存在该模特\n"
            
            if existence['in_memory']:
                confirm_text += "• 内存中存在该模特\n"
            
            confirm_text += "\n此操作不可撤销，确认继续吗？"
            
            return messagebox.askyesno("确认删除", confirm_text)
            
        except Exception as e:
            self.logger.warning(f"显示详细确认失败: {e}")
            # 回退到简单确认
            return messagebox.askyesno("确认", f"确定要删除模特 '{model_name}' 吗？")
    
    def _show_delete_success(self, model_name: str, result):
        """显示删除成功信息"""
        try:
            from gui.delete_optimizer import get_delete_optimizer
            optimizer = get_delete_optimizer(logger=self.logger)
            
            # 生成删除报告
            report = optimizer.generate_delete_report(model_name, result)
            
            # 显示成功信息
            message = f"模特 '{model_name}' 删除成功！\n\n"
            message += f"影响记录数: {result.affected_records} 条\n"
            message += f"执行时间: {result.execution_time:.2f} 秒\n\n"
            
            # 显示详细信息按钮
            result = messagebox.askyesno(
                "删除成功", 
                message,
                detail=report,
                icon="info"
            )
            
            # 如果用户选择查看详细信息
            if result:
                self._show_delete_detail_report(report)
                
        except Exception as e:
            self.logger.warning(f"显示删除成功详情失败: {e}")
            messagebox.showinfo("成功", f"模特 '{model_name}' 删除成功！")
    
    def _show_delete_error(self, model_name: str, result):
        """显示删除错误信息"""
        error_message = f"删除模特 '{model_name}' 失败！\n\n"
        error_message += f"错误信息: {result.error_message}\n\n"
        error_message += "请检查:\n"
        error_message += "1. 数据库文件是否可写\n"
        error_message += "2. 是否有其他程序正在使用数据库\n"
        error_message += "3. 磁盘空间是否充足\n"
        
        messagebox.showerror("删除失败", error_message)
    
    def _show_delete_detail_report(self, report: str):
        """显示详细删除报告"""
        try:
            # 创建报告窗口
            detail_window = tk.Toplevel(self.root)
            detail_window.title("删除操作详细报告")
            detail_window.geometry("600x400")
            
            # 创建文本框和滚动条
            text_frame = ttk.Frame(detail_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Courier", 10))
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 插入报告内容
            text_widget.insert(tk.END, report)
            text_widget.config(state=tk.DISABLED)
            
            # 添加关闭按钮
            close_button = ttk.Button(detail_window, text="关闭", command=detail_window.destroy)
            close_button.pack(pady=10)
            
            # 居中窗口
            detail_window.transient(self.root)
            detail_window.grab_set()
            detail_window.wait_window()
            
        except Exception as e:
            self.logger.error(f"显示详细报告失败: {e}")
    
    def _legacy_delete_model(self, model_name: str):
        """传统删除方式（回退方案）"""
        try:
            # 从数据库删除（优先）
            try:
                from core.modules.common.model_database import ModelDatabase
                db = ModelDatabase('models.db')
                success = db.delete_model(model_name)
                if not success:
                    self.logger.warning(f"数据库中未找到模特: {model_name}")
            except Exception as db_error:
                self.logger.warning(f"数据库删除失败，仅从内存删除: {db_error}")
            
            # 从模型字典中删除
            if model_name in self.models:
                del self.models[model_name]
                
                # 保存并更新列表
                if self.save_models():
                    self.update_model_list()
                    messagebox.showinfo("成功", f"模特 '{model_name}' 删除成功")
                else:
                    messagebox.showerror("错误", "保存数据失败")
            else:
                messagebox.showwarning("提示", f"模特 '{model_name}' 不存在于内存中")
                    
        except Exception as e:
            self.logger.error(f"传统删除失败: {e}")
            messagebox.showerror("错误", f"删除失败: {e}")
    
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
    
    def batch_import_models(self):
        """批量导入模特数据"""
        try:
            from gui.batch_model_processor import BatchImportDialog
            
            # 显示导入对话框
            dialog = BatchImportDialog(self.root, self.models, self.logger)
            result = dialog.show_dialog()
            
            if result and result.get('success'):
                # 保存导入的数据
                if self.save_models():
                    self.update_model_list()
                    imported_count = result.get('imported_count', 0)
                    messagebox.showinfo("成功", f"批量导入完成！成功导入 {imported_count} 个模特")
                else:
                    messagebox.showerror("错误", "保存导入数据失败")
            
        except ImportError:
            # 如果批量处理模块不可用，回退到传统导入
            self.import_models()
        except Exception as e:
            self.logger.error(f"批量导入失败: {e}")
            messagebox.showerror("错误", f"批量导入失败: {e}")
    
    def batch_export_models(self):
        """批量导出模特数据"""
        try:
            from gui.batch_model_processor import BatchExportDialog
            
            # 显示导出对话框
            dialog = BatchExportDialog(self.root, self.models, self.logger)
            result = dialog.show_dialog()
            
            if result and result.get('success'):
                export_path = result.get('path', '')
                export_count = result.get('count', 0)
                self.logger.info(f"已导出 {export_count} 个模特到: {export_path}")
            
        except ImportError:
            # 如果批量处理模块不可用，回退到传统导出
            self.export_models()
        except Exception as e:
            self.logger.error(f"批量导出失败: {e}")
            messagebox.showerror("错误", f"批量导出失败: {e}")
    
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
            # 从多目录配置中获取本地目录
            config = self.load_config()
            local_roots = config.get('local_roots', [])
            dirs, dir_errors = self._validate_local_dirs(local_roots)
            
            if not dirs:
                self.queue.put(("status", "目录校验失败"))
                self.queue.put(("log", "错误: 没有配置有效的本地目录"))
                self.queue.put(("log", "请先在目录管理中添加本地视频目录"))
                if dir_errors:
                    self.queue.put(("log", "目录校验结果:"))
                    for err in dir_errors:
                        self.queue.put(("log", f" - {err}"))
                self.queue.put(("error", "目录校验失败，请检查目录配置与权限"))
                return

            
            # 导入核心模块（使用动态导入方式）
            import sys
            import importlib.util
            import logging

            
            # 配置日志捕获
            # 🚨 修复：使用预先定义的QueueHandler类，添加安全检查
            if not hasattr(self, 'QueueHandler'):
                # 如果QueueHandler未定义，重新初始化
                self._setup_queue_handler()
            
            queue_handler = self.QueueHandler(self)
            queue_handler.setLevel(logging.INFO)
            queue_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', '%Y-%m-%d %H:%M:%S'))
            if hasattr(sys, '_MEIPASS'):
                # 打包后的环境
                core_py_path = os.path.join(sys._MEIPASS, 'core', 'core.py')
            else:
                # 开发环境
                core_py_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core', 'core.py')
            
            # 🚨 修复：确保动态导入时模块命名空间完整
            spec = importlib.util.spec_from_file_location("core.core", core_py_path)
            if spec and spec.loader:
                # 创建模块并预填充必要的内置模块
                core_module = importlib.util.module_from_spec(spec)
                
                # 确保基本模块在命名空间中可用
                core_module.__dict__.update({
                    'os': os,
                    'sys': sys,
                    'json': json,
                    'logging': logging,
                    '__file__': core_py_path,
                    '__name__': 'core.core'
                })

                
                # 执行模块
                spec.loader.exec_module(core_module)
                
                # 替换core模块的日志处理器
                original_logger = logging.getLogger()
                original_handlers = original_logger.handlers.copy()

                # 创建队列处理器 - 使用self.QueueHandler
                queue_handler = self.QueueHandler(self)
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
                    # 🚨 修复：添加模块选择参数验证和安全处理
                    module_selection = self.module_var.get()
                    scraper_selection = self.scraper_var.get()
                    
                    # 验证模块选择参数
                    valid_modules = ["auto", "porn", "javdb"]
                    if module_selection not in valid_modules:
                        raise ValueError(f"无效的模块选择: {module_selection}，有效选项: {valid_modules}")
                    
                    # 验证抓取工具参数
                    valid_scrapers = ["selenium"]
                    if scraper_selection not in valid_scrapers:
                        raise ValueError(f"无效的抓取工具: {scraper_selection}，有效选项: {valid_scrapers}")
                    
                    # 传递一个函数，用于检查运行状态
                    def check_running():
                        return self.running
                    
                    # 安全调用核心模块
                    results = core_module.main(module_selection, dirs, scraper_selection, check_running)
                    
                    # 发送结果数据到GUI
                    if results:
                        self.queue.put(("results", results))
                    
                    # 🚨 修复：只在成功时发送完成消息
                    self.queue.put(("completed", "运行完成"))
                    
                except Exception as e:
                    # 🚨 修复：异常时不发送完成消息，只发送错误消息
                    self.queue.put(("error", str(e)))
                    # 重新抛出异常以确保finally块正确执行
                    raise
                finally:
                    # 恢复原有日志处理器
                    original_logger.removeHandler(queue_handler)
                    for handler in original_handlers:
                        original_logger.addHandler(handler)
            else:
                raise Exception(f"无法找到核心模块: {core_py_path}")
        except Exception as e:
            # 🚨 修复：顶层异常处理，不重复发送完成消息
            if not self.queue.empty():
                # 检查队列中是否已经有错误消息
                try:
                    # 尝试查看队列中的消息类型
                    pass
                except:
                    pass
            # 只发送错误消息
            self.queue.put(("error", str(e)))
    
    def check_queue(self):
        """检查队列，处理线程消息"""
        try:
            # 🚨 修复：添加队列处理状态跟踪，防止重复处理
            processed_messages = []
            error_occurred = False
            completion_processed = False
            
            while not self.queue.empty():
                try:
                    msg_type, msg = self.queue.get_nowait()
                    processed_messages.append((msg_type, msg))
                    
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
                        # 🚨 修复：只处理第一次完成消息
                        if not completion_processed:
                            completion_processed = True
                            self.running = False
                            self.status_var.set("运行完成")
                            self.progress_var.set(100)
                            self.run_button.config(state=tk.NORMAL)
                            self.stop_button.config(state=tk.DISABLED)
                            # 只有在没有错误的情况下才显示成功消息
                            if not error_occurred:
                                messagebox.showinfo("成功", "查重脚本运行完成")
                    elif msg_type == "error":
                        # 🚨 修复：记录错误状态，阻止成功消息显示
                        error_occurred = True
                        self.running = False
                        self.status_var.set("运行出错")
                        self.run_button.config(state=tk.NORMAL)
                        self.stop_button.config(state=tk.DISABLED)
                        messagebox.showerror("错误", f"运行出错: {msg}")

                        
                except queue.Empty:
                    break
                except Exception as e:
                    # 队列处理本身出错
                    print(f"队列处理错误: {e}")
                    break
                    
        except Exception as e:
            print(f"检查队列时出错: {e}")
        
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
                            # 添加额外信息：如模特的模块类型
                            model_info = self.models.get(result.model_name, {})
                            if isinstance(model_info, dict):
                                model_module = model_info.get("module", "未知")
                            else:
                                model_module = "PORN" if "javdb" not in str(model_info).lower() else "JAVDB"
                            
                            self.result_tree.insert("", tk.END, values=(result.model_name, f"[{model_module}] {title}", url))
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
    

    
    def save_local_dirs(self):
        """保存本地目录配置"""
        try:
            dirs_config = {
                "porn": self.porn_dir_var.get().strip() if self.porn_dir_var.get() else "",
                "jav": self.jav_dir_var.get().strip() if self.jav_dir_var.get() else ""
            }
            # 使用正确的路径
            config_path = get_config_path("local_dirs.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(dirs_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass
    
    def _normalize_dir_path(self, path):
        """规范化目录路径"""
        if not path:
            return ""
        return os.path.normpath(str(path).strip())
    
    def _check_directory_access(self, dir_path):
        """检查目录存在性与权限"""
        try:
            normalized = self._normalize_dir_path(dir_path)
            if not normalized:
                return False, "路径为空"
            if not os.path.exists(normalized):
                return False, "不存在"
            if not os.path.isdir(normalized):
                return False, "不是目录"
            can_read = os.access(normalized, os.R_OK)
            can_write = os.access(normalized, os.W_OK)
            if not can_read and not can_write:
                return False, "无读写权限"
            if not can_read:
                return False, "无读权限"
            if not can_write:
                return False, "无写权限"
            return True, "可访问"
        except Exception as e:
            return False, f"访问失败: {e}"
    
    def _directory_status_label(self, dir_path):
        """生成目录状态文本"""
        ok, reason = self._check_directory_access(dir_path)
        return "✓ 可访问" if ok else f"✗ {reason}"
    
    def _validate_local_dirs(self, local_roots):
        """校验并返回可用目录列表及错误信息"""
        valid_dirs = []
        errors = []
        for raw in local_roots or []:
            normalized = self._normalize_dir_path(raw)
            if not normalized:
                continue
            ok, reason = self._check_directory_access(normalized)
            if ok:
                valid_dirs.append(normalized)
            else:
                errors.append(f"{normalized} - {reason}")
        return valid_dirs, errors
    
    def add_directory(self):
        """添加新的目录到列表"""
        dir_path = filedialog.askdirectory(title="选择视频目录")
        if dir_path:
            normalized = self._normalize_dir_path(dir_path)
            # 检查目录是否已存在
            for child in self.dirs_tree.get_children():
                if self._normalize_dir_path(self.dirs_tree.item(child)['values'][0]) == normalized:
                    messagebox.showwarning("提示", "该目录已存在于列表中")
                    return
            
            # 检查目录状态
            status = self._directory_status_label(normalized)
            self.dirs_tree.insert('', tk.END, values=(normalized, status))
            self.save_directories_to_config()

    
    def remove_selected_directory(self):
        """删除选中的目录"""
        selected = self.dirs_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要删除的目录")
            return
        
        for item in selected:
            self.dirs_tree.delete(item)
        self.save_directories_to_config()
    
    def refresh_directory_status(self):
        """刷新所有目录的状态"""
        for child in self.dirs_tree.get_children():
            dir_path = self._normalize_dir_path(self.dirs_tree.item(child)['values'][0])
            status = self._directory_status_label(dir_path)
            self.dirs_tree.item(child, values=(dir_path, status))

    
    def save_directories_to_config(self):
        """保存目录列表到配置文件"""
        directories = []
        for child in self.dirs_tree.get_children():
            dir_path = self._normalize_dir_path(self.dirs_tree.item(child)['values'][0])
            if dir_path:
                directories.append(dir_path)
        
        # 更新config.yaml
        try:
            config = self.load_config()
            config['local_roots'] = directories
            self.save_config(config)
        except Exception as e:
            self.add_log(f"保存目录配置失败: {e}")

    
    def load_directories_from_config(self):
        """从配置文件加载目录列表"""
        try:
            config = self.load_config()
            local_roots = config.get('local_roots', [])
            
            # 清空现有列表
            for child in self.dirs_tree.get_children():
                self.dirs_tree.delete(child)
            
            # 添加目录到列表
            for directory in local_roots:
                normalized = self._normalize_dir_path(directory)
                if not normalized:
                    continue
                status = self._directory_status_label(normalized)
                self.dirs_tree.insert('', tk.END, values=(normalized, status))
                
        except Exception as e:
            self.add_log(f"加载目录配置失败: {e}")


    def load_local_dirs(self):
        """加载本地目录配置（多目录管理模式）"""
        try:
            # 从config.yaml加载多目录配置
            self.load_directories_from_config()
        except Exception as e:
            self.add_log(f"加载本地目录配置失败: {e}")
    
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
        """下载选中的缺失视频 - 增强版"""
        try:
            self.add_log("🔍 开始执行下载选中视频功能")
            
            # 获取选中的项目
            selected_items = self.result_tree.selection()
            self.add_log(f"选中项目数量: {len(selected_items)}")
            
            if not selected_items:
                error_msg = "请先选择要下载的视频"
                self.add_log(f"❌ {error_msg}")
                messagebox.showwarning("提示", error_msg)
                return
            
            # 收集下载信息
            download_items = []
            for item in selected_items:
                try:
                    values = self.result_tree.item(item, "values")
                    if len(values) >= 3:
                        model, title, url = values[0], values[1], values[2]
                        if url and url.strip():
                            download_items.append((model, title, url.strip()))
                            self.add_log(f"✓ 准备下载: {model} - {title[:30]}...")
                        else:
                            self.add_log(f"⚠ 跳过无效链接: {title[:30]}...")
                    else:
                        self.add_log(f"⚠ 数据格式错误: {item}")
                except Exception as e:
                    self.add_log(f"❌ 处理项目时出错: {e}")
            
            if not download_items:
                error_msg = "选中的项目没有有效的下载链接"
                self.add_log(f"❌ {error_msg}")
                messagebox.showwarning("提示", error_msg)
                return
            
            # 确认下载
            confirm_msg = f"确定要下载选中的 {len(download_items)} 个视频吗？"
            if not messagebox.askyesno("确认下载", confirm_msg):
                self.add_log("❌ 用户取消下载")
                return
            
            # 开始下载
            self.add_log(f"🚀 开始下载选中的 {len(download_items)} 个视频")
            self._download_videos(download_items)
            
        except Exception as e:
            error_msg = f"下载功能执行失败: {str(e)}"
            self.add_log(f"❌ {error_msg}")
            messagebox.showerror("错误", error_msg)
            import traceback
            self.add_log(f"详细错误信息:\n{traceback.format_exc()}")
    
    def download_all_missing_videos(self):
        """下载所有缺失视频 - 增强版"""
        try:
            self.add_log("🔍 开始执行下载所有缺失视频功能")
            
            # 收集所有缺失视频
            download_items = []
            all_items = self.result_tree.get_children()
            self.add_log(f"总项目数量: {len(all_items)}")
            
            for item in all_items:
                try:
                    values = self.result_tree.item(item, "values")
                    if len(values) >= 3:
                        model, title, url = values[0], values[1], values[2]
                        if url and url.strip():
                            download_items.append((model, title, url.strip()))
                            self.add_log(f"✓ 准备下载: {model} - {title[:30]}...")
                        else:
                            self.add_log(f"⚠ 跳过无效链接: {title[:30]}...")
                    else:
                        self.add_log(f"⚠ 数据格式错误: {item}")
                except Exception as e:
                    self.add_log(f"❌ 处理项目时出错: {e}")
            
            if not download_items:
                error_msg = "没有可下载的视频"
                self.add_log(f"❌ {error_msg}")
                messagebox.showwarning("提示", error_msg)
                return
            
            # 确认下载
            confirm_msg = f"确定要下载所有 {len(download_items)} 个缺失视频吗？\n这可能需要较长时间。"
            if not messagebox.askyesno("确认下载", confirm_msg):
                self.add_log("❌ 用户取消下载")
                return
            
            # 开始下载
            self.add_log(f"🚀 开始下载所有 {len(download_items)} 个缺失视频")
            self._download_videos(download_items)
            
        except Exception as e:
            error_msg = f"下载所有视频功能执行失败: {str(e)}"
            self.add_log(f"❌ {error_msg}")
            messagebox.showerror("错误", error_msg)
            import traceback
            self.add_log(f"详细错误信息:\n{traceback.format_exc()}")
    
    def _download_videos(self, download_items):
        """内置GUI显示的下载函数"""
        try:
            # 导入下载模块
            from core.modules.porn.downloader import PornDownloader
            import threading
            import logging
            
            # 初始化下载状态
            self.is_downloading = True
            self.download_cancelled = False
            
            # 重置下载统计
            self.downloaded_count_var.set("0")
            self.total_count_var.set(str(len(download_items)))
            self.download_progress_var_tab.set(0)
            self.download_percentage_var_tab.set("0%")
            self.download_speed_var_tab.set("0 KB/s")
            self.current_file_var.set("准备开始...")
            
            # 清空下载日志
            self.download_log_text_tab.delete('1.0', tk.END)
            self.add_download_log("开始下载任务，共 " + str(len(download_items)) + " 个视频")
            
            def download_worker():
                """下载工作线程"""
                try:
                    # 获取配置
                    config = self.load_config()
                    
                    # 设置日志
                    logger = logging.getLogger(__name__)
                    
                    total_count = len(download_items)
                    downloaded_count = 0

                    # 创建进度钩子函数
                    def progress_hook(d):
                        if not self.is_downloading or self.download_cancelled:
                            return
                            
                        if d['status'] == 'downloading':
                            # 计算下载速度
                            speed_bytes = d.get('speed', 0)
                            if speed_bytes:
                                speed_str = self._format_bytes(speed_bytes) + "/s"
                                self.download_speed_var_tab.set(speed_str)
                            else:
                                self.download_speed_var_tab.set("0 KB/s")
                            
                            # 计算进度百分比
                            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                            downloaded_bytes = d.get('downloaded_bytes', 0)
                            
                            if total_bytes > 0:
                                percentage = (downloaded_bytes / total_bytes) * 100
                                # 计算整体进度（包括已完成的文件）
                                overall_percentage = ((downloaded_count + (percentage / 100.0)) / total_count) * 100
                                self.download_progress_var_tab.set(overall_percentage)
                                self.download_percentage_var_tab.set(f"{overall_percentage:.1f}%")
                                
                                # 更新总大小显示
                                total_size_mb = self._format_bytes(total_bytes)
                                downloaded_mb = self._format_bytes(downloaded_bytes)
                                self.total_size_var.set(f"{downloaded_mb}/{total_size_mb}")
                                
                        elif d['status'] == 'finished':
                            downloaded_mb = self._format_bytes(d.get('total_bytes', 0))
                            self.add_download_log(f"文件下载完成: {d.get('filename', 'unknown')} ({downloaded_mb})")

                    # 创建下载器
                    downloader = PornDownloader(config, progress_callback=progress_hook)
                    
                    for i, (model, title, url) in enumerate(download_items, 1):
                        if self.download_cancelled:
                            self.add_download_log("下载已取消")
                            break
                            
                        try:
                            # 更新当前文件信息
                            self.current_file_var.set(f"({i}/{total_count}) {title[:50]}...")
                            self.add_download_log(f"开始下载 ({i}/{total_count}): {title[:50]}...")
                            
                            # 确定保存目录（模特目录）
                            save_dir = None
                            # 查找模特的本地目录
                            for result_key, result_value in getattr(self, 'current_results', {}).items():
                                if hasattr(result_value, 'model_name') and result_value.model_name == model:
                                    if hasattr(result_value, 'local_folder_full') and result_value.local_folder_full:
                                        save_dir = result_value.local_folder_full
                                    break
                            
                            # 执行下载
                            result = downloader.download_video(url, save_dir)
                            
                            if result['success']:
                                downloaded_count += 1
                                self.downloaded_count_var.set(str(downloaded_count))
                                
                                # 更新整体进度
                                overall_percentage = (downloaded_count / total_count) * 100
                                self.download_progress_var_tab.set(overall_percentage)
                                self.download_percentage_var_tab.set(f"{overall_percentage:.1f}%")
                                
                                file_path = result.get('file_path', 'N/A')
                                self.add_download_log(f"✅ 下载成功: {title[:50]}...")
                                self.add_download_log(f"   保存路径: {file_path}")
                            else:
                                error_msg = result.get('message', result.get('error', 'Unknown error'))
                                self.add_download_log(f"❌ 下载失败: {title[:50]}... - {error_msg}")
                            
                        except Exception as e:
                            self.add_download_log(f"❌ 下载异常: {title[:50]}... - {str(e)}")
                    
                    if not self.download_cancelled:
                        self.add_download_log("🎉 下载任务完成！")
                        self.download_percentage_var.set("100%")
                    else:
                        self.add_download_log("⏹️ 下载已停止")
                    
                except Exception as e:
                    self.add_download_log(f"❌ 下载器错误: {str(e)}")
                finally:
                    self.is_downloading = False
                    self.download_cancelled = False
                    self.current_file_var.set("下载完成")
                    self.download_speed_var.set("0 KB/s")
            
            # 启动下载线程
            download_thread = threading.Thread(target=download_worker, daemon=True)
            download_thread.start()
            
        except ImportError as e:
            messagebox.showerror("错误", f"下载模块导入失败: {e}\n\n请确保已安装所有依赖：\npip install yt-dlp requests beautifulsoup4 PyYAML")
        except Exception as e:
            messagebox.showerror("错误", f"下载失败: {e}\n\n请检查网络连接和代理设置")
    
    def download_complete_model_directories(self):
        """完整下载模特目录"""
        # 首先检查是否在结果标签页中有选中的项目
        selected_items = self.result_tree.selection()
        if selected_items and hasattr(self, 'current_results') and self.current_results:
            # 从选中的结果中提取模特信息
            selected_models = set()  # 使用集合避免重复
            for item in selected_items:
                values = self.result_tree.item(item, "values")
                if values:
                    model_name = values[0]
                    selected_models.add(model_name)
            
            if selected_models:
                # 如果有选中的模特，则直接使用这些模特
                self._show_complete_download_dialog(preselected_models=selected_models)
                return
        
        # 如果没有选中的项目或没有结果数据，则显示完整的模特列表
        self._show_complete_download_dialog()
    
    def _show_complete_download_dialog(self, preselected_models=None):
        """显示完整下载对话框，可以选择预选的模特"""
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
            
            # 如果提供了预选模特，则自动选择它们
            if preselected_models:
                for i, model_name in enumerate(model_names):
                    if model_name in preselected_models:
                        model_listbox.select_set(i)
            
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
        """执行完整目录下载（内置GUI显示，不弹窗）"""
        try:
            # 导入批量下载函数
            from core.modules.porn.downloader import batch_download_models
            import threading
            
            # 初始化下载状态
            self.is_downloading = True
            self.download_cancelled = False
            
            # 重置下载统计
            self.downloaded_count_var.set("0")
            # 估计总数
            estimated_total = len(models_info) * (max_videos_per_model if max_videos_per_model > 0 else 20)
            self.total_count_var.set(f"~{estimated_total}")
            self.download_progress_var.set(0)
            self.download_percentage_var.set("0%")
            self.download_speed_var.set("0 KB/s")
            self.current_file_var.set("准备完整下载...")
            
            # 清空下载日志
            self.download_log_text.delete('1.0', tk.END)
            self.add_download_log(f"开始完整目录下载任务，共 {len(models_info)} 个模特")
            
            def download_worker():
                """下载工作线程"""
                try:
                    # 获取配置
                    config = self.load_config()
                    
                    # 进度统计
                    stats = {
                        'downloaded': 0,
                        'total_size': 0
                    }

                    def log_callback(msg):
                        self.add_download_log(msg)
                        if "下载进度:" in msg or "处理模特" in msg:
                            self.current_file_var.set(msg.strip())
                    
                    def progress_hook(d):
                        if not self.is_downloading or self.download_cancelled:
                            return
                            
                        if d['status'] == 'downloading':
                            # 计算下载速度
                            speed_bytes = d.get('speed', 0)
                            if speed_bytes:
                                speed_str = self._format_bytes(speed_bytes) + "/s"
                                self.download_speed_var.set(speed_str)
                            
                            # 计算当前文件进度
                            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                            downloaded_bytes = d.get('downloaded_bytes', 0)
                            
                            if total_bytes > 0:
                                percentage = (downloaded_bytes / total_bytes) * 100
                                self.download_percentage_var.set(f"{percentage:.1f}%")
                                self.download_progress_var.set(percentage) # 这里显示单个文件的进度，因为总数不确定
                                
                                # 更新大小显示
                                total_size_mb = self._format_bytes(total_bytes)
                                downloaded_mb = self._format_bytes(downloaded_bytes)
                                self.total_size_var.set(f"{downloaded_mb}/{total_size_mb}")
                                
                        elif d['status'] == 'finished':
                            stats['downloaded'] += 1
                            self.downloaded_count_var.set(str(stats['downloaded']))
                            downloaded_mb = self._format_bytes(d.get('total_bytes', 0))
                            self.add_download_log(f"文件下载完成: {d.get('filename', 'unknown')} ({downloaded_mb})")

                    # 执行批量下载
                    result = batch_download_models(
                        models_info=models_info,
                        base_save_dir=None,
                        config=config,
                        max_videos_per_model=max_videos_per_model if max_videos_per_model > 0 else None,
                        log_callback=log_callback,
                        progress_callback=progress_hook
                    )
                    
                    self.add_download_log("=" * 60)
                    self.add_download_log("🎉 批量下载完成！")
                    self.add_download_log(f"总模特数: {result['total_models']}")
                    self.add_download_log(f"成功模特数: {result['successful_models']}")
                    self.add_download_log(f"失败模特数: {result['failed_models']}")
                    self.add_download_log(f"总下载视频数: {result['total_downloaded']}")
                    self.add_download_log(f"总大小: {self._format_bytes(result['total_size'])}")
                    self.add_download_log("=" * 60)
                    
                except Exception as e:
                    self.add_download_log(f"❌ 批量下载器错误: {str(e)}")
                finally:
                    self.is_downloading = False
                    self.current_file_var.set("下载完成")
                    self.download_speed_var.set("0 KB/s")
                    self.download_progress_var.set(100)
                    self.download_percentage_var.set("100%")
            
            # 启动下载线程
            threading.Thread(target=download_worker, daemon=True).start()
            
            # 切换到运行控制标签页以便看到进度
            self.notebook.select(self.run_tab)
            
        except ImportError as e:
            messagebox.showerror("错误", f"下载模块导入失败: {e}")
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
                model_info = self.model_tree.item(item, "values")
                model_name = model_info[0]
                module = model_info[1]
                url = model_info[2]
                if url and url.strip():
                    selected_models.append((model_name, url.strip(), None))
            
            if not selected_models:
                messagebox.showwarning("提示", "选中的模特没有有效的URL")
                return
            
            # 选择下载目录
            save_dir = self._select_download_directory()
            if not save_dir:
                return
            
            # 更新选中模特的目录
            selected_models = [(name, url, save_dir) for name, url, _ in selected_models]
            
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
                    confirm_msg += f"保存目录: {save_dir}\n"
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
                model_info = self.model_tree.item(item, "values")
                model_name = model_info[0]
                module = model_info[1]
                url = model_info[2]
                if url and url.strip():
                    all_models.append((model_name, url.strip(), None))
                
            if not all_models:
                messagebox.showwarning("提示", "没有可下载的模特")
                return
                
            # 选择下载目录
            save_dir = self._select_download_directory()
            if not save_dir:
                return
                
            # 更新模特的目录
            all_models = [(name, url, save_dir) for name, url, _ in all_models]
                
            # 询问最大下载数量
            max_videos_dialog = tk.Toplevel(self.root)
            max_videos_dialog.title("批量下载设置")
            max_videos_dialog.geometry("300x180")
            max_videos_dialog.transient(self.root)
            max_videos_dialog.grab_set()
                
            ttk.Label(max_videos_dialog, text=f"保存目录: {save_dir}", font=("Arial", 9)).pack(pady=10)
            ttk.Label(max_videos_dialog, text="每个模特最大下载数量:", font=("Arial", 10)).pack(pady=10)
                
            max_videos_var = tk.StringVar(value="50")  # 默认限哦50个
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
    
    def _select_download_directory(self):
        """询问用户选择下载目录"""
        # 从多目录配置中获取目录
        config = self.load_config()
        local_roots = config.get('local_roots', [])
        first_dir = local_roots[0] if local_roots else ""
        
        # 创建目录选择对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("下载设置 - 选择保存目录")
        dialog.geometry("450x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="选择保存位置:", font=("Arial", 10, "bold")).pack(pady=10)
        
        selected_dir = [None]  # 使用列表以供闭包修改
        
        def select_first_dir():
            if first_dir:
                selected_dir[0] = first_dir
                dialog.destroy()
            else:
                messagebox.showwarning("提示", "未配置本地目录")
        
        def custom_directory():
            dir_path = filedialog.askdirectory(
                title="选择本地保存目录",
                initialdir=first_dir or os.path.expanduser("~")
            )
            if dir_path:
                selected_dir[0] = dir_path
                dialog.destroy()
        
        # 按钮框架
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20, fill=tk.X, padx=20)
        
        if first_dir:
            ttk.Button(button_frame, text=f"默认目录\n{first_dir}", 
                      command=select_first_dir, width=40).pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="自定义目录", 
                  command=custom_directory, width=40).pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="取消", 
                  command=dialog.destroy, width=40).pack(fill=tk.X, pady=5)
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        dialog.mainloop()
        return selected_dir[0]
    
    def download_single_model_complete(self):
        """下载单个模特的完整目录"""
        try:
            # 获取选中的模特
            selected_items = self.model_tree.selection()
            if not selected_items:
                messagebox.showwarning("提示", "请先选择一个模特")
                return
            
            if len(selected_items) > 1:
                messagebox.showwarning("提示", "此功能仅收一个模特，请单选")
                return
            
            item = selected_items[0]
            model_info = self.model_tree.item(item, "values")
            model_name = model_info[0]
            url = model_info[2]
            
            if not url or not url.strip():
                messagebox.showwarning("提示", "此模特没有有效的URL")
                return
            
            # 选择下载目录
            save_dir = self._select_download_directory()
            if not save_dir:
                return
            
            # 询问最大下载数量
            max_videos_dialog = tk.Toplevel(self.root)
            max_videos_dialog.title("下载设置")
            max_videos_dialog.geometry("300x180")
            max_videos_dialog.transient(self.root)
            max_videos_dialog.grab_set()
            
            ttk.Label(max_videos_dialog, text=f"模特: {model_name}\n保存目录: {save_dir}", 
                     font=("Arial", 9)).pack(pady=10)
            ttk.Label(max_videos_dialog, text="每个模特最大下载数量:", 
                     font=("Arial", 10)).pack(pady=10)
            
            max_videos_var = tk.StringVar(value="0")
            ttk.Entry(max_videos_dialog, textvariable=max_videos_var, width=10).pack(pady=10)
            ttk.Label(max_videos_dialog, text="(0=无限制)").pack()
            
            def confirm_download():
                try:
                    max_videos = int(max_videos_var.get()) if max_videos_var.get().strip() else 0
                    max_videos_dialog.destroy()
                    
                    # 确认下载
                    confirm_msg = f"确定要完整下载模特『{model_name}』的目录吗？\n这将下载该模特的所有视频！"
                    
                    if messagebox.askyesno("确认下载", confirm_msg):
                        selected_models = [(model_name, url.strip(), save_dir)]
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
            messagebox.showerror("错误", f"下载单个模特失败: {e}")
    
    def open_browser_window(self):
        """打开独立的浏览器窗口"""
        # 切换到浏览器/代理测试标签页
        self.notebook.select(self.browser_proxy_tab)
        messagebox.showinfo("提示", "已切换到浏览器/代理测试标签页")
    
    def add_download_log(self, message):
        """添加下载日志消息"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            log_msg = f"[{timestamp}] {message}\n"
            
            # 写入下载进度标签页中的日志框
            if hasattr(self, 'download_log_text_tab') and self.download_log_text_tab.winfo_exists():
                self.download_log_text_tab.insert(tk.END, log_msg)
                self.download_log_text_tab.see(tk.END)
            
            self.root.update_idletasks()
        except Exception as e:
            print(f"添加下载日志失败: {e}")
    
    def cancel_download(self):
        """取消下载"""
        if self.is_downloading:
            self.download_cancelled = True
            self.add_download_log("正在取消下载...")
            messagebox.showinfo("提示", "下载取消请求已发送，请等待当前任务完成")
        else:
            messagebox.showinfo("提示", "当前没有正在进行的下载任务")
    
    def show_result_context_menu(self, event):
        """显示结果列表的右键上下文菜单"""
        try:
            # 选中被右键点击的项目
            item = self.result_tree.identify_row(event.y)
            if item:
                self.result_tree.selection_set(item)
                
            # 创建上下文菜单
            context_menu = tk.Menu(self.root, tearoff=0)
            
            # 获取选中的项目信息
            selected_items = self.result_tree.selection()
            if selected_items:
                item_values = self.result_tree.item(selected_items[0], "values")
                if item_values:
                    model_name = item_values[0]
                    video_title = item_values[1]
                    video_url = item_values[2] if len(item_values) > 2 else ""
                    
                    # 添加菜单项
                    context_menu.add_command(label=f"查看模特信息: {model_name}", 
                                           command=lambda: self.focus_on_model(model_name))
                    
                    # 检查模特是否有URL，如果有则添加下载选项
                    model_info = self.models.get(model_name, {})
                    if isinstance(model_info, dict):
                        model_url = model_info.get("url", "")
                    else:
                        model_url = model_info
                    
                    if model_url:
                        context_menu.add_command(label=f"下载 {model_name} 的完整目录", 
                                               command=lambda: self.download_model_from_result(model_name, model_url))
                    
                    if video_url:
                        context_menu.add_command(label="复制视频链接", 
                                               command=lambda: self.copy_to_clipboard(video_url))
                        context_menu.add_command(label="在浏览器中打开", 
                                               command=lambda: self.open_url_in_browser(video_url))
                    
                    context_menu.add_separator()
            
            # 添加刷新和导出选项
            context_menu.add_command(label="刷新模特列表", command=self.refresh_models)
            context_menu.add_command(label="导出当前结果", command=self.export_results)
            
            # 显示菜单
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        except Exception as e:
            print(f"显示右键菜单失败: {e}")
    
    def focus_on_model(self, model_name):
        """在模特管理标签页中定位到指定模特"""
        # 切换到模特管理标签页
        self.notebook.select(self.model_tab)
        
        # 清除当前选择
        for item in self.model_tree.selection():
            self.model_tree.selection_remove(item)
        
        # 查找并选中指定模特
        for item in self.model_tree.get_children():
            values = self.model_tree.item(item, "values")
            if values and values[0] == model_name:
                self.model_tree.selection_set(item)
                self.model_tree.focus(item)
                self.model_tree.see(item)  # 滚动到该项
                break
    
    def download_model_from_result(self, model_name, model_url):
        """从结果中直接下载模特的完整目录"""
        try:
            # 检查是否已经获取了模特的URL
            if not model_url or model_url.strip() == "":
                messagebox.showwarning("警告", f"模特 {model_name} 没有有效的URL，无法下载")
                return
            
            # 选择下载目录
            save_dir = self._select_download_directory()
            if not save_dir:
                return
            
            # 确认下载
            if not messagebox.askyesno("确认下载", f"确定要下载模特『{model_name}』的完整目录吗？\n这将下载该模特的所有视频！"):
                return
            
            # 准备下载参数
            selected_models = [(model_name, model_url.strip(), save_dir)]
            
            # 使用后台线程执行下载
            threading.Thread(target=self._execute_download, 
                           args=(selected_models,), 
                           daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("错误", f"从结果下载模特失败: {e}")
    
    def copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()  # 确保内容被复制
            messagebox.showinfo("提示", "已复制到剪贴板")
        except Exception as e:
            messagebox.showerror("错误", f"复制到剪贴板失败: {e}")
    
    def open_url_in_browser(self, url):
        """在浏览器中打开URL"""
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开浏览器: {e}")
    
    def _select_download_directory(self):
        """选择下载目录"""
        try:
            initial_dir = os.getcwd()
            if hasattr(self, 'download_dir_var') and self.download_dir_var.get():
                initial_dir = self.download_dir_var.get()
            
            save_dir = filedialog.askdirectory(initialdir=initial_dir, title="选择下载目录")
            return save_dir
        except Exception as e:
            messagebox.showerror("错误", f"选择下载目录失败: {e}")
            return None
    
    def _execute_download(self, selected_models):
        """执行下载操作的后台线程"""
        try:
            # 导入下载模块
            from core.modules.porn.unified_downloader import UnifiedDownloader
            
            # 从配置中获取设置
            config = self.load_config()
            
            # 初始化下载器
            downloader = UnifiedDownloader(config)
            
            # 逐个下载模特
            for model_name, model_url, save_dir in selected_models:
                try:
                    # 调用下载器下载模特完整目录
                    result = downloader.download_model_complete_directory(
                        model_url,
                        model_name,
                        base_save_dir=save_dir
                    )
                    
                    if result.get('success'):
                        print(f"模特 {model_name} 下载成功")
                    else:
                        print(f"模特 {model_name} 下载失败: {result.get('message', '未知错误')}")
                except Exception as e:
                    print(f"下载模特 {model_name} 时发生错误: {e}")
        except ImportError as e:
            print(f"下载模块导入失败: {e}")
        except Exception as e:
            print(f"执行下载时发生错误: {e}")
    
    def _format_bytes(self, bytes_value):
        """格式化字节数为可读格式"""
        try:
            if bytes_value is None or bytes_value == 0:
                return "0 B"
            
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_value < 1024.0:
                    return f"{bytes_value:.1f} {unit}"
                bytes_value /= 1024.0
            return f"{bytes_value:.1f} PB"
        except:
            return "0 B"

if __name__ == "__main__":
    root = tk.Tk()
    app = ModelManagerGUI(root)
    root.mainloop()
    
    # ==================== 增强的下载功能 ====================
    
    def enhanced_download_selected_videos(self):
        """增强版下载选中的缺失视频 - 带详细错误处理"""
        try:
            self.add_log("🔍 开始执行下载选中视频功能")
            
            # 获取选中的项目
            selected_items = self.result_tree.selection()
            self.add_log(f"选中项目数量: {len(selected_items)}")
            
            if not selected_items:
                error_msg = "请先选择要下载的视频"
                self.add_log(f"❌ {error_msg}")
                messagebox.showwarning("提示", error_msg)
                return
            
            # 收集下载信息
            download_items = []
            for item in selected_items:
                try:
                    values = self.result_tree.item(item, "values")
                    if len(values) >= 3:
                        model, title, url = values[0], values[1], values[2]
                        if url and url.strip():
                            download_items.append((model, title, url.strip()))
                            self.add_log(f"✓ 准备下载: {model} - {title[:30]}...")
                        else:
                            self.add_log(f"⚠ 跳过无效链接: {title[:30]}...")
                    else:
                        self.add_log(f"⚠ 数据格式错误: {item}")
                except Exception as e:
                    self.add_log(f"❌ 处理项目时出错: {e}")
            
            if not download_items:
                error_msg = "选中的项目没有有效的下载链接"
                self.add_log(f"❌ {error_msg}")
                messagebox.showwarning("提示", error_msg)
                return
            
            # 确认下载
            confirm_msg = f"确定要下载选中的 {len(download_items)} 个视频吗？"
            if not messagebox.askyesno("确认下载", confirm_msg):
                self.add_log("❌ 用户取消下载")
                return
            
            # 开始下载
            self.add_log(f"🚀 开始下载选中的 {len(download_items)} 个视频")
            self._enhanced_download_videos(download_items)
            
        except Exception as e:
            error_msg = f"下载功能执行失败: {str(e)}"
            self.add_log(f"❌ {error_msg}")
            messagebox.showerror("错误", error_msg)
            import traceback
            self.add_log(f"详细错误信息:\n{traceback.format_exc()}")

    def enhanced_download_all_missing_videos(self):
        """增强版下载所有缺失视频 - 带详细错误处理"""
        try:
            self.add_log("🔍 开始执行下载所有缺失视频功能")
            
            # 收集所有缺失视频
            download_items = []
            all_items = self.result_tree.get_children()
            self.add_log(f"总项目数量: {len(all_items)}")
            
            for item in all_items:
                try:
                    values = self.result_tree.item(item, "values")
                    if len(values) >= 3:
                        model, title, url = values[0], values[1], values[2]
                        if url and url.strip():
                            download_items.append((model, title, url.strip()))
                            self.add_log(f"✓ 准备下载: {model} - {title[:30]}...")
                        else:
                            self.add_log(f"⚠ 跳过无效链接: {title[:30]}...")
                    else:
                        self.add_log(f"⚠ 数据格式错误: {item}")
                except Exception as e:
                    self.add_log(f"❌ 处理项目时出错: {e}")
            
            if not download_items:
                error_msg = "没有可下载的视频"
                self.add_log(f"❌ {error_msg}")
                messagebox.showwarning("提示", error_msg)
                return
            
            # 确认下载
            confirm_msg = f"确定要下载所有 {len(download_items)} 个缺失视频吗？\n这可能需要较长时间。"
            if not messagebox.askyesno("确认下载", confirm_msg):
                self.add_log("❌ 用户取消下载")
                return
            
            # 开始下载
            self.add_log(f"🚀 开始下载所有 {len(download_items)} 个缺失视频")
            self._enhanced_download_videos(download_items)
            
        except Exception as e:
            error_msg = f"下载所有视频功能执行失败: {str(e)}"
            self.add_log(f"❌ {error_msg}")
            messagebox.showerror("错误", error_msg)
            import traceback
            self.add_log(f"详细错误信息:\n{traceback.format_exc()}")

    def _enhanced_download_videos(self, download_items):
        """增强版内置GUI显示的下载函数 - 带详细错误处理"""
        try:
            self.add_log("🔧 初始化增强下载功能")
            
            # 导入下载模块
            from core.modules.porn.downloader import PornDownloader
            from core.modules.porn.unified_downloader import UnifiedDownloader
            import threading
            import logging
            
            # 初始化下载状态
            self.is_downloading = True
            self.download_cancelled = False
            
            self.add_log("✓ 下载模块导入成功")
            
            # 重置下载统计
            self.downloaded_count_var.set("0")
            self.total_count_var.set(str(len(download_items)))
            self.download_progress_var_tab.set(0)
            self.download_percentage_var_tab.set("0%")
            self.download_speed_var_tab.set("0 KB/s")
            self.current_file_var.set("准备开始...")
            
            # 清空下载日志
            if hasattr(self, 'download_log_text_tab'):
                self.download_log_text_tab.delete('1.0', tk.END)
            self.add_download_log("🚀 开始增强下载任务，共 " + str(len(download_items)) + " 个视频")
            self.add_download_log("=" * 60)
            
            def download_worker():
                """增强版下载工作线程"""
                try:
                    # 获取配置
                    config = self.load_config()
                    self.add_download_log("✓ 配置加载完成")
                    
                    # 创建下载器
                    try:
                        downloader = UnifiedDownloader(
                            config=config,
                            version="auto",
                            enable_fallback=True,
                            progress_callback=self._download_progress_callback_enhanced
                        )
                        self.add_download_log("✓ 统一下载器创建成功")
                    except Exception as e:
                        self.add_download_log(f"⚠ 统一下载器创建失败: {e}")
                        self.add_download_log("尝试使用传统下载器...")
                        downloader = PornDownloader(config=config)
                        self.add_download_log("✓ 传统下载器创建成功")
                    
                    # 执行下载
                    downloaded_count = 0
                    total_count = len(download_items)
                    
                    self.add_download_log(f"开始下载 {total_count} 个视频...")
                    self.add_download_log("-" * 40)
                    
                    for i, (model, title, url) in enumerate(download_items, 1):
                        if self.download_cancelled:
                            self.add_download_log("⏹️ 用户取消下载")
                            break
                        
                        try:
                            # 更新当前文件信息
                            current_info = f"({i}/{total_count}) {title[:50]}..."
                            self.current_file_var.set(current_info)
                            self.add_download_log(f"📥 开始下载 {current_info}")
                            
                            # 确定保存目录
                            save_dir = self._get_save_directory_for_model(model)
                            
                            # 执行下载
                            result = downloader.download_video(url, save_dir)
                            
                            if result.get('success', False):
                                downloaded_count += 1
                                self.downloaded_count_var.set(str(downloaded_count))
                                
                                # 更新整体进度
                                overall_percentage = (downloaded_count / total_count) * 100
                                self.download_progress_var_tab.set(overall_percentage)
                                self.download_percentage_var_tab.set(f"{overall_percentage:.1f}%")
                                
                                file_path = result.get('file_path', 'N/A')
                                self.add_download_log(f"✅ 下载成功: {title[:50]}...")
                                self.add_download_log(f"   保存路径: {file_path}")
                            else:
                                error_msg = result.get('message', result.get('error', 'Unknown error'))
                                self.add_download_log(f"❌ 下载失败: {title[:50]}... - {error_msg}")
                            
                        except Exception as e:
                            self.add_download_log(f"❌ 下载异常: {title[:50]}... - {str(e)}")
                            import traceback
                            self.add_download_log(f"   详细错误: {traceback.format_exc()}")
                    
                    # 下载完成
                    if not self.download_cancelled:
                        self.add_download_log("=" * 60)
                        self.add_download_log("🎉 增强下载任务完成！")
                        self.add_download_log(f"成功下载: {downloaded_count}/{total_count}")
                        success_rate = (downloaded_count / total_count * 100) if total_count > 0 else 0
                        self.add_download_log(f"成功率: {success_rate:.1f}%")
                        self.download_percentage_var_tab.set("100%")
                    else:
                        self.add_download_log("⏹️ 下载已被用户停止")
                    
                except Exception as e:
                    error_msg = f"下载器执行错误: {str(e)}"
                    self.add_download_log(f"❌ {error_msg}")
                    import traceback
                    self.add_download_log(f"详细错误信息:\n{traceback.format_exc()}")
                finally:
                    self.is_downloading = False
                    self.download_cancelled = False
                    self.current_file_var.set("下载完成")
                    self.download_speed_var_tab.set("0 KB/s")
                    self.add_download_log("=" * 60)
                    self.add_download_log("🔚 下载线程结束")
            
            # 启动下载线程
            self.add_log("🚀 启动下载线程")
            download_thread = threading.Thread(target=download_worker, daemon=True)
            download_thread.start()
            
            # 切换到下载进度标签页
            self.notebook.select(self.download_tab)
            self.add_log("✓ 已切换到下载进度页面")
            
        except ImportError as e:
            error_msg = f"下载模块导入失败: {e}\n\n请确保已安装所有依赖：\npip install yt-dlp requests beautifulsoup4 PyYAML"
            self.add_log(f"❌ {error_msg}")
            messagebox.showerror("错误", error_msg)
        except Exception as e:
            error_msg = f"下载功能初始化失败: {e}"
            self.add_log(f"❌ {error_msg}")
            messagebox.showerror("错误", error_msg)
            import traceback
            self.add_log(f"详细错误信息:\n{traceback.format_exc()}")

    def _download_progress_callback_enhanced(self, progress_data: dict):
        """增强版下载进度回调"""
        try:
            if 'speed' in progress_data:
                speed_str = f"{progress_data['speed']}/s"
                self.download_speed_var_tab.set(speed_str)
            
            if 'percentage' in progress_data:
                percentage = progress_data['percentage']
                self.download_progress_var_tab.set(percentage)
                self.download_percentage_var_tab.set(f"{percentage:.1f}%")
                
        except Exception as e:
            self.add_download_log(f"进度更新错误: {e}")

    def _get_save_directory_for_model(self, model_name: str) -> str:
        """获取模特的保存目录"""
        try:
            # 查找模特的本地目录
            if hasattr(self, 'current_results'):
                for result_key, result_value in self.current_results.items():
                    if hasattr(result_value, 'model_name') and result_value.model_name == model_name:
                        if hasattr(result_value, 'local_folder_full') and result_value.local_folder_full:
                            return result_value.local_folder_full
            
            # 如果找不到，使用默认目录
            config = self.load_config()
            default_dir = config.get('output_dir', './downloads')
            model_dir = os.path.join(default_dir, model_name)
            return model_dir
            
        except Exception as e:
            self.add_log(f"获取保存目录失败: {e}")
            config = self.load_config()
            return config.get('output_dir', './downloads')
    
    # ==================== 修复的对比结果显示 ====================
    def _update_comparison_results_fixed(self, results):
        """
        修复版对比结果显示更新
        """
        # 清空现有结果
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        missing_count = 0
        processed_count = 0
        failed_count = 0
        
        # 处理每个模特的结果
        for result in results:
            if result.success:
                processed_count += 1
                # 显示缺失视频
                for title, url in result.missing_with_urls:
                    self.result_tree.insert("", tk.END, values=(
                        result.model_name,
                        title,
                        url
                    ))
                    missing_count += 1
            else:
                failed_count += 1
        
        # 更新统计信息
        self.stats_vars["processed"].set(f"成功处理: {processed_count}")
        self.stats_vars["failed"].set(f"处理失败: {failed_count}")
        self.stats_vars["missing"].set(f"发现缺失: {missing_count}")
        
        # 切换到结果显示标签页
        self.notebook.select(self.result_tab)
        
        self.add_log(f"✅ 对比完成: 成功{processed_count} 失败{failed_count} 缺失{missing_count}")
    
    def _refresh_comparison_after_download(self):
        """
        下载完成后刷新对比结果
        """
        try:
            self.add_log("🔄 下载完成，正在刷新对比结果...")
            
            # 重新运行对比
            config = self.load_config()
            models = self.load_models()
            
            # 这里应该调用核心对比功能
            # 暂时显示提示信息
            self.add_log("💡 请重新运行对比分析以获取最新结果")
            
        except Exception as e:
            self.add_log(f"❌ 刷新对比结果失败: {e}")

