import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import threading
import queue
import time
from datetime import datetime
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

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
        
        # 初始化各标签页
        self.init_model_tab()
        self.init_run_tab()
        self.init_result_tab()
        
        # 加载模特数据
        self.models = self.load_models()
        self.update_model_list()
        
        # 队列用于线程间通信
        self.queue = queue.Queue()
        self.running = False
    
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
        
        # 搜索框
        search_frame = ttk.Frame(list_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="搜索: ").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        ttk.Button(search_frame, text="搜索", command=self.search_models).pack(side=tk.RIGHT)
        
        # 列表视图
        columns = ("model_name", "url")
        self.model_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # 设置列标题
        self.model_tree.heading("model_name", text="模特名称")
        self.model_tree.heading("url", text="链接")
        
        # 设置列宽
        self.model_tree.column("model_name", width=200)
        self.model_tree.column("url", width=400)
        
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
        
        # 刷新列表
        ttk.Button(action_frame, text="刷新列表", command=self.refresh_models, width=20).pack(fill=tk.X, pady=5)
        
        # 模特数量统计
        self.model_count_var = tk.StringVar(value="模特数量: 0")
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
        
        # 初始化默认目录
        self.dir_listbox.insert(tk.END, "F:\\作品")
        
        # 使用Selenium选项
        self.use_selenium_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="使用Selenium", variable=self.use_selenium_var).pack(anchor=tk.W, pady=2)
        
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
        
        # 导出按钮
        export_frame = ttk.Frame(result_frame)
        export_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(export_frame, text="导出结果", command=self.export_results).pack(side=tk.RIGHT)
    
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
                return json.load(f)
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
        
        # 添加模特数据
        for model_name, url in self.models.items():
            self.model_tree.insert("", tk.END, values=(model_name, url))
        
        # 更新统计信息
        self.model_count_var.set(f"模特数量: {len(self.models)}")
    
    def search_models(self):
        """搜索模特"""
        search_term = self.search_var.get().lower()
        
        # 清空现有列表
        for item in self.model_tree.get_children():
            self.model_tree.delete(item)
        
        # 添加匹配的模特
        for model_name, url in self.models.items():
            if search_term in model_name.lower() or search_term in url.lower():
                self.model_tree.insert("", tk.END, values=(model_name, url))
    
    def add_model(self):
        """添加模特"""
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("添加模特")
        dialog.geometry("500x200")
        dialog.resizable(False, False)
        
        # 居中显示
        dialog.update_idletasks()
        x = (self.root.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"500x200+{x}+{y}")
        
        # 创建框架
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 模特名称
        ttk.Label(frame, text="模特名称: ").grid(row=0, column=0, sticky=tk.W, pady=10)
        model_name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=model_name_var, width=40).grid(row=0, column=1, sticky=tk.W, pady=10)
        
        # 链接
        ttk.Label(frame, text="链接: ").grid(row=1, column=0, sticky=tk.W, pady=10)
        url_var = tk.StringVar()
        ttk.Entry(frame, textvariable=url_var, width=40).grid(row=1, column=1, sticky=tk.W, pady=10)
        
        # 按钮
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        def on_ok():
            model_name = model_name_var.get().strip()
            url = url_var.get().strip()
            
            if not model_name:
                messagebox.showerror("错误", "模特名称不能为空")
                return
            
            if not url:
                messagebox.showerror("错误", "链接不能为空")
                return
            
            # 添加到模型字典
            self.models[model_name] = url
            
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
    
    def edit_model(self):
        """编辑模特"""
        # 获取选中的项
        selected_items = self.model_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请选择要编辑的模特")
            return
        
        # 获取选中项的数据
        item = selected_items[0]
        model_name, url = self.model_tree.item(item, "values")
        
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("编辑模特")
        dialog.geometry("500x200")
        dialog.resizable(False, False)
        
        # 居中显示
        dialog.update_idletasks()
        x = (self.root.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"500x200+{x}+{y}")
        
        # 创建框架
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 模特名称
        ttk.Label(frame, text="模特名称: ").grid(row=0, column=0, sticky=tk.W, pady=10)
        model_name_var = tk.StringVar(value=model_name)
        ttk.Entry(frame, textvariable=model_name_var, width=40).grid(row=0, column=1, sticky=tk.W, pady=10)
        
        # 链接
        ttk.Label(frame, text="链接: ").grid(row=1, column=0, sticky=tk.W, pady=10)
        url_var = tk.StringVar(value=url)
        ttk.Entry(frame, textvariable=url_var, width=40).grid(row=1, column=1, sticky=tk.W, pady=10)
        
        # 按钮
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        def on_ok():
            new_model_name = model_name_var.get().strip()
            new_url = url_var.get().strip()
            
            if not new_model_name:
                messagebox.showerror("错误", "模特名称不能为空")
                return
            
            if not new_url:
                messagebox.showerror("错误", "链接不能为空")
                return
            
            # 更新模型字典
            if new_model_name != model_name:
                # 如果名称改变，删除旧的，添加新的
                del self.models[model_name]
                self.models[new_model_name] = new_url
            else:
                # 只更新链接
                self.models[model_name] = new_url
            
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
            # 导入核心模块
            from core.core import main
            
            # 获取所有目录
            dirs = [self.dir_listbox.get(i) for i in range(self.dir_listbox.size())]
            if not dirs:
                messagebox.showinfo("提示", "请至少添加一个本地目录")
                return
            
            # 运行脚本
            main(self.module_var.get(), dirs)
            
            # 发送完成消息
            self.queue.put(("completed", "运行完成"))
        except Exception as e:
            self.queue.put(("error", str(e)))
    
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
        
        # 继续轮询
        if self.running:
            self.root.after(100, self.check_queue)
    
    def open_config(self):
        """打开配置文件"""
        try:
            os.startfile("config.yaml")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开配置文件: {e}")
    
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
    
    def remove_local_dir(self):
        """删除选中的本地目录"""
        selected = self.dir_listbox.curselection()
        if selected:
            self.dir_listbox.delete(selected)
    
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

if __name__ == "__main__":
    root = tk.Tk()
    app = ModelManagerGUI(root)
    root.mainloop()
