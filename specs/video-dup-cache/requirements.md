# Requirements Document

## Introduction

本需求用于当前“模特查重/缺失视频检测”流程：在完成一次查重后，将查重过程所需的关键数据与结果进行缓存；后续运行时优先读取缓存，避免重复抓取/对比。

核心目标：
- 第一次查重后缓存“在线列表/本地列表/缺失列表/版本标识”。
- 下次运行尽量不重新抓取在线数据，除非缓存过期或检测到版本变化。
- 当用户下载补齐缺失视频后，再次运行时快速判断“是否已补齐”，不必重新做完整查重展示。

## Definitions

- **Model**：模特条目（`model_name` + `module` + `url`）。
- **Local Snapshot**：本地扫描得到的“标题集合/数量/指纹”。
- **Remote Snapshot**：在线抓取得到的“标题集合/数量/指纹”。
- **Diff Result**：对比结果（缺失标题列表、缺失链接列表、无效链接列表、统计信息）。
- **Cache Entry**：某一模特在某一次查重时生成的缓存记录（存储于 SQLite）。
- **Cache Key**：`model_name + module + url`。


## Requirements

### Requirement 1 - 首次查重生成并持久化缓存

**User Story:** 作为使用者，我希望首次查重完成后系统自动把查重数据缓存，下次运行不用再重复获取。

#### Acceptance Criteria

1. When 某模特第一次完成查重, the 系统 shall 将本地快照、本地对比结果、远端快照与对比结果写入缓存。
2. When 写入缓存成功, the 系统 shall 记录该缓存的 `created_at`、`checked_at`、`cache_version`。
3. When 缓存写入失败, the 系统 shall 继续输出查重结果但提示缓存不可用。

### Requirement 2 - 后续运行优先使用缓存并判断是否需要重新查重

**User Story:** 作为使用者，我希望后续运行时优先使用缓存，只有在必要时才重新抓取和对比。

#### Acceptance Criteria

1. While 缓存命中且未过期, when 再次查重同一模特, the 系统 shall 优先读取缓存的远端快照与对比结果。
2. While 缓存命中, when 本地目录发生变化（例如新增文件/下载补齐）, the 系统 shall 仅重新计算本地快照，并与缓存中的“缺失标题集合”快速判定补齐状态。
3. While 缓存命中, when 需要验证远端是否变化, the 系统 shall 每次先轻量探测远端版本标识（例如远端页面/列表签名或抓取页的ETag/最后更新时间），若未变化则不进行完整远端抓取。
4. When 缓存过期或远端版本变化, the 系统 shall 执行完整查重并刷新缓存。


### Requirement 3 - 补齐后快速判定并减少重复展示

**User Story:** 作为使用者，当我下载补齐缺失视频后，我希望系统下次运行能快速判断是否已补齐，不需要重复展示同样的缺失结果。

#### Acceptance Criteria

1. While 缓存中存在上一轮缺失集合, when 再次查重, the 系统 shall 计算 `remaining_missing = cached_missing - current_local_snapshot`。
2. When `remaining_missing` 为空, the 系统 shall 将该模特状态标记为“已补齐”，并可选择不再生成/展示缺失明细（仅输出摘要）。
3. When `remaining_missing` 非空, the 系统 shall 仅输出仍缺失的条目，并更新缓存。
4. While 判定“已补齐”, when 校验缺失标题的链接, the 系统 shall 要求对应链接可用（更严格）。


### Requirement 4 - 缓存一致性与版本状态记录

**User Story:** 作为使用者，我希望缓存能准确反映版本状态，并能高效识别本地/远端变化。

#### Acceptance Criteria

1. When 生成本地快照, the 系统 shall 计算本地指纹（例如：标题集合哈希 + 文件数 + 最后修改时间摘要）。
2. When 生成远端快照, the 系统 shall 计算远端指纹（例如：标题集合哈希 + 在线数量 + 抓取时间）。
3. When 本地指纹与缓存不一致, the 系统 shall 标记 `local_changed=true`。
4. When 远端指纹与缓存不一致, the 系统 shall 标记 `remote_changed=true`。
5. When 缓存损坏或版本不兼容, the 系统 shall 自动重建缓存且不影响主流程。

### Requirement 5 - 性能

**User Story:** 作为使用者，我希望在大量模特下运行依然高效。

#### Acceptance Criteria

1. When 多模特批量查重, the 系统 shall 优先复用缓存结果，减少远端抓取次数。
2. When 写入缓存, the 系统 shall 采用原子写入策略（事务或临时文件替换）。
3. The 系统 shall 支持按模特粒度的缓存清理与强制刷新。

## Out of Scope

- 自动下载补齐视频（本需求只负责判定与减少重复查重；下载仍由现有下载模块负责）。
- 分布式缓存/跨机器同步缓存。
