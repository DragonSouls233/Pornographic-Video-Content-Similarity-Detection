---
name: fix-gui-progress-log-visibility
overview: 检查查重系统运行中的进度条与日志更新链路，定位无进度或无日志的原因，并补齐可视化反馈与启动失败提示的修复方案。
todos:
  - id: scan-path-validation
    content: 使用[subagent:code-explorer]检索目录校验与路径处理逻辑的调用链
    status: completed
  - id: fix-run-script-scope
    content: 修复run_script中的路径校验作用域问题并统一目录检查入口
    status: completed
    dependencies:
      - scan-path-validation
  - id: add-permission-checks
    content: 增加目录存在性与读写权限检查并输出明确错误提示
    status: completed
    dependencies:
      - fix-run-script-scope
  - id: update-dir-status-ui
    content: 强化目录列表状态刷新与日志提示，确保错误可视化
    status: completed
    dependencies:
      - add-permission-checks
  - id: verify-workflow
    content: 验证配置读取、目录校验与运行流程的一致性
    status: completed
    dependencies:
      - update-dir-status-ui
---

## User Requirements

- 分析当前“目录错误”的可能原因，覆盖路径设置、目录权限、目录存在性等常见问题
- 给出适用于 Windows 环境的具体排查步骤与解决方案
- 提供完整修复方案，确保目录配置与运行流程可稳定工作
- 运行中能清晰展示错误原因与修复建议，避免误判为目录问题

## Product Overview

- 在现有 GUI 查重流程中补强目录校验、错误定位与提示逻辑，使用户能快速定位路径或权限问题，并保证运行流程可继续或安全终止

## Core Features

- 目录存在性、读写权限与路径合法性检查
- 配置读取与目录列表状态一致性校验
- 运行错误的详细提示与修复建议展示

## Tech Stack Selection

- 语言：Python（现有项目）
- GUI：Tkinter（现有项目）
- 文件/路径：os、pathlib（现有标准库）

## Implementation Approach

- 基于现有 `gui/gui.py` 的目录管理与运行入口，定位目录检查逻辑并加固异常处理。修复 `run_script` 中路径检查触发的作用域问题，统一目录校验流程；补充权限与路径合法性检测，输出更具体的错误提示，避免误报为“目录错误”。

### Key Decisions & Trade-offs

- 复用现有 `load_config / save_config` 与目录列表管理逻辑，避免引入新配置格式。
- 在 GUI 层进行路径与权限验证，保证用户可直接看到问题，不依赖核心模块输出。
- 增加校验会带来少量 I/O 开销，但只在启动/更新目录时执行，影响可忽略。

## Implementation Notes (Execution Details)

- 避免函数内部重复 `import os` 造成局部变量遮蔽；确保 `os.path.exists` 在运行前可用。
- 对目录执行 `os.path.exists` 与 `os.access(dir, os.R_OK | os.W_OK)` 检测；对网络盘/移动盘加入异常捕获与提示。
- 目录字符串进行 `strip()` 与规范化处理（如 `os.path.normpath`），避免空格或非法字符导致误判。
- 运行前在 GUI 日志区输出“目录校验结果”，并在失败时阻止运行并提示具体原因。

## Architecture Design

- GUI 运行入口 `run_script`：读取配置 → 校验目录 → 运行核心模块
- 目录管理模块：添加/删除/刷新 → 写入 `config.yaml` → 目录状态展示

## Directory Structure

project-root/
├── gui/
│   └── gui.py  # [MODIFY] 修复目录校验触发的作用域问题；新增目录权限/路径合法性检查与更明确的错误提示。

## Agent Extensions

### SubAgent

- **code-explorer**
- Purpose: 在多文件中检索目录校验与路径处理相关逻辑，确认无重复导入/遮蔽问题
- Expected outcome: 明确所有路径校验与运行入口的调用链，避免遗漏导致的误报或未覆盖场景