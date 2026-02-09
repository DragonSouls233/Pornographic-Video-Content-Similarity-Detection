# 模特查重管理系统

一个用于管理和检查模特视频的工具，支持通过GUI界面管理模特信息并自动检查本地视频与在线视频的一致性，包括JAV模特的同步和识别功能。

## ✨ 功能特点

- ✅ **模特管理**：添加、编辑、删除模特信息
- ✅ **自动查重**：检查本地视频与在线视频的一致性
- ✅ **缓存机制**：记录已查询过的视频标题，跳过重复查询
- ✅ **多线程**：运行脚本时使用线程，避免界面卡顿
- ✅ **实时更新**：运行状态和日志实时显示
- ✅ **导出功能**：导出查询结果和模特数据
- ✅ **跨平台**：支持在不同Windows电脑上运行
- ✅ **JAV模特支持**：专门支持JAV模特的同步和识别
- ✅ **智能识别**：自动识别和匹配JAV模特视频
- ✅ **国家分类**：按国家分类管理模特和视频
- ✅ **增强的文件名清理**：更智能的文件名清理和标准化
- ✅ **Selenium支持**：浏览器自动化抓取，应对反爬虫
- ✅ **代理支持**：完整的HTTP/SOCKS5代理配置
- ✅ **错误处理**：自动重试和错误恢复机制

## 🚀 快速开始

### 方法一：下载可执行文件（推荐）

1. 从 [Releases](../../releases) 下载 `模特查重管理系统.exe`
2. 双击运行
3. 首次运行会自动生成配置文件

### 方法二：从源码运行

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/Pornographic-Video-Content-Similarity-Detection.git
cd Pornographic-Video-Content-Similarity-Detection

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行测试
python test_system.py

# 4. 启动程序
python gui/gui.py
```

**详细安装说明：** 查看 [INSTALL.md](INSTALL.md)  
**快速启动指南：** 查看 [QUICKSTART.md](QUICKSTART.md)

## 📋 系统要求

- **Python**: 3.8 或更高版本
- **Chrome**: 最新版本（使用 Selenium 时需要）
- **操作系统**: Windows / Linux / macOS
- **网络**: 稳定的网络连接（建议配置代理访问国外网站）

## 🎯 主要更新（v1.1）

### 🆕 新功能

1. **Selenium 浏览器自动化**
   - 应对反爬虫机制
   - 自动下载和管理 ChromeDriver
   - 支持无头模式和代理配置

2. **增强的错误处理**
   - 自动重试机制
   - 错误分类和统计
   - 详细的错误报告

3. **改进的代理支持**
   - HTTP 和 SOCKS5 代理
   - 代理测试功能
   - GUI 中的代理配置和测试

4. **完整的测试套件**
   - 系统健康检查
   - 依赖验证
   - 配置验证

### 🔧 修复

- ✅ 修复 GUI 浏览器模块的代理问题
- ✅ 改进打包脚本，支持跨平台
- ✅ 增强日志系统
- ✅ 优化文件扫描性能

## 📁 项目结构

```
Pornographic-Video-Content-Similarity-Detection/
├── core/                          # 核心模块
│   ├── core.py                   # 主程序入口
│   └── modules/                  # 功能模块
│       ├── common/               # 通用工具
│       │   ├── common.py        # 配置、日志、缓存
│       │   ├── selenium_helper.py  # Selenium 助手
│       │   └── error_handler.py    # 错误处理
│       ├── pronhub/             # PRONHUB 模块
│       └── javdb/               # JAVDB 模块
├── gui/                          # GUI 界面
│   ├── gui.py                   # 主界面
│   ├── browser.py               # 浏览器组件
│   └── config_template.py       # 配置模板
├── config.yaml                   # 配置文件
├── models.json                   # 模特数据
├── local_dirs.json              # 本地目录配置
├── requirements.txt             # Python 依赖
├── test_system.py              # 测试脚本
├── 打包脚本.bat                 # Windows 打包
├── build.sh                     # Linux/Mac 打包
├── README.md                    # 本文件
├── INSTALL.md                   # 详细安装指南
└── QUICKSTART.md                # 快速启动指南
```

## 🔧 配置说明

配置文件包含详细的系统设置，以下是主要配置项：

```yaml
# =====================================
# 配置文件 - 视频内容相似度检测系统
# =====================================

# === 扫描设置 ===
# 本地视频文件根目录列表，系统将从这些目录开始扫描视频文件
# 示例目录配置，请根据实际情况修改为您的本地目录路径
local_roots:
  - "D:\\Videos\\Examples\\Category1"       # 示例目录1
  - "D:\\Videos\\Examples\\Category2"       # 示例目录2
  - "D:\\Videos\\Examples\\Category3"       # 示例目录3

# === 网页抓取设置 ===
use_selenium: true            # 是否使用Selenium浏览器进行网页抓取（true=启用）
delay_between_pages:           # 页面间延迟设置，避免请求过于频繁被封
  min: 2.0                     # 最小延迟时间（秒）
  max: 3.5                     # 最大延迟时间（秒）
retry_on_fail: 2               # 请求失败时的重试次数
max_pages: -1                  # 最大翻页数（-1表示无限制翻页）

# === 文件过滤 ===
# 支持的视频文件扩展名列表，只有这些扩展名的文件会被处理
video_extensions:
  - ".mp4"   # MPEG-4视频格式
  - ".mkv"   # Matroska视频格式
  - ".avi"   # AVI视频格式
  - ".mov"   # QuickTime视频格式
  - ".wmv"   # Windows Media视频格式
  - ".flv"   # Flash视频格式

# === 清洗规则 ===
# 文件名清洗正则表达式列表，用于从文件名中移除无关信息
filename_clean_patterns:
  - "^\\[Channel\\]\\s*"        # 移除开头的[Channel]标记
  - "_\\d{3,4}x\\d{3,4}"        # 移除分辨率信息（如_1920x1080）
  - "_\\d{8}"                    # 移除日期信息（如_20240101）
  - "\\[.*?\\]"                  # 移除方括号内的所有内容
  - "\\(.*?\\)"                  # 移除圆括号内的所有内容
  - "\\d{3,4}p"                  # 移除清晰度标记（如1080p）
  - "HD|FHD|UHD|4K"               # 移除高清标记
  - "web[-_]?dl|webrip|bluray|dvdrip"  # 移除来源标记

# === 输出设置 ===
output_dir: "output"          # 输出结果目录
log_dir: "logs"               # 日志文件目录

# === 缓存管理 ===
cache:
  enabled: true                  # 是否启用缓存
  cache_dir: "cache"             # 缓存目录路径（相对于output_dir）
  expiration_days: 3650          # 缓存过期时间（天）- 设置为10年
  max_size_mb: -1                # 缓存最大大小（MB）- -1表示无限制
  cleanup_strategy: "none"       # 清理策略：none（不清理）、expired（只清理过期）、size（按大小）、all（全部）
  compress: false                # 是否压缩缓存文件

# === 网络请求 ===
network:
  timeout: 300                   # 请求超时时间（秒）- 设置为5分钟
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"  # 自定义User-Agent
  headers:                       # 额外的HTTP请求头
    Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    Accept-Language: "zh-CN,zh;q=0.9,en;q=0.8"
  proxy:                         # 代理服务器设置
    enabled: false
    http: ""
    https: ""
  verify_ssl: true               # 是否验证SSL证书
  pool_size: 10                  # HTTP连接池大小 - 增大连接池
  backoff_factor: 0.5            # 重试间隔的退避因子

# === 对比逻辑 ===
comparison:
  mode: "new_only"               # 对比模式：new_only（只检查新视频）、all（所有视频）
  similarity_threshold: 0.8       # 相似度阈值（0-1）
  match_strategy: "fuzzy"        # 匹配策略：exact（精确）、fuzzy（模糊）
  ignore_list:                   # 忽略的视频标题列表
    - "Sample Video"
    - "Test Video"
  case_sensitive: false          # 是否区分大小写
  strip_punctuation: true        # 是否移除标点符号后对比

# === 日志配置 ===
logging:
  level: "INFO"                  # 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s | %(levelname)-8s | %(message)s"  # 日志格式
  datefmt: "%Y-%m-%d %H:%M:%S"   # 日期时间格式
  encoding: "utf-8"              # 日志文件编码
  max_bytes: 10485760            # 单个日志文件最大大小（10MB）
  backup_count: 5                # 保留的日志文件数量
  console: true                  # 是否输出到控制台
  missing_video_detail: true     # 缺失视频日志的详细程度
  countries_log_structure: true  # 是否创建国家分类日志目录

# === Selenium配置 ===
selenium:
  browser: "chrome"              # 浏览器类型：chrome, firefox, edge
  chromedriver_path: ""          # ChromeDriver路径（留空自动查找）
  window_size: "1920x1080"       # 浏览器窗口大小
  page_load_timeout: 600         # 页面加载超时时间（秒）- 设置为10分钟
  script_timeout: 300            # 脚本执行超时时间（秒）- 设置为5分钟
  headless: true                 # 是否启用无头模式
  disable_extensions: true       # 是否禁用浏览器扩展
  disable_gpu: true              # 是否禁用GPU加速
  user_data_dir: ""              # 用户数据目录（留空使用临时目录）
  profile_directory: ""          # 浏览器配置文件目录

# === 本地文件扫描 ===
local_scan:
  max_depth: -1                  # 最大扫描深度 - -1表示无限制
  thread_count: 3                # 扫描线程数
  min_file_size: 0               # 最小文件大小（字节）- 0表示无限制
  max_file_size: -1              # 最大文件大小（字节）- -1表示无限制
  ignore_dirs:                   # 忽略的目录列表
    - "System Volume Information"
    - "$RECYCLE.BIN"
  ignore_files:                  # 忽略的文件列表
    - "Thumbs.db"
  model_dir_pattern: "^\\[.*?\\]\\s*"  # 模特目录匹配模式
  scan_timeout: -1               # 扫描超时时间（秒）- -1表示无限制
  follow_symlinks: false         # 是否跟随符号链接

# === 文件名清理 ===
filename_cleaning:
  enabled: true                  # 是否启用文件名清理
  clean_patterns:                # 自定义清理规则（会与默认规则合并）
    - "^\\[Sample\\]\\s*"        # 示例：移除开头的[Sample]标记
  clean_order:                   # 清理规则的应用顺序
    - "brackets"                 # 方括号内容
    - "parentheses"              # 圆括号内容
    - "resolution"               # 分辨率信息
    - "date"                     # 日期信息
    - "special_chars"            # 特殊字符
  character_mapping:             # 字符映射规则
    "　": " "                    # 全角空格转半角
    "–": "-"                     # 长破折号转短破折号
  post_cleanup:                  # 清理后处理
    normalize_spaces: true       # 标准化空格
    trim: true                   # 移除首尾空白
    lowercase: false             # 转为小写

# === 输出文件 ===
output:
  formats:                       # 启用的输出格式
    - "txt"                      # TXT格式
    - "json"                     # JSON格式
  filename_pattern: "{timestamp}_{type}"  # 文件名模式
  directory_structure: "country/model"  # 目录结构：flat（扁平）、country（按国家）、country/model（按国家和模特）
  overwrite_existing: true       # 是否覆盖已存在的文件
  encoding: "utf-8"              # 输出文件编码
  max_file_size: -1              # 单个文件最大大小（字节）- -1表示无限制
  compress: false                # 是否压缩输出文件
  retention_days: -1             # 保留天数 - -1表示无限制

# === 错误处理 ===
error_handling:
  strategy: "continue"           # 错误处理策略：continue（继续）、stop（停止）
  max_retries: 3                 # 最大重试次数
  retry_delay: 5                 # 重试间隔（秒）
  error_categories:              # 错误分类和处理
    network: "retry"             # 网络错误：重试
    parsing: "skip"              # 解析错误：跳过
    permission: "warn"           # 权限错误：警告
  alert_threshold: 10            # 错误告警阈值
  collect_statistics: true       # 是否收集错误统计
  detailed_error_reports: true   # 是否生成详细的错误报告
```

### models.json

```json
{
  "模特名称1": "https://example.com/model1/videos",
  "模特名称2": "https://example.com/model2/videos"
}
```

## 使用方法

### 1. 使用GUI界面（推荐）

双击运行 `gui.py` 文件，或在命令行中执行：

```bash
python gui.py
```

#### 模特管理
- 在"模特管理"标签页中，点击"添加模特"按钮添加新模特
- 选择模特后点击"编辑模特"按钮修改信息
- 选择模特后点击"删除模特"按钮删除
- 在搜索框中输入关键词搜索模特

#### 运行查重
- 在"运行控制"标签页中，设置运行参数
- 点击"开始运行"按钮启动脚本
- 查看运行进度和日志
- 点击"停止运行"按钮停止脚本

#### 查看结果
- 在"结果显示"标签页中，查看统计信息
- 查看缺失视频列表
- 点击"导出结果"按钮导出结果

### 2. 使用命令行

在命令行中执行：

```bash
python 脚本.py
```

## 打包说明

### 打包为EXE文件

1. **安装PyInstaller**：

```bash
pip install pyinstaller
```

2. **打包命令行版本**：

```bash
pyinstaller --onefile --name=查重脚本 --add-data="config.yaml;./" --add-data="models.json;./" 脚本.py
```

3. **打包GUI版本**：

```bash
pyinstaller --onefile --name=查重脚本GUI --add-data="config.yaml;./" --add-data="models.json;./" gui.py
```

4. **打包结果**：

打包完成后，可执行文件会生成在 `dist` 目录中：
- `查重脚本.exe` - 命令行版本
- `查重脚本GUI.exe` - GUI版本

## 在不同电脑上运行

1. **复制文件**：
   - 将整个 `dist` 文件夹复制到目标电脑
   - 或复制打包后的EXE文件和配置文件

2. **首次运行**：
   - 首次运行会创建必要的目录结构
   - 会自动生成 `logs` 和 `output` 目录

3. **后续运行**：
   - 后续运行会使用缓存，跳过已查询过的内容
   - 缓存文件保存在 `output/cache` 目录中

## 注意事项

1. **网络连接**：需要稳定的网络连接以获取在线视频信息
2. **权限**：确保脚本有写入权限，以便创建缓存文件和日志
3. **内存**：运行时可能需要较多内存，特别是处理大量模特时
4. **Chrome浏览器**：使用Selenium模式时需要Chrome浏览器
5. **配置文件**：确保 `config.yaml` 和 `models.json` 文件在正确的位置

## 故障排除

### 常见问题

1. **无法启动**：
   - 检查Python是否正确安装
   - 检查依赖库是否安装完整

2. **运行出错**：
   - 检查网络连接是否正常
   - 检查Chrome浏览器是否安装
   - 查看日志文件了解详细错误信息

3. **缓存问题**：
   - 如果缓存文件损坏，可删除 `output/cache` 目录重新生成

4. **路径问题**：
   - 确保 `local_roots` 中的路径在目标电脑上存在

## 日志文件

- **运行日志**：保存在 `logs` 目录中
- **缺失视频日志**：保存在 `logs` 目录中，文件名格式为 `missing_YYYYMMDD.log`
- **国家-模特报告**：保存在 `logs/countries/国家/模特名称` 目录中

## 缓存文件

缓存文件保存在 `output/cache` 目录中，每个模特对应一个JSON文件，记录已查询过的视频标题。

## 许可证

本项目仅供个人使用，请勿用于商业用途。

## 更新日志

### v1.0
- ✅ 初始版本
- ✅ 基本的模特管理功能
- ✅ 自动查重功能
- ✅ 缓存机制
- ✅ GUI界面
- ✅ 打包功能

### v1.1 - JAV模特增强版
- ⏳ **JAV模特支持**：专门支持JAV模特的同步和识别（开发中）
- ⏳ **智能识别**：自动识别和匹配JAV模特视频（开发中）
- ✅ **国家分类**：按国家分类管理模特和视频
- ✅ **增强的文件名清理**：更智能的文件名清理和标准化
- ✅ **详细的配置选项**：新增60+个配置项，支持精细调整
- ✅ **无限制模式**：移除所有大小和时间限制
- ✅ **优化的网络请求**：更稳定的网络请求和重试机制
- ✅ **增强的Selenium配置**：更灵活的浏览器自动化设置
- ✅ **详细的日志和报告**：更全面的日志记录和报告生成
- ✅ **优化的本地文件扫描**：更高效的文件系统扫描

## 联系信息

如果有任何问题或建议，欢迎反馈。
