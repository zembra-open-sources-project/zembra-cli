# 最新 Schema 与 Workspace 支持设计文档

日期：2026.06.25

需求澄清文档：`docs/request-clarify/database/rb004-latest-schema-workspace-support.md`

## 核心功能（WHAT）

将共享 schema 更新到远端最新版本，并让 `zembra-cli` 的 direct SQLite 模式支持最新 workspace-scoped schema。CLI 使用 `~/.zembra/config.cli.toml` 中的 workspace 配置确定本地操作所属 workspace；workspace 字段不从全局配置回退。

### 需求背景（WHY）

远端最新 schema 已从单本地库模型演进为 workspace-scoped 数据契约，所有主要业务表都需要 `workspace_id`。当前 CLI 仍按旧 schema 读写，升级 submodule 后会在 `NOT NULL`、外键和唯一约束上失败。为了让本仓库只支持最新 schema，需要同步更新模型、Repository、初始化流程和测试。

### 需求目标（GOAL）

| 目标 | 说明 |
| --- | --- |
| schema 最新 | submodule 指向远端最新 schema |
| workspace 配置明确 | CLI direct 模式从 `config.cli.toml` 获取 workspace ID |
| 不读全局 workspace | workspace 字段不从 `~/.zembra.env` 级联 |
| init 完整初始化 | 创建最新 schema 数据库、workspace 记录和 CLI workspace 配置 |
| Repository workspace 化 | 所有 SQLite 读写限定当前 workspace |
| 模型对齐 | Pydantic record 支持最新字段 |
| 不兼容旧库 | 不写旧 schema 兼容和迁移路径 |

### 范围边界

| 纳入范围 | 不纳入范围 |
| --- | --- |
| `vendor/zembra-schema` 更新到最新远端指针 | 旧 SQLite 数据迁移 |
| `ZembraConfig.workspace_id` 和 `workspace_name` | 从 `.zembra.env` 读取 workspace |
| `zembra-cli init --workspace-id` 和 `--workspace-name` | 多 workspace 切换命令 |
| `workspaces` 表插入和校验 | sync 业务写入 |
| Repository 注入 workspace ID | Supabase/Postgres 后端适配 |
| 根 tag 兼容最新 tag schema | 层级 tag 管理命令 |
| 最新 schema 自动化测试 | 老版本 schema 兼容分支 |

## 实现流程（HOW）

### Schema 指针

将 `vendor/zembra-schema` checkout 到远端最新 `origin/master`。当前远端最新可由 `git -C vendor/zembra-schema describe --tags --always origin/master` 描述为 `0.5.1`，其文档中的统一 schema version 为 `0.5.0`。README 中更新共享 schema 说明，避免继续声称当前固定到 `v0.1.0` 或 `v0.2.0`。

### 配置设计

`config.py` 的级联读取继续用于 `cli.mode`、`cli.http_base_url` 和 `database.path`。workspace 字段使用单独读取规则：只读取 CLI 配置文件。

| 字段 | 配置位置 | 是否全局回退 | 说明 |
| --- | --- | --- | --- |
| `workspace.id` | `~/.zembra/config.cli.toml` | 否 | direct 模式必填 |
| `workspace.name` | `~/.zembra/config.cli.toml` | 否 | 可省略；省略时运行值为 `None`，数据库值为 NULL |

`ZembraConfig` 增加 `workspace_id: Path | str` 不合适，推荐使用 `workspace_id: str | None` 和 `workspace_name: str | None`。`load_cascading_config()` 在读取 CLI 配置文件时额外提取 `[workspace]` 字段，但不会从全局配置合并这些字段。HTTP 模式不需要 workspace ID；direct 模式缺少 `workspace.id` 时抛出配置错误，提示运行 `zembra-cli init`。

### init 设计

`zembra-cli init` 增加两个参数。

| 参数 | 类型 | 默认 | 行为 |
| --- | --- | --- | --- |
| `--workspace-id` | `str | None` | `None` | 未传时生成 UUID 字符串 |
| `--workspace-name` | `str | None` | `None` | 未传时配置中省略 name，数据库写入 NULL |

执行流程：

| 步骤 | 说明 |
| --- | --- |
| 1 | 解析数据库路径和 workspace 参数 |
| 2 | 初始化最新 schema 数据库 |
| 3 | 确保 `~/.zembra/` 存在 |
| 4 | 写入 `[database].path`、`[cli].mode = "direct"` 和 `[workspace].id`；仅在用户传入 `--workspace-name` 时写入 `[workspace].name` |
| 5 | 在 `workspaces` 表插入或复用对应 workspace |
| 6 | 输出数据库路径、配置路径和 workspace ID |

如果数据库中已存在同 ID workspace，`init` 可复用该记录，并在 name 不冲突时更新或保持；为保持最小实现，推荐使用 `INSERT OR IGNORE` 创建 workspace，本轮不做 workspace 重命名逻辑。

### Repository 设计

`ZembraRepository` 构造时接收 `workspace_id`。可以把 workspace ID 放在 `BaseRepository`，让 `FieldTagRepository` 和 `ZembraRepository` 共用。

| 操作 | 最新 schema 适配 |
| --- | --- |
| 创建 field | 写入 `workspace_id`，按 `(workspace_id, name)` 查找 |
| 创建 tag | 写入 `workspace_id`、`parent_tag_id = NULL`、`path = name`、`depth = 0`，按 `(workspace_id, path)` 查找 |
| 创建 note | 写入 `workspace_id`、`last_change_id = NULL`、`conflict_status = "none"` |
| 创建 note revision | 写入 `workspace_id`、`base_revision_id = NULL`、`change_id = NULL` |
| note_tags | 主键和查询都包含 `workspace_id` |
| list/get/random | 所有查询条件包含当前 `workspace_id` |
| field/tag list | 只返回当前 workspace 内记录 |

MCP direct 模式通过合并配置得到最终 direct 配置，再要求 `workspace_id` 存在，并用该 workspace ID 构造 Repository。

### 模型设计

新增或更新 Pydantic models。

| 模型 | 字段调整 |
| --- | --- |
| `WorkspaceRecord` | 新增 `id`、`workspace_name`、`created_at`、`updated_at`、`archived_at`、`deleted_at` |
| `FieldRecord` | 新增 `workspace_id` |
| `TagRecord` | 新增 `workspace_id`、`parent_tag_id`、`path`、`depth` |
| `DeviceRecord` | 新增 `workspace_id`、`sync_enabled`、`last_synced_at` |
| `NoteRecord` | 新增 `workspace_id`、`last_change_id`、`conflict_status` |
| `NoteTagRecord` | 新增 `workspace_id` |
| `NoteLinkRecord` | 新增 `workspace_id` |
| `AttachmentRecord` | 新增 `workspace_id` |
| `NoteRevisionRecord` | 新增 `workspace_id`、`base_revision_id`、`change_id` |

同步表模型本轮可以只覆盖数据库初始化测试，不要求暴露 Repository 操作；如果已有模型测试需要完整表达 schema，可新增 `SyncChangeRecord`、`SyncStateRecord` 和 `SyncConflictRecord`。

## 测试用例

### 编译检查

| 用例 | 预期 |
| --- | --- |
| `uv run ruff check .` | 通过 |
| `uv run pytest` | 通过 |

### 回归检查

| 用例 | 预期 |
| --- | --- |
| schema 初始化 | 创建 `workspaces`、核心业务表和 sync 表 |
| notes 表 | 包含 `workspace_id`、`last_change_id`、`conflict_status` |
| tags 表 | 包含 `parent_tag_id`、`path`、`depth` |
| config 读取 | direct 模式缺少 CLI workspace ID 时报错 |
| config 级联 | `.zembra.env` 中的 workspace 字段不生效 |
| init 默认 workspace | 未传 `--workspace-id` 时写入 UUID |
| init workspace name | 未传 `--workspace-name` 时配置省略 name，数据库写入 NULL |
| repository create note | 写入当前 workspace 并可读回 |
| repository isolation | 不返回其他 workspace 的 field、tag、note |
| root tag | tag 写入 `path=name`、`depth=0`、`parent_tag_id=NULL` |
| CLI add/list/random/run | 在最新 schema 和 workspace 配置下通过 |
| MCP direct | 使用 workspace 配置访问本地数据库 |
