# 最新 Schema 与 Workspace 支持实现计划

> **给 Claude：** 必需工作流：使用 superpowers:executing-plans 逐任务实现此计划。

**目标：** 更新共享 schema 到远端最新版本，并让 `zembra-cli` direct 模式只支持最新 workspace-scoped schema。

**需求澄清文档：** `docs/request-clarify/database/rb004-latest-schema-workspace-support.md`

**相关设计文档：** `docs/design-docs/database/rb004-latest-schema-workspace-support.md`

**架构：** schema submodule 是数据契约唯一来源；配置层负责从 `config.cli.toml` 读取 CLI 专属 workspace 字段；Repository 持有当前 workspace ID，所有 SQLite 读写都带 workspace 过滤；CLI 和 MCP 只通过配置构造 workspace-scoped Repository。

**技术栈：** Python 3.12、Pydantic、SQLite、Typer、Rich、pytest、ruff、uv、Git submodule。

**范围 / 非范围：** 本计划覆盖最新 schema submodule、CLI workspace 配置、init workspace 创建、模型更新、Repository workspace 化、CLI/MCP 回归和文档更新；不覆盖旧 schema 迁移、多 workspace 切换命令、sync 业务写入、Supabase/Postgres 后端适配和层级 tag 管理命令。

---

## Stage #1: Schema 指针与数据库初始化

### 任务 #1: 更新 schema submodule 到远端最新

**Status:** Finished

**Files:** Modify `vendor/zembra-schema`; Modify `README.md`; Modify `docs/exec-plans/active/database/rb004-latest-schema-workspace-support.md`

功能：将共享 schema submodule 指向远端最新提交。

实现说明：运行 `git -C vendor/zembra-schema checkout origin/master`，记录 `git -C vendor/zembra-schema describe --tags --always HEAD` 和 submodule commit。README 更新共享 schema 当前版本说明。

预期验证结果：`git submodule status` 显示新指针，schema DDL 包含 `workspaces` 和 sync 表。

### 任务 #2: 更新数据库核心表和初始化测试

**Status:** Finished

**Files:** Modify `src/zembra_cli/database/core.py`; Modify `tests/test_db.py`

功能：让数据库初始化和完整性检查识别最新 schema。

实现说明：更新 `CORE_TABLES`，加入 `workspaces`、`sync_changes`、`sync_state`、`sync_conflicts`。测试验证 `notes.workspace_id`、`notes.conflict_status`、`tags.path`、`tags.depth` 和 sync 表存在。

预期验证结果：`uv run pytest tests/test_db.py -q` 通过。

## Stage #2: 配置层 workspace 字段

### 任务 #3: 配置模型新增 CLI-only workspace

**Status:** Finished

**Files:** Modify `src/zembra_cli/config.py`; Modify `tests/test_config.py`

功能：从 `config.cli.toml` 读取 `[workspace].id` 和 `[workspace].name`，且不从 `.zembra.env` 回退。

实现说明：`ZembraConfig` 增加 `workspace_id: str | None` 和 `workspace_name: str | None`。`load_cascading_config()` 在读取 CLI 配置时读取 workspace 字段，direct 模式缺少 `workspace.id` 报错。测试覆盖 `.zembra.env` 有 workspace 但 CLI 配置没有 workspace 时仍报错。

预期验证结果：配置测试证明 workspace 是 CLI-only 字段。

### 任务 #4: init 写入 workspace 配置和数据库记录

**Status:** Finished

**Files:** Modify `src/zembra_cli/cli.py`; Modify `src/zembra_cli/config.py`; Modify `tests/test_cli.py`

功能：`zembra-cli init` 创建 workspace 配置和 `workspaces` 记录。

实现说明：`init` 新增 `--workspace-id` 和 `--workspace-name`。未传 workspace ID 时用 `uuid.uuid4()` 生成字符串；未传 workspace name 时配置中省略 `workspace.name`，数据库 `workspace_name` 为 NULL。写入配置时更新 `[workspace]` section。

预期验证结果：init 后 `config.cli.toml` 含 UUID workspace ID 且未写入默认 name，数据库 `workspaces` 有同 ID 记录且 `workspace_name` 为 NULL。

## Stage #3: 最新 schema 模型与 Repository

### 任务 #5: 更新 Pydantic schema models

**Status:** Finished

**Files:** Modify `src/zembra_cli/models.py`; Modify `tests/test_models.py`

功能：让 Pydantic record 模型匹配最新 schema 字段。

实现说明：新增 `WorkspaceRecord`，给现有业务模型补 `workspace_id` 等最新字段。`TagRecord` 支持根 tag 字段，`NoteRecord` 支持 `last_change_id` 和 `conflict_status`。必要时新增 sync 表模型。

预期验证结果：模型测试覆盖 workspace、note、tag 和 revision 最新字段，未知字段仍被拒绝。

### 任务 #6: Repository 注入 workspace 并更新 SQL

**Status:** Finished

**Files:** Modify `src/zembra_cli/repository/base.py`; Modify `src/zembra_cli/repository/field_tag.py`; Modify `src/zembra_cli/repository/notes.py`; Modify `tests/test_repository.py`

功能：所有 direct Repository 操作限定当前 workspace。

实现说明：Repository 构造函数接收 `workspace_id`。field/tag 的 get-or-create 和 list 查询都按 workspace 过滤；note 创建、revision 创建、note_tags 插入都写入 workspace；get/list/random/resolve 都限定 workspace。根 tag 写入 `parent_tag_id = NULL`、`path = name`、`depth = 0`。

预期验证结果：Repository 测试能创建 note，能隔离其他 workspace 数据，根 tag 字段正确。

## Stage #4: CLI、MCP 和 HTTP 边界更新

### 任务 #7: CLI direct 和 MCP 使用 workspace-scoped Repository

**Status:** Finished

**Files:** Modify `src/zembra_cli/cli.py`; Modify `src/zembra_cli/mcp_server.py`; Modify `tests/test_cli.py`; Modify `tests/test_mcp_server.py`

功能：CLI direct 模式和 MCP direct 模式通过配置 workspace ID 构造 Repository。

实现说明：`open_cli_repository()` direct 分支要求 `config.workspace_id` 存在。HTTP 模式不要求 workspace ID。MCP direct 分支同样要求 workspace ID。测试更新 helper，让 direct 配置都写入 `[workspace].id`。

预期验证结果：CLI add/list/random/run 和 MCP 工具在最新 schema 下通过；缺少 workspace ID 时报错。

### 任务 #8: HTTP 模式模型适配

**Status:** Finished

**Files:** Modify `src/zembra_cli/http_client.py`; Modify `tests/test_http_client.py`; Modify `tests/test_cli.py`

功能：让 HTTP 返回解析适配最新模型字段。

实现说明：更新测试 payload，包含 `workspace_id`、tag path/depth 等必填字段。HTTP 模式不从本地 CLI workspace 配置补字段，只按后端返回结构解析。

预期验证结果：HTTP client 和 CLI HTTP 模式测试通过。

## Stage #5: 文档、验证和提交

### 任务 #9: 更新 README 和计划状态

**Status:** Finished

**Files:** Modify `README.md`; Modify `docs/exec-plans/active/database/rb004-latest-schema-workspace-support.md`

功能：更新用户文档和执行计划状态。

实现说明：README 说明最新 schema、workspace 配置和 init 参数。执行计划按实际完成状态更新。

预期验证结果：README 不再描述旧 schema 固定版本，计划验证记录完整。

### 任务 #10: 运行全量验证并提交

**Status:** Finished

**Files:** Verify full repository

功能：完成格式、定向测试和全量测试，并按仓库规则提交。

实现说明：运行 `uv run ruff check .`，运行 `uv run pytest tests/test_db.py tests/test_config.py tests/test_models.py tests/test_repository.py tests/test_cli.py tests/test_http_client.py tests/test_mcp_server.py -q`，最终运行 `uv run pytest -q`。通过后 stage 并提交。

预期验证结果：ruff 和 pytest 全部通过，提交包含 schema 指针、代码、测试和文档。

## 提交计划

| 阶段 | 提交点 | Commit message |
| --- | --- | --- |
| Stage #1-2 | schema 指针、数据库初始化和配置 workspace 完成后 | `feat: add workspace config for latest schema` |
| Stage #3-4 | Repository、CLI、MCP 和 HTTP 适配完成后 | `feat: support workspace-scoped schema` |
| Stage #5 | 文档、验证和计划回写完成后 | `docs: document latest schema support` |

## 验证记录

2026.06.25：已运行 `uv run ruff check .`，检查通过。

2026.06.25：已运行 `uv run pytest tests/test_db.py tests/test_config.py tests/test_models.py tests/test_repository.py tests/test_cli.py tests/test_http_client.py tests/test_mcp_server.py -q`，127 个测试通过。

2026.06.25：已运行 `uv run pytest -q`，143 个测试通过。
