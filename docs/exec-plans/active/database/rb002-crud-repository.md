# CRUD Repository 开发计划

日期：2026.04.26

## Related Design Doc

`docs/design-docs/database/rb002-crud-repository.md`

需求澄清文档：`docs/request-clarify/database/rb002-crud-repository.md`

## Stage #1: Repository 基础结构与读写骨架

### Task #1: 定义 Repository 公共结构

**Status:** Finished

**Files:** Create `src/zembra_cli/repository.py`; Modify `src/zembra_cli/models.py` if input模型确有必要; Verify `tests/test_repository.py`

**Function:** 建立 `ZembraRepository`、`RecordNotFoundError`、ID 生成和 clock 注入机制。

**Implementation Notes:** Repository 接收 `sqlite3.Connection`，不创建连接；默认使用 `uuid.uuid4().hex` 生成 ID，默认 clock 返回 Unix timestamp。所有 SQL 读取结果统一转换为现有 Pydantic record 模型。

**Expected Verification Result:** 可以实例化 Repository，并在测试中使用固定 clock 和临时 SQLite 数据库。

### Task #2: 实现 field/tag 获取或创建

**Status:** Finished

**Files:** Modify `src/zembra_cli/repository.py`; Create/Modify `tests/test_repository.py`

**Function:** 实现 `get_or_create_field(name)`、`get_or_create_tag(name)`、field/tag 按名称查询和列表查询。

**Implementation Notes:** 先按唯一 `name` 查询，不存在则插入；重复调用返回同一条记录。字段值保持调用方传入内容，不在 Repository 中做复杂归一化。

**Expected Verification Result:** 重复 get-or-create 不产生重复 field/tag，返回 Pydantic record。

## Stage #2: Note CRUD 与 Revision

### Task #3: 实现 note 创建

**Status:** Finished

**Files:** Modify `src/zembra_cli/repository.py`; Modify `tests/test_repository.py`

**Function:** 实现 `create_note(content, field_name=None, tag_names=None, device_id=None)`。

**Implementation Notes:** 在同一事务内自动创建 field/tag，插入 note，建立 note_tags，写入初始 note_revision，并更新 `notes.current_revision_id`。`created_at` 和 `updated_at` 使用同一 clock 值。

**Expected Verification Result:** 创建 note 后可查到 note、field、tags、note_tags 和一条 revision，`current_revision_id` 指向该 revision。

### Task #4: 实现 note 查询和列表

**Status:** Finished

**Files:** Modify `src/zembra_cli/repository.py`; Modify `tests/test_repository.py`

**Function:** 实现 `get_note(note_id, include_deleted=False)` 和 `list_notes(include_deleted=False)`。

**Implementation Notes:** 默认添加 `deleted_at IS NULL` 条件；`include_deleted=True` 时允许返回软删除记录。列表默认按 `updated_at DESC, created_at DESC` 排序。

**Expected Verification Result:** 默认查询不返回软删除 note，开启 include_deleted 后可以返回。

### Task #5: 实现 note content 更新并写 revision

**Status:** Finished

**Files:** Modify `src/zembra_cli/repository.py`; Modify `tests/test_repository.py`

**Function:** 实现 `update_note_content(note_id, content, device_id=None)`。

**Implementation Notes:** note 不存在时抛出 `RecordNotFoundError`；更新 `content`、`updated_at`，写入完整正文快照 revision，并更新 `current_revision_id`。该操作在单事务内完成。

**Expected Verification Result:** 更新后 note content 改变，revision 数量增加，`current_revision_id` 指向最新 revision。

## Stage #3: Note 状态变更与 Tag 关联

### Task #6: 实现归档和软删除

**Status:** Finished

**Files:** Modify `src/zembra_cli/repository.py`; Modify `tests/test_repository.py`

**Function:** 实现 `archive_note(note_id)` 和 `delete_note(note_id)`。

**Implementation Notes:** 归档写入 `archived_at`，软删除写入 `deleted_at`；二者不物理删除记录。不自动写 revision。

**Expected Verification Result:** 归档 note 仍可默认查询；软删除 note 默认查询和列表不可见。

### Task #7: 实现 note tag 关联管理

**Status:** Finished

**Files:** Modify `src/zembra_cli/repository.py`; Modify `tests/test_repository.py`

**Function:** 实现 `add_tag_to_note(note_id, tag_name)`、`remove_tag_from_note(note_id, tag_name)`、`list_note_tags(note_id)`。

**Implementation Notes:** 添加 tag 时自动创建不存在的 tag；重复添加保持幂等。移除关联只删除 note_tags，不删除 tags 表记录。

**Expected Verification Result:** 重复添加 tag 不产生重复关联，移除后 tag 记录保留且 note_tags 关联消失。

## Stage #4: 整体验证与计划回写

### Task #8: 回归验证

**Status:** Finished

**Files:** Verify full repository; Modify `docs/exec-plans/active/database/rb002-crud-repository.md`

**Function:** 运行完整测试和 lint，并回写任务状态与验证结果。

**Implementation Notes:** 执行 `uv run pytest` 和 `uv run ruff check .`。确认未新增 CLI 命令入口。

**Expected Verification Result:** 所有测试通过，ruff 通过，执行计划记录实际验证结果。完成 Stage 后进行一次原子提交。

## 验证记录

- 2026.04.26：`uv run pytest`，17 passed。
- 2026.04.26：`uv run ruff check .`，All checks passed。
- 2026.04.26：确认未新增 CLI 命令入口，本阶段仅实现 Repository 层和测试。
