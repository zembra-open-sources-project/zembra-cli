# CLI HTTP Mode Client 设计文档

日期：2026.05.03

需求澄清文档：`docs/request-clarify/cli/rc009-http-mode-client.md`

## 核心功能

为 zembra-cli 增加 HTTP repository 实现。CLI 根据 `.zembra.env` 的 `[cli]` 分节选择 direct 模式或 HTTP 模式，让现有命令可以连接数据库。

## 设计目标

| 目标 | 说明 |
| --- | --- |
| 命令复用 | 不新增 HTTP 专用命令，复用 `add`、`list`、`run` |
| 配置文件驱动 | 通过已有 `.zembra.env` 启用 HTTP 模式并提供 base URL |
| 类型兼容 | HTTP 返回值解析为现有 Pydantic model |
| 错误清晰 | 网络错误、HTTP 错误和响应结构错误转成 CLI 可读失败 |
| direct 不回归 | `[cli].mode = "direct"` 时保持当前直接访问 SQLite 的行为 |

## 配置设计

`.zembra.env` 继续使用 TOML。CLI 的连接行为只由 `[cli]` 分节管理；`[database].path` 只在 `[cli].mode = "direct"` 时作为 direct 模式的 SQLite 数据库路径读取。

| 配置项 | 示例 | 说明 |
| --- | --- | --- |
| `cli.mode` | `"direct"` 或 `"http"` | CLI 连接模式；必填 |
| `cli.http_base_url` | `"http://127.0.0.1:3000"` | HTTP 模式后端地址 |
| `database.path` | `"/path/to/zembra.sqlite3"` | direct 模式 SQLite 数据库路径 |

direct 配置示例：

```toml
[cli]
mode = "direct"

[database]
path = "/path/to/zembra.sqlite3"
```

HTTP 配置示例：

```toml
[cli]
mode = "http"
http_base_url = "http://127.0.0.1:3000"
```

规则：缺少 `[cli].mode` 时视为配置错误。HTTP 模式不读取 `[database].path`，direct 模式必须读取并校验 `[database].path`。

## 模块设计

| 模块 | 职责 |
| --- | --- |
| `src/zembra_cli/http_client.py` | 封装 `httpx.Client`、请求、响应解析和 HTTP 错误 |
| `src/zembra_cli/repository/protocol.py` | 定义 CLI 当前需要的 repository 协议 |
| `src/zembra_cli/config.py` | 扩展 `.zembra.env` 读取模型，支持 HTTP 模式 |
| `src/zembra_cli/cli.py` | 根据配置创建 SQLite 或 HTTP repository |
| `src/zembra_cli/interactive.py` | 将 repository 类型收窄到协议，去除对 SQLite 异常的强绑定 |

## Repository 协议

| 方法 | 用途 |
| --- | --- |
| `create_note(content, role="Human", field_name=None, tag_names=None, device_id=None)` | `add` 和 `run` 创建 note |
| `list_tags()` | `list tags` |
| `list_fields()` | `list fields` |
| `list_notes(include_deleted=False)` | `run` 启动统计 |

当前 CLI 只依赖这些方法。SQLite repository 已经天然满足协议，HTTP repository 实现同名方法即可。

## HTTP API 映射

| Repository 方法 | HTTP 请求 | 响应处理 |
| --- | --- | --- |
| `create_note` | `POST /notes` | 读取 `note` 字段并解析为 `NoteRecord` |
| `list_tags` | `GET /tags` | 读取 `tags` 字段并解析为 `TagRecord` 列表 |
| `list_fields` | `GET /fields` | 读取 `fields` 字段并解析为 `FieldRecord` 列表 |
| `list_notes` | `GET /notes` | 读取 `notes` 字段并解析为 `NoteRecord` 列表 |

`list_tags` 和 `list_fields` 的数量截断继续由 CLI 层执行，保持 SQLite 与 HTTP 输出一致。

## 错误处理

| 场景 | 处理 |
| --- | --- |
| 缺少 `cli.mode` | 读取配置时抛出配置错误 |
| `cli.mode` 非法 | 读取配置时抛出配置错误 |
| HTTP 模式缺少 `cli.http_base_url` | 读取配置时抛出配置错误 |
| direct 模式缺少 `database.path` | 读取配置时抛出配置错误 |
| base URL 非法 | 创建 HTTP repository 时抛出配置错误 |
| 连接失败或超时 | 输出 `Could not connect to Zembra backend: ...` |
| 非 2xx 响应 | 优先读取 `error.message`，否则输出状态码 |
| JSON 无法解析 | 输出响应格式错误 |
| JSON 字段缺失或 model 校验失败 | 输出响应格式错误 |

HTTP 错误统一封装为自定义异常，让 CLI 和 interactive 可以用同一套自然语言输出。

## CLI 调整

| 命令 | 调整 |
| --- | --- |
| `add` | 通过配置和 repository 工厂获得 SQLite 或 HTTP repository |
| `list tags` | 同上 |
| `list fields` | 同上 |
| `run` | 同上，启动文案在 HTTP 模式下显示后端 URL |
| `init` | 继续只初始化本地 SQLite，同时写出显式 `[cli].mode = "direct"` |
| `config database` | 保持写入 SQLite 数据库路径；不隐式设置 `[cli].mode` |

## 依赖调整

在 `pyproject.toml` 的运行依赖中新增 `httpx`。锁文件通过 `uv lock` 更新。

## 测试设计

| 测试 | 预期 |
| --- | --- |
| HTTP client create note | 正确发送 JSON 并解析 `NoteRecord` |
| HTTP client list tags | 正确解析 `tags` |
| HTTP client list fields | 正确解析 `fields` |
| HTTP client error response | 结构化错误转为自定义异常 |
| CLI HTTP add | `.zembra.env` 配置 HTTP 模式后不读取 SQLite 数据库路径，输出 JSON |
| CLI HTTP list | `.zembra.env` 配置 HTTP 模式后通过 HTTP 输出 names |
| CLI direct 回归 | `.zembra.env` 配置 `[cli].mode = "direct"` 时现有 SQLite 行为保持通过 |
| CLI 配置缺失 | `.zembra.env` 缺少 `[cli].mode` 时返回配置错误 |

## 预期改动范围

| 文件 | 改动 |
| --- | --- |
| `pyproject.toml` | 新增 `httpx` 依赖 |
| `uv.lock` | 更新依赖锁 |
| `src/zembra_cli/http_client.py` | 新增 HTTP client 与异常 |
| `src/zembra_cli/config.py` | 扩展配置模型和 HTTP 模式校验 |
| `src/zembra_cli/repository/protocol.py` | 新增 repository 协议 |
| `src/zembra_cli/cli.py` | 新增 repository 工厂和 HTTP 模式接入 |
| `src/zembra_cli/interactive.py` | 接收 repository 协议并处理 HTTP 错误 |
| `tests/test_http_client.py` | 新增 HTTP client 单元测试 |
| `tests/test_cli.py` | 新增 HTTP 模式 CLI 测试 |
