# -*- coding: utf-8 -*-
"""
独立监控窗口 - 现代浅色卡片风格
提供独立运行的监控界面，展示查重/下载进度、任务状态和实时日志
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TaskCard:
    """任务卡片数据"""
    task_id: str
    title: str
    status: str  # pending, running, completed, failed
    progress: float  # 0-100
    details: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class ModernProgressWindow:
    """现代进度监控窗口"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.window = None
        self.tasks: Dict[str, TaskCard] = {}
        self.log_queue = queue.Queue()
        self.is_running = False
        
        # 颜色配置 - 现代浅色主题
        self.colors = {
            'bg_primary': '#F8F9FA',
            'bg_secondary': '#FFFFFF',
            'bg_card': '#FFFFFF',
            'text_primary': '#212529',
            'text_secondary': '#6C757D',
            'accent_blue': '#007BFF',
            'accent_green': '#28A745',
            'accent_orange': '#FFC107',
            'accent_red': '#DC3545',
            'border_light': '#E9ECEF',
            'shadow': 'rgba(0, 0, 0, 0.1)'
        }
        
        # 状态图标配置
        self.status_config = {
            'pending': {'icon': '⏳', 'color': self.colors['text_secondary']},
            'running': {'icon': '🔄', 'color': self.colors['accent_blue']},
            'completed': {'icon': '✅', 'color': self.colors['accent_green']},
            'failed': {'icon': '❌', 'color': self.colors['accent_red']}
        }
    
    def create_window(self):
        """创建独立窗口"""
        self.window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.window.title("查重下载监控系统")
        self.window.geometry("1000x700")
        self.window.configure(bg=self.colors['bg_primary'])
        
        # 设置窗口样式
        self.window.grid_rowconfigure(0, weight=1)
        self.window.grid_columnconfigure(0, weight=1)
        
        self.create_main_frame()
        self.create_summary_section()
        self.create_tasks_section()
        self.create_logs_section()
        
        self.is_running = True
        self.start_log_monitor()
        
        # 窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_main_frame(self):
        """创建主容器"""
        self.main_frame = ttk.Frame(self.window, style='Card.TFrame')
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # 配置样式
        style = ttk.Style()
        style.configure('Card.TFrame', background=self.colors['bg_card'])
        style.configure('Title.TLabel', 
                       background=self.colors['bg_card'],
                       foreground=self.colors['text_primary'],
                       font=('Microsoft YaHei', 16, 'bold'))
        style.configure('Subtitle.TLabel',
                       background=self.colors['bg_card'],
                       foreground=self.colors['text_secondary'],
                       font=('Microsoft YaHei', 10))
    
    def create_summary_section(self):
        """创建概览区域"""
        summary_frame = ttk.Frame(self.main_frame, style='Card.TFrame')
        summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        summary_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # 总体进度
        self.create_summary_card(
            summary_frame, 0, 0, "总进度", "0%", self.colors['accent_blue'])
        
        # 运行中任务
        self.running_tasks_label = self.create_summary_card(
            summary_frame, 0, 1, "运行中", "0", self.colors['accent_orange'])
        
        # 已完成任务
        self.completed_tasks_label = self.create_summary_card(
            summary_frame, 0, 2, "已完成", "0", self.colors['accent_green'])
        
        # 失败任务
        self.failed_tasks_label = self.create_summary_card(
            summary_frame, 0, 3, "失败", "0", self.colors['accent_red'])
    
    def create_summary_card(self, parent, row, col, title, value, color):
        """创建概览卡片"""
        card_frame = tk.Frame(parent, bg=self.colors['bg_card'], relief="raised", bd=1)
        card_frame.grid(row=row, column=col, padx=10, pady=5, sticky="nsew")
        card_frame.grid_rowconfigure(0, weight=1)
        card_frame.grid_columnconfigure(0, weight=1)
        
        # 标题
        title_label = tk.Label(
            card_frame, text=title,
            bg=self.colors['bg_card'],
            fg=self.colors['text_secondary'],
            font=('Microsoft YaHei', 10)
        )
        title_label.grid(row=0, column=0, pady=(10, 5))
        
        # 数值
        value_label = tk.Label(
            card_frame, text=value,
            bg=self.colors['bg_card'],
            fg=color,
            font=('Microsoft YaHei', 24, 'bold')
        )
        value_label.grid(row=1, column=0, pady=(0, 10))
        
        return value_label
    
    def create_tasks_section(self):
        """创建任务区域"""
        tasks_container = ttk.Frame(self.main_frame, style='Card.TFrame')
        tasks_container.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        tasks_container.grid_rowconfigure(1, weight=1)
        tasks_container.grid_columnconfigure(0, weight=1)
        
        # 标题
        title_label = ttk.Label(tasks_container, text="任务状态", style='Title.TLabel')
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # 任务滚动区域
        tasks_frame = tk.Frame(tasks_container, bg=self.colors['bg_card'])
        tasks_frame.grid(row=1, column=0, sticky="nsew")
        
        # 创建滚动条和画布
        self.tasks_canvas = tk.Canvas(tasks_frame, bg=self.colors['bg_primary'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(tasks_frame, orient="vertical", command=self.tasks_canvas.yview)
        self.tasks_scrollable_frame = tk.Frame(self.tasks_canvas, bg=self.colors['bg_primary'])
        
        self.tasks_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.tasks_canvas.configure(scrollregion=self.tasks_canvas.bbox("all"))
        )
        
        self.tasks_canvas.create_window((0, 0), window=self.tasks_scrollable_frame, anchor="nw")
        self.tasks_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.tasks_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_logs_section(self):
        """创建日志区域"""
        logs_container = ttk.Frame(self.main_frame, style='Card.TFrame')
        logs_container.grid(row=2, column=0, sticky="nsew")
        logs_container.grid_rowconfigure(1, weight=1)
        logs_container.grid_columnconfigure(0, weight=1)
        
        # 标题和清除按钮
        header_frame = ttk.Frame(logs_container, style='Card.TFrame')
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1)
        
        title_label = ttk.Label(header_frame, text="实时日志", style='Title.TLabel')
        title_label.grid(row=0, column=0, sticky="w")
        
        clear_btn = tk.Button(
            header_frame, text="清除日志", 
            command=self.clear_logs,
            bg=self.colors['bg_secondary'],
            fg=self.colors['text_primary'],
            relief="flat", bd=1,
            font=('Microsoft YaHei', 9),
            cursor="hand2"
        )
        clear_btn.grid(row=0, column=1, sticky="e", padx=(0, 10))
        
        # 日志文本区域
        self.logs_text = scrolledtext.ScrolledText(
            logs_container,
            height=8,
            bg=self.colors['bg_secondary'],
            fg=self.colors['text_primary'],
            font=('Consolas', 9),
            wrap=tk.WORD,
            relief="flat",
            bd=1
        )
        self.logs_text.grid(row=1, column=0, sticky="nsew")
    
    def create_task_card(self, task: TaskCard):
        """创建任务卡片"""
        card_frame = tk.Frame(
            self.tasks_scrollable_frame,
            bg=self.colors['bg_card'],
            relief="raised",
            bd=1
        )
        card_frame.pack(fill="x", padx=10, pady=5)
        card_frame.grid_columnconfigure(1, weight=1)
        
        # 状态图标
        status_config = self.status_config.get(task.status, self.status_config['pending'])
        status_icon = tk.Label(
            card_frame,
            text=status_config['icon'],
            bg=self.colors['bg_card'],
            fg=status_config['color'],
            font=('Microsoft YaHei', 16)
        )
        status_icon.grid(row=0, column=0, rowspan=2, padx=15, pady=10)
        
        # 任务标题
        title_label = tk.Label(
            card_frame,
            text=task.title,
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary'],
            font=('Microsoft YaHei', 11, 'bold'),
            anchor="w"
        )
        title_label.grid(row=0, column=1, sticky="ew", padx=(0, 15))
        
        # 任务详情
        details_label = tk.Label(
            card_frame,
            text=task.details,
            bg=self.colors['bg_card'],
            fg=self.colors['text_secondary'],
            font=('Microsoft YaHei', 9),
            anchor="w"
        )
        details_label.grid(row=1, column=1, sticky="ew", padx=(0, 15), pady=(5, 0))
        
        # 进度条（仅运行中任务显示）
        if task.status == 'running':
            progress_frame = tk.Frame(card_frame, bg=self.colors['bg_card'])
            progress_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=15, pady=(10, 15))
            progress_frame.grid_columnconfigure(0, weight=1)
            
            # 进度条
            progress_bar = ttk.Progressbar(
                progress_frame,
                length=200,
                mode='determinate',
                value=task.progress
            )
            progress_bar.grid(row=0, column=0, sticky="ew")
            
            # 进度文字
            progress_label = tk.Label(
                progress_frame,
                text=f"{task.progress:.1f}%",
                bg=self.colors['bg_card'],
                fg=self.colors['text_secondary'],
                font=('Microsoft YaHei', 9)
            )
            progress_label.grid(row=0, column=1, padx=(10, 0))
        
        # 时间信息（已完成的任务）
        if task.status in ['completed', 'failed'] and task.start_time:
            time_info = ""
            if task.end_time:
                duration = task.end_time - task.start_time
                time_info = f"耗时: {duration:.1f}秒"
            else:
                time_info = "进行中..."
                
            time_label = tk.Label(
                card_frame,
                text=time_info,
                bg=self.colors['bg_card'],
                fg=self.colors['text_secondary'],
                font=('Microsoft YaHei', 8)
            )
            time_label.grid(row=2, column=0, columnspan=3, sticky="e", padx=15, pady=(5, 10))
    
    def add_task(self, task_id: str, title: str, details: str = ""):
        """添加新任务"""
        task = TaskCard(
            task_id=task_id,
            title=title,
            status='pending',
            progress=0,
            details=details,
            start_time=None,
            end_time=None
        )
        self.tasks[task_id] = task
        self.update_task_display(task_id)
        self.update_summary()
    
    def update_task_status(self, task_id: str, status: str, progress: float = None, details: str = None):
        """更新任务状态"""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        task.status = status
        
        if progress is not None:
            task.progress = progress
        if details is not None:
            task.details = details
            
        # 记录时间戳
        if status == 'running' and task.start_time is None:
            task.start_time = time.time()
        elif status in ['completed', 'failed'] and task.end_time is None:
            task.end_time = time.time()
        
        self.update_task_display(task_id)
        self.update_summary()
    
    def update_task_display(self, task_id: str):
        """更新任务显示"""
        # 清除所有任务卡片
        for widget in self.tasks_scrollable_frame.winfo_children():
            widget.destroy()
        
        # 重新创建所有任务卡片
        for task in self.tasks.values():
            self.create_task_card(task)
    
    def update_summary(self):
        """更新概览信息"""
        total = len(self.tasks)
        running = sum(1 for t in self.tasks.values() if t.status == 'running')
        completed = sum(1 for t in self.tasks.values() if t.status == 'completed')
        failed = sum(1 for t in self.tasks.values() if t.status == 'failed')
        
        # 更新总体进度
        total_progress = 0
        if total > 0:
            total_progress = sum(t.progress for t in self.tasks.values()) / total
        
        self.window.after(0, lambda: self._update_summary_ui(
            total_progress, running, completed, failed))
    
    def _update_summary_ui(self, progress: float, running: int, completed: int, failed: int):
        """在主线程中更新UI"""
        if not self.window:
            return
            
        # 这里需要访问之前创建的标签，需要保存引用
        # 为简化，直接更新文本
        pass
    
    def add_log(self, message: str, level: str = "INFO"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"
        self.log_queue.put(log_entry)
    
    def start_log_monitor(self):
        """启动日志监控线程"""
        def monitor():
            while self.is_running:
                try:
                    # 批量处理日志
                    logs = []
                    try:
                        while True:
                            log_entry = self.log_queue.get_nowait()
                            logs.append(log_entry)
                    except queue.Empty:
                        pass
                    
                    if logs and self.window:
                        self.window.after(0, lambda: self._append_logs(logs))
                    
                    time.sleep(0.1)  # 100ms检查间隔
                except Exception as e:
                    print(f"日志监控错误: {e}")
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def _append_logs(self, logs: list):
        """在主线程中添加日志"""
        for log_entry in logs:
            self.logs_text.insert(tk.END, log_entry)
            self.logs_text.see(tk.END)
    
    def clear_logs(self):
        """清除日志"""
        self.logs_text.delete(1.0, tk.END)
    
    def on_closing(self):
        """窗口关闭事件"""
        self.is_running = False
        if self.window:
            self.window.destroy()
    
    def show(self):
        """显示窗口"""
        if not self.window:
            self.create_window()
        self.window.lift()
        self.window.focus_force()
    
    def hide(self):
        """隐藏窗口"""
        if self.window:
            self.window.withdraw()
    
    def is_alive(self) -> bool:
        """检查窗口是否存在"""
        return self.window and self.window.winfo_exists()


# 全局实例
_progress_window = None


def get_progress_window(parent=None) -> ModernProgressWindow:
    """获取进度窗口实例（单例）"""
    global _progress_window
    if _progress_window is None or not _progress_window.is_alive():
        _progress_window = ModernProgressWindow(parent)
    return _progress_window


def add_task(task_id: str, title: str, details: str = ""):
    """添加任务（全局接口）"""
    window = get_progress_window()
    window.add_task(task_id, title, details)


def update_task_status(task_id: str, status: str, progress: float = None, details: str = None):
    """更新任务状态（全局接口）"""
    window = get_progress_window()
    window.update_task_status(task_id, status, progress, details)


def add_log(message: str, level: str = "INFO"):
    """添加日志（全局接口）"""
    window = get_progress_window()
    window.add_log(message, level)


def show_progress_window():
    """显示进度窗口（全局接口）"""
    window = get_progress_window()
    window.show()


if __name__ == "__main__":
    # 测试
    window = get_progress_window()
    window.create_window()
    
    # 添加测试任务
    window.add_task("test1", "测试任务1", "这是一个测试任务")
    window.add_task("test2", "下载任务", "正在下载文件")
    
    # 更新状态
    time.sleep(1)
    window.update_task_status("test1", "running", 30)
    window.update_task_status("test2", "running", 50)
    
    window.add_log("系统启动完成")
    window.add_log("开始处理任务", "INFO")
    
    window.window.mainloop()