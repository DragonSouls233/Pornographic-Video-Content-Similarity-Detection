# 完整目录下载功能

## 功能概述

完整目录下载功能允许您批量下载模特的所有视频，而不仅仅是缺失的视频。这个功能基于 yt-dlp 实现，支持最高分辨率下载、代理配置和会员内容。

## 主要特性

### 1. 单个模特完整下载
- 下载指定模特的所有视频
- 支持最大下载数量限制
- 自动跳过已存在的文件
- 实时进度显示

### 2. 批量模特下载
- 同时下载多个模特的完整目录
- 支持每个模特的下载限制
- 汇总下载统计信息
- 详细的下载报告

### 3. 高级功能
- **智能重复检测**: 自动跳过已存在的文件
- **代理支持**: 完整支持 HTTP/SOCKS 代理
- **会员内容**: 支持 Cookie 配置下载会员专享内容
- **分辨率选择**: 自动选择最高可用分辨率
- **错误恢复**: 下载失败时继续处理其他视频
- **进度监控**: 实时显示下载进度和状态

## GUI 操作界面

### 结果页面下载按钮

1. **下载选中视频**: 下载在结果列表中选中的缺失视频
2. **下载所有缺失视频**: 下载所有查重发现的缺失视频
3. **完整下载模特目录**: 批量下载选定模特的完整视频目录

### 模特管理页面下载按钮

1. **下载选中模特完整目录**: 下载在模特列表中选中的模特
2. **批量下载所有模特**: 批量下载所有已配置的模特

## 使用方法

### 方法 1: GUI 界面操作

1. 运行查重分析获取模特数据
2. 在"结果显示"标签页中点击"完整下载模特目录"
3. 在弹出的对话框中选择要下载的模特
4. 设置每个模特的最大下载数量（可选，0=无限制）
5. 确认开始下载

### 方法 2: 模特管理页面操作

1. 在"模特管理"标签页中选择模特
2. 点击"下载选中模特完整目录"或"批量下载所有模特"
3. 设置下载参数
4. 确认开始下载

### 方法 3: 命令行/脚本调用

```python
from core.modules.pronhub.downloader import (
    download_model_complete_directory,
    batch_download_models
)

# 单个模特完整下载
result = download_model_complete_directory(
    model_url="https://www.pornhub.com/model/your-model",
    model_name="模特名称",
    max_videos=50,  # 可选：限制下载数量
    progress_callback=lambda msg: print(f"进度: {msg}")
)

# 批量下载
models_info = [
    ("模特1", "https://www.pornhub.com/model/model1", "自定义保存目录"),
    ("模特2", "https://www.pornhub.com/model/model2", None),
]

result = batch_download_models(
    models_info=models_info,
    max_videos_per_model=100,
    progress_callback=lambda msg: print(f"进度: {msg}")
)
```

## 配置要求

### 1. 安装依赖

```bash
pip install yt-dlp
```

### 2. 代理配置（如需要）

在 `config.yaml` 中配置代理：

```yaml
network:
  proxy:
    enabled: true
    type: "socks5"  # 或 "http"
    host: "127.0.0.1"
    port: "10808"
    id: ""  # 可选
    password: ""  # 可选
```

### 3. 会员内容配置（如需要）

在 `config.yaml` 中配置 Cookie：

```yaml
pronhub:
  cookies_file: "path/to/cookies.txt"
```

## 下载选项配置

在 `config.yaml` 中可以配置下载选项：

```yaml
pronhub:
  download_options:
    max_resolution: 0      # 0=不限制，其他值为像素高度
    preferred_format: "mp4"  # 首选视频格式
    download_thumbnail: true   # 是否下载缩略图
    max_retries: 3        # 重试次数
    timeout: 300           # 超时时间（秒）
```

## 输出结构

下载的文件会按以下结构组织：

```
output/
└── [Channel] 模特名称/
    ├── 视频1_标题1.mp4
    ├── 视频2_标题2.mp4
    └── ...
```

## 结果数据

### 单个模特下载结果

```python
{
    'success': bool,              # 整体是否成功
    'model_name': str,          # 模特名称
    'model_url': str,           # 模特URL
    'save_dir': str,           # 保存目录
    'total_videos': int,         # 总视频数
    'successful_downloads': int, # 成功下载数
    'failed_downloads': int,    # 下载失败数
    'skipped_downloads': int,   # 跳过已存在数
    'total_size': int,         # 总文件大小（字节）
    'download_details': [       # 详细下载信息
        {
            'title': str,
            'url': str,
            'status': str,        # success/failed/skipped
            'file_path': str,     # 成功时的文件路径
            'file_size': int,     # 成功时的文件大小
            'error': str          # 失败时的错误信息
        }
    ],
    'errors': [str],           # 错误列表
    'start_time': str,         # 开始时间
    'end_time': str           # 结束时间
}
```

### 批量下载结果

```python
{
    'success': bool,              # 整体是否成功
    'total_models': int,         # 总模特数
    'successful_models': int,    # 成功模特数
    'failed_models': int,        # 失败模特数
    'total_videos': int,         # 总视频数
    'total_downloaded': int,     # 总下载数
    'total_size': int,           # 总文件大小（字节）
    'model_results': [...],       # 每个模特的下载结果
    'start_time': str,          # 开始时间
    'end_time': str            # 结束时间
}
```

## 注意事项

1. **存储空间**: 完整目录下载可能需要大量存储空间，请确保有足够的磁盘空间
2. **网络稳定**: 下载大量视频需要稳定的网络连接
3. **时间消耗**: 根据视频数量和网络状况，下载可能需要很长时间
4. **合规使用**: 请确保下载行为符合相关法律法规和网站使用条款
5. **会员限制**: 某些视频可能需要会员权限，请正确配置 Cookie
6. **地区限制**: 某些内容可能有地区限制，必要时使用代理

## 常见问题

### Q: 下载速度很慢怎么办？
A: 
- 检查网络连接稳定性
- 尝试使用代理
- 调整并发下载数量（在 yt-dlp 配置中）
- 考虑在网络空闲时段下载

### Q: 下载失败如何处理？
A: 
- 检查视频 URL 是否有效
- 确认代理配置是否正确
- 验证 Cookie 配置（针对会员内容）
- 查看详细错误信息进行针对性解决

### Q: 如何避免重复下载？
A: 
- 系统会自动检测已存在的文件并跳过
- 下载中断后重新运行会自动继续未完成的下载

### Q: 会员内容无法下载？
A: 
- 确保配置了正确的 Cookie 文件
- 检查 Cookie 是否仍然有效
- 验证会员权限状态

## 演示脚本

运行 `demo_complete_download.py` 可以查看功能演示：

```bash
python demo_complete_download.py
```

该脚本提供了：
- 单个模特完整下载演示
- 批量下载演示
- 视频信息获取演示

请将演示中的 URL 替换为实际的模特 URL 进行测试。