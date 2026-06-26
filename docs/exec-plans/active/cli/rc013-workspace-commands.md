# Workspace 命令执行计划

日期：2026-06-26

需求澄清文档：`docs/request-clarify/cli/rc013-workspace-commands.md`

设计文档：`docs/design-docs/cli/rc013-workspace-commands.md`

## Stage 1：配置与 HTTP workspace 查询

### Task 1.1：新增 workspace 命令配置读取与写入能力

状态：Finished

修改：`src/zembra_cli/config.py`、`tests/test_config.py`

功能：新增 workspace 命令专用配置读取函数，读取合并配置中的 `cli.http_base_url`，并把 CLI 配置中的 workspace 字段作为可选值返回；新增 `write_default_workspace()`，只更新 `~/.zembra/config.cli.toml` 的 `[workspace]` 段。

实现说明：读取函数不能写死默认 URL，缺少 `cli.http_base_url` 时返回明确配置错误；读取函数允许缺少 `workspace.id`，用于支持首次通过 `workspaces list` 查找可选 workspace。`write_default_workspace()` 保留配置文件中既有 `[cli]`、`[database]` 和其他字段，只更新 `workspace.id`，在 `workspace_name` 为 `None` 时删除旧的 `workspace.name`。

预期验证结果：配置中只有 `cli.http_base_url` 时 workspace 命令配置可加载；缺少 `cli.http_base_url` 时报错；写入默认 workspace 后 TOML 中其他字段不变；写入空名称时旧名称被移除。

### Task 1.2：新增 HTTP workspace 列表客户端

状态：Finished

修改：`src/zembra_cli/http_client.py`、`tests/test_http_client.py`

功能：在 HTTP 客户端中新增 `list_workspaces()`，请求后端 `GET /workspaces` 并返回 workspace 列表数据。

实现说明：请求 `/workspaces` 时不附加 `workspace_id` 查询参数。响应顶层必须包含 `workspaces` 数组，数组元素按 `workspace_id`、`workspace_name`、`short_hash`、`visible_note_count`、`latest_note_created_at` 校验。HTTP 状态错误、JSON 结构错误或字段校验失败统一转换为 `ZembraHttpClientError`。

预期验证结果：mock backend 收到 `GET /workspaces`；合法响应被解析为 workspace 记录；缺失 `workspaces`、非数组响应和非法字段都会抛出可读错误。

Stage 1 完成后提交：配置读写和 HTTP 客户端能力作为一个原子提交。

验证记录：2026-06-26 已运行 `uv run pytest tests/test_config.py tests/test_http_client.py -q`，35 个测试通过。

## Stage 2：CLI 命令实现

### Task 2.1：实现 `workspaces list`

状态：Designed

修改：`src/zembra_cli/cli.py`、`tests/test_cli.py`

功能：新增 `zembra-cli workspaces list`，通过配置中的 backend URL 动态查询 workspace 列表，默认表格输出，支持 `--json`。

实现说明：新增 `workspaces_app` 并注册到主 Typer app。默认表格列包含默认标记、短 hash、名称、完整 ID、可见 note 数和最近 note 时间；当前默认 workspace 来自 CLI 配置，缺少默认值时不标记任何行。`--json` 输出必须是纯 JSON，结构包含 `workspaces`、`default_workspace_id`，每个 workspace 项包含 `is_default`。

预期验证结果：有 `cli.http_base_url` 时命令调用 `/workspaces` 并输出表格；`--json` 可被 `json.loads()` 解析；配置缺少 backend URL 时命令失败；缺少默认 workspace 时仍可列出 workspace。

### Task 2.2：实现 `workspaces set-default <hash-or-name>`

状态：Designed

修改：`src/zembra_cli/cli.py`、`tests/test_cli.py`

功能：新增默认 workspace 设置命令，按完整 ID、短 hash 前缀或 workspace 名称精确匹配后写入 CLI 配置。

实现说明：命令先调用 `list_workspaces()` 获取后端真源列表，再统一收集匹配项。唯一匹配时调用 `write_default_workspace()`；无匹配时报错；多匹配时报错并列出候选 workspace 的短 hash、名称和完整 ID。后端返回 `workspace_name = null` 时写入 id 并移除旧 name。

预期验证结果：完整 ID、短 hash 前缀和名称三种输入都能在唯一匹配时更新配置；无匹配和多匹配都以非零退出码失败；成功输出包含已设置的 workspace 标识；配置文件不修改数据库路径和 backend URL。

Stage 2 完成后提交：CLI workspace 命令和对应测试作为一个原子提交。

## Stage 3：文档、验证与计划回写

### Task 3.1：更新用户文档

状态：Designed

修改：`README.md`、`README.zh-CN.md`

功能：补充 workspace 命令用法，说明 `workspaces list`、`workspaces list --json` 和 `workspaces set-default <hash-or-name>`。

实现说明：文档必须说明后端地址只来自 `cli.http_base_url`，不会使用默认 URL；`set-default` 会写入 `~/.zembra/config.cli.toml`。Markdown 自然段保持连续段落，不在段落内部硬换行。

预期验证结果：README 中包含 workspace 命令示例和配置前提；不引入与当前需求无关的 workspace 创建、删除或重命名说明。

### Task 3.2：运行整体验证并回写计划状态

状态：Designed

修改：`docs/exec-plans/active/cli/rc013-workspace-commands.md`

功能：运行定向测试、全量测试和 lint，并把完成状态与验证记录写回本计划。

实现说明：优先运行 `uv run pytest tests/test_config.py tests/test_http_client.py tests/test_cli.py -q`，再运行 `uv run pytest -q` 和 `uv run ruff check .`。如果发现失败，先修复再回写计划，不把失败状态标记为完成。

预期验证结果：定向测试、全量测试和 Ruff 检查全部通过；计划中对应任务状态更新为 Finished，并记录验证命令和结果。

Stage 3 完成后提交：文档、验证记录和计划状态回写作为一个原子提交。
