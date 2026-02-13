# Implementation Plan

- [ ] 1. 设计并实现缓存数据层（SQLite表 + 读写接口）
  - 建立 `dup_cache` 表结构与索引
  - 实现缓存键生成与序列化/反序列化
  - _Requirement: Requirement 1, Requirement 4, Requirement 5_

- [ ] 2. 实现远端轻量探测与本地快照签名
  - 远端签名计算（抓取第一页/ETag/Last-Modified）
  - 本地签名计算（标题集合 hash + 数量 + mtime）
  - _Requirement: Requirement 2, Requirement 4_

- [ ] 3. 集成缓存判定流程到查重主流程
  - 缓存命中/过期判断
  - 远端未变化时走快速补齐判定
  - 远端变化时执行完整查重刷新缓存
  - _Requirement: Requirement 2, Requirement 3_

- [ ] 4. 实现“已补齐”严格判定逻辑
  - 基于缓存缺失集合 + 本地快照
  - 额外校验缺失标题对应链接可用
  - _Requirement: Requirement 3_

- [ ] 5. 增加缓存管理能力
  - 按模特清理缓存/强制刷新
  - 缓存损坏时自动重建
  - _Requirement: Requirement 4, Requirement 5_
