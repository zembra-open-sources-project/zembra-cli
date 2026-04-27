# Init 命令开发计划

日期：2026.04.27

## Related Design Doc

`docs/design-docs/cli/rc006-init-command.md`

需求澄清文档：`docs/request-clarify/cli/rc006-init-command.md`

## Stage #1: database 子包迁移

### Task #1: 建立 database 子包并迁移现有 db 能力

**Status:** Finished

**Files:** Create `src/zembra_cli/database/__init__.py`; Create `src/zembra_cli/database/core.py`; Delete `src/zembra_cli/db.py`; Modify `src/zembra_cli/cli.py`; Modify `tests/test_db.py`; Modify `tests/test_cli.py`; Modify `tests/test_repository.py`

**Function:** 将现有顶层 `db.py` 迁移到 `database` 子包，避免数据库能力继续堆在单个顶层文件里。

**Implementation Notes:** `core.py` 承接现有 `connect_database()`、`database_connection()`、`initialize_database()`、`missing_core_tables()` 等能力；`database/__init__.py` 导出公共 API；调用方统一改为 `from zembra_cli.database import ...`。迁移后删除顶层 `src/zembra_cli/db.py`，避免两个数据库入口并存。

**Expected Verification Result:** 迁移后现有数据库、CLI、Repository 测试继续通过，导入路径统一到 `zembra_cli.database`。

## Stage #2: 数据库安全初始化 helper

### Task #2: 新增初始化结果和错误类型

**Status:** Finished

**Files:** Modify `src/zembra_cli/database/core.py`; Modify `src/zembra_cli/database/__init__.py`; Modify `tests/test_db.py`

**Function:** 表达数据库初始化结果和不完整 schema 错误，供 CLI 输出清晰状态。

**Implementation Notes:** 在 database 子包内新增 `DatabaseInitResult`，包含 `database_path` 和 `status`。新增 `DatabaseInitializationError` 基类和 `DatabaseSchemaIncompleteError`，错误消息包含数据库路径和缺失核心表。通过 `database/__init__.py` 导出这些类型。

**Expected Verification Result:** 单元测试可断言错误类型、错误消息和结果状态。

### Task #3: 实现数据库文件安全初始化

**Status:** Finished

**Files:** Modify `src/zembra_cli/database/core.py`; Modify `src/zembra_cli/database/__init__.py`; Modify `tests/test_db.py`

**Function:** 新增 `initialize_database_file(database_path)`，自动创建父目录，安全创建或跳过数据库 schema 初始化。

**Implementation Notes:** 数据库文件不存在时创建并执行 `initialize_database()`；文件存在时只检查 `missing_core_tables()`；schema 完整返回 `skipped`；schema 不完整抛出错误，不覆盖已有文件。初始化逻辑收敛在 database 子包内，CLI 不承载数据库细节。

**Expected Verification Result:** 测试覆盖新建数据库、自动创建父目录、已完整数据库跳过、不完整数据库失败。

## Stage #3: init 命令接入

### Task #4: 新增 `zembra-cli init` 命令

**Status:** Finished

**Files:** Modify `src/zembra_cli/cli.py`; Modify `tests/test_cli.py`

**Function:** CLI 新增 `init` 命令，默认初始化 `~/.zembra/zembra.sqlite3`，并支持 `--database` 指定路径。

**Implementation Notes:** 命令从 `zembra_cli.database` 导入并调用 `initialize_database_file()`，随后调用 `write_database_path()`。配置状态通过写入前配置文件是否存在区分 `created` 和 `updated`。数据库和配置错误都走 `fail_command()`。

**Expected Verification Result:** CLI 测试覆盖默认路径、自定义路径、成功输出、配置 TOML 格式错误、不完整数据库失败。

### Task #5: 验证 init 后 add/run 可用路径

**Status:** Finished

**Files:** Modify `tests/test_cli.py`

**Function:** 确认 `init` 写入的配置可被现有数据库命令读取。

**Implementation Notes:** 测试中 monkeypatch `default_config_path()` 和 `DEFAULT_DATABASE_PATH` 或通过 `--database` 使用临时路径，执行 init 后调用配置读取，并验证数据库核心表存在。若测试成本合适，可追加一次 `add` 创建笔记。

**Expected Verification Result:** init 后 `load_config()` 返回初始化数据库路径，数据库具备核心表，`add` 能成功创建 note。

## Stage #4: 验证与计划回写

### Task #6: 回归验证与静态检查

**Status:** Finished

**Files:** Verify full repository; Modify `docs/exec-plans/active/cli/rc006-init-command.md`

**Function:** 运行全量测试和 lint，确认 init 命令不影响既有 CLI、配置、数据库和交互 run 行为。

**Implementation Notes:** 执行 `uv run pytest` 和 `uv run ruff check .`。实现完成后更新本计划任务状态和验证记录。完成 Stage 后按 Git 安全规则进行原子提交，commit message 使用符合规范的 Conventional Commits。

**Expected Verification Result:** 所有测试通过，ruff 通过，执行计划记录验证结果。

## 验证记录

- 2026.04.27：`uv run pytest`，83 passed。
- 2026.04.27：`uv run ruff check .`，All checks passed。
