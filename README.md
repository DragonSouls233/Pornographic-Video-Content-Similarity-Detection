# 模特查重管理系统  
  
## ?? 文档位置  
  
所有项目文档已移动到 [docs/](docs/) 目录  
  
## ?? 快速开始  
1. 阅读 [docs/README.md](docs/README.md) 了解文档结构  
2. 查看 [docs/QUICKSTART.md](docs/QUICKSTART.md) 快速上手  
3. 查看 [docs/COMPLETE_DOWNLOAD.md](docs/COMPLETE_DOWNLOAD.md) 了解完整目录下载功能  

## ? 新功能：完整目录下载  

现在支持批量下载模特的完整视频目录，不仅仅是缺失的视频！  

### 主要特性：
- ? **完整下载**: 下载模特的所有视频，而不仅仅是缺失的视频
- ? **批量处理**: 支持同时下载多个模特的完整目录
- ? **智能重复检测**: 自动跳过已存在的文件，避免重复下载
- ? **代理支持**: 完整支持 HTTP/SOCKS 代理配置
- ? **会员支持**: 支持 Cookie 配置下载会员专享内容
- ? **进度监控**: 实时显示下载进度和详细统计
- ?? **灵活配置**: 支持最大下载数量、分辨率等参数设置

### 快速使用：
```python
from core.modules.porn.downloader import download_model_complete_directory

# 下载单个模特的完整目录
result = download_model_complete_directory(
    model_url="https://www.porn.com/model/your-model",
    model_name="模特名称",
    max_videos=50  # 可选：限制下载数量
)
```

详细使用说明请查看 [docs/COMPLETE_DOWNLOAD.md](docs/COMPLETE_DOWNLOAD.md)  
 
