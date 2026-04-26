# 数据库基础设施设计

日期：2026.04.26

需求澄清文档：`docs/request-clarify/database/r001-database-infrastructure.md`

## 设计目标

为 zembra-cli 建立轻量、可测试、可演进的数据基础设施。共享数据表契约继续由 `vendor/zembra-schema` 维护，本仓库只消费该契约。

## 模块设计

| 模块 | 职责 |
| --- | --- |
| `zembra_cli.models` | 定义 Pydantic 数据模型，对应 notes、fields、tags、note_tags、note_links、attachments、note_revisions、devices |
| `zembra_cli.db` | 提供 SQLite 连接、外键启用、schema 初始化和表存在性检查 |
| `tests/test_models.py` | 验证 Pydantic 模型基础约束 |
| `tests/test_db.py` | 验证数据库初始化能创建共享 schema 中的核心表 |

## 关键约束

| 约束 | 设计 |
| --- | --- |
| schema 单一来源 | SQLite DDL 从 `vendor/zembra-schema/sqlite/001_initial_schema.sql` 读取 |
| 时间戳 | 使用非负 Unix timestamp，Pydantic 中统一校验 |
| 字符串 ID | 使用非空字符串约束 |
| 可选字段 | 按共享 schema 的 nullable 语义表达 |
| 数据库连接 | 每次连接启用 `PRAGMA foreign_keys = ON` |

## 后续演进

后续可以在该基础上增加 Repository 层、迁移版本表和 CLI 数据命令。若 schema repo 发布新的 tag，本仓库先升级 submodule 指针，再同步调整模型和测试。
