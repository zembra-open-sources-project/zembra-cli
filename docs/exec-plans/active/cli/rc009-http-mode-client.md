# CLI HTTP Mode Client 执行计划

日期：2026.05.03

需求澄清文档：`docs/request-clarify/cli/rc009-http-mode-client.md`

设计文档：`docs/design-docs/cli/rc009-http-mode-client.md`

## Stage 1：HTTP client 基础能力

### Task 1.1：新增依赖与 HTTP client 模块

状态：Finished

功能：新增 `httpx` 依赖，并实现面向 Zembra 后端的 HTTP client。

实现要点：

| 项目 | 说明 |
| --- | --- |
| 依赖 | `pyproject.toml` 增加 `httpx` |
| 请求封装 | 使用 `httpx.Client` 设置 base URL 和 timeout |
| 响应解析 | 将 JSON 响应解析为现有 Pydantic model |
| 错误封装 | 网络、HTTP 状态码、JSON 和 model 校验错误统一为自定义异常 |

预期测试结果：HTTP client 单元测试覆盖成功响应和错误响应。

### Task 1.2：实现 HTTP repository 兼容层

状态：Finished

功能：实现与 CLI 当前用法兼容的 HTTP repository。

实现要点：

| 方法 | HTTP API |
| --- | --- |
| `create_note` | `POST /notes` |
| `list_tags` | `GET /tags` |
| `list_fields` | `GET /fields` |
| `list_notes` | `GET /notes` |

预期测试结果：HTTP repository 返回 `NoteRecord`、`TagRecord`、`FieldRecord` 列表，和 SQLite repository 的调用形状一致。

## Stage 2：CLI 模式切换

### Task 2.1：新增 repository 协议和工厂

状态：Finished

功能：让 CLI 可以根据 `.zembra.env` 的 `[cli]` 配置选择 direct 或 HTTP repository。

实现要点：

| 项目 | 说明 |
| --- | --- |
| 协议 | 定义 CLI 当前依赖的 repository 方法集合 |
| 配置读取 | 复用现有 `load_config(default_config_path())` |
| 模式来源 | CLI 行为只读取 `[cli].mode`，不根据 `[database].path` 推断 |
| direct 模式 | `.zembra.env` 中 `cli.mode = "direct"` 时读取 `[database].path` 并直接访问 SQLite |
| HTTP 模式 | `.zembra.env` 中 `cli.mode = "http"` 时启用 |
| 配置缺失 | `[cli].mode` 缺失时报配置错误 |
| HTTP 配置 | HTTP 模式从 `cli.http_base_url` 读取后端地址 |
| HTTP 执行 | HTTP 模式不读取本地数据库路径，不执行 SQLite 初始化检查 |
| init 行为 | `init` 初始化本地 SQLite 后写出显式 `[cli].mode = "direct"` |

预期测试结果：`.zembra.env` 配置不同模式时分别进入对应 repository。

### Task 2.2：接入现有命令

状态：Finished

功能：让 `add`、`list tags`、`list fields`、`run` 支持 HTTP 模式。

实现要点：

| 命令 | 说明 |
| --- | --- |
| `add` | HTTP 模式调用 `POST /notes` 并保持输出 JSON 结构 |
| `list tags` | HTTP 模式调用 `GET /tags` 并保持紧凑输出 |
| `list fields` | HTTP 模式调用 `GET /fields` 并保持紧凑输出 |
| `run` | HTTP 模式启动统计来自 `GET /notes`，保存来自 `POST /notes` |

预期测试结果：现有命令在 HTTP 模式下输出格式与 direct 模式一致。

## Stage 3：验证与记录

### Task 3.1：补充测试

状态：Finished

功能：补充 HTTP client 和 CLI HTTP 模式测试。

实现要点：

| 测试范围 | 说明 |
| --- | --- |
| client 成功响应 | 覆盖 create/list |
| client 错误响应 | 覆盖结构化后端错误 |
| CLI 模式切换 | 验证 `.zembra.env` 中 HTTP 模式配置生效 |
| direct 回归 | 配置 direct 模式后保持现有 SQLite 行为通过 |
| 配置错误 | 缺少 `[cli].mode` 时返回配置错误 |

预期测试结果：新增测试和已有测试全部通过。

### Task 3.2：运行验证并更新计划

状态：Finished

功能：运行测试和必要的手动 HTTP 验证，更新本执行计划状态与验证记录。

实现要点：

| 命令 | 预期 |
| --- | --- |
| `uv run pytest` | 全部测试通过 |
| HTTP 手动验证 | 连接本地 `http://127.0.0.1:3000` 成功 |

预期测试结果：验证完成后记录结果。

## 验证记录

2026.05.03：已运行 `uv run pytest`，全部 107 个测试通过。

2026.05.03：已运行 `uv run ruff check .`，检查通过。

2026.05.03：已使用 `HttpZembraRepository("http://127.0.0.1:3000")` 对本地后端执行只读验证，成功读取 tags、fields、notes，数量分别为 4、3、7。
