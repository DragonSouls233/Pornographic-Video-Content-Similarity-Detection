"""
性能优化模块
提供高性能的批量数据处理能力
"""

import time
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import Dict, List, Any, Callable, Optional, Tuple
import logging
import gc
import psutil
import os
from dataclasses import dataclass
import json

@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_items: int
    processed_items: int
    success_count: int
    error_count: int
    start_time: float
    end_time: Optional[float] = None
    items_per_second: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    def calculate_metrics(self):
        """计算性能指标"""
        if self.end_time is None:
            self.end_time = time.time()
        
        elapsed_time = self.end_time - self.start_time
        if elapsed_time > 0:
            self.items_per_second = self.processed_items / elapsed_time
        
        # 获取系统资源使用情况
        process = psutil.Process(os.getpid())
        self.memory_usage_mb = process.memory_info().rss / 1024 / 1024
        self.cpu_usage_percent = process.cpu_percent()

class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self, logger=None, max_workers: Optional[int] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.chunk_size = 100  # 默认块大小
        self.memory_limit_mb = 1024  # 内存限制（MB）
        
    def optimize_chunk_size(self, total_items: int, item_size_estimate: int = 1024) -> int:
        """
        根据系统资源优化块大小
        
        Args:
            total_items: 总项目数
            item_size_estimate: 每个项目估计大小（字节）
            
        Returns:
            优化后的块大小
        """
        # 获取可用内存
        available_memory_mb = psutil.virtual_memory().available / 1024 / 1024
        
        # 计算理论最大块大小（基于内存限制）
        max_chunk_by_memory = int((self.memory_limit_mb * 1024 * 1024) / item_size_estimate)
        
        # 计算理论最小块大小（基于CPU核心数）
        min_chunk = max(10, total_items // (self.max_workers * 4))
        
        # 计算理论最大块大小（保证足够的任务数）
        max_chunk_by_cpu = total_items // self.max_workers if total_items > self.max_workers else total_items
        
        # 选择合适的块大小
        chunk_size = min(
            max_chunk_by_memory,
            max_chunk_by_cpu,
            max(100, min_chunk)
        )
        
        self.logger.debug(f"优化块大小: {chunk_size} (总项目: {total_items}, 可用内存: {available_memory_mb:.1f}MB)")
        
        return chunk_size
    
    def batch_process_with_threading(self, 
                                   items: List[Any], 
                                   process_func: Callable,
                                   chunk_size: Optional[int] = None,
                                   use_memory_optimization: bool = True) -> Tuple[List[Any], PerformanceMetrics]:
        """
        使用线程池批量处理数据
        
        Args:
            items: 要处理的项目列表
            process_func: 处理函数
            chunk_size: 块大小
            use_memory_optimization: 是否使用内存优化
            
        Returns:
            (处理结果列表, 性能指标)
        """
        if not items:
            return [], PerformanceMetrics(0, 0, 0, 0, time.time())
        
        # 优化块大小
        if chunk_size is None:
            chunk_size = self.optimize_chunk_size(len(items))
        
        # 分块处理
        chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
        
        # 性能指标
        metrics = PerformanceMetrics(
            total_items=len(items),
            processed_items=0,
            success_count=0,
            error_count=0,
            start_time=time.time()
        )
        
        results = []
        
        def process_chunk_with_metrics(chunk):
            """处理单个块并收集指标"""
            chunk_results = []
            chunk_success = 0
            chunk_error = 0
            
            for item in chunk:
                try:
                    result = process_func(item)
                    chunk_results.append(result)
                    chunk_success += 1
                except Exception as e:
                    self.logger.error(f"处理项目失败: {e}")
                    chunk_error += 1
            
            return chunk_results, chunk_success, chunk_error
        
        try:
            # 使用线程池处理
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_chunk = {
                    executor.submit(process_chunk_with_metrics, chunk): chunk 
                    for chunk in chunks
                }
                
                # 收集结果
                for future in as_completed(future_to_chunk):
                    try:
                        chunk_results, chunk_success, chunk_error = future.result()
                        results.extend(chunk_results)
                        metrics.success_count += chunk_success
                        metrics.error_count += chunk_error
                        
                    except Exception as e:
                        self.logger.error(f"处理块失败: {e}")
                        metrics.error_count += len(future_to_chunk[future])
                    
                    # 更新处理计数
                    metrics.processed_items = metrics.success_count + metrics.error_count
                    
                    # 内存优化
                    if use_memory_optimization and metrics.processed_items % 1000 == 0:
                        gc.collect()
                        
                    # 实时性能监控
                    if metrics.processed_items % 500 == 0:
                        metrics.calculate_metrics()
                        self.logger.debug(
                            f"处理进度: {metrics.processed_items}/{metrics.total_items} "
                            f"({metrics.processed_items/metrics.total_items*100:.1f}%), "
                            f"速度: {metrics.items_per_second:.1f} 项/秒"
                        )
        
        except Exception as e:
            self.logger.error(f"批量处理失败: {e}")
            raise
        
        # 计算最终指标
        metrics.calculate_metrics()
        
        self.logger.info(
            f"批量处理完成: 总计 {metrics.total_items} 项, "
            f"成功 {metrics.success_count} 项, 失败 {metrics.error_count} 项, "
            f"耗时 {metrics.end_time - metrics.start_time:.2f} 秒, "
            f"速度 {metrics.items_per_second:.1f} 项/秒"
        )
        
        return results, metrics
    
    def batch_process_with_progress_callback(self,
                                            items: List[Any],
                                            process_func: Callable,
                                            progress_callback: Optional[Callable[[int, int], None]] = None,
                                            **kwargs) -> Tuple[List[Any], PerformanceMetrics]:
        """
        带进度回调的批量处理
        
        Args:
            items: 要处理的项目列表
            process_func: 处理函数
            progress_callback: 进度回调函数 (processed, total)
            **kwargs: 其他参数
            
        Returns:
            (处理结果列表, 性能指标)
        """
        # 创建包装函数以支持进度回调
        def process_with_progress(item):
            result = process_func(item)
            # 调用进度回调（需要在主线程中安全调用）
            if progress_callback:
                try:
                    # 这里可能需要线程安全的回调机制
                    pass
                except Exception:
                    pass
            return result
        
        return self.batch_process_with_threading(items, process_with_progress, **kwargs)
    
    def monitor_system_resources(self) -> Dict[str, float]:
        """监控系统资源"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_available_gb': psutil.virtual_memory().available / 1024 / 1024 / 1024,
            'disk_usage_percent': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:\\').percent
        }
    
    def adapt_workers_based_on_resources(self) -> int:
        """根据系统资源自适应调整工作线程数"""
        resources = self.monitor_system_resources()
        
        # 根据CPU使用率调整
        if resources['cpu_percent'] > 80:
            adaptive_workers = max(2, self.max_workers // 2)
        elif resources['cpu_percent'] > 60:
            adaptive_workers = max(4, self.max_workers * 3 // 4)
        else:
            adaptive_workers = self.max_workers
        
        # 根据内存使用率进一步调整
        if resources['memory_percent'] > 80:
            adaptive_workers = max(2, adaptive_workers // 2)
        
        self.logger.debug(f"自适应工作线程数: {adaptive_workers} (CPU: {resources['cpu_percent']:.1f}%, 内存: {resources['memory_percent']:.1f}%)")
        
        return adaptive_workers

class HighPerformanceBatchProcessor:
    """高性能批量处理器"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.optimizer = PerformanceOptimizer(logger)
        self.queue = queue.Queue()
        self.results_queue = queue.Queue()
        self.stop_event = threading.Event()
        
    def process_large_dataset(self,
                             file_path: str,
                             process_func: Callable,
                             file_type: str = 'excel',
                             progress_callback: Optional[Callable[[int, int], None]] = None) -> Tuple[List[Any], PerformanceMetrics]:
        """
        处理大型数据集
        
        Args:
            file_path: 文件路径
            process_func: 处理函数
            file_type: 文件类型 ('excel', 'csv', 'json')
            progress_callback: 进度回调
            
        Returns:
            (处理结果, 性能指标)
        """
        try:
            # 根据文件类型读取数据
            if file_type == 'excel':
                items = self._read_excel_large(file_path)
            elif file_type == 'csv':
                items = self._read_csv_large(file_path)
            elif file_type == 'json':
                items = self._read_json_large(file_path)
            else:
                raise ValueError(f"不支持的文件类型: {file_type}")
            
            # 使用优化的批量处理
            return self.optimizer.batch_process_with_threading(
                items, process_func, use_memory_optimization=True
            )
            
        except Exception as e:
            self.logger.error(f"处理大型数据集失败: {e}")
            raise
    
    def _read_excel_large(self, file_path: str) -> List[Dict]:
        """分块读取大型Excel文件"""
        import pandas as pd
        
        items = []
        chunk_size = self.optimizer.chunk_size
        
        try:
            for chunk_df in pd.read_excel(file_path, chunksize=chunk_size):
                # 转换为字典列表
                chunk_items = chunk_df.to_dict('records')
                items.extend(chunk_items)
                
                # 内存管理
                if len(items) % (chunk_size * 5) == 0:
                    gc.collect()
                    
        except Exception as e:
            self.logger.error(f"读取Excel文件失败: {e}")
            raise
        
        return items
    
    def _read_csv_large(self, file_path: str) -> List[Dict]:
        """分块读取大型CSV文件"""
        import pandas as pd
        
        items = []
        chunk_size = self.optimizer.chunk_size
        
        try:
            for chunk_df in pd.read_csv(file_path, chunksize=chunk_size):
                # 转换为字典列表
                chunk_items = chunk_df.to_dict('records')
                items.extend(chunk_items)
                
                # 内存管理
                if len(items) % (chunk_size * 5) == 0:
                    gc.collect()
                    
        except Exception as e:
            self.logger.error(f"读取CSV文件失败: {e}")
            raise
        
        return items
    
    def _read_json_large(self, file_path: str) -> List[Dict]:
        """流式读取大型JSON文件"""
        items = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # 尝试逐行读取（每行一个JSON对象）
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        try:
                            item = json.loads(line)
                            items.append(item)
                            
                            # 定期清理内存
                            if line_num % 1000 == 0:
                                gc.collect()
                                
                        except json.JSONDecodeError as e:
                            self.logger.warning(f"第{line_num}行JSON解析失败: {e}")
                            continue
        
        except Exception as e:
            self.logger.error(f"读取JSON文件失败: {e}")
            raise
        
        return items

class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self, memory_limit_mb: int = 1024):
        self.memory_limit_mb = memory_limit_mb
        self.logger = logging.getLogger(__name__)
        
    def check_memory_usage(self) -> Tuple[float, bool]:
        """
        检查内存使用情况
        
        Returns:
            (当前使用量MB, 是否超过限制)
        """
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        is_over_limit = memory_mb > self.memory_limit_mb
        
        if is_over_limit:
            self.logger.warning(f"内存使用超过限制: {memory_mb:.1f}MB > {self.memory_limit_mb}MB")
        
        return memory_mb, is_over_limit
    
    def force_garbage_collection(self):
        """强制垃圾回收"""
        collected = gc.collect()
        self.logger.debug(f"垃圾回收释放了 {collected} 个对象")
        
        new_memory_mb, _ = self.check_memory_usage()
        return new_memory_mb

def create_performance_aware_processor(logger=None) -> HighPerformanceBatchProcessor:
    """
    创建性能感知的处理器
    
    Args:
        logger: 日志记录器
        
    Returns:
        高性能批量处理器实例
    """
    return HighPerformanceBatchProcessor(logger)

# 性能优化装饰器
def performance_monitor(func):
    """性能监控装饰器"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            result = func(*args, **kwargs)
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            logger = logging.getLogger(func.__module__)
            logger.info(
                f"函数 {func.__name__} 执行完成: "
                f"耗时 {end_time - start_time:.3f}s, "
                f"内存变化 {end_memory - start_memory:+.1f}MB"
            )
            
            return result
            
        except Exception as e:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            logger = logging.getLogger(func.__module__)
            logger.error(
                f"函数 {func.__name__} 执行失败: "
                f"耗时 {end_time - start_time:.3f}s, "
                f"内存变化 {end_memory - start_memory:+.1f}MB, "
                f"错误: {e}"
            )
            
            raise
    
    return wrapper