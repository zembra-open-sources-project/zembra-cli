# CLI 级联配置实现计划

> **给 Claude：** 必需工作流：使用 superpowers:executing-plans 逐任务实现此计划。

**目标：** 为 `zembra-cli` 增加 `~/.zembra/config.cli.toml` 独立配置，并通过字段级级联读取兼容旧全局配置 `~/.zembra.env`。

**需求澄清文档：** `docs/request-clarify/cli/rc011-cli-cascading-config.md`

**相关设计文档：** `docs/design-docs/cli/rc011-cli-cascading-config.md`

**架构：** 配置层负责读取 CLI 配置和全局配置并按字段合并，返回现有 `ZembraConfig` 运行模型。CLI、MCP 和 repository 打开逻辑只消费合并后的配置，不直接关心字段来自哪个文件；写入命令只写 CLI 配置文件。

**技术栈：** Python 3.12、Typer、Rich、tomllib、SQLite、pytest、ruff、uv。

**范围 / 非范围：** 本计划覆盖 CLI 独立配置路径、字段级级联读取、写入目标调整、init 目录创建、MCP 接入、README 和测试更新；不做旧配置自动迁移、不删除全局配置读取、不改默认数据库路径、不新增 profile。

---

## Stage #1: 配置层级联读取

### 任务 #1: 增加配置路径函数和级联读取模型

**Status:** Finished

**Files:** Modify `src/zembra_cli/config.py`; Modify `tests/test_config.py`

功能：新增 CLI 配置路径和全局配置路径，并实现字段级级联读取入口。

实现说明：在 `config.py` 新增 `default_cli_config_path()` 返回 `Path.home() / ".zembra" / "config.cli.toml"`，新增 `default_global_config_path()` 返回 `Path.home() / ".zembra.env"`。实现 `load_cascading_config(cli_config_path=None, global_config_path=None)`，分别读取存在的 TOML 文件，按 `cli.mode`、`cli.http_base_url`、`database.path` 字段级合并后返回 `ZembraConfig`。删除旧的 `default_config_path()` 和 `load_config()` 公共入口，不保留兼容函数。

预期验证结果：`tests/test_config.py` 覆盖只有 CLI 配置、只有全局配置、两个配置同时存在、CLI 字段覆盖全局字段、CLI 缺字段由全局补齐。

### 任务 #2: 配置错误提示和非法 TOML 路径定位

**Status:** Finished

**Files:** Modify `src/zembra_cli/config.py`; Modify `tests/test_config.py`

功能：让级联读取失败时输出可定位、符合需求的错误信息。

实现说明：两个配置文件都不存在时，错误消息必须包含已检查 `~/.zembra/config.cli.toml` 和 `~/.zembra.env`。存在的任一配置 TOML 非法时，错误消息包含具体文件路径和解析错误。合并后缺少必需字段时沿用现有缺字段错误语义。

预期验证结果：缺少可用配置、CLI 配置 TOML 非法、全局配置 TOML 非法、合并后缺少 `cli.mode`、direct 缺少 `database.path`、HTTP 缺少 `cli.http_base_url` 的测试都通过。

## Stage #2: CLI 和 MCP 接入

### 任务 #3: 读取入口改为级联配置

**Status:** Finished

**Files:** Modify `src/zembra_cli/cli.py`; Modify `src/zembra_cli/mcp_server.py`; Modify `tests/test_cli.py`; Modify `tests/test_mcp_server.py`

功能：让数据库命令、HTTP 模式命令和 MCP 入口使用合并后的最终配置。

实现说明：`open_cli_repository()` 改为调用 `load_cascading_config()`。`mcp_server.open_mcp_repository()` 使用级联读取，仍要求最终 `cli_mode == "direct"`，仍校验数据库存在和核心表完整。测试中用临时路径 monkeypatch CLI 配置和全局配置路径，避免读写真实 home。

预期验证结果：CLI direct、CLI HTTP、MCP direct 都能从 CLI 配置或全局配置读取；CLI 配置字段可以覆盖全局字段；MCP 在最终 HTTP 模式下继续拒绝启动。

### 任务 #4: 写入命令改为 CLI 配置

**Status:** Finished

**Files:** Modify `src/zembra_cli/config.py`; Modify `src/zembra_cli/cli.py`; Modify `tests/test_config.py`; Modify `tests/test_cli.py`

功能：`zembra-cli config database <path>` 和 `zembra-cli init` 写入 `~/.zembra/config.cli.toml`。

实现说明：调整 `write_database_path()` 默认路径为 CLI 配置路径，保留显式路径参数以便测试。`config database` 调用默认 CLI 配置路径，并在 `~/.zembra/` 不存在时创建目录。`init` 初始化数据库后写入 CLI 配置，并设置 `[cli].mode = "direct"`。成功输出中的 Config 路径改为 `~/.zembra/config.cli.toml`。

预期验证结果：`config database` 新建或更新的是 CLI 配置文件，不触碰 `.zembra.env`；`init` 自动创建 `~/.zembra/`、数据库文件和 `config.cli.toml`；写入后 `load_cascading_config()` 可读到 direct 配置。

## Stage #3: 文档、回归验证和计划回写

### 任务 #5: 更新 README 和配置说明

**Status:** Finished

**Files:** Modify `README.md`; Verify `docs/design-docs/cli/rc011-cli-cascading-config.md`; Verify `docs/request-clarify/cli/rc011-cli-cascading-config.md`

功能：让用户文档中的默认配置路径和兼容回退规则与实现一致。

实现说明：README 中把默认 CLI 配置文件改为 `~/.zembra/config.cli.toml`，补充 `~/.zembra.env` 仍作为低优先级回退读取来源。文档自然段保持连续段落，不在段落内部硬换行。

预期验证结果：README 不再把 `~/.zembra.env` 描述为唯一默认配置；新配置路径、写入命令和回退规则清晰一致。

### 任务 #6: 运行验证并更新计划状态

**Status:** Finished

**Files:** Modify `docs/exec-plans/active/cli/rc011-cli-cascading-config.md`; Verify full repository

功能：运行格式、定向测试和全量测试，记录验证结果。

实现说明：优先运行 `uv run ruff check .`，再运行 `uv run pytest tests/test_config.py tests/test_cli.py tests/test_mcp_server.py -q`，最后运行 `uv run pytest -q`。所有验证通过后，把本计划中已完成任务状态更新为 `Finished`，并追加验证记录。完成代码修改后按项目规则 stage 并提交。

预期验证结果：ruff、定向测试和全量测试通过；计划状态和验证记录准确；提交包含本需求相关代码、测试和文档。

## 提交计划

| 阶段 | 提交点 | Commit message |
| --- | --- | --- |
| Stage #1 | 级联读取和配置层测试完成后 | `feat: add cascading CLI config loading` |
| Stage #2 | CLI/MCP 读取和写入目标完成后 | `feat: write CLI config to zembra directory` |
| Stage #3 | 文档、验证和计划回写完成后 | `docs: document CLI cascading config` |

## 验证记录

2026.06.25：已运行 `uv run pytest tests/test_config.py tests/test_cli.py tests/test_mcp_server.py -q`，75 个测试通过。

2026.06.25：已运行 `uv run ruff check .`，检查通过。

2026.06.25：已运行 `uv run pytest -q`，136 个测试通过。
