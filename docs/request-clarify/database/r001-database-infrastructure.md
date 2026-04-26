# 数据库基础设施需求澄清

日期：2026.04.26

## 需求结论

初始化 zembra-cli 的数据库基础设施，基于 `vendor/zembra-schema` 中的共享 schema 建立本仓库的数据模型和 SQLite 初始化能力。

## 范围

| 项目 | 说明 |
| --- | --- |
| 共享 schema 来源 | `vendor/zembra-schema`，当前固定到 `v0.1.0` |
| 数据模型 | 尽可能使用 Pydantic v2 表达表结构和基础约束 |
| 数据库引擎 | 第一阶段使用 Python 标准库 `sqlite3` |
| 初始化能力 | 读取共享 schema 的 SQLite DDL 并创建数据库表 |
| 暂不包含 | CRUD Repository、同步协议、冲突解决、CLI 数据命令 |

## 技术选择

推荐使用 `sqlite3 + Pydantic v2`。`sqlite3` 保持轻量，直接执行共享 schema 的 migration；Pydantic 负责跨层数据校验和类型表达。第一阶段不引入 ORM，避免 ORM 模型成为新的 schema 来源。
