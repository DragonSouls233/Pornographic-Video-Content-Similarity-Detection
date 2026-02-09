# 🚀 快速启动指南

## 立即开始（5分钟）

### 步骤 1: 安装依赖

```bash
pip install -r requirements.txt
```

### 步骤 2: 运行测试

```bash
python test_system.py
```

确保所有测试通过 ✅

### 步骤 3: 启动程序

```bash
# GUI 版本（推荐）
python gui/gui.py

# 命令行版本
python core/core.py
```

---

## ⚙️ 最小配置

### 1. 配置代理（如果需要访问被墙网站）

打开 `config.yaml`，修改：

```yaml
network:
  proxy:
    enabled: true
    type: "socks5"
    host: "127.0.0.1"
    port: "10808"
```

常见代理端口：
- v2rayN: 10808
- Clash: 7890
- Shadowsocks: 1080

### 2. 添加本地目录

在 GUI 中：
1. 【运行控制】→ 【添加】
2. 选择视频文件夹

或编辑 `local_dirs.json`：
```json
["F:\\作品"]
```

### 3. 添加模特

在 GUI 中：
1. 【模特管理】→ 【添加模特】
2. 输入名称和 URL

或编辑 `models.json`：
```json
{
  "JULIA": "https://javdb.com/actors/1KBW"
}
```

---

## ▶️ 运行查重

### GUI 方式

1. 【运行控制】标签页
2. 选择模块：`auto`（推荐）
3. 选择抓取工具：`selenium`（推荐）
4. 点击【开始运行】

### 命令行方式

```bash
python core/core.py
```

---

## 📊 查看结果

### 日志文件
```
logs/
├── sync_20260209.log           # 主日志
├── missing_20260209.log        # 缺失视频日志
└── countries/                  # 按国家分类的详细报告
```

### 输出文件
```
output/
├── missing_summary_*.txt       # 缺失视频汇总
├── missing_detail_*.json       # JSON 格式详细数据
└── missing_current.txt         # 当前缺失清单
```

---

## 🔍 测试代理

1. 【代理测试】标签页
2. 输入测试 URL: `https://www.google.com`
3. 点击【测试代理连接】
4. 查看结果

如果失败：
- 确认代理工具已启动
- 检查端口配置
- 尝试不同的代理类型（HTTP/SOCKS5）

---

## 🐛 常见问题快速解决

### ❌ ImportError: No module named 'xxx'

```bash
pip install -r requirements.txt
```

### ❌ ChromeDriver 版本不匹配

程序会自动下载正确版本，只需等待。

如果下载失败：
1. 检查网络连接
2. 配置代理
3. 手动下载放到系统 PATH

### ❌ 代理连接失败

1. 启动代理工具（v2rayN/Clash等）
2. 检查 `config.yaml` 中的端口
3. 在【代理测试】中验证

### ❌ 无法获取在线视频

1. 检查网络连接
2. 启用代理
3. 切换到 Selenium 模式
4. 检查 URL 是否正确

---

## 📦 打包发布

### Windows

```bash
打包脚本.bat
```

### Linux/Mac

```bash
chmod +x build.sh
./build.sh
```

生成的可执行文件在 `dist/` 目录。

---

## 💡 使用技巧

### 1. 加速抓取

- 减少 `max_pages`（只抓取前几页）
- 使用 `requests` 模式（快但可能被拦截）
- 缩小扫描目录范围

### 2. 提高成功率

- 使用 `selenium` 模式
- 启用代理
- 增大超时时间

### 3. 定期运行

创建计划任务，每天/每周自动运行：

Windows:
```batch
schtasks /create /tn "视频查重" /tr "python F:\path\to\core\core.py" /sc daily /st 02:00
```

Linux/Mac:
```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨2点运行）
0 2 * * * cd /path/to/project && python core/core.py
```

---

## 📚 更多文档

- [完整安装指南](INSTALL.md)
- [README](README.md)
- [配置文件说明](config.yaml)

---

## 🆘 获取帮助

- 遇到问题？运行测试脚本检查：`python test_system.py`
- 查看日志文件了解详细错误
- 在 GitHub 提 Issue
- 阅读 INSTALL.md 获取详细说明

---

**祝使用愉快！** 🎉
