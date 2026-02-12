---
name: fix-model-delete-no-response
overview: 修复打包EXE中“删除模特无反应”的问题，确保前端点击、删除逻辑与数据库/JSON同步稳定可用，并补充必要的打包与日志验证。
todos:
  - id: fix-delete-entry
    content: 修复删除入口的选中值解包与异常捕获，确保无反应问题可见化
    status: pending
  - id: unify-delete-paths
    content: 统一删除流程的数据库与JSON路径解析，保证EXE环境可定位文件
    status: pending
    dependencies:
      - fix-delete-entry
  - id: harden-delete-optimizer
    content: 增强删除优化器的存在性检查与容错逻辑，避免静默失败
    status: pending
    dependencies:
      - unify-delete-paths
  - id: verify-delete-feedback
    content: 完善删除成功与失败的界面提示与日志记录，确保结果可感知
    status: pending
    dependencies:
      - harden-delete-optimizer
---

## User Requirements

- 点击“删除模特”后必须有明确的交互反馈，删除动作能真实生效
- 删除流程要稳定可靠，失败时能看到可理解的错误提示
- 保留现有模特管理的核心功能与数据一致性

## Product Overview

- 模特管理删除流程提供清晰的确认、执行与结果反馈
- 删除成功后列表立即刷新，数据从内存与持久化存储同步移除
- 删除失败时提示原因并避免“无反应”的静默失败

## Core Features

- 删除入口与选择校验
- 删除执行与存储同步
- 明确的成功/失败提示

## Tech Stack Selection

- 现有技术栈沿用：Python + Tkinter GUI、SQLite、JSON 本地存储

## Implementation Approach

- 修正 GUI 删除入口的数据解包与异常边界，确保任何异常都会显示弹窗提示
- 统一删除流程使用正确的配置路径，保证打包 EXE 环境下能定位数据库与 JSON
- 强化删除优化器的存在性检查与容错，避免“无反应”与隐式失败
- 收敛为单一稳定删除链路：GUI 触发 -> 删除优化器 -> 数据库/JSON -> 列表刷新

## Implementation Notes (Execution Details)

- 关键修复点：Treeview 返回值为 3 列，删除逻辑必须按实际长度解包
- 删除确认与执行全部置于 try/except 内，任何异常都通过 messagebox 与日志反馈
- db/json 路径使用 get_config_path 统一解析，避免 EXE 工作目录差异导致删除失败
- Tkinter messagebox 不支持 detail 参数，避免使用不兼容参数导致无响应

## Architecture Design

- GUI 层负责交互确认与结果展示
- 删除优化器负责数据库/JSON 删除与清理
- 数据库层负责最终持久化一致性

## Directory Structure Summary

本次修改聚焦删除流程的稳定性与 EXE 环境下的路径一致性。

```
f:/Pornographic-Video-Content-Similarity-Detection/
├── gui/
│   ├── gui.py                 # [MODIFY] 修复删除按钮入口、Treeview 值解包、异常反馈与路径解析
│   └── delete_optimizer.py    # [MODIFY] 强化存在性校验与异常容错，保证删除流程可见可追踪
```