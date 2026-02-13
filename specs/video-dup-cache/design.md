# Technical Solution Design

## Overview

为“模特查重/缺失视频检测”增加一套**SQLite 缓存层**与**轻量远端版本探测**机制，降低重复抓取成本，并在补齐后快速判断“已补齐”。

核心思路：
- 缓存以 **`model_name + module + url`** 为键。
- 远端每次先做轻量探测（例如：抓取第一页并提取可计算签名，或请求 HEAD 获取更新时间/ETag）。
- 本地变化只重算本地快照，结合缓存缺失集和链接可用性判定是否补齐。

## Architecture

```mermaid
flowchart TD
    A[查重入口] --> B[读取缓存(SQLite)]
    B -->|命中| C[远端轻量探测]
    C -->|未变化| D[本地快照重算]
    D --> E[补齐判定/差异输出]
    C -->|变化| F[完整远端抓取]
    F --> G[完整对比]
    G --> H[写入缓存(SQLite)]
    E --> H
    B -->|未命中| F
```

## Data Model (SQLite)

新增缓存表（单独数据库文件或复用现有数据库）：

- **table: `dup_cache`**
  - `id` INTEGER PK
  - `cache_key` TEXT UNIQUE  
    - 由 `model_name + module + url` 规范化组合
  - `model_name` TEXT
  - `module` TEXT
  - `url` TEXT
  - `remote_signature` TEXT  
    - 远端签名（hash/etag/last-modified）
  - `local_signature` TEXT  
    - 本地签名（hash/文件数/最近修改摘要）
  - `online_count` INTEGER
  - `local_count` INTEGER
  - `missing_titles_json` TEXT  
    - JSON数组：缺失标题
  - `missing_with_urls_json` TEXT  
    - JSON数组：[(title, url)]
  - `invalid_links_json` TEXT  
    - JSON数组：无效/缺失链接标题
  - `checked_at` TIMESTAMP
  - `created_at` TIMESTAMP
  - `cache_version` TEXT

## Key Components

1. **CacheKeyBuilder**
   - 统一生成缓存键（对 `model_name/module/url` 进行标准化）
   - 确保同一模特不同 URL/模块互不干扰

2. **RemoteProbe**
   - 每次运行先做“轻量探测”
   - 方案：
     - `requests` 获取第一页 HTML
     - 提取可稳定字段（视频标题集合 hash / 页码总数 / 最后更新时间）
     - 计算 `remote_signature`

3. **LocalSnapshotter**
   - 本地扫描后计算 `local_signature`
   - 组合：`len(local_titles) + hash(sorted(local_titles)) + latest_mtime`

4. **DiffResolver**
   - 使用缓存缺失集合 + 本地快照快速计算 `remaining_missing`
   - 严格规则：若 `remaining_missing` 为空，还需验证缺失标题对应链接可用

5. **CacheWriter (Atomic)**
   - 所有写入使用事务
   - 失败时不影响主流程

## Integration Points

- **核心查重流程**：`core/core.py -> ModelProcessor.process_single_model`
  - 读取缓存
  - 远端轻量探测
  - 决定是否全量抓取
  - 更新缓存

- **缺失/补齐逻辑**：
  - 在生成缺失列表前，先根据缓存判定是否需要完整查重

## Remote Signature Strategy

- 默认：抓取第 1 页 HTML -> 提取标题列表 -> 计算 SHA1
- 可扩展：支持 `ETag / Last-Modified`
- 若失败：回退到完整抓取

## Local Signature Strategy

- 标题集合 hash + 数量 + 最近修改时间
- 支持多目录合并

## Error Handling

- 缓存损坏：自动重建
- 远端探测失败：回退到完整抓取
- 本地目录缺失：标记为 `local_missing`

## Security & Performance

- 使用 SQLite + 索引
- 远端探测只抓取必要页面
- 本地扫描遵循现有的 `local_scan` 配置

## Migration / Compatibility

- 不修改现有输出结构
- 缓存为新增模块，可逐步启用
- 如需切换 JSON 缓存，可提供适配器

