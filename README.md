# 模特查重管理系统

一个用于管理和检查模特视频的工具，支持通过GUI界面管理模特信息并自动检查本地视频与在线视频的一致性。

## 功能特点

- ✅ **模特管理**：添加、编辑、删除模特信息
- ✅ **自动查重**：检查本地视频与在线视频的一致性
- ✅ **缓存机制**：记录已查询过的视频标题，跳过重复查询
- ✅ **多线程**：运行脚本时使用线程，避免界面卡顿
- ✅ **实时更新**：运行状态和日志实时显示
- ✅ **导出功能**：导出查询结果和模特数据
- ✅ **跨平台**：支持在不同Windows电脑上运行

## 项目结构

```
查重脚本/
├── .gitignore          # Git忽略文件
├── README.md           # 项目说明
├── config.yaml         # 配置文件
├── gui.py              # GUI界面
├── models.json         # 模特数据
└── 脚本.py             # 核心脚本
```

## 安装说明

### 1. 安装Python

确保你的电脑上安装了Python 3.8或更高版本。可以从 [Python官网](https://www.python.org/downloads/) 下载并安装。

### 2. 安装依赖

在项目目录中打开命令行，执行以下命令安装所需的依赖库：

```bash
pip install beautifulsoup4 requests selenium pyyaml
```

### 3. 配置Chrome浏览器

如果使用Selenium模式（默认启用），请确保你的电脑上安装了Chrome浏览器，并且Chrome版本与Selenium兼容。

## 配置文件

### config.yaml

```yaml
# 本地目录列表
local_roots:
  - "\\Dragons\欧洲"
  - "\\Dragons\亚美"
  - "\\Dragons\原始"

# 输出目录
output_dir: "output"

# 日志目录
log_dir: "logs"

# 视频扩展名
video_extensions:
  - .mp4
  - .avi
  - .mov
  - .wmv

# 文件名清理模式
filename_clean_patterns:
  - '\[.*?\]'
  - '\(.*?\)'

# 使用Selenium
use_selenium: true

# 最大翻页
max_pages: -1

# 失败重试次数
retry_on_fail: 2

# 页面间延时
Delay_between_pages:
  min: 2.0
  max: 3.5
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

## 联系信息

如果有任何问题或建议，欢迎反馈。
