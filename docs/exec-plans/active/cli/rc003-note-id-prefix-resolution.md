# Note ID Prefix Resolution 开发计划

日期：2026.04.26

## Related Design Doc

`docs/design-docs/cli/rc003-note-id-prefix-resolution.md`

需求澄清文档：`docs/request-clarify/cli/rc003-note-id-prefix-resolution.md`

## Stage #1: Repository 短 ID 解析能力

### Task #1: 新增 note 引用解析错误类型

**Status:** Finished

**Files:** Modify `src/zembra_cli/repository/exceptions.py`; Modify `tests/test_repository.py`

**Function:** 定义短 ID 解析相关仓储错误，覆盖无效输入、前缀过短和前缀冲突。

**Implementation Notes:** 新增 `InvalidNoteReferenceError`、`NoteReferenceTooShortError`、`AmbiguousNoteReferenceError`。错误对象需要保留原始输入；过短错误保留最短长度；冲突错误保留候选 `NoteRecord` 列表。现有 `RecordNotFoundError` 继续用于完整 id 或前缀无匹配场景。

**Expected Verification Result:** 单元测试可以断言错误类型、原始输入、最短长度和候选列表字段稳定可用。

### Task #2: 实现 note id 前缀解析 API

**Status:** Finished

**Files:** Modify `src/zembra_cli/repository/notes.py`; Modify `tests/test_repository.py`

**Function:** 在 `ZembraRepository` 中实现 `resolve_note_id(note_ref, include_deleted=False)` 和可选便利方法 `get_note_by_ref(note_ref, include_deleted=False)`。

**Implementation Notes:** 输入先去除两端空白并统一小写。空字符串和非十六进制输入抛出无效引用错误；少于 4 位抛出过短错误；32 位输入优先走完整 id 精确查询；4 到 31 位输入使用前缀查询。默认查询条件包含 `deleted_at IS NULL`。冲突候选按 `updated_at DESC, created_at DESC, id ASC` 排序，并限制候选数量避免错误对象过大。

**Expected Verification Result:** 完整 id、4 位唯一前缀、大写前缀都能解析到完整 id；3 位前缀、非 hex、无匹配、多匹配和软删除过滤都能稳定触发预期行为。

### Task #3: 覆盖完整 ID 兼容和软删除边界

**Status:** Finished

**Files:** Modify `tests/test_repository.py`

**Function:** 补齐完整 32 位 id 精确查询、完整 id 不参与冲突判断、软删除 note 不参与默认短 ID 解析的回归测试。

**Implementation Notes:** 测试中使用确定性 id_factory 构造共享前缀的 note id，避免依赖随机 UUID。软删除测试需要先创建 note，再调用 `delete_note`，确认默认 `resolve_note_id` 按未找到处理。

**Expected Verification Result:** Repository 测试证明完整 id 兼容现有语义，并且所有常规短 ID 解析只关注未删除笔记。

## Stage #2: CLI 可复用接入层

### Task #4: 新增 CLI note 引用解析辅助函数

**Status:** Finished

**Files:** Modify `src/zembra_cli/cli.py`; Modify `tests/test_cli.py`

**Function:** 在 CLI 层新增后续命令可复用的 `resolve_note_reference(repository, note_ref)` 辅助函数。

**Implementation Notes:** 辅助函数调用 `repository.resolve_note_id`，捕获 `InvalidNoteReferenceError`、`NoteReferenceTooShortError`、`AmbiguousNoteReferenceError` 和 `RecordNotFoundError`，并通过现有 `fail_command` 输出自然语言错误。该函数不直接连接数据库，也不直接写 SQL。

**Expected Verification Result:** CLI 测试可以通过 fake repository 或临时数据库验证错误会转换为非 0 退出，并且成功场景返回完整 note id。

### Task #5: 实现冲突候选摘要格式化

**Status:** Finished

**Files:** Modify `src/zembra_cli/cli.py`; Modify `tests/test_cli.py`

**Function:** 增加 `summarize_note_content(content, max_length=...)` 和冲突候选格式化逻辑。

**Implementation Notes:** 摘要需要去除换行造成的多行干扰，并按固定长度截断。冲突提示展示候选 note 的前 8 位 id 和内容摘要，提示用户输入更多字符。Repository 只提供候选 note，最终文案由 CLI 层生成。

**Expected Verification Result:** 多匹配前缀错误输出包含原始输入、输入更多字符的提示、候选短 id 和稳定摘要。

## Stage #3: 回归验证与计划回写

### Task #6: 执行自动化回归验证

**Status:** Designed

**Files:** Verify full repository

**Function:** 运行完整测试，确认短 ID 解析不会破坏现有 CLI、配置和仓储行为。

**Implementation Notes:** 执行 `uv run pytest`。如项目配置中已有 lint 命令，再执行对应 lint；若没有配置，则记录未执行原因。验证失败时先定位根因，再更新实现或计划状态。

**Expected Verification Result:** 所有自动化测试通过，现有 `add`、`config database`、repository CRUD 测试保持稳定。

### Task #7: 更新开发计划状态与验证记录

**Status:** Designed

**Files:** Modify `docs/exec-plans/active/cli/rc003-note-id-prefix-resolution.md`

**Function:** 根据实际实现和验证结果，把完成的任务状态更新为 `Finished`，并记录验证命令与结果。

**Implementation Notes:** 每个 Stage 完成后，如果修改了代码，按 Git 安全规则进行一次原子提交。commit message 必须符合 Conventional Commits 白名单和项目防火墙规则。

**Expected Verification Result:** 开发计划准确反映实现进度、验证结果和提交边界。

## 验证记录

- 2026.04.26：Stage #1 完成 note 引用解析错误类型、Repository 前缀解析 API、完整 ID 兼容和软删除边界测试；`uv run pytest tests/test_repository.py`，18 passed。
- 2026.04.26：Stage #1 执行 `uv run ruff check src/zembra_cli/repository tests/test_repository.py`，All checks passed。
- 2026.04.26：Stage #2 完成 CLI note 引用解析辅助函数和冲突候选摘要格式化；`uv run pytest tests/test_cli.py`，17 passed。
- 2026.04.26：Stage #2 执行 `uv run ruff check src/zembra_cli/cli.py tests/test_cli.py`，All checks passed。
