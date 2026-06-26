# Workspace 命令设计

日期：2026-06-26

需求澄清文档：`docs/request-clarify/cli/rc013-workspace-commands.md`

## 核心功能（WHAT）

新增 `zembra-cli workspaces` 命令组，提供 `list` 和 `set-default` 两个子命令。`list` 通过配置中的后端地址请求 `GET /workspaces`，默认以表格展示所有 workspace，并支持 `--json` 输出。`set-default <hash-or-name>` 使用同一接口查询可选 workspace，根据完整 `workspace_id`、`short_hash` 前缀或 `workspace_name` 精确匹配唯一 workspace，并把结果写入 `~/.zembra/config.cli.toml` 的 `[workspace]` 配置。

### 需求背景（WHY）

当前 CLI 已经用 `[workspace].id` 作为业务命令的 workspace 上下文，但用户缺少从后端查看所有 workspace 并切换默认 workspace 的入口。后端已经提供 workspace 列表接口，本需求让 CLI 能基于后端当前数据完成默认 workspace 选择，避免用户手工编辑配置文件。

### 需求目标（GOAL）

本需求目标是在不改变既有 note、field、tag 命令语义的前提下，让用户可以通过 `zembra-cli workspaces list` 查看后端所有 workspace，并通过 `zembra-cli workspaces set-default <hash-or-name>` 安全更新 CLI 默认 workspace。命令必须只从配置读取后端地址，配置缺少可用后端地址时直接报错，不写死任何默认 URL。

### 范围边界

| 类别 | 设计结论 |
| --- | --- |
| 新增命令 | `zembra-cli workspaces list`、`zembra-cli workspaces set-default <hash-or-name>` |
| 后端地址 | 优先读取级联合并后的 `cli.http_base_url`；缺失时读取配置中的 `server.host` 和 `server.port` 组装 URL |
| 后端接口 | 使用 `GET /workspaces` |
| 输出形态 | `list` 默认 Rich 表格，`--json` 输出 JSON |
| 当前默认标记 | 基于配置中的 `workspace.id` 标记，不要求当前默认一定存在于后端列表 |
| 设置默认值 | 只写 CLI 配置文件 `~/.zembra/config.cli.toml` |
| 不纳入范围 | 不创建、不删除、不重命名、不归档 workspace；不实现本地 SQLite workspace 列表；不修改后端接口 |

## 实现流程（HOW）

### 数据模型

新增用于 HTTP workspace 列表的轻量模型，建议放在 `src/zembra_cli/http_client.py` 或 `src/zembra_cli/models.py`。如果模型只服务 HTTP 客户端，可以先放在 `http_client.py`，避免扩大共享模型边界；如果后续 CLI 输出和测试需要复用，再提取到 `models.py`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `workspace_id` | `str` | 后端返回的完整 workspace ID |
| `workspace_name` | `str | None` | 可选显示名 |
| `short_hash` | `str` | 后端返回的短 hash |
| `visible_note_count` | `int` | 可见 note 数量 |
| `latest_note_created_at` | `int | None` | 最近 note 创建时间 |

HTTP 响应校验保持当前 `HttpZembraRepository` 的风格：顶层必须包含 `workspaces`，类型错误、字段缺失或模型校验失败时抛出 `ZembraHttpClientError`，错误消息适合 CLI 直接展示。

### HTTP client

在 `HttpZembraRepository` 中新增 `list_workspaces()`，请求 `GET /workspaces`，不附加 `workspace_id` 查询参数。workspace 列表接口用于选择 workspace，本身不依赖当前默认 workspace。该方法复用 `_request_json()`、`_require_key()` 和模型解析辅助函数，保持 HTTP 错误处理一致。

### 配置写入

在 `src/zembra_cli/config.py` 新增专用函数 `write_default_workspace(workspace_id, workspace_name, config_path=None)`。该函数只读取和写入目标 CLI TOML 文件中的 `[workspace]` 段，不修改 `[database]`、`[cli]` 或其他已存在配置。`workspace_name` 为字符串时写入 `name`，为 `None` 时删除旧的 `name` 字段。目标目录不存在时沿用现有配置写入风格，调用方负责创建默认 CLI 配置目录或函数内部创建父目录；为了与 `set-default` 的用户场景一致，推荐函数内部创建父目录。

### CLI 命令

在 `src/zembra_cli/cli.py` 新增 `workspaces_app = typer.Typer(...)` 并注册到主 app。新增辅助函数读取配置并打开 workspace HTTP 客户端：先调用 workspace 命令专用配置读取函数，从 CLI 配置和全局配置级联读取后端地址；优先使用 `cli.http_base_url`，缺失时使用配置中的 `server.host` 和 `server.port` 组装 URL；如果 workspace ID 缺失则允许 `list` 继续展示但无法标记默认值。当前通用配置加载函数会要求 workspace ID，本轮实现需要保留只读取 HTTP backend 地址和可选 workspace 的配置读取路径，避免 `workspaces list` 在没有默认 workspace 时无法列出可选项。

`workspaces list` 默认表格列建议为 `Default`、`Hash`、`Name`、`Workspace ID`、`Notes`、`Latest Note`。默认标记使用 `*`，名称为空时显示空字符串或 `-`，最近 note 时间为空时显示 `-`。`--json` 输出结构建议为 `{"workspaces": [...], "default_workspace_id": "...或null"}`，每个 workspace 项额外包含 `is_default` 布尔值。

`workspaces set-default <hash-or-name>` 调用 `list_workspaces()` 后匹配目标。匹配顺序不需要短路，先收集所有满足条件的 workspace，再按数量判断。匹配条件为完整 `workspace_id` 相等、`short_hash` 以输入为前缀、`workspace_name` 与输入完全相等。无匹配时报错；多匹配时报错并列出候选的 `short_hash`、名称和完整 ID；唯一匹配时调用 `write_default_workspace()` 并输出成功信息。

### 配置读取调整

当前 `load_cascading_config()` 会强制要求 workspace 字段存在，而 `workspaces list` 的目标之一是帮助用户找到并设置默认 workspace。因此设计上需要新增低风险的内部读取函数，例如 `load_workspace_command_config(cli_config_path, global_config_path)`，返回可用后端 URL 和可选 `workspace_id`、`workspace_name`，同时保留非法 TOML、非法 `cli.mode`、缺少所有连接材料等现有错误风格。这个函数只供 workspace 命令使用，不替代业务命令的配置读取入口。

## 测试用例

| 类型 | 用例 | 预期 |
| --- | --- | --- |
| 配置测试 | workspace 命令配置读取缺少 `workspace.id` 但存在 `cli.http_base_url` | 可读取后端地址，默认 workspace 为 `None` |
| 配置测试 | workspace 命令配置读取缺少 `cli.http_base_url` 但存在 `server.host` 和 `server.port` | 可从配置组装后端地址 |
| 配置测试 | `write_default_workspace()` 写入名称 | `[workspace].id` 和 `[workspace].name` 正确写入，其他段保留 |
| 配置测试 | `write_default_workspace()` 收到 `workspace_name = None` | 更新 id 并删除旧 name |
| HTTP client 测试 | `list_workspaces()` 请求 `/workspaces` | 返回 workspace 列表模型 |
| HTTP client 测试 | 后端返回缺失或非法 `workspaces` | 抛出 `ZembraHttpClientError` |
| CLI 测试 | `workspaces list` 默认输出 | 表格包含 hash、名称、ID、note 数和默认标记 |
| CLI 测试 | `workspaces list --json` | stdout 是合法 JSON，包含 `is_default` |
| CLI 测试 | 缺少可用后端地址 | 命令失败并提示配置后端地址 |
| CLI 测试 | `set-default` 使用完整 ID、短 hash 前缀、名称 | 唯一匹配时更新配置 |
| CLI 测试 | `set-default` 无匹配或多匹配 | 命令失败并展示可操作错误信息 |
| 回归检查 | 现有 note、list、random、run 配置读取 | 既有测试继续通过 |
