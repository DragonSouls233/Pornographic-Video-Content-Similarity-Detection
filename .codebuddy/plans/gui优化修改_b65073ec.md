---
name: gui优化修改
overview: 优化GUI界面：1)抓取工具只保留selenium选项 2)配置对话框增加多线程设置 3)运行结果同步显示到结果标签页 4)合并内置浏览器和代理测试标签页
todos:
  - id: fix-scraper-options
    content: 简化抓取工具选项为仅selenium
    status: completed
  - id: add-multithreading-config
    content: 在配置对话框中添加多线程设置UI
    status: completed
  - id: return-results-from-core
    content: 修改core.py的main函数返回results数据
    status: completed
  - id: sync-results-to-gui
    content: 实现运行结果同步到结果显示标签页
    status: completed
    dependencies:
      - return-results-from-core
  - id: merge-browser-proxy-tabs
    content: 合并内置浏览器和代理测试标签页
    status: completed
---

## 问题概述

用户需要对模特查重管理系统的GUI进行4项优化修改：

### 问题1：抓取工具选项过多

运行控制标签页中的抓取工具选择目前有4个选项（selenium, playwright, drissionpage, zendriver），需要简化为只保留selenium一个选项。

### 问题2：配置对话框缺少多线程设置

配置文件config.yaml中已有multithreading配置（enabled和max_workers），但GUI的配置对话框中没有对应的设置界面，需要添加多线程启用/禁用和线程数设置。

### 问题3：结果显示未同步

运行完成后，缺失视频的结果没有显示在"结果显示"标签页中。需要将core模块返回的处理结果（ModelResult列表）传递到GUI并更新结果显示区域的统计信息和缺失视频列表。

### 问题4：标签页合并

"内置浏览器"和"代理测试"两个独立标签页需要合并为一个"浏览器/代理测试"标签页，整合两者的功能。

## 核心功能需求

1. 简化抓取工具选择为单一选项
2. 在配置对话框中添加多线程配置UI
3. 实现运行结果到结果显示标签页的数据传递和展示
4. 合并内置浏览器和代理测试功能到一个标签页

## 技术栈

- Python 3.x
- tkinter (GUI框架)
- 现有项目结构：gui/gui.py (主GUI), gui/browser.py (浏览器模块), core/core.py (核心逻辑)

## 实现方案

### 问题1：抓取工具简化

- 修改gui/gui.py第220行，将scraper_combobox的values从`["selenium", "playwright", "drissionpage", "zendriver"]`改为`["selenium"]`
- 保持现有逻辑不变，仅限制用户选择

### 问题2：多线程配置UI

- 在show_config_dialog()方法的配置对话框中添加新的"性能设置"标签页
- 添加多线程启用复选框（对应multithreading.enabled）
- 添加工作线程数输入框（对应multithreading.max_workers，范围3-10）
- 保存配置时更新config.yaml中的multithreading部分

### 问题3：结果显示同步

- 修改core/core.py的main()函数，在处理完成后返回results列表
- 修改gui/gui.py的run_script()方法，接收main()返回的结果数据
- 通过queue将结果数据传递到主线程
- 在check_queue()中处理"results"消息类型，更新结果显示标签页：
- 更新统计信息（processed, failed, missing数量）
- 清空并重新填充result_tree（缺失视频列表）
- 修改ModelResult数据结构的使用，提取model_name, missing_with_urls等信息

### 问题4：标签页合并

- 移除单独的browser_tab和proxy_test_tab创建
- 创建新的combined_browser_proxy_tab标签页
- 整合init_browser_tab()和init_proxy_test_tab()的功能：
- 保留browser.py中的BrowserTab功能（地址栏、代理配置显示、测试结果区域）
- 整合代理测试功能（测试URL输入、超时设置、测试按钮）
- 删除独立的代理测试标签页初始化方法

## 目录结构

```
f:/Pornographic-Video-Content-Similarity-Detection/
├── gui/
│   ├── gui.py              # [MODIFY] 主GUI文件，修改4个问题点
│   └── browser.py          # [MODIFY] 可能需要调整以支持整合后的标签页
├── core/
│   └── core.py             # [MODIFY] main()函数返回results数据
└── config.yaml             # [已存在] 已有multithreading配置
```

## 关键代码修改点

### gui/gui.py修改内容：

1. 第220行：scraper_combobox values改为["selenium"]
2. show_config_dialog()：添加"性能设置"标签页，包含多线程配置
3. run_script()：接收core.main()返回的结果，通过queue传递
4. check_queue()：添加"results"消息处理，更新result_tree和stats_vars
5. 第58-64行：合并browser_tab和proxy_test_tab为一个标签页
6. 删除init_proxy_test_tab()方法，整合功能到init_browser_tab()

### core/core.py修改内容：

1. main()函数：在处理完成后return results列表（当前已有results变量，只需添加return语句）

### browser.py修改内容（如需要）：

1. 调整BrowserTab类以支持代理测试功能的整合