# Zembra Env Config 开发计划

日期：2026.04.26

## Related Design Doc

`docs/design-docs/cli/rc002-zembra-env-config.md`

需求澄清文档：`docs/request-clarify/cli/rc002-zembra-env-config.md`

## Stage #1: 配置模块基础能力

### Task #1: 新增配置模型与错误类型

**Status:** Finished

**Files:** Create `src/zembra_cli/config.py`; Create `tests/test_config.py`

**Function:** 定义 `ZembraConfig`、默认配置路径、配置错误类型和基础校验入口。

**Implementation Notes:** 默认配置路径为 `Path.home() / ".zembra.env"`。配置模型只包含 `database_path: Path`。错误类型需要覆盖配置缺失、TOML 格式错误、数据库路径缺失、配置父目录缺失等场景，便于 CLI 层输出自然语言原因。

**Expected Verification Result:** 测试可以实例化配置模型，并能识别默认配置路径和配置缺失错误。

### Task #2: 实现 TOML 配置读取

**Status:** Finished

**Files:** Modify `src/zembra_cli/config.py`; Modify `tests/test_config.py`

**Function:** 实现 `load_config(config_path=None)`，读取 TOML 并返回 `ZembraConfig`。

**Implementation Notes:** 使用 Python 3.12 标准库 `tomllib`。读取 `[database].path`，要求该字段存在且为非空字符串，加载后转为 `Path`。配置文件不存在、TOML 解析失败、字段缺失或类型不符合预期时抛出配置错误。

**Expected Verification Result:** 有效配置能返回数据库路径；缺失文件、坏 TOML、缺失 `[database].path` 都能被测试稳定覆盖。

### Task #3: 实现 TOML 配置写入

**Status:** Finished

**Files:** Modify `src/zembra_cli/config.py`; Modify `tests/test_config.py`

**Function:** 实现 `write_database_path(database_path, config_path=None)`，创建或更新 `~/.zembra.env` 中的 `[database].path`。

**Implementation Notes:** 配置文件不存在时从空配置写入；存在时先读取原始 TOML 字典，只更新 `database.path`，保留其他已有字段。不自动创建配置文件父目录，父目录缺失时报错。写入格式保持稳定 TOML，当前不承诺保留注释。

**Expected Verification Result:** 新建配置写出 `[database].path`；更新配置能保留未知字段；父目录缺失时报错；写入后可再次通过 `load_config` 读取。

## Stage #2: CLI 配置命令与数据库命令迁移

### Task #4: 新增 config database 命令

**Status:** Designed

**Files:** Modify `src/zembra_cli/cli.py`; Modify `tests/test_cli.py`

**Function:** 新增 `zembra-cli config database <file-path>` 命令，用于写入 zembra 系统共享配置文件。

**Implementation Notes:** 使用 Typer 子命令结构，`config` 作为命令组，`database` 接收一个路径参数。命令调用 `write_database_path`，成功时输出自然语言成功信息。该命令不要求配置文件预先存在，也不校验数据库文件是否存在。

**Expected Verification Result:** CLI 测试可通过临时配置路径写入 TOML，输出成功信息，并能读取到配置中的数据库路径。

### Task #5: 将 add 命令迁移为读取配置路径

**Status:** Designed

**Files:** Modify `src/zembra_cli/cli.py`; Modify `tests/test_cli.py`

**Function:** `add` 命令执行前加载 `~/.zembra.env`，使用 `[database].path` 指向的 SQLite 数据库。

**Implementation Notes:** 替换当前固定 `DEFAULT_DATABASE_PATH` 逻辑。数据库命令先调用 `load_config()`，配置缺失时输出 `Config file is missing at ~/.zembra.env. Create it with: zembra-cli config database <file-path>` 并返回非 0。数据库文件存在性和核心表检查沿用现有逻辑，但数据库路径来自配置。

**Expected Verification Result:** `add` 使用配置中的数据库路径创建 note；配置缺失时失败并提示 config 命令；数据库文件缺失或 schema 缺失仍按自然语言错误返回。

### Task #6: 保证非数据库命令不强制加载配置

**Status:** Designed

**Files:** Modify `src/zembra_cli/cli.py`; Modify `tests/test_cli.py`

**Function:** 确保 `--version`、`--help`、`hello` 和 `config database` 在配置文件不存在时仍可正常执行。

**Implementation Notes:** 不在 Typer callback 中全局加载配置；只在需要数据库的命令内部调用配置读取函数。CLI 错误处理集中捕获配置错误并转换为自然语言输出。

**Expected Verification Result:** 删除或不创建 `~/.zembra.env` 时，非数据库命令 exit code 为 0；`add` exit code 为非 0。

## Stage #3: 回归验证与计划回写

### Task #7: 补齐配置与 CLI 自动化测试

**Status:** Designed

**Files:** Modify `tests/test_config.py`; Modify `tests/test_cli.py`

**Function:** 覆盖设计文档中列出的配置读取、写入、错误和 CLI 行为。

**Implementation Notes:** 测试中 monkeypatch 配置默认路径，避免读写真实 `~/.zembra.env`。测试数据库继续使用临时 SQLite 文件和 `initialize_database`。重点覆盖新建配置、更新配置、保留未知字段、缺失配置提示、add 读取配置路径。

**Expected Verification Result:** 配置模块和 CLI 测试稳定通过，不污染用户 HOME。

### Task #8: 执行整体验证并回写计划状态

**Status:** Designed

**Files:** Verify full repository; Modify `docs/exec-plans/active/cli/rc002-zembra-env-config.md`

**Function:** 运行完整 lint 和测试，记录实际验证结果，并将已完成任务状态更新为 `Finished`。

**Implementation Notes:** 执行 `uv run pytest` 和 `uv run ruff check .`。若实现阶段修改了代码，完成每个 Stage 后按 Git 安全规则进行一次原子提交，commit message 使用符合规范的 Conventional Commits。

**Expected Verification Result:** 所有自动化测试通过，ruff 通过，开发计划中记录验证命令和结果。

## 验证记录

- 2026.04.26：Stage #1 完成配置模型、配置错误、TOML 读取和写入；`uv run pytest`，31 passed。
- 2026.04.26：Stage #1 执行 `uv run ruff check .`，All checks passed。
