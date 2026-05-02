# Slash 命令即时帮助开发计划

日期：2026.05.02

## Related Design Doc

`docs/design-docs/cli/rc008-slash-command-help.md`

需求澄清文档：`docs/request-clarify/cli/rc008-slash-command-help.md`

## Stage #1: 命令候选模型与补全

### Task #1: 定义斜杠命令候选与前缀匹配

**Status:** Finished

**Files:** Modify `src/zembra_cli/interactive.py`; Modify `tests/test_interactive.py`

**Function:** 为现有 `/help` 和 `/exit` 建立统一候选数据，并根据当前输入文本执行前缀匹配。

**Implementation Notes:** 新增轻量数据结构记录命令和说明；新增 `match_slash_commands(input_text: str)`。只有输入以 `/` 开头时返回候选；`/` 返回全部，`/h` 返回 `/help`，`/e` 返回 `/exit`，普通正文中的 `/` 返回空列表。

**Expected Verification Result:** 单元测试覆盖 `/`、`/h`、`/e`、未知前缀和 `note / text`。

### Task #2: 新增 prompt_toolkit 候选补全

**Status:** Finished

**Files:** Modify `src/zembra_cli/interactive.py`; Modify `tests/test_interactive.py`

**Function:** 用 prompt_toolkit completer 展示斜杠命令候选列表和说明。

**Implementation Notes:** 新增 `SlashCommandCompleter`，将匹配结果转换为 `Completion`，使用 `display_meta` 展示说明。候选菜单只展示斜杠命令，不包含普通笔记示例；完整帮助仍由 `render_help()` 负责。

**Expected Verification Result:** 单元测试验证 completer 返回匹配命令和说明，且前缀过滤后的候选不包含未匹配命令。

## Stage #2: 输入读取即时提示接入

### Task #3: 在生产输入函数中接入即时帮助

**Status:** Finished

**Files:** Modify `src/zembra_cli/interactive.py`; Modify `tests/test_interactive.py`

**Function:** 在 `read_interactive_line()` 的输入过程中，当当前内容以 `/` 开头时显示 prompt_toolkit 临时候选菜单。

**Implementation Notes:** `PromptSession` 传入 `SlashCommandCompleter` 并启用 `complete_while_typing`。不使用 Rich 表格打印候选，避免每次按键留下历史输出。`run_interactive_session()` 的提交后处理逻辑保持不变。

**Expected Verification Result:** 测试验证 `/` 前缀触发候选，普通输入不触发，提交 `/help` 和 `/exit` 的现有行为不变。

## Stage #3: 验证与计划回写

### Task #4: 回归验证与计划状态更新

**Status:** Finished

**Files:** Modify `docs/exec-plans/active/cli/rc008-slash-command-help.md`; Verify full repository

**Function:** 运行静态检查和全量测试，并把实现过程、验证结果和任务状态回写到本计划。

**Implementation Notes:** 执行 `uv run ruff check .` 和 `uv run pytest`。完成 Stage 后如有代码改动，按 Git 安全规则进行一次原子提交，commit message 必须符合 Conventional Commits 规范。

**Expected Verification Result:** ruff 通过，全量 pytest 通过，计划中的任务状态和验证记录更新完整。

## 验证记录

- 2026.05.03：`uv run pytest tests/test_interactive.py -q`，16 passed。
- 2026.05.03：`uv run ruff check .`，All checks passed。
- 2026.05.03：`uv run pytest`，94 passed。
- 2026.05.03：根据手工反馈修正为 prompt_toolkit 临时候选菜单，移除 Rich 表格打印式候选。
- 2026.05.03：`uv run ruff check .`，All checks passed。
- 2026.05.03：`uv run pytest`，94 passed。
