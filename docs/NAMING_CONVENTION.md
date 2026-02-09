# 📝 项目命名规范

## 🎯 总体原则

命名应遵循**清晰、一致、语义化**的原则，便于理解代码意图和维护。

## 🐍 Python 命名约定

### 文件命名
- **模块文件**: `snake_case.py`
  - ✅ 正确: `common.py`, `porn.py`, `downloader.py`
  - ❌ 错误: `Common.py`, `PORN.py`, `Downloader.py`

- **包目录**: `lowercase`
  - ✅ 正确: `core`, `modules`, `common`, `porn`
  - ❌ 错误: `Core`, `MODULES`, `Common`

### 类命名
- **类名**: `PascalCase`
  - ✅ 正确: `ModelProcessor`, `SmartCache`, `PornDownloader`
  - ❌ 错误: `model_processor`, `smart_cache`, `porn_downloader`

### 函数命名
- **函数名**: `snake_case`
  - ✅ 正确: `extract_local_videos`, `download_video`, `get_video_info`
  - ❌ 错误: `ExtractLocalVideos`, `DownloadVideo`, `GetVideoInfo`

### 变量命名
- **变量名**: `snake_case`
  - ✅ 正确: `video_titles`, `cache_dir`, `model_name`
  - ❌ 错误: `VideoTitles`, `CacheDir`, `ModelName`

### 常量命名
- **常量**: `UPPER_SNAKE_CASE`
  - ✅ 正确: `MAX_RETRIES`, `DEFAULT_TIMEOUT`, `VIDEO_EXTENSIONS`
  - ❌ 错误: `max_retries`, `DefaultTimeout`, `videoExtensions`

### 私有成员
- **私有成员**: `_single_underscore_prefix`
  - ✅ 正确: `_private_method`, `_internal_variable`
  - ❌ 错误: `__private_method`, `private_method`

## 🔄 接口一致性规范

### 下载相关函数命名统一

**核心下载函数命名**:
```python
# ✅ 统一使用以下命名模式
def download_video(url: str, save_dir: Optional[str] = None) -> Dict:
def download_videos(urls: List[str], save_dir: Optional[str] = None) -> List[Dict]:
def download_model_videos(model_name: str, save_dir: Optional[str] = None) -> List[Dict]:
```

**版本区分命名**:
```python
# ✅ 版本后缀命名规范
def download_porn_video(url: str, ...)           # 统一调度器（推荐）
def download_porn_video_v1(url: str, ...)        # V1版本
def download_porn_video_v3_fixed(url: str, ...)  # V3版本
```

### 参数命名一致性

**常用参数命名**:
```python
# ✅ 统一参数命名
model_name: str          # 模特名称
save_dir: str           # 保存目录
config: dict           # 配置字典
url: str               # URL地址
urls: List[str]        # URL列表
video_id: str          # 视频ID
title: str             # 标题
```

### 返回值结构统一

**标准返回值格式**:
```python
# ✅ 成功返回
{
    'success': True,
    'message': '操作成功',
    'data': {...}  # 具体数据
}

# ✅ 失败返回
{
    'success': False,
    'error': '错误信息',
    'message': '详细错误描述'
}
```

## 📁 模块组织规范

### 包导入顺序
1. 标准库导入
2. 第三方库导入
3. 项目内部导入

```python
# ✅ 正确的导入顺序
import os
import sys
from typing import List, Dict

import requests
import yaml

from core.modules.common.common import get_config
from core.modules.porn.downloader import PornDownloader
```

### 模块初始化
每个包目录应包含 `__init__.py` 文件，用于控制模块暴露的接口。

## 🔧 重构建议

### 已识别的命名问题

1. **函数命名不一致**:
   - `download_single_video` vs `download_video`
   - `download_multiple_videos` vs `download_videos`

2. **版本命名混乱**:
   - 缺少统一的版本后缀规范

3. **参数命名不统一**:
   - 相同含义的参数在不同函数中使用不同名称

### 修复计划

1. **第一阶段**: 统一核心下载函数命名
2. **第二阶段**: 标准化参数命名
3. **第三阶段**: 规范返回值结构
4. **第四阶段**: 完善文档和注释

## 📋 检查清单

- [ ] 所有文件名使用 snake_case
- [ ] 所有类名使用 PascalCase
- [ ] 所有函数名使用 snake_case
- [ ] 所有变量名使用 snake_case
- [ ] 所有常量使用 UPPER_SNAKE_CASE
- [ ] 私有成员使用单下划线前缀
- [ ] 下载函数命名统一为 download_video 模式
- [ ] 参数命名在同类函数中保持一致
- [ ] 返回值结构遵循标准格式
- [ ] 导入顺序符合规范
- [ ] 包含适当的文档字符串

## 🚨 注意事项

1. **向后兼容**: 重构时保持API兼容性
2. **渐进式改进**: 分阶段实施，避免大规模破坏性变更
3. **充分测试**: 每次重构后都要进行充分测试
4. **文档同步**: 及时更新相关文档和注释