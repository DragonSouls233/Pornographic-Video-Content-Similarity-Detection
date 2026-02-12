---
name: fix-link-validation-and-progress-monitor
overview: 在不改动固定抓取设置的前提下，修复增量缓存导致的链接失效问题，并新增可监控的查重进度与结果校验/报告能力。
design:
  architecture:
    framework: html
  styleKeywords:
    - 结构化
    - 高可读
    - 侧栏布局
    - 对比高亮
  fontSystem:
    fontFamily: 微软雅黑
    heading:
      size: 16px
      weight: 600
    subheading:
      size: 13px
      weight: 500
    body:
      size: 12px
      weight: 400
  colorSystem:
    primary:
      - "#2F6FEB"
      - "#1D4ED8"
    background:
      - "#F5F7FA"
      - "#FFFFFF"
    text:
      - "#1F2937"
      - "#4B5563"
    functional:
      - "#16A34A"
      - "#DC2626"
      - "#F59E0B"
      - "#6B7280"
todos:
  - id: analyze-link-flow
    content: 使用[subagent:code-explorer]梳理链接抓取、缓存、缺失输出的完整链路与可复用点
    status: completed
  - id: fix-cache-url-mapping
    content: 修复增量缓存标题合并时的URL补全与无效链接过滤逻辑
    status: completed
    dependencies:
      - analyze-link-flow
  - id: add-link-validation-report
    content: 新增模特级链接校验与独立报告输出，区分本地对比视频
    status: completed
    dependencies:
      - fix-cache-url-mapping
  - id: ui-progress-sidebar
    content: 在运行控制页实现右侧侧栏三列进度卡片与可折叠日志面板
    status: completed
    dependencies:
      - add-link-validation-report
  - id: result-marking
    content: 结果页新增异常标识与统计概览，确保链接校验可视化
    status: completed
    dependencies:
      - ui-progress-sidebar
---

## User Requirements

- 新增查重进度监控区域：位于右侧侧栏，支持固定三列并行显示多任务进度，显示实时进度条与百分比
- 提供可折叠的详细日志面板，默认展开
- 优化日志系统以准确追踪模特视频链接，支持链接有效性统计、过滤无效链接
- 区分并标记本地对比视频，避免混入在线链接统计
- 为每个模特生成独立的链接报告，并在界面上标注可能异常的对比项

## Product Overview

- 右侧侧栏集中展示查重进度、并行任务状态与日志，提升批量查重监控可见性
- 结果区对比项具备异常标识与链接校验提示，减少无效链接干扰
- 模特级别链接报告可独立查看与追踪，保证统计准确清晰

## Core Features

- 右侧侧栏三列并行进度卡片与总进度条
- 可折叠日志面板与实时日志输出
- 链接有效性统计与无效链接过滤
- 本地对比视频标记与异常对比项高亮
- 模特独立链接报告生成与展示

## Tech Stack Selection

- 语言与运行环境：Python
- UI 框架：Tkinter（现有 GUI）
- 数据与缓存：SQLite、JSON、SmartCache
- 抓取与对比：现有 core 模块（PORN/JAVDB）

## Implementation Approach

- 在不改动“固定抓取设置”的前提下，补齐增量缓存中标题与 URL 的映射，确保链接统计准确
- 在对比结果生成阶段增加链接校验与过滤逻辑，并按模特输出独立报告
- 扩展 GUI 运行控制页的进度区域为右侧侧栏布局，三列并行任务展示与折叠日志
- 对异常结果进行标识，避免界面与日志出现“空链接”噪声

## Implementation Notes (Execution Details)

- 增量缓存仅合并标题导致 URL 空缺，需从 SmartCache 读取 URL 并补全映射
- 保留现有抓取工具固定为 selenium 的设置，不修改该配置点
- 日志输出需区分模特维度，避免多模特混淆
- 结果校验应在生成 missing_with_urls 之前完成，减少无效条目进入 UI

## Architecture Design

- 抓取层：PORN/JAVDB 获取在线标题与链接
- 缓存层：SmartCache 提供标题与 URL 访问
- 对比层：core 计算缺失并执行链接校验
- 表现层：GUI 右侧侧栏展示进度与日志，结果区显示异常标识

## Directory Structure Summary

本次修改聚焦链接统计修复、日志与报告增强、以及 GUI 进度侧栏布局。

```
f:/Pornographic-Video-Content-Similarity-Detection/
├── gui/
│   └── gui.py  # [MODIFY] 右侧侧栏进度区、三列并行展示、可折叠日志、异常标识显示
├── core/
│   ├── core.py  # [MODIFY] 缺失结果生成前的链接校验、缓存URL补全、模特报告入口
│   └── modules/
│       ├── porn/
│       │   └── porn.py  # [MODIFY] 增量缓存标题合并时补齐URL映射
│       ├── javdb/
│       │   └── javdb.py  # [MODIFY] 增量缓存标题合并时补齐URL映射
│       └── common/
│           ├── smart_cache.py  # [MODIFY] 提供缓存URL读取能力被复用
│           └── common.py  # [MODIFY] 增强链接日志与模特报告生成
```

## Design Style

采用桌面应用可读性优先的结构化布局：主工作区保持现有结果与控制区，右侧新增固定侧栏承载进度与日志。侧栏顶部显示总进度条与百分比，中部三列并行任务卡片，底部为默认展开的日志面板，支持折叠。异常结果在结果表中用颜色与图标标识，提示链接校验异常与本地对比视频状态。

## Pages

- 运行控制页：新增右侧侧栏进度区与日志面板
- 结果显示页：异常标识与本地对比标记

## Block Layout (运行控制页)

1. 顶部操作区：运行/停止按钮与配置项保持现有布局，右侧留出侧栏宽度。
2. 右侧侧栏头部：总进度条+百分比+状态文本，居中对齐。
3. 右侧侧栏主体：固定三列任务卡片，卡片包含模特名、进度条、百分比、状态。
4. 右侧侧栏日志：默认展开的日志面板，标题栏含折叠按钮与清空按钮。

## Block Layout (结果显示页)

1. 结果表格：新增异常标识列与本地对比标记列。
2. 统计区：显示有效链接数量与过滤数量概览。
3. 详情提示：选中项显示校验结果与来源类型。
4. 操作区：导出模特链接报告入口。

## Agent Extensions

### SubAgent

- **code-explorer**
- Purpose: 深度梳理链接抓取、缓存与结果输出链路，定位可复用模式与变更边界
- Expected outcome: 输出与实现一致的依赖关系与修改路径，降低误改风险