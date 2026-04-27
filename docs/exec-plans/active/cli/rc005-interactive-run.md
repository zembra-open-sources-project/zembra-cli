# Run 交互式笔记录入开发计划

日期：2026.04.27

## Related Design Doc

`docs/design-docs/cli/rc005-interactive-run.md`

需求澄清文档：`docs/request-clarify/cli/rc005-interactive-run.md`

## Stage #1: 交互输入解析与展示基础

### Task #1: 新增交互输入解析模型

**Status:** Finished

**Files:** Create `src/zembra_cli/interactive.py`; Create `tests/test_interactive.py`

**Function:** 解析用户输入中的正文、`@field` 和 `#tag`，缺少 field 时使用默认 `inbox`。

**Implementation Notes:** 新增 `InteractiveNoteInput` 数据结构和 `parse_interactive_note_input()`。解析独立 token，移除 field/tag 标记后生成正文；多个 tag 按输入顺序去重；多个 field 使用最后一个 field。

**Expected Verification Result:** 单元测试覆盖默认 field、显式 field、多个 tag、重复 tag、多个 field、空正文。

### Task #2: 新增 Rich intro 与帮助输出

**Status:** Finished

**Files:** Create `src/zembra_cli/interactive.py`; Create `tests/test_interactive.py`

**Function:** 使用 Rich 输出 Zembra TUI Logo、数据库路径、笔记统计和交互帮助。

**Implementation Notes:** 将 intro 渲染函数设计为接收 Console、数据库路径和统计值，便于测试和后续替换为 Textual。帮助输出只包含 `/help`、`/exit`、`@field`、`#tag` 的使用说明。

**Expected Verification Result:** 测试可通过 Rich record console 验证输出包含 Logo、数据库路径、统计和帮助关键文本。

## Stage #2: run 命令接入与持久交互

### Task #3: 实现交互循环与保存反馈

**Status:** Finished

**Files:** Create `src/zembra_cli/interactive.py`; Modify `tests/test_interactive.py`

**Function:** 持续读取用户输入，处理 `/help`、`/exit`、空输入、未知命令和普通笔记保存。

**Implementation Notes:** 交互循环接收输入函数、Console 和 Repository，便于测试注入。保存普通笔记时调用 `repository.create_note(content, field_name=field, tag_names=tags)`，成功后输出 `Saved note <短ID> · <时间>`。

**Expected Verification Result:** 测试可模拟多轮输入，验证 `/help` 不退出、`/exit` 退出、普通笔记保存并输出短 ID。

### Task #4: 新增 `zembra-cli run` 命令

**Status:** Finished

**Files:** Modify `src/zembra_cli/cli.py`; Modify `tests/test_cli.py`

**Function:** CLI 增加 `run` 命令，启动时加载配置、校验数据库、渲染 intro 并进入交互循环。

**Implementation Notes:** 配置错误沿用 `ConfigError.message`；数据库缺失和核心表缺失沿用 `require_initialized_database()`；SQLite 打开失败使用自然语言失败提示。命令层只做编排，不复制解析逻辑。

**Expected Verification Result:** CLI 测试覆盖配置缺失、数据库未初始化，以及可注入交互循环的成功启动路径。

## Stage #3: 验证与计划回写

### Task #5: 回归验证与静态检查

**Status:** Finished

**Files:** Verify full repository

**Function:** 运行全量测试和 lint，确认新增 `run` 命令不影响既有 CLI、配置和 Repository 行为。

**Implementation Notes:** 执行 `uv run pytest` 和 `uv run ruff check .`。如实现阶段修改代码，完成 Stage 后按 Git 安全规则进行原子提交，commit message 使用符合规范的 Conventional Commits。

**Expected Verification Result:** 所有测试通过，ruff 通过，执行计划更新验证记录。

## 验证记录

- 2026.04.27：`uv run pytest`，75 passed。
- 2026.04.27：`uv run ruff check .`，All checks passed。
