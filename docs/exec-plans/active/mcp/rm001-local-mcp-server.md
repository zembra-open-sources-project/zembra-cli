# Local MCP Server 实现计划

日期：2026.06.11

需求澄清文档：`docs/request-clarify/mcp/rm001-local-mcp-server.md`

## 关联设计文档

`docs/design-docs/mcp/rm001-local-mcp-server.md`

**目标：** 在 `zembra-cli` 中实现 direct SQLite 模式的本地 MCP Server，通过 `zembra-cli mcp` 暴露首批 note/taxonomy tools。

**架构：** 新增 `src/zembra_cli/mcp_server.py` 负责 MCP app 构建、direct-only repository 打开和 tool 注册。CLI 只新增 `mcp` 子命令作为启动入口，具体数据读写复用 `ZembraRepository`。

**技术栈：** Python 3.12、Typer、sqlite3、Pydantic v2、MCP Python SDK、pytest、ruff。

**范围 / 非范围：** 本计划只实现 stdio MCP Tools 和 direct SQLite 访问；不实现 HTTP MCP transport、MCP Resources、Prompts、鉴权、多用户、schema 迁移或 backend 代理。

---

## Stage #1: MCP 基础依赖与 direct-only 数据访问

### Task #1: 引入 MCP SDK 依赖

**Status:** Designed

**Files:** Modify `pyproject.toml`; Modify `uv.lock`

**Function:** 增加 MCP Python SDK 依赖，确保项目能导入 server 构建 API。

**Implementation Notes:** 使用 `uv add mcp` 更新依赖和 lockfile。只加入实现 MCP Server 所需依赖，不新增额外 server framework。

**Expected Verification Result:** `uv run python -c "import mcp"` 成功，lockfile 与 `pyproject.toml` 一致。

### Task #2: 实现 direct-only repository 打开函数

**Status:** Designed

**Files:** Create `src/zembra_cli/mcp_server.py`; Modify `tests/test_mcp_server.py`

**Function:** 读取 `.zembra.env`，只允许 `[cli].mode = "direct"`，校验数据库存在且核心表完整，并返回可用的 `ZembraRepository`。

**Implementation Notes:** 复用 `load_config`、`default_config_path`、`database_connection`、`missing_core_tables` 或现有等价逻辑。HTTP mode 必须直接失败，不创建 `HttpZembraRepository`。连接建议按 tool 调用打开并关闭。

**Expected Verification Result:** direct config 能打开 repository；HTTP config 返回 MCP direct-only 错误；缺失数据库返回未初始化错误。

## Stage #2: MCP Tools 实现

### Task #3: 构建 MCP Server 与 tool 注册

**Status:** Designed

**Files:** Modify `src/zembra_cli/mcp_server.py`; Create/Modify `tests/test_mcp_server.py`

**Function:** 创建 MCP app，并注册 `create_note`、`list_notes`、`list_tags`、`list_fields`、`random_notes`。

**Implementation Notes:** `create_note` 默认 `role="Agent"`，可选输入包括 `field_name`、`tag_names`、`role`。所有 tool 返回 Pydantic `model_dump(mode="json")` 结构。`random_notes` 对 `number < 1` 返回参数错误。

**Expected Verification Result:** 测试可直接调用 tool 包装后的业务函数或底层 handler，确认每个 tool 访问本地 SQLite 并返回 JSON 兼容结构。

### Task #4: 增加 `zembra-cli mcp` 启动入口

**Status:** Designed

**Files:** Modify `src/zembra_cli/cli.py`; Modify `tests/test_cli.py`

**Function:** 新增 `mcp` 子命令，启动 stdio MCP Server。

**Implementation Notes:** CLI 入口只调用 `run_mcp_server()` 或等价函数。stdio 模式下禁止向 stdout 输出普通文本；错误通过 Typer 失败路径或 MCP SDK 错误处理呈现。不要影响现有 `add`、`list`、`random`、`run` 命令。

**Expected Verification Result:** CLI help 中出现 `mcp` 命令；现有 CLI 测试不回归；启动函数可通过 monkeypatch 验证被调用。

## Stage #3: 文档、验证与收尾

### Task #5: 补充 MCP 使用说明

**Status:** Designed

**Files:** Modify `README.md`

**Function:** 说明 `zembra-cli mcp` 的 direct SQLite 前提、示例启动命令和首批 tools。

**Implementation Notes:** 文档只描述当前已实现能力，不写未实现的 Resources、Prompts 或远程 transport。

**Expected Verification Result:** README 中可找到 MCP Server 启动方式、direct 模式要求和 tools 列表。

### Task #6: 回归验证与计划状态回写

**Status:** Designed

**Files:** Verify full repository; Modify `docs/exec-plans/active/mcp/rm001-local-mcp-server.md`

**Function:** 运行定向和全量验证，并把任务状态、验证记录写回执行计划。

**Implementation Notes:** 执行 `uv run pytest tests/test_mcp_server.py -q`、`uv run pytest tests/test_cli.py -q`、`uv run pytest -q`、`uv run ruff check .`。每个 Stage 完成后按仓库规则提交一次原子 commit，commit message 必须符合 Conventional Commits。

**Expected Verification Result:** 所有测试和 lint 通过，执行计划记录实际验证结果。
