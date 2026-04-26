# CRUD Repository 需求澄清

日期：2026.04.26

## 需求结论

围绕数据库基础设施补充增删改查基本操作。本阶段只实现 Python Repository 层和自动化测试，不实现 CLI 命令。

## 已确认规则

| 问题 | 结论 |
| --- | --- |
| 删除语义 | note 删除采用软删除，只写入 `deleted_at` |
| revision 语义 | 创建 note 和更新 note content 时自动写入 `note_revisions` |
| field/tag 创建 | field 和 tag 不存在时自动创建 |
| note 列表过滤 | 默认过滤 `deleted_at IS NOT NULL` 的 note |
| CLI 范围 | CLI 非本需求范围，禁止实现 CLI 命令 |

## 本阶段范围

| 对象 | 操作 |
| --- | --- |
| notes | 创建、按 ID 查询、列表查询、更新 content、归档、软删除 |
| fields | 按名称获取或创建、按名称查询、列表查询 |
| tags | 按名称获取或创建、按名称查询、列表查询 |
| note_tags | 添加 tag、移除 tag、查询 note 的 tags |
| note_revisions | 创建 note 和更新 content 时自动写入完整正文快照 |

## 暂不包含

- CLI 命令入口
- TUI/API 接入
- note_links CRUD
- attachments CRUD
- 多端同步、冲突解决
- schema migration 版本管理
