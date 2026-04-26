# CRUD Repository 设计文档

日期：2026.04.26

需求澄清文档：`docs/request-clarify/database/rb002-crud-repository.md`

## 核心功能（WHAT）

为 zembra-cli 增加数据库 CRUD Repository 层，封装 notes、fields、tags、note_tags、note_revisions 的基础读写操作。Repository 使用现有 `sqlite3` 连接和 Pydantic 数据模型，不引入 ORM，不实现 CLI。

### 需求背景（WHY）

当前项目已经具备 SQLite schema 初始化和 Pydantic 数据模型，但还没有应用层可复用的数据操作接口。Repository 层用于承接后续 CLI、TUI 或同步服务调用，同时保持共享 schema 仍然是数据结构的唯一来源。

### 需求目标（GOAL）

| 目标 | 说明 |
| --- | --- |
| 提供基础 CRUD | 支持 note、field、tag、note_tag 的常用读写 |
| 保持软删除语义 | 删除 note 时只更新 `deleted_at` |
| 自动维护 revision | 创建 note 和更新 content 时写入 `note_revisions` |
| 自动创建分类对象 | field/tag 不存在时自动创建 |
| 默认过滤删除数据 | note 列表默认不返回软删除记录 |
| 严守范围 | 不新增 CLI 命令 |

### 范围边界

#### In Scope

| 模块 | 改动 |
| --- | --- |
| `zembra_cli.repository` | 新增 Repository 类或函数，封装事务内 CRUD |
| `zembra_cli.models` | 如有必要，补充用于创建/更新输入的 Pydantic 模型 |
| `tests/test_repository.py` | 覆盖 CRUD、自动创建、软删除、revision 写入 |

#### Out of Scope

| 项目 | 原因 |
| --- | --- |
| CLI 命令 | 用户明确禁止越界 |
| note_links CRUD | 不属于本阶段基本操作 |
| attachments CRUD | 不属于本阶段基本操作 |
| ORM 引入 | 当前 sqlite3 足够，ORM 会增加 schema 双重来源风险 |
| 同步冲突处理 | 属于多端同步阶段 |

## 实现流程（HOW）

### 技术决策

推荐继续使用 `sqlite3 + Pydantic v2`。Repository 直接执行 SQL，返回现有 Pydantic record 模型。ID 生成使用 Python 标准库 `uuid.uuid4().hex`，时间戳通过可注入 clock 生成，便于测试固定时间。

### Repository 结构

| 组件 | 职责 |
| --- | --- |
| `ZembraRepository` | 持有 SQLite connection，提供 CRUD 方法 |
| `create_note` | 自动创建 field/tag，插入 note，维护 note_tags，写入初始 revision |
| `get_note` | 按 ID 查询单条 note，默认不返回软删除记录 |
| `list_notes` | 按更新时间或创建时间返回 note 列表，默认过滤软删除 |
| `update_note_content` | 更新 `content`、`updated_at`，写入新 revision，并更新 `current_revision_id` |
| `archive_note` | 写入 `archived_at` |
| `delete_note` | 写入 `deleted_at` |
| `get_or_create_field` | 按 name 查询 field，不存在则插入 |
| `get_or_create_tag` | 按 name 查询 tag，不存在则插入 |
| `add_tag_to_note` | 写入 `note_tags`，重复添加保持幂等 |
| `remove_tag_from_note` | 删除 `note_tags` 关联 |
| `list_note_tags` | 查询指定 note 的 tags |

### 方法设计

| 方法 | 输入 | 输出 | 说明 |
| --- | --- | --- | --- |
| `create_note(content, field_name=None, tag_names=None, device_id=None)` | 正文、可选 field、可选 tags、可选设备 | `NoteRecord` | 创建 note 并写入初始 revision |
| `get_note(note_id, include_deleted=False)` | note ID、是否包含软删除 | `NoteRecord \| None` | 默认过滤软删除 |
| `list_notes(include_deleted=False)` | 是否包含软删除 | `list[NoteRecord]` | 默认过滤软删除 |
| `update_note_content(note_id, content, device_id=None)` | note ID、新正文、可选设备 | `NoteRecord` | 写入 revision 并更新 current revision |
| `archive_note(note_id)` | note ID | `NoteRecord` | 设置 `archived_at` |
| `delete_note(note_id)` | note ID | `NoteRecord` | 设置 `deleted_at` |
| `get_or_create_field(name)` | field 名称 | `FieldRecord` | 不存在时自动插入 |
| `get_or_create_tag(name)` | tag 名称 | `TagRecord` | 不存在时自动插入 |
| `add_tag_to_note(note_id, tag_name)` | note ID、tag 名称 | `NoteTagRecord` | tag 不存在时自动创建 |
| `remove_tag_from_note(note_id, tag_name)` | note ID、tag 名称 | `None` | 移除关联 |
| `list_note_tags(note_id)` | note ID | `list[TagRecord]` | 返回 note 已关联 tags |

### 关键约束

| 约束 | 处理方式 |
| --- | --- |
| 事务一致性 | create/update note 与 revision 写入在同一连接事务中完成 |
| 幂等创建 | field/tag 按唯一 name 查询或插入 |
| 重复 tag 关联 | 使用 `INSERT OR IGNORE` 或等价逻辑 |
| 不存在 note | 更新、归档、删除时抛出明确异常，例如 `RecordNotFoundError` |
| Pydantic 校验 | SQL 读取结果统一转换为 record 模型 |
| 默认查询语义 | `get_note`、`list_notes` 默认排除软删除 |

## 测试用例

### 编译检查

| 用例 | 预期 |
| --- | --- |
| `uv run ruff check .` | 通过 |
| `uv run pytest` | 通过 |

### 回归检查

| 用例 | 预期 |
| --- | --- |
| 创建 note | note 插入成功，自动写入一条 revision |
| 创建 note 带 field/tag | field/tag 不存在时自动创建，并建立 note_tags |
| 更新 content | note content 更新，revision 数量增加，`current_revision_id` 更新 |
| 软删除 note | `deleted_at` 有值，默认列表和查询不返回该 note |
| include_deleted 查询 | 可以返回软删除 note |
| 归档 note | `archived_at` 有值，note 仍可查询 |
| 添加重复 tag | 不产生重复 note_tags |
| 移除 tag | note_tags 关联被删除，tag 记录保留 |
