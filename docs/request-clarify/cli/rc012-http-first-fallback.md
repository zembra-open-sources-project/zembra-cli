# HTTP 优先回退直连需求澄清

日期：2026-06-26

## 背景

当前 CLI 通过配置文件中的 `[cli].mode` 在 HTTP backend 和本地 SQLite 直连之间二选一。用户希望取消配置文件中的模式开关，运行时优先尝试 HTTP 连接，HTTP 调用失败后自动回退为本地数据库直连。

## 范围

| 项目 | 结论 |
| --- | --- |
| 连接选择 | CLI 命令优先使用 `cli.http_base_url` 指向的 HTTP backend |
| 回退策略 | HTTP repository 操作抛出 HTTP client 错误后，自动使用配置中的 `database.path` 打开本地 SQLite repository 重试同一个操作 |
| 配置模式 | `cli.mode` 不再作为必填字段，也不再决定 CLI 命令使用 HTTP 或 direct |
| 旧配置兼容 | 如果旧配置仍包含 `cli.mode = "direct"` 或 `cli.mode = "http"`，读取时允许保留；非法值继续报错，避免静默吞掉拼写错误 |
| 缺少 HTTP 地址 | 没有 `cli.http_base_url` 时直接使用本地数据库，不视为错误 |
| 缺少数据库路径 | HTTP 失败且没有 `database.path` 时返回数据库路径缺失错误 |
| 工作区 | 继续要求 `workspace.id` 存在，HTTP 和 direct 都使用同一个 workspace ID |
| MCP | MCP server 继续只使用 direct SQLite，不参与 HTTP 优先回退 |

## 非目标

- 不改后端 HTTP API。
- 不新增多 profile 或多 backend 配置。
- 不自动迁移或删除用户已有的 `cli.mode` 字段。
- 不改变本地数据库 schema、workspace 语义或现有命令输出格式。

## 验收标准

| 场景 | 预期 |
| --- | --- |
| 配置同时包含 `cli.http_base_url`、`database.path` 和 `workspace.id` | CLI 命令优先调用 HTTP repository |
| HTTP repository 抛出 `ZembraHttpClientError` 且本地数据库可用 | CLI 自动回退 direct repository，并完成同一个命令 |
| 配置只有 `database.path` 和 `workspace.id` | CLI 使用 direct repository，不要求 `cli.mode` |
| 配置只有 `cli.http_base_url` 和 `workspace.id` | HTTP 成功时可运行；HTTP 失败时报数据库路径缺失 |
| 配置包含非法 `cli.mode` | 继续返回 mode 非法配置错误 |
