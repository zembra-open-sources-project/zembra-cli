# CLI Add Command 开发计划

日期：2026.04.26

## Related Design Doc

`docs/design-docs/cli/rc001-cli-add-command.md`

需求澄清文档：`docs/request-clarify/cli/rc001-cli-add-command.md`

## Stage #1: CLI 入口与数据库访问边界

### Task #1: 统一命令行入口为 zembra-cli

**Status:** Finished

**Files:** Modify `pyproject.toml`; Modify `src/zembra_cli/cli.py`; Verify `tests/test_cli.py`

**Function:** 将项目 console script 统一为 `zembra-cli`，并让 Typer app 的展示名称与入口保持一致。

**Implementation Notes:** 将 `[project.scripts]` 中的旧入口 `zembra` 调整为 `zembra-cli = "zembra_cli.cli:app"`。保留 `--version` 能力，版本输出文本同步使用 `zembra-cli`。如已有测试断言旧名称，需要同步更新。

**Expected Verification Result:** `--version` 输出包含 `zembra-cli` 和当前包版本，测试不再依赖旧入口名 `zembra`。

### Task #2: 定义默认数据库路径和初始化校验

**Status:** Finished

**Files:** Modify `src/zembra_cli/db.py`; Modify `src/zembra_cli/cli.py`; Verify `tests/test_cli.py`

**Function:** 为 CLI 提供固定数据库路径 `~/.zembra/zembra.sqlite3`，并在执行写入前确认数据库存在且包含核心表。

**Implementation Notes:** 默认路径建议集中放在 `db.py` 或 CLI 私有辅助函数中，避免散落硬编码。执行 `add` 时先展开 `Path.home()`，如果数据库文件不存在或核心表不完整，输出自然语言错误并使用非 0 退出码。`add` 命令不隐式初始化数据库。

**Expected Verification Result:** 数据库不存在时 `add` 命令失败，stdout 或 stderr 包含明确自然语言原因，退出码非 0。

## Stage #2: add 命令与输出契约

### Task #3: 实现 tags 参数解析

**Status:** Finished

**Files:** Modify `src/zembra_cli/cli.py`; Modify `tests/test_cli.py`

**Function:** 支持 `--tags python --tags cli`、`--tags python,cli` 和混合写法，并输出有效 tag 名称列表。

**Implementation Notes:** 对每个 `--tags` 输入按英文逗号拆分，去除两端空白，过滤空字符串。保留用户输入顺序，并对重复 tag 做稳定去重，保证 metadata 和 Repository 调用中的 tag 列表一致。

**Expected Verification Result:** 重复参数、逗号参数、混合参数都能解析为预期列表；空白会被清理，重复 tag 不重复返回。

### Task #4: 实现 add 命令创建 note

**Status:** Finished

**Files:** Modify `src/zembra_cli/cli.py`; Verify `src/zembra_cli/repository/notes.py`; Modify `tests/test_cli.py`

**Function:** 新增 `zembra-cli add <note-string-content> --tags <multi-tags> --field <field>` 命令，调用 `ZembraRepository.create_note` 写入 note、field 和 tags。

**Implementation Notes:** CLI 层只负责参数解析、数据库连接和调用 Repository，不重复实现持久化逻辑。`note-string-content` 按 Typer 接收到的字符串原样传递，不主动解码 `\n`、`\t` 等转义序列。`--field` 为必填参数，不存在时由 Repository 自动创建。

**Expected Verification Result:** 使用已初始化测试数据库调用 `add` 后，返回 note content 与输入一致，数据库中存在 note、field、tags 和 note_tags 关联。

### Task #5: 实现成功 JSON 和失败自然语言输出

**Status:** Finished

**Files:** Modify `src/zembra_cli/cli.py`; Modify `tests/test_cli.py`

**Function:** 成功时返回只包含当前 note 与用户输入 metadata 的 JSON；失败时返回自然语言错误原因和非 0 退出码。

**Implementation Notes:** 成功 JSON 使用 `note.model_dump()` 作为 `note` 字段，`metadata.field` 使用用户传入 field，`metadata.tags` 使用解析后的有效 tag 列表。避免返回 field/tag 全量记录、数据库路径、其他 note 或无关环境信息。业务失败捕获为面向 CLI 用户的自然语言文本。

**Expected Verification Result:** 成功输出可被 `json.loads` 解析，字段只包含 `note` 和 `metadata`；数据库缺失、未初始化或 SQLite 写入失败时输出可读错误并返回非 0。

## Stage #3: 回归验证与计划回写

### Task #6: 补齐 CLI 自动化测试

**Status:** Finished

**Files:** Modify `tests/test_cli.py`; Verify `src/zembra_cli/cli.py`

**Function:** 为 CLI add 命令补齐参数、返回值和错误路径测试。

**Implementation Notes:** 测试中使用临时 HOME 或 monkeypatch 默认数据库路径，避免写入真实 `~/.zembra/zembra.sqlite3`。测试数据库通过现有 `initialize_database` 初始化。覆盖基础创建、重复 tags、逗号 tags、混合 tags、长文本原样保存、数据库不存在、数据库未初始化。

**Expected Verification Result:** CLI 测试可稳定运行，不依赖用户本机真实数据库，不污染用户目录。

### Task #7: 执行整体验证并回写计划状态

**Status:** Finished

**Files:** Verify full repository; Modify `docs/exec-plans/active/cli/rc001-cli-add-command.md`

**Function:** 运行完整 lint 和测试，记录实际验证结果，并将已完成任务状态更新为 `Finished`。

**Implementation Notes:** 执行 `uv run pytest` 和 `uv run ruff check .`。若实现阶段修改了代码，完成本 Stage 后按 Git 安全规则进行一次原子提交，commit message 使用符合规范的 Conventional Commits。

**Expected Verification Result:** 所有自动化测试通过，ruff 通过，开发计划中记录验证命令和结果。

## 验证记录

- 2026.04.26：Stage #1 完成统一入口名和默认数据库表检查辅助函数；`uv run pytest`，18 passed。
- 2026.04.26：Stage #1 执行 `uv run ruff check .`，All checks passed。
- 2026.04.26：Stage #2 完成 `add` 命令、tags 解析、JSON 输出和错误路径；`uv run pytest`，23 passed。
- 2026.04.26：Stage #2 执行 `uv run ruff check .`，All checks passed。
- 2026.04.26：Stage #3 完成 CLI 自动化测试补齐和最终回归；`uv run pytest`，23 passed。
- 2026.04.26：Stage #3 执行 `uv run ruff check .`，All checks passed。
