---
name: pronhub-downloader-module
overview: 新增PRONHUB下载模块并在GUI中支持勾选缺失视频下载，同时提供URL直连下载入口，使用yt-dlp获取最高分辨率并支持会员登录。
todos:
  - id: verify-integration-points
    content: 使用[subagent:code-explorer]复核GUI结果与核心字段对接位置
    status: completed
  - id: add-downloader-module
    content: 新增core/modules/pronhub/downloader.py并实现最高分辨率下载
    status: completed
    dependencies:
      - verify-integration-points
  - id: extend-core-result
    content: 修改core/core.py补充模特本地完整路径到结果数据
    status: in_progress
    dependencies:
      - verify-integration-points
  - id: update-gui-download
    content: 修改gui/gui.py添加下载按钮与选中项下载流程
    status: pending
    dependencies:
      - add-downloader-module
      - extend-core-result
  - id: update-config-deps
    content: 更新config.yaml与requirements.txt以支持Cookie和yt-dlp
    status: pending
    dependencies:
      - add-downloader-module
---

## User Requirements

- 新增一个下载模块并接入PRONHUB模块体系
- GUI新增“下载缺失视频”按钮，支持用户选择条目下载
- 支持传入任意PRONHUB视频URL进行下载
- 自动选择最高分辨率并下载
- 文件保存到模特目录，命名规则与现有下载脚本一致
- 支持会员内容下载（需要登录/凭证）

## Product Overview

在现有模特查重系统内新增可下载缺失视频的能力，并提供独立URL下载入口，保持现有操作流程与结果展示习惯。

## Core Features

- 选中缺失条目后执行下载并记录进度
- 输入PRONHUB视频链接即可下载
- 自动选择最高分辨率并生成规范文件名

## Tech Stack Selection

- 语言与运行环境：Python（延续现有项目）
- GUI框架：Tkinter（复用现有GUI结构）
- 下载解析：yt-dlp（最高分辨率与m3u8处理）
- 配置与日志：复用现有config.yaml与日志体系

## Implementation Approach

采用新增下载模块方式，封装“URL解析 + 文件命名 + 保存路径 + 下载执行”的完整流程；GUI按钮触发下载时从结果列表提取选中条目，结合核心结果中保存的本地路径进行落盘。通过yt-dlp实现最高分辨率选择与会员内容下载，并用配置中的代理与Cookie参数确保可访问性。相比自行解析页面，yt-dlp更稳定但需要新增依赖，换取更高成功率与可维护性。

## Implementation Notes (Execution Details)

- 复用common.clean_filename进行标题清洗，新增命名函数复刻下载脚本的“标题+ID+可选模特”组合格式
- 使用load_config读取代理、输出目录和Cookie配置；优先使用network.proxy设置
- 下载在后台线程中执行，避免GUI卡顿；将状态与错误写入现有日志/GUI日志区
- 对已存在文件进行跳过或覆盖处理，遵循配置策略以避免重复下载
- 会员下载使用Cookie文件/字符串配置，不在日志中输出敏感信息

## Architecture Design

- GUI层：结果列表选中项 → 触发下载任务 → 更新状态与日志
- 业务层：新增downloader模块负责URL解析、命名、下载执行
- 配置层：从config.yaml读取代理与Cookie等下载参数
- 文件层：写入到模特目录结构

## Directory Structure Summary

本次实现新增下载模块并扩展GUI/核心结果字段，保证下载保存到正确的本地模特目录。
project-root/
├── core/
│   └── modules/
│       └── pronhub/
│           ├── downloader.py  # [NEW] 下载实现模块。封装URL解析、最高分辨率选择、命名与文件写入流程，支持Cookie与代理配置。
│           └── **init**.py    # [MODIFY] 导出下载接口（如需在其他模块直接调用）。
├── core/
│   └── core.py                # [MODIFY] 扩展ModelResult，补充模特本地完整路径以支持GUI保存目标。
├── gui/
│   └── gui.py                 # [MODIFY] 结果页新增“下载缺失视频”按钮，支持选中行下载与后台线程执行。
├── config.yaml                # [MODIFY] 新增下载相关配置（Cookie/下载目录策略等）。
└── requirements.txt           # [MODIFY] 增加yt-dlp依赖。

## Agent Extensions

- **code-explorer**
- Purpose: 在实现前再次核对GUI结果列表与核心结果字段的对接点
- Expected outcome: 明确需要新增/调整的字段与调用链，避免遗漏保存路径与URL来源