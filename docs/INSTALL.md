# 安装指南

## 📦 快速开始

### 方法一：使用打包的可执行文件（推荐）

1. 从 Release 页面下载 `模特查重管理系统.exe`
2. 双击运行即可

**首次运行会自动：**
- 生成默认配置文件 `config.yaml`
- 生成空的模特配置 `models.json`
- 下载 ChromeDriver（需要网络连接）

### 方法二：从源码运行

#### 1. 安装 Python

确保安装了 Python 3.8 或更高版本：
```bash
python --version
```

下载地址：https://www.python.org/downloads/

#### 2. 克隆或下载项目

```bash
git clone https://github.com/your-repo/Pornographic-Video-Content-Similarity-Detection.git
cd Pornographic-Video-Content-Similarity-Detection
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

**依赖列表：**
- beautifulsoup4 - HTML 解析
- requests - HTTP 请求
- PyYAML - 配置文件解析
- lxml - XML/HTML 解析器
- selenium - 浏览器自动化
- webdriver-manager - ChromeDriver 管理
- PySocks - SOCKS 代理支持

#### 4. 运行程序

```bash
# 运行 GUI 版本
python gui/gui.py

# 或运行命令行版本
python core/core.py
```

---

## 🔧 配置说明

### 1. 配置代理（可选但推荐）

如果需要访问被墙的网站，需要配置代理。

**编辑 `config.yaml`：**

```yaml
network:
  proxy:
    enabled: true              # 启用代理
    type: "socks5"             # 代理类型: http 或 socks5
    host: "127.0.0.1"          # 代理主机
    port: "10808"              # 代理端口
    id: ""                     # 代理账号（如果需要）
    password: ""               # 代理密码（如果需要）
```

**常见代理工具配置：**

| 工具 | 默认端口 | 类型 |
|------|---------|------|
| v2rayN | 10808 | SOCKS5 |
| Clash | 7890 | HTTP |
| Shadowsocks | 1080 | SOCKS5 |

### 2. 配置本地视频目录

**方式一：在 GUI 中配置**
1. 打开程序
2. 进入【运行控制】标签页
3. 点击【添加】按钮，选择本地视频目录
4. 可以添加多个目录，系统会同时扫描所有配置的目录

**方式二：编辑配置文件**

编辑 `config.yaml`：
```yaml
local_roots:
  - "F:\\作品"              # 主要作品目录
  - "D:\\Videos\\PORN"      # PORN平台视频目录
  - "E:\\收藏\\欧美作品"     # 欧美作品收藏目录
  - "G:\\备份\\JAV收藏"      # JAV作品备份目录
  - "H:\\临时下载"           # 临时下载目录
```

或编辑 `local_dirs.json`：
```json
[
  "F:\\作品",
  "D:\\Videos\\PORN", 
  "E:\\收藏\\欧美作品",
  "G:\\备份\\JAV收藏",
  "H:\\临时下载"
]
```

**多目录配置最佳实践：**
- 按照视频类型或来源分类存储（如PORN、JAV、欧美等）
- 避免配置重复的目录路径
- 使用绝对路径确保系统能正确访问
- 定期清理无效或已删除的目录配置

### 3. 添加模特信息

**方式一：在 GUI 中添加**
1. 打开程序
2. 进入【模特管理】标签页
3. 点击【添加模特】按钮
4. 输入模特名称和 URL

**方式二：编辑 JSON 文件**

编辑 `models.json`：
```json
{
  "JULIA": "https://javdb.com/actors/1KBW",
  "模特名2": "https://example.com/model2"
}
```

---

## 🚀 使用说明

### GUI 界面使用

#### 1. 模特管理
- **添加模特**：点击"添加模特"按钮，输入名称和 URL
- **编辑模特**：选中模特，点击"编辑模特"
- **删除模特**：选中模特，点击"删除模特"
- **搜索模特**：在搜索框输入关键词

#### 2. 运行查重
1. 进入【运行控制】标签页
2. 选择模块类型：
   - `auto`：自动识别（推荐）
   - `porn`：只处理 PORN 格式
   - `javdb`：只处理 JAVDB 格式
3. 选择抓取工具：
   - `selenium`：浏览器自动化（推荐，可绕过反爬虫）
   - `requests`：直接 HTTP 请求（快速但可能被拦截）
4. 点击【开始运行】

#### 3. 查看结果
- 进入【结果显示】标签页
- 查看统计信息和缺失视频列表
- 点击【导出结果】导出为文本文件

#### 4. 测试代理
1. 进入【代理测试】标签页
2. 输入测试 URL
3. 点击【测试代理连接】
4. 查看测试结果

### 命令行使用

```bash
# 运行核心脚本
python core/core.py

# 指定模块
python core/core.py --module porn

# 指定抓取工具
python core/core.py --scraper selenium
```

---

## 📁 目录结构说明

### PORN 格式
```
本地目录/
├── 国家名/
│   ├── [Channel] 模特名1/
│   │   ├── 视频1.mp4
│   │   └── 视频2.mp4
│   └── [Channel] 模特名2/
│       └── 视频3.mp4
```

系统会：
- 扫描带 `[Channel]` 前缀的文件夹
- 提取视频文件名作为标题
- 与在线视频列表对比

### JAVDB 格式
```
本地目录/
├── 国家名/
│   ├── 模特名1/
│   │   ├── 视频番号1/
│   │   │   └── video.mp4
│   │   └── 视频番号2/
│   │       └── video.mp4
│   └── 模特名2/
│       └── 视频番号3/
│           └── video.mp4
```

系统会：
- 扫描不带前缀的文件夹
- 提取子文件夹名称作为标题
- 与在线视频列表对比

---

## ⚙️ 高级配置

### Selenium 配置

```yaml
selenium:
  browser: "chrome"              # 浏览器类型
  chromedriver_path: ""          # 留空自动下载
  window_size: "1920x1080"       # 窗口大小
  page_load_timeout: 600         # 页面加载超时（秒）
  script_timeout: 300            # 脚本执行超时（秒）
  headless: true                 # 无头模式（不显示浏览器窗口）
  disable_extensions: true       # 禁用扩展
  disable_gpu: true              # 禁用 GPU
```

### 缓存配置

```yaml
cache:
  enabled: true                  # 启用缓存
  cache_dir: "cache"             # 缓存目录
  expiration_days: 3650          # 缓存过期天数（10年）
  max_size_mb: -1                # 缓存大小限制（-1无限制）
  cleanup_strategy: "none"       # 清理策略
```

### 日志配置

```yaml
logging:
  level: "INFO"                  # 日志级别
  console: true                  # 控制台输出
  countries_log_structure: true  # 按国家分类日志
```

---

## 🐛 常见问题

### 1. 无法启动程序

**错误：找不到 Python**
```
解决方案：
1. 安装 Python 3.8+
2. 添加 Python 到系统 PATH
3. 重启命令行
```

**错误：缺少依赖库**
```
解决方案：
pip install -r requirements.txt
```

### 2. ChromeDriver 问题

**错误：ChromeDriver 版本不匹配**
```
解决方案：
1. 删除旧的 ChromeDriver
2. 程序会自动下载匹配版本
```

**错误：无法下载 ChromeDriver**
```
解决方案：
1. 检查网络连接
2. 配置代理
3. 手动下载并放置到指定路径
```

### 3. 代理问题

**错误：代理连接失败**
```
解决方案：
1. 确认代理工具已启动
2. 检查代理端口是否正确
3. 在【代理测试】标签页测试连接
4. 尝试访问 https://www.google.com
```

### 4. 抓取问题

**错误：无法获取在线视频列表**
```
解决方案：
1. 检查网络连接
2. 启用代理（如果网站被墙）
3. 切换到 Selenium 模式
4. 检查网站 URL 是否有效
```

**错误：网页选择器失效**
```
原因：网站改版导致选择器变化

解决方案：
1. 在 GitHub 提 Issue
2. 等待更新
3. 或自行修改选择器代码
```

### 5. 性能问题

**程序运行缓慢**
```
解决方案：
1. 减少 max_pages 限制
2. 增大 delay_between_pages
3. 使用 requests 模式（而非 Selenium）
4. 缩小扫描目录范围
```

---

## 📊 输出文件说明

### 日志文件

```
logs/
├── sync_20260209.log              # 主日志
├── missing_20260209.log           # 缺失视频日志
└── countries/                     # 按国家分类
    ├── 日本/
    │   ├── JULIA/
    │   │   └── JULIA_report_20260209.txt
    │   └── 模特B/
    └── 美国/
```

### 输出文件

```
output/
├── missing_summary_20260209_143022.txt    # 缺失视频汇总
├── missing_detail_20260209_143022.json    # 详细数据（JSON）
├── missing_current.txt                    # 当前缺失清单
└── cache/                                  # 缓存目录
    ├── JULIA.json
    └── 模特B.json
```

---

## 🔐 隐私和安全

- 所有数据仅存储在本地
- 不上传任何信息到云端
- 配置文件包含敏感信息（代理账号密码），请妥善保管
- 建议在 `.gitignore` 中排除配置文件

---

## 📝 更新日志

### v1.1 (2026-02-09)
- ✅ 添加 Selenium 支持，应对反爬虫
- ✅ 增强错误处理和重试机制
- ✅ 修复 GUI 浏览器模块代理问题
- ✅ 改进打包脚本，支持 Linux/Mac
- ✅ 添加详细的安装和使用文档
- ✅ 支持多种抓取工具切换

### v1.0
- ✅ 初始版本
- ✅ 基本的模特管理功能
- ✅ 自动查重功能
- ✅ 缓存机制
- ✅ GUI 界面

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

本项目仅供个人学习和研究使用，请勿用于商业用途。
