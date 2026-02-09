# PRON文件命名标准规范

## 📋 概述

本文档定义了PRON模块的文件命名标准，确保下载的文件具有统一、规范且易于管理的命名格式。

## 📁 目录结构

### 标准目录格式
```
output/
└── [Channel] 模特名称/
    ├── 视频标题1.mp4
    ├── 视频标题2.mp4
    └── ...
```

### 目录命名规则
- 使用 `[Channel]` 前缀标识PRON内容
- 模特名称经过标准化清理
- 支持中文、英文、数字字符
- 移除危险字符 `< > : " / \ | ? *`

## 📄 文件命名规范

### 标准文件名格式
```
{视频标题}.{扩展名}
```

### 示例
```
Beautiful Angel in Red Dress.mp4
Hot Summer Beach Fun.mkv
Private Session with Model.avi
```

### 命名规则详解

#### 1. 视频标题处理
- **移除危险字符**: `< > : " / \ | ? *`
- **移除质量标记**: HD, FHD, UHD, 4K, 1080p, 720p, 480p
- **移除来源标记**: WEB-DL, WEBRip, BluRay, DVD, HDRip
- **移除括号内容**: `[组名]`, `(备注)`
- **标准化空格**: 多个连续空格合并为单个空格
- **长度限制**: 最大150个字符（Windows兼容）

#### 2. 扩展名处理
- 保持原始视频格式扩展名
- 常见格式：`.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`

#### 3. 不包含的内容
- ❌ 视频ID（如 `_abc123`）
- ❌ 时间戳
- ❌ 分辨率信息
- ❌ 平台特定标记

## ⚙️ 技术实现

### 核心清理函数
```python
def _clean_title(self, title: str) -> str:
    """PRON标准标题清理"""
    # 移除危险字符
    title = re.sub(r'[<>:"/\\|?*]', '', title)
    
    # 移除质量和来源标记
    title = re.sub(r'\b(HD|FHD|UHD|4K|1080p|720p|480p)\b', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\b(WEB-DL|WEBRip|BluRay|DVD|HDRip)\b', '', title, flags=re.IGNORECASE)
    
    # 移除括号内容
    title = re.sub(r'\[[^\]]*\]', '', title)
    title = re.sub(r'\([^\)]*\)', '', title)
    
    # 标准化空格
    title = re.sub(r'[\s_\-\.]+', ' ', title).strip()
    
    # 长度限制
    if len(title) > 150:
        title = title[:150]
        
    return title or "Unknown_Title"
```

### yt-dlp配置
```python
download_options = {
    'outtmpl': '[Channel] %(uploader)s/%(title)s.%(ext)s',
    'restrictfilenames': False,
    'windowsfilenames': True,
    # ... 其他配置
}
```

## 🔄 与旧版本的差异

### 旧版命名格式
```
视频标题_abc123.mp4
```

### 新版PRON标准格式
```
视频标题.mp4
```

### 改进优势
1. **简洁性**: 去除冗余的视频ID
2. **可读性**: 更清晰的文件名
3. **一致性**: 统一的命名规范
4. **兼容性**: 更好的跨平台支持
5. **管理性**: 便于文件整理和查找

## 🛠️ 配置选项

### config.yaml配置
```yaml
filename_cleaning:
  enabled: true
  clean_patterns:
    - "^\\[Sample\\]\\s*"
    - "\\b(HD|FHD|UHD|4K|1080p|720p|480p)\\b"
    - "\\b(WEB-DL|WEBRip|BluRay|DVD|HDRip)\\b"
    - "\\[[^\\]]*\\]"
    - "\\([^\\)]*\\)"
  max_length: 150

download_naming:
  directory_pattern: "[Channel] {model_name}"
  filename_pattern: "{title}.{ext}"
  include_video_id: false
  restrict_filenames: false
  windows_filenames: true
```

## 📝 最佳实践

### 推荐做法
1. **保持一致性**: 所有PRON内容使用相同命名规范
2. **定期清理**: 移除重复或损坏的文件
3. **备份重要文件**: 定期备份有价值的下载内容
4. **监控磁盘空间**: 注意存储容量管理

### 避免的做法
1. ❌ 手动修改文件名（可能导致系统识别问题）
2. ❌ 使用特殊字符作为文件名
3. ❌ 创建过深的目录层级
4. ❌ 忽略文件名长度限制

## 🐛 故障排除

### 常见问题

#### 文件名过长
**问题**: 下载失败，提示文件名太长
**解决方案**: 检查标题清理函数，确保长度限制生效

#### 特殊字符问题
**问题**: 文件名包含非法字符导致保存失败
**解决方案**: 完善字符清理规则，添加更多过滤条件

#### 重复文件检测失效
**问题**: 相同内容被重复下载
**解决方案**: 确保文件名清理足够彻底，移除变化元素

## 📈 未来改进方向

1. **智能去重**: 基于内容哈希而非文件名的重复检测
2. **元数据支持**: 嵌入视频元数据信息
3. **多语言支持**: 更好的国际化文件名处理
4. **自定义模板**: 用户可配置的命名模板系统

---

*最后更新: 2024年*
*版本: v1.0 PRON标准*