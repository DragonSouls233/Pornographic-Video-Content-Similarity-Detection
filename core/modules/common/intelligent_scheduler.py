"""
智能调度器模块
基于历史数据和系统状态智能安排任务执行时间和优先级
"""

import time
import heapq
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """调度任务数据类"""
    task_id: str
    model_name: str
    priority: TaskPriority
    scheduled_time: datetime
    status: TaskStatus = TaskStatus.PENDING
    estimated_duration: float = 0.0  # 预估执行时间（秒）
    actual_duration: float = 0.0    # 实际执行时间（秒）
    execution_count: int = 0        # 执行次数
    last_execution: Optional[datetime] = None
    failure_count: int = 0          # 失败次数
    callback: Optional[Callable] = None
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """用于优先队列排序"""
        # 优先级高的排前面，相同优先级按时序排列
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.scheduled_time < other.scheduled_time


class PerformanceAnalyzer:
    """性能分析器 - 分析历史执行数据"""
    
    def __init__(self):
        self.execution_history = {}  # {model_name: [execution_records]}
        self.system_metrics = []
    
    def record_execution(self, model_name: str, duration: float, success: bool, 
                        start_time: datetime, end_time: datetime):
        """记录任务执行数据"""
        if model_name not in self.execution_history:
            self.execution_history[model_name] = []
        
        record = {
            'duration': duration,
            'success': success,
            'start_time': start_time,
            'end_time': end_time,
            'hour_of_day': start_time.hour
        }
        
        self.execution_history[model_name].append(record)
        
        # 限制历史记录数量
        if len(self.execution_history[model_name]) > 100:
            self.execution_history[model_name] = self.execution_history[model_name][-50:]
    
    def get_average_duration(self, model_name: str) -> float:
        """获取平均执行时间"""
        if model_name not in self.execution_history:
            return 300.0  # 默认5分钟
        
        records = self.execution_history[model_name]
        successful_records = [r for r in records if r['success']]
        
        if not successful_records:
            return 300.0
        
        return sum(r['duration'] for r in successful_records) / len(successful_records)
    
    def get_best_execution_time(self, model_name: str) -> int:
        """获取最佳执行时间段（小时）"""
        if model_name not in self.execution_history:
            return 2  # 默认凌晨2点
        
        records = self.execution_history[model_name]
        successful_records = [r for r in records if r['success']]
        
        if not successful_records:
            return 2
        
        # 按小时统计成功率和平均耗时
        hourly_stats = {}
        for record in successful_records:
            hour = record['hour_of_day']
            if hour not in hourly_stats:
                hourly_stats[hour] = {'count': 0, 'total_duration': 0}
            
            hourly_stats[hour]['count'] += 1
            hourly_stats[hour]['total_duration'] += record['duration']
        
        # 选择成功率高且耗时短的时段
        best_hour = 2
        best_score = 0
        
        for hour, stats in hourly_stats.items():
            success_rate = stats['count'] / len([r for r in records if r['hour_of_day'] == hour])
            avg_duration = stats['total_duration'] / stats['count']
            # 评分：成功率权重0.7，速度权重0.3
            score = success_rate * 0.7 + (1 - avg_duration / 600) * 0.3
            
            if score > best_score:
                best_score = score
                best_hour = hour
        
        return best_hour
    
    def predict_execution_time(self, model_name: str) -> float:
        """预测执行时间"""
        return self.get_average_duration(model_name)


class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self):
        self.cpu_threshold = 80.0
        self.memory_threshold = 85.0
        self.network_threshold = 1000  # KB/s
    
    def get_system_load(self) -> Dict[str, float]:
        """获取系统负载信息"""
        try:
            import psutil
            
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_io': psutil.disk_io_counters().read_bytes + psutil.disk_io_counters().write_bytes,
                'network_io': psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
            }
        except ImportError:
            # 如果没有psutil，返回默认值
            return {
                'cpu_percent': 50.0,
                'memory_percent': 60.0,
                'disk_io': 0,
                'network_io': 0
            }
    
    def is_system_busy(self) -> bool:
        """判断系统是否繁忙"""
        load = self.get_system_load()
        return (load['cpu_percent'] > self.cpu_threshold or 
                load['memory_percent'] > self.memory_threshold)
    
    def get_available_resources(self) -> float:
        """获取可用资源比例"""
        load = self.get_system_load()
        cpu_available = max(0, 100 - load['cpu_percent']) / 100
        memory_available = max(0, 100 - load['memory_percent']) / 100
        return min(cpu_available, memory_available)


class IntelligentScheduler:
    """智能调度器主类"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.task_queue = []  # 优先队列
        self.running_tasks = {}  # {task_id: task}
        self.completed_tasks = {}  # {task_id: task}
        self.analyzer = PerformanceAnalyzer()
        self.monitor = ResourceMonitor()
        self.scheduler_thread = None
        self.running = False
        self._lock = threading.RLock()
        
        # 调度配置
        self.max_concurrent_tasks = self.config.get('scheduler', {}).get('max_concurrent', 3)
        self.check_interval = self.config.get('scheduler', {}).get('check_interval', 30)
        self.enable_adaptive_scheduling = self.config.get('scheduler', {}).get('adaptive_scheduling', True)
    
    def start_scheduler(self):
        """启动调度器"""
        if self.running:
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info("智能调度器已启动")
    
    def stop_scheduler(self):
        """停止调度器"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("智能调度器已停止")
    
    def schedule_task(self, model_name: str, priority: TaskPriority = TaskPriority.NORMAL,
                     delay_minutes: int = 0, callback: Callable = None, **kwargs) -> str:
        """
        调度任务
        
        Args:
            model_name: 模特名称
            priority: 任务优先级
            delay_minutes: 延迟执行分钟数
            callback: 完成回调函数
            **kwargs: 附加数据
            
        Returns:
            任务ID
        """
        with self._lock:
            task_id = f"{model_name}_{int(time.time())}"
            
            # 计算调度时间
            scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)
            
            # 智能调整调度时间（如果启用自适应调度）
            if self.enable_adaptive_scheduling and delay_minutes == 0:
                best_hour = self.analyzer.get_best_execution_time(model_name)
                now = datetime.now()
                
                # 如果当前不是最佳时间，调度到下一个最佳时间
                if now.hour != best_hour:
                    if now.hour < best_hour:
                        scheduled_time = now.replace(hour=best_hour, minute=0, second=0, microsecond=0)
                    else:
                        # 调度到明天的最佳时间
                        scheduled_time = (now + timedelta(days=1)).replace(
                            hour=best_hour, minute=0, second=0, microsecond=0
                        )
            
            # 预估执行时间
            estimated_duration = self.analyzer.predict_execution_time(model_name)
            
            task = ScheduledTask(
                task_id=task_id,
                model_name=model_name,
                priority=priority,
                scheduled_time=scheduled_time,
                estimated_duration=estimated_duration,
                callback=callback,
                data=kwargs
            )
            
            heapq.heappush(self.task_queue, task)
            logger.info(f"任务已调度: {model_name} (ID: {task_id}), "
                       f"优先级: {priority.name}, 预计执行时间: {scheduled_time}")
            
            return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            # 从运行任务中取消
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                task.status = TaskStatus.CANCELLED
                del self.running_tasks[task_id]
                logger.info(f"任务已取消: {task_id}")
                return True
            
            # 从队列中移除
            for i, task in enumerate(self.task_queue):
                if task.task_id == task_id:
                    task.status = TaskStatus.CANCELLED
                    self.task_queue.pop(i)
                    heapq.heapify(self.task_queue)
                    logger.info(f"任务已取消: {task_id}")
                    return True
            
            return False
    
    def get_pending_tasks(self) -> List[ScheduledTask]:
        """获取待处理任务列表"""
        with self._lock:
            return [task for task in self.task_queue if task.status == TaskStatus.PENDING]
    
    def get_running_tasks(self) -> List[ScheduledTask]:
        """获取运行中任务列表"""
        with self._lock:
            return list(self.running_tasks.values())
    
    def get_task_stats(self) -> Dict[str, int]:
        """获取任务统计信息"""
        with self._lock:
            return {
                'pending': len(self.get_pending_tasks()),
                'running': len(self.running_tasks),
                'completed': len(self.completed_tasks),
                'failed': len([t for t in self.completed_tasks.values() if t.status == TaskStatus.FAILED])
            }
    
    def _scheduler_loop(self):
        """调度器主循环"""
        while self.running:
            try:
                self._process_tasks()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"调度器循环异常: {e}")
                time.sleep(5)
    
    def _process_tasks(self):
        """处理任务"""
        with self._lock:
            # 检查是否有可执行的任务
            ready_tasks = []
            remaining_tasks = []
            
            while self.task_queue:
                task = heapq.heappop(self.task_queue)
                
                if task.status == TaskStatus.CANCELLED:
                    continue
                
                if task.scheduled_time <= datetime.now():
                    ready_tasks.append(task)
                else:
                    remaining_tasks.append(task)
            
            # 将未到期的任务放回队列
            for task in remaining_tasks:
                heapq.heappush(self.task_queue, task)
            
            # 执行准备好的任务（考虑并发限制）
            available_slots = self.max_concurrent_tasks - len(self.running_tasks)
            tasks_to_execute = ready_tasks[:available_slots]
            
            for task in tasks_to_execute:
                self._execute_task(task)
    
    def _execute_task(self, task: ScheduledTask):
        """执行单个任务"""
        task.status = TaskStatus.RUNNING
        task.execution_count += 1
        start_time = datetime.now()
        
        self.running_tasks[task.task_id] = task
        logger.info(f"开始执行任务: {task.model_name} (ID: {task.task_id})")
        
        try:
            # 这里应该调用实际的任务执行函数
            # 为了演示，我们模拟执行过程
            time.sleep(2)  # 模拟任务执行
            
            # 模拟执行结果
            success = True
            result = {"status": "completed", "message": "任务执行成功"}
            
        except Exception as e:
            success = False
            result = {"status": "failed", "error": str(e)}
            task.failure_count += 1
            logger.error(f"任务执行失败: {task.model_name} - {e}")
        
        # 记录执行结果
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        task.actual_duration = duration
        task.last_execution = end_time
        task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        
        # 更新性能分析器
        self.analyzer.record_execution(
            task.model_name, duration, success, start_time, end_time
        )
        
        # 移动到完成列表
        del self.running_tasks[task.task_id]
        self.completed_tasks[task.task_id] = task
        
        # 执行回调
        if task.callback:
            try:
                task.callback(task, result)
            except Exception as e:
                logger.error(f"任务回调执行失败: {e}")
        
        logger.info(f"任务执行完成: {task.model_name} (ID: {task.task_id}), "
                   f"耗时: {duration:.2f}秒, 状态: {task.status.value}")


# 便捷函数
def create_scheduler(config: dict = None) -> IntelligentScheduler:
    """创建智能调度器实例"""
    return IntelligentScheduler(config)


# 示例使用
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s'
    )
    
    print("=" * 60)
    print("智能调度器测试")
    print("=" * 60)
    
    # 创建调度器
    scheduler = IntelligentScheduler({
        'scheduler': {
            'max_concurrent': 2,
            'check_interval': 5,
            'adaptive_scheduling': True
        }
    })
    
    # 启动调度器
    scheduler.start_scheduler()
    
    # 定义回调函数
    def task_callback(task, result):
        print(f"📋 任务回调: {task.model_name} - {result}")
    
    # 调度几个测试任务
    scheduler.schedule_task("TestModel1", TaskPriority.HIGH, callback=task_callback)
    scheduler.schedule_task("TestModel2", TaskPriority.NORMAL, delay_minutes=1, callback=task_callback)
    scheduler.schedule_task("TestModel3", TaskPriority.LOW, callback=task_callback)
    
    # 显示任务状态
    time.sleep(3)
    stats = scheduler.get_task_stats()
    print(f"\n📊 任务统计: {stats}")
    
    pending = scheduler.get_pending_tasks()
    print(f"⏳ 待处理任务: {len(pending)}")
    for task in pending:
        print(f"  - {task.model_name} (优先级: {task.priority.name})")
    
    # 等待一段时间让任务执行
    time.sleep(10)
    
    # 停止调度器
    scheduler.stop_scheduler()
    print("\n✅ 测试完成")