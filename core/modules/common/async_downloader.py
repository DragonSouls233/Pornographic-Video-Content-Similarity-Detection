"""
异步下载引擎模块
基于asyncio和aiohttp实现高性能并发下载
"""

import asyncio
import aiohttp
import aiofiles
import os
import re
import logging
import time
from typing import Dict, List, Optional, Tuple, Callable, Any
from pathlib import Path
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    """下载状态枚举"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadTask:
    """下载任务数据类"""
    task_id: str
    url: str
    filename: str
    save_path: Path
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed: float = 0.0  # bytes/sec
    eta: float = 0.0    # seconds
    start_time: float = 0.0
    end_time: float = 0.0
    error_message: str = ""
    retries: int = 0
    max_retries: int = 3
    headers: Dict[str, str] = field(default_factory=dict)
    callback: Optional[Callable] = None


class AsyncDownloadEngine:
    """异步下载引擎"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.tasks: Dict[str, DownloadTask] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        self.semaphore = None
        
        # 下载配置
        self.max_concurrent = self.config.get('download', {}).get('max_workers', 4)
        self.timeout = self.config.get('download', {}).get('timeout', 300)
        self.chunk_size = self.config.get('download', {}).get('chunk_size', 8192)
        self.retry_delay = self.config.get('download', {}).get('retry_delay', 5)
        
        # 代理配置
        self.proxy_config = self.config.get('network', {}).get('proxy', {})
        self.proxy = None
        if self.proxy_config.get('enabled', False):
            self.proxy = self.proxy_config.get('http', 'socks5://127.0.0.1:10808')
    
    async def __aenter__(self):
        """异步上下文管理器进入"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.stop()
    
    async def start(self):
        """启动下载引擎"""
        if self.running:
            return
        
        # 创建信号量控制并发数
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # 创建HTTP会话
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent * 2,
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
        )
        
        self.running = True
        logger.info(f"异步下载引擎已启动，最大并发数: {self.max_concurrent}")
    
    async def stop(self):
        """停止下载引擎"""
        if not self.running:
            return
        
        self.running = False
        
        if self.session:
            await self.session.close()
            self.session = None
        
        logger.info("异步下载引擎已停止")
    
    def add_task(self, url: str, filename: str, save_path: str, 
                 headers: Dict[str, str] = None, callback: Callable = None) -> str:
        """
        添加下载任务
        
        Args:
            url: 下载URL
            filename: 文件名
            save_path: 保存路径
            headers: 请求头
            callback: 完成回调函数
            
        Returns:
            任务ID
        """
        task_id = f"task_{int(time.time() * 1000000)}"
        
        task = DownloadTask(
            task_id=task_id,
            url=url,
            filename=filename,
            save_path=Path(save_path),
            headers=headers or {},
            callback=callback
        )
        
        self.tasks[task_id] = task
        logger.info(f"添加下载任务: {filename} (ID: {task_id})")
        return task_id
    
    async def download_single(self, task_id: str) -> Dict[str, Any]:
        """
        下载单个任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            下载结果字典
        """
        if task_id not in self.tasks:
            return {"success": False, "error": "任务不存在"}
        
        task = self.tasks[task_id]
        task.status = DownloadStatus.DOWNLOADING
        task.start_time = time.time()
        
        try:
            async with self.semaphore:
                result = await self._download_task(task)
                return result
                
        except asyncio.CancelledError:
            task.status = DownloadStatus.CANCELLED
            task.error_message = "任务被取消"
            logger.info(f"任务被取消: {task_id}")
            return {"success": False, "error": "任务被取消"}
        except Exception as e:
            task.status = DownloadStatus.FAILED
            task.error_message = str(e)
            logger.error(f"下载任务失败: {task_id} - {e}")
            return {"success": False, "error": str(e)}
    
    async def _download_task(self, task: DownloadTask) -> Dict[str, Any]:
        """执行单个下载任务"""
        # 确保保存目录存在
        task.save_path.parent.mkdir(parents=True, exist_ok=True)
        file_path = task.save_path / task.filename
        
        # 检查文件是否已存在
        if file_path.exists():
            task.status = DownloadStatus.COMPLETED
            task.progress = 100.0
            task.downloaded_bytes = file_path.stat().st_size
            task.total_bytes = task.downloaded_bytes
            
            result = {
                "success": True,
                "task_id": task.task_id,
                "file_path": str(file_path),
                "file_size": task.downloaded_bytes,
                "message": "文件已存在"
            }
            
            if task.callback:
                task.callback(task, result)
            
            return result
        
        # 执行下载
        for attempt in range(task.max_retries + 1):
            try:
                return await self._perform_download(task, file_path)
            except Exception as e:
                task.retries += 1
                if attempt < task.max_retries:
                    logger.warning(f"下载失败，第{attempt + 1}次重试: {task.filename} - {e}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # 指数退避
                else:
                    raise
        
        # 如果所有重试都失败
        raise Exception(f"下载失败，已重试{task.max_retries}次")
    
    async def _perform_download(self, task: DownloadTask, file_path: Path) -> Dict[str, Any]:
        """执行实际的下载操作"""
        # 确保父目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
        
        try:
            # 发送HEAD请求获取文件大小
            async with self.session.head(task.url, proxy=self.proxy, headers=task.headers) as response:
                if response.status == 200:
                    task.total_bytes = int(response.headers.get('content-length', 0))
            
            # 开始下载
            async with self.session.get(task.url, proxy=self.proxy, headers=task.headers) as response:
                response.raise_for_status()
                
                # 获取实际的文件大小
                if task.total_bytes == 0:
                    task.total_bytes = int(response.headers.get('content-length', 0))
                
                downloaded = 0
                last_update = time.time()
                last_bytes = 0
                
                async with aiofiles.open(temp_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(self.chunk_size):
                        if not self.running:
                            raise asyncio.CancelledError("下载引擎已停止")
                        
                        await f.write(chunk)
                        downloaded += len(chunk)
                        task.downloaded_bytes = downloaded
                        
                        # 更新进度和速度
                        current_time = time.time()
                        if current_time - last_update >= 1.0:  # 每秒更新一次
                            time_diff = current_time - last_update
                            bytes_diff = downloaded - last_bytes
                            
                            task.speed = bytes_diff / time_diff
                            task.progress = (downloaded / task.total_bytes * 100) if task.total_bytes > 0 else 0
                            
                            # 计算ETA
                            if task.speed > 0 and task.total_bytes > 0:
                                remaining_bytes = task.total_bytes - downloaded
                                task.eta = remaining_bytes / task.speed
                            else:
                                task.eta = 0
                            
                            last_update = current_time
                            last_bytes = downloaded
                
                # 下载完成
                task.progress = 100.0
                task.speed = 0.0
                task.eta = 0.0
                task.end_time = time.time()
                task.status = DownloadStatus.COMPLETED
                
                # 重命名临时文件
                temp_path.rename(file_path)
                
                result = {
                    "success": True,
                    "task_id": task.task_id,
                    "file_path": str(file_path),
                    "file_size": task.downloaded_bytes,
                    "download_time": task.end_time - task.start_time,
                    "average_speed": task.downloaded_bytes / (task.end_time - task.start_time)
                }
                
                logger.info(f"下载完成: {task.filename} ({task.downloaded_bytes / (1024*1024):.2f}MB)")
                
                if task.callback:
                    task.callback(task, result)
                
                return result
                
        except Exception as e:
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
            raise
        finally:
            # 清理临时文件（如果下载失败）
            if temp_path.exists() and task.status != DownloadStatus.COMPLETED:
                temp_path.unlink()
    
    async def download_batch(self, task_ids: List[str]) -> List[Dict[str, Any]]:
        """
        批量下载任务
        
        Args:
            task_ids: 任务ID列表
            
        Returns:
            下载结果列表
        """
        if not task_ids:
            return []
        
        # 创建下载任务
        tasks = [self.download_single(task_id) for task_id in task_ids]
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "task_id": task_ids[i]
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_task_status(self, task_id: str) -> Optional[DownloadTask]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[DownloadTask]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == DownloadStatus.DOWNLOADING:
                task.status = DownloadStatus.CANCELLED
                logger.info(f"任务已标记为取消: {task_id}")
                return True
        return False
    
    def get_statistics(self) -> Dict[str, int]:
        """获取下载统计信息"""
        stats = {
            'total': len(self.tasks),
            'pending': 0,
            'downloading': 0,
            'completed': 0,
            'failed': 0,
            'cancelled': 0
        }
        
        for task in self.tasks.values():
            status_key = task.status.value
            if status_key in stats:
                stats[status_key] += 1
        
        return stats


class AsyncDownloaderAdapter:
    """异步下载器适配器，兼容原有下载器接口"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.engine = AsyncDownloadEngine(config)
    
    async def __aenter__(self):
        await self.engine.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.engine.stop()
    
    async def download_single_video(self, url: str, save_dir: str = None) -> Dict[str, Any]:
        """
        下载单个视频（兼容接口）
        
        Args:
            url: 视频URL
            save_dir: 保存目录
            
        Returns:
            下载结果
        """
        # 提取文件名（这里需要实现URL到文件名的转换逻辑）
        filename = self._extract_filename_from_url(url)
        
        if not save_dir:
            save_dir = self.config.get('download', {}).get('output_dir', 'downloads')
        
        # 添加任务
        task_id = self.engine.add_task(
            url=url,
            filename=filename,
            save_path=save_dir
        )
        
        # 执行下载
        result = await self.engine.download_single(task_id)
        
        # 转换结果格式以兼容原有接口
        if result['success']:
            return {
                'success': True,
                'url': url,
                'title': filename,
                'save_path': save_dir,
                'filename': filename,
                'file_path': result['file_path'],
                'file_size': result['file_size'],
                'error': None
            }
        else:
            return {
                'success': False,
                'url': url,
                'error': result['error'],
                'message': result['error']
            }
    
    async def download_multiple_videos(self, urls: List[str], save_dir: str = None) -> List[Dict[str, Any]]:
        """
        批量下载视频（兼容接口）
        
        Args:
            urls: 视频URL列表
            save_dir: 保存目录
            
        Returns:
            下载结果列表
        """
        tasks = []
        for url in urls:
            task = self.download_single_video(url, save_dir)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append({
                    'success': False,
                    'error': str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def _extract_filename_from_url(self, url: str) -> str:
        """从URL提取文件名"""
        # 简单的文件名提取逻辑，实际应用中需要更复杂的处理
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename or '.' not in filename:
            filename = f"video_{int(time.time())}.mp4"
        return filename


# 便捷函数
async def create_async_downloader(config: dict = None) -> AsyncDownloadEngine:
    """创建异步下载器实例"""
    engine = AsyncDownloadEngine(config)
    await engine.start()
    return engine


async def download_videos_async(urls: List[str], save_dir: str = None, 
                              config: dict = None) -> List[Dict[str, Any]]:
    """
    异步下载视频的便捷函数
    
    Args:
        urls: 视频URL列表
        save_dir: 保存目录
        config: 配置字典
        
    Returns:
        下载结果列表
    """
    async with AsyncDownloaderAdapter(config) as downloader:
        return await downloader.download_multiple_videos(urls, save_dir)


# 示例使用
if __name__ == "__main__":
    import asyncio
    
    async def demo():
        # 配置日志
        logging.basicConfig(level=logging.INFO)
        
        print("=" * 60)
        print("异步下载引擎演示")
        print("=" * 60)
        
        # 创建下载引擎
        config = {
            'download': {
                'max_workers': 3,
                'timeout': 300,
                'chunk_size': 8192
            }
        }
        
        async with AsyncDownloadEngine(config) as engine:
            # 添加测试任务
            test_urls = [
                "https://httpbin.org/bytes/1024",  # 1KB测试文件
                "https://httpbin.org/bytes/2048",  # 2KB测试文件
                "https://httpbin.org/bytes/4096",  # 4KB测试文件
            ]
            
            task_ids = []
            for i, url in enumerate(test_urls):
                task_id = engine.add_task(
                    url=url,
                    filename=f"test_file_{i}.dat",
                    save_path="downloads"
                )
                task_ids.append(task_id)
            
            print(f"已添加 {len(task_ids)} 个下载任务")
            
            # 批量下载
            print("开始批量下载...")
            results = await engine.download_batch(task_ids)
            
            # 显示结果
            print("\n下载结果:")
            for result in results:
                if result['success']:
                    print(f"✅ {result['task_id']}: {result['file_path']} ({result['file_size']} bytes)")
                else:
                    print(f"❌ {result['task_id']}: {result['error']}")
            
            # 显示统计
            stats = engine.get_statistics()
            print(f"\n统计信息: {stats}")
        
        print("\n演示完成!")
    
    # 运行演示
    asyncio.run(demo())