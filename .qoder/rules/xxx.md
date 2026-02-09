---
trigger: always_on
---
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
# 📐 项目结构图

## 🎯 命名规范

### Python 命名约定

**文件命名**
- 模块文件：`snake_case.py`（如 `common.py`, `porn.py`）
- 类名：`PascalCase`（如 `ModelProcessor`, `SmartCache`）
- 函数名：`snake_case`（如 `extract_local_videos`, `download_video`）
- 变量名：`snake_case`（如 `video_titles`, `cache_dir`）
- 常量：`UPPER_SNAKE_CASE`（如 `MAX_RETRIES`, `DEFAULT_TIMEOUT`）
- 私有成员：`_single_underscore_prefix`（如 `_private_method`）

**目录结构**
- 包目录：`lowercase`（如 `core`, `modules`, `common`）
- 配置文件：`snake_case.extension`（如 `config.yaml`, `models.json`）

### 接口一致性
- 相同功能的函数在不同模块中应使用相同名称
- 参数命名应保持一致（如 `model_name`, `save_dir`, `config`）
- 返回值结构应统一

## 🌳 完整目录树

```
Pornographic-Video-Content-Similarity-Detection/
│
├── 📁 core/                                # 核心功能模块
│   ├── 📄 __init__.py                     # 包初始化文件
│   ├── 📄 core.py                         # ⭐ 主程序入口，核心处理逻辑
│   │
│   └── 📁 modules/                        # 功能模块目录
│       ├── 📄 __init__.py
│       │
│       ├── 📁 common/                     # 通用工具模块
│       │   ├── 📄 __init__.py
│       │   ├── 📄 common.py               # ⭐ 配置、日志、缓存、文件处理
│       │   ├── 📄 selenium_helper.py      # ⭐ Selenium 浏览器自动化助手
│       │   └── 📄 error_handler.py        # ⭐ 错误处理和重试机制
│       │
│       ├── 📁 porn/                    # PORN 平台模块
│       │   ├── 📄 __init__.py
│       │   └── 📄 porn.py              # ⭐ PORN 视频抓取逻辑
│       │
│       └── 📁 javdb/                      # JAVDB 平台模块
│           ├── 📄 __init__.py
│           └── 📄 javdb.py                # ⭐ JAVDB 视频抓取逻辑
│
├── 📁 gui/                                # 图形用户界面模块
│   ├── 📄 __init__.py
│   ├── 📄 gui.py                          # ⭐ 主界面窗口（模特管理、运行控制）
│   ├── 📄 browser.py                      # ⭐ 内置浏览器/代理测试模块
│   └── 📄 config_template.py              # 配置模板生成器
│
├── 📁 output/                             # 输出文件目录（自动生成）
│   ├── 📁 cache/                          # 缓存文件
│   │   └── 📄 *.json                      # 模特视频缓存
│   ├── 📁 logs/                           # 日志文件
│   │   ├── 📄 app.log                     # 应用日志
│   │   ├── 📄 missing_videos.log          # 缺失视频专用日志
│   │   └── 📁 countries/                  # 按国家分类的报告
│   │       ├── 📁 日本/
│   │       ├── 📁 美国/
│   │       └── 📁 其他/
│   └── 📁 reports/                        # 生成的报告文件
│       └── 📄 *.txt
│
├── 📄 config.yaml                         # ⭐ 主配置文件
├── 📄 models.json                         # ⭐ 模特数据（名称和URL）
├── 📄 local_dirs.json                     # ⭐ 本地视频目录配置
│
├── 📄 requirements.txt                    # ⭐ Python 依赖清单
├── 📄 test_system.py                      # ⭐ 系统测试脚本
│
├── 🪟 打包脚本.bat                         # Windows 打包脚本
├── 🐧 build.sh                            # Linux/Mac 打包脚本
│
├── 📖 README.md                           # 项目说明文档
├── 📖 INSTALL.md                          # 详细安装指南
├── 📖 QUICKSTART.md                       # 快速启动指南
├── 📖 FIXES.md                            # 修复总结报告
└── 📖 PROJECT_STRUCTURE.md                # 本文件（项目结构）
```

---

## 🏗️ 模块架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                          GUI 层 (gui/)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐      │
│  │   gui.py     │  │  browser.py  │  │ config_template  │      │
│  │ (主界面窗口)  │  │ (代理测试)    │  │  .py (配置生成)  │      │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      核心逻辑层 (core/)                          │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                    core.py                            │       │
│  │         (主程序流程控制、模特处理、结果汇总)            │       │
│  └──────────────────┬───────────────────────────────────┘       │
│                     │                                            │
│                     ▼                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              modules/ (功能模块)                          │   │
│  │  ┌────────────────┐ ┌──────────────┐ ┌──────────────┐  │   │
│  │  │  common/       │ │  porn/    │ │   javdb/     │  │   │
│  │  │ • common.py    │ │ • porn.py │ │ • javdb.py   │  │   │
│  │  │ • selenium_    │ └──────────────┘ └──────────────┘  │   │
│  │  │   helper.py    │                                     │   │
│  │  │ • error_       │                                     │   │
│  │  │   handler.py   │                                     │   │
│  │  └────────────────┘                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                       数据/配置层                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ config.yaml  │  │ models.json  │  │ local_dirs   │          │
│  │  (系统配置)   │  │ (模特数据)    │  │  .json       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       外部依赖层                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Selenium    │  │  Requests    │  │ BeautifulSoup│          │
│  │ (浏览器自动化)│  │  (HTTP请求)   │  │  (HTML解析)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  ChromeDriver│  │  PyYAML      │  │  PySocks     │          │
│  │  (驱动管理)   │  │ (配置解析)    │  │  (代理支持)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 数据流向图

```
用户操作 (GUI)
    │
    ▼
┌──────────────────────┐
│  gui/gui.py          │
│  • 读取配置          │◄─────── config.yaml
│  • 加载模特列表      │◄─────── models.json
│  • 扫描本地目录      │◄─────── local_dirs.json
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  core/core.py        │
│  • 初始化日志        │─────► logs/app.log
│  • 遍历模特列表      │
│  • 调用抓取模块      │
└──────────┬───────────┘
           │
           ├─────────────────────┬─────────────────────┐
           ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ modules/common  │   │ modules/porn │   │ modules/javdb   │
│ • 文件扫描      │   │ • 网页抓取      │   │ • 网页抓取      │
│ • 缓存加载      │◄──┤ • 标题提取      │   │ • 标题提取      │
│ • 文件名清理    │   │ • 分页处理      │   │ • 分页处理      │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                     │
         │                     ▼                     │
         │          ┌──────────────────┐             │
         │          │ selenium_helper  │             │
         │          │ • 浏览器启动     │             │
         │          │ • 页面访问       │             │
         │          │ • 元素等待       │             │
         │          │ • 代理配置       │             │
         │          └──────────────────┘             │
         │                     │                     │
         └─────────────────────┴─────────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │  error_handler   │
                    │  • 异常捕获      │
                    │  • 自动重试      │
                    │  • 错误统计      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  core/core.py    │
                    │  • 对比标题      │
                    │  • 找出缺失      │
                    │  • 更新缓存      │
                    │  • 生成报告      │
                    └────────┬─────────┘
                             │
                             ├─────────────┬──────────────┐
                             ▼             ▼              ▼
                    ┌────────────┐  ┌────────────┐  ┌────────────┐
                    │ cache/     │  │ logs/      │  │ reports/   │
                    │ *.json     │  │ countries/ │  │ *.txt      │
                    └────────────┘  └────────────┘  └────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  GUI 显示结果     │
                    │  • 统计信息      │
                    │  • 缺失视频列表  │
                    │  • 实时日志      │
                    └──────────────────┘
```

---

## 📋 核心模块详解

### 1. **core/core.py** - 主程序入口
```python
主要功能：
├── 配置加载和初始化
├── 本地目录扫描
│   ├── 识别 PORN 格式 ([Channel] 模特名/)
│   └── 识别 JAVDB 格式 (模特名/)
├── 模特遍历处理
│   ├── 加载缓存
│   ├── 调用抓取模块
│   ├── 对比标题
│   ├── 找出缺失
│   └── 更新缓存
├── 生成报告
│   ├── 按国家分类
│   ├── 统计信息
│   └── 缺失视频列表
└── 日志记录
```

### 2. **modules/common/common.py** - 通用工具
```python
主要功能：
├── load_config()              # 加载 YAML 配置
├── load_models()              # 加载模特数据
├── setup_logging()            # 配置日志系统
├── load_cache()               # 加载缓存
├── save_cache()               # 保存缓存
├── clean_filename()           # 文件名清理
├── scan_local_videos()        # 扫描本地视频
└── extract_video_titles()     # 提取视频标题
```

### 3. **modules/common/selenium_helper.py** - Selenium 助手
```python
主要功能：
├── SeleniumHelper 类
│   ├── __init__()             # 初始化配置
│   ├── setup_driver()         # 启动 Chrome 浏览器
│   │   ├── 配置代理
│   │   ├── 设置无头模式
│   │   ├── 禁用自动化检测
│   │   └── 自动下载 ChromeDriver
│   ├── get_page()             # 访问页面并等待
│   ├── get_page_source()      # 获取页面源码
│   ├── scroll_to_bottom()     # 滚动加载
│   ├── click_next_page()      # 翻页
│   └── close()                # 关闭浏览器
└── create_selenium_helper()   # 工厂函数
```

### 4. **modules/common/error_handler.py** - 错误处理
```python
主要功能：
├── 自定义异常类
│   ├── RetryException         # 可重试异常
│   ├── NetworkException       # 网络错误
│   ├── ParsingException       # 解析错误
│   └── PermissionException    # 权限错误
├── retry_on_exception()       # 重试装饰器
│   ├── 指数退避
│   ├── 最大重试次数
│   └── 异常类型过滤
├── safe_execute()             # 安全执行函数
└── ErrorCollector 类          # 错误收集器
    ├── add_error()            # 添加错误
    ├── get_statistics()       # 获取统计
    ├── get_report()           # 生成报告
    └── clear()                # 清空记录
```

### 5. **modules/porn/porn.py** - PORN 抓取
```python
主要功能：
├── fetch_with_requests_porn()     # 总入口（自动选择）
├── fetch_with_selenium_porn()     # Selenium 抓取
│   ├── 启动浏览器
│   ├── 访问页面
│   ├── 提取标题（多选择器）
│   ├── 自动翻页
│   └── 错误处理
├── fetch_with_requests_only_porn() # Requests 抓取
│   ├── HTTP 请求
│   ├── BeautifulSoup 解析
│   ├── 提取标题
│   └── 自动翻页
├── clean_porn_title()             # 标题清理
├── match_porn_videos()            # 视频匹配
└── scan_porn_directory()          # 目录扫描
```

### 6. **modules/javdb/javdb.py** - JAVDB 抓取
```python
主要功能：
├── fetch_with_requests_javdb()       # 总入口（自动选择）
├── fetch_with_selenium_javdb()       # Selenium 抓取
│   ├── 启动浏览器
│   ├── 访问页面
│   ├── 提取标题（多选择器）
│   ├── 自动翻页
│   └── 错误处理
├── fetch_with_requests_only_javdb()  # Requests 抓取
│   ├── HTTP 请求
│   ├── BeautifulSoup 解析
│   ├── 提取标题
│   └── 自动翻页
├── clean_javdb_title()               # 标题清理
├── match_javdb_videos()              # 视频匹配
└── scan_javdb_directory()            # 目录扫描
```

### 7. **gui/gui.py** - 主界面
```python
主要功能：
├── MainWindow 类
│   ├── 模特管理标签页
│   │   ├── 增加模特
│   │   ├── 删除模特
│   │   ├── 编辑模特
│   │   ├── 搜索模特
│   │   ├── 导入/导出
│   │   └── 批量操作
│   ├── 运行控制标签页
│   │   ├── 配置选择（模块、代理等）
│   │   ├── 启动/停止按钮
│   │   ├── 进度显示
│   │   └── 实时日志
│   ├── 结果展示标签页
│   │   ├── 统计信息
│   │   ├── 缺失视频列表
│   │   └── 导出功能
│   └── 菜单栏
│       ├── 文件（打开配置、退出）
│       ├── 工具（清理缓存、查看日志）
│       └── 帮助（关于）
└── 线程管理
    └── 后台运行 core.py
```

### 8. **gui/browser.py** - 代理测试浏览器
```python
主要功能：
├── BrowserWindow 类
│   ├── init_browser()         # 初始化界面
│   │   ├── 代理配置显示
│   │   ├── 测试结果区域
│   │   └── 使用说明
│   ├── browser_go()           # 访问并测试
│   │   ├── 使用 requests 测试
│   │   ├── 显示响应信息
│   │   ├── 错误诊断
│   │   └── 询问是否打开浏览器
│   ├── browser_refresh()      # 刷新测试
│   ├── browser_back()         # 清空结果
│   └── open_system_browser()  # 打开系统浏览器
└── 代理测试
    ├── 连接测试
    ├── 响应时间
    └── 页面解析
```

---

## 📊 配置文件结构

### config.yaml
```yaml
local_roots:                      # 本地视频目录列表
  - F:/作品
  - D:/Videos

video_extensions:                 # 支持的视频格式
  - .mp4
  - .avi
  - .mkv

filename_clean_patterns:          # 文件名清理规则
  - pattern: \[.*?\]
  - pattern: \d{3,4}p

network:
  proxy:
    enabled: true                 # 启用代理
    type: socks5                  # 代理类型
    host: 127.0.0.1              # 代理主机
    port: 10808                   # 代理端口
  user_agent: ...                 # User Agent
  timeout: 30                     # 请求超时

cache:
  enabled: true                   # 启用缓存
  expire_days: 7                  # 缓存过期天数
  directory: output/cache         # 缓存目录

selenium:
  enabled: true                   # 启用 Selenium
  headless: true                  # 无头模式
  window_size: 1920x1080          # 窗口大小
  chromedriver_path: ""           # ChromeDriver 路径

logging:
  level: INFO                     # 日志级别
  file: output/logs/app.log       # 日志文件
  format: ...                     # 日志格式
```

### models.json
```json
{
  "JULIA": "https://javdb.com/actors/1KBW",
  "三上悠亚": "https://javdb.com/actors/ABC",
  "桥本有菜": "https://javdb.com/actors/XYZ"
}
```

### local_dirs.json
```json
[
  "F:/作品",
  "D:/Videos/JAV"
]
```

---

## 🔐 安全和隐私

### 数据保护
```
本地存储：
├── 所有数据存储在本地
├── 不上传任何个人信息
└── 缓存可随时清除

网络请求：
├── 仅访问用户配置的URL
├── 支持代理保护隐私
└── 可配置请求头和参数
```

---

## 📈 性能优化点

### 当前实现
```
✅ 缓存机制（避免重复查询）
✅ 文件名预处理（减少对比次数）
✅ 多模块并行扫描（PORN + JAVDB）
✅ 日志分级（减少 I/O 开销）
✅ 代理支持（绕过限制）
```

### 可优化方向
```
🔄 多线程抓取（并发处理多个模特）
🔄 数据库存储（替代 JSON 文件）
🔄 增量更新（只抓取新视频）
🔄 智能匹配（模糊匹配算法）
🔄 分布式部署（多机协同）
```

---

## 🎯 总结

这个项目采用了清晰的**模块化架构**，主要特点：

1. **分层设计**: GUI → Core → Modules → Data
2. **功能分离**: 每个模块职责单一
3. **易于扩展**: 新增平台只需添加模块
4. **配置灵活**: 通过配置文件控制行为
5. **错误恢复**: 完善的异常处理机制
6. **可维护性高**: 代码结构清晰，注释完整

---

**创建日期**: 2026-02-09  
**版本**: v1.1  
**状态**: ✅ 完整
