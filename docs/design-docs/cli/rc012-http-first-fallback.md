# HTTP 优先回退直连设计

日期：2026-06-26

需求澄清文档：`docs/request-clarify/cli/rc012-http-first-fallback.md`

## 设计目标

CLI 连接选择从显式 mode 开关改为能力优先级：有 HTTP 地址时先构造 HTTP repository，HTTP 操作失败时使用同一份配置中的本地 SQLite repository 重试；没有 HTTP 地址时直接使用 SQLite。这样配置文件只描述可用连接材料，不再要求用户声明当前模式。

## 配置模型

| 字段 | 类型 | 新语义 |
| --- | --- | --- |
| `cli.mode` | `"direct" | "http" | None` | 兼容旧配置；存在时只校验合法性，不参与 CLI repository 选择 |
| `cli.http_base_url` | `str | None` | HTTP backend 地址；存在时 CLI 优先尝试 HTTP |
| `database.path` | `Path | None` | 本地 SQLite 路径；无 HTTP 地址时使用，HTTP 失败时作为回退 |
| `workspace.id` | `str` | HTTP 和 direct 共用的 workspace ID，继续只从 CLI 配置文件读取 |

配置读取继续使用 `load_cascading_config()` 合并 CLI 配置和全局配置。`cli.mode` 从必填字段改为可选字段，配置中存在非法 mode 时继续抛出 `ConfigCliModeInvalidError`。

## Repository 打开策略

| 条件 | 行为 |
| --- | --- |
| 有 `http_base_url` | `open_cli_repository()` 返回 HTTP 优先包装器 |
| HTTP 操作成功 | 直接返回 HTTP 操作结果 |
| HTTP 操作抛出 `ZembraHttpClientError` | 记录 warning，打开 direct repository，重试同一个方法 |
| 无 `http_base_url` | 直接打开 direct repository |
| direct 所需 `database.path` 或 `workspace.id` 缺失 | 沿用现有配置错误输出 |

HTTP 优先包装器只包装现有 repository 方法，不改命令层输出逻辑。direct repository 延迟到第一次回退时打开，并在 CLI context 退出时统一关闭连接。

## 文档影响

README 的 HTTP Mode 段落改为说明 `http_base_url` 是优先连接地址，`database.path` 是本地回退路径。`cli.mode` 不再出现在推荐配置示例中，避免继续引导用户手动选择模式。

## 测试策略

| 测试 | 覆盖 |
| --- | --- |
| 配置测试 | 缺少 `cli.mode` 时仍可加载 direct 或 HTTP 材料 |
| CLI HTTP 优先测试 | 有 HTTP 地址时命令调用 HTTP repository |
| CLI 回退测试 | HTTP 操作失败后同一命令使用 direct repository 成功 |
| CLI direct 测试 | 只有数据库配置时不要求 `cli.mode` |
| 文档回归 | README 不再要求配置 `[cli].mode` 来选择 HTTP |
