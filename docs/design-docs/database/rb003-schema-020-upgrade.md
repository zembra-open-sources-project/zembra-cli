# Schema 0.2.0 升级设计文档

日期：2026.04.27

需求澄清文档：`docs/request-clarify/database/rb003-schema-020-upgrade.md`

## 核心功能

将共享 schema 升级到 `v0.2.0`，让本仓库的数据模型和写入逻辑支持 `notes.role` 字段。

## 设计要点

| 项目 | 设计 |
| --- | --- |
| schema 来源 | 继续以 `vendor/zembra-schema` submodule 为唯一数据表契约来源 |
| 新增字段 | `notes.role TEXT NOT NULL DEFAULT 'Human' CHECK (role IN ('Human', 'Agent'))` |
| 模型表达 | `NoteRecord.role` 使用固定枚举值，默认 `Human` |
| 写入策略 | `create_note()` 增加 `role` 参数，默认写入 `Human` |
| 兼容策略 | 封闭开发场景下只做正向升级，不新增旧库自动迁移 |

## 预期改动范围

| 文件 | 改动 |
| --- | --- |
| `vendor/zembra-schema` | submodule 指针更新到 `v0.2.0` |
| `src/zembra_cli/models.py` | `NoteRecord` 增加 `role` 字段 |
| `src/zembra_cli/repository/notes.py` | `create_note()` 写入 role |
| `tests/test_db.py` | 验证 role 列和 SQLite 约束 |
| `tests/test_models.py` | 验证 Pydantic role 枚举 |
| `tests/test_repository.py` | 验证 Repository 默认和 Agent role 写入 |
| `README.md` | 更新共享 schema 固定版本说明 |

## 验证方式

| 命令 | 预期 |
| --- | --- |
| `uv run pytest` | 全量测试通过 |
| `uv run ruff check .` | 静态检查通过 |
