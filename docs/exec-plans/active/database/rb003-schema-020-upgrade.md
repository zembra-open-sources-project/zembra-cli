# Schema 0.2.0 升级开发计划

日期：2026.04.27

## Related Design Doc

`docs/design-docs/database/rb003-schema-020-upgrade.md`

需求澄清文档：`docs/request-clarify/database/rb003-schema-020-upgrade.md`

## Stage #1: Schema 指针升级

### Task #1: 更新共享 schema submodule

**Status:** Finished

**Files:** Modify `vendor/zembra-schema`; Modify `README.md`

**Function:** 将共享 schema 固定版本从 `v0.1.0` 升级到 `v0.2.0`。

**Implementation Notes:** submodule 切换到远端 tag `v0.2.0`，README 同步记录新 tag 和 commit。

**Expected Verification Result:** `git submodule status` 显示 `vendor/zembra-schema` 指向 `v0.2.0`。

## Stage #2: Role 字段适配

### Task #2: 适配 NoteRecord

**Status:** Finished

**Files:** Modify `src/zembra_cli/models.py`; Modify `tests/test_models.py`

**Function:** 支持 `notes.role` 的 `Human` 与 `Agent` 枚举值。

**Implementation Notes:** `NoteRecord.role` 默认 `Human`，非法 role 由 Pydantic 拒绝。

**Expected Verification Result:** 默认 note role 为 `Human`，`Agent` 可通过，未知值失败。

### Task #3: 适配 Repository 写入

**Status:** Finished

**Files:** Modify `src/zembra_cli/repository/notes.py`; Modify `tests/test_repository.py`

**Function:** 创建 note 时写入 role。

**Implementation Notes:** `create_note()` 增加 `role` 参数，默认 `Human`，调用方可传入 `Agent`。

**Expected Verification Result:** Repository 创建的 note 能读回正确 role。

### Task #4: 验证 SQLite schema

**Status:** Finished

**Files:** Modify `tests/test_db.py`

**Function:** 验证初始化后的 `notes` 表包含 role 列和枚举约束。

**Implementation Notes:** 使用临时 SQLite 数据库执行共享 schema，并通过 `PRAGMA table_info(notes)` 与非法插入验证。

**Expected Verification Result:** role 列存在，默认值为 `Human`，非法 role 被 SQLite 拒绝。

## Stage #3: 验证、提交与 tag

### Task #5: 运行验证并创建版本 tag

**Status:** Finished

**Files:** Verify full repository

**Function:** 执行测试和 lint，提交 schema 升级，并创建 `v0.2.0` tag。

**Implementation Notes:** 包版本保持 `0.1.0`；commit message 使用 Conventional Commits。

**Expected Verification Result:** `uv run pytest` 和 `uv run ruff check .` 通过，主仓库存在 `v0.2.0` tag。

## 验证记录

- 2026.04.27：`uv run pytest`，55 passed。
- 2026.04.27：`uv run ruff check .`，All checks passed。
