# CLI HTTP Mode Client 需求澄清

日期：2026.05.03

## 背景

当前后端服务已启动，OpenAPI 文档地址为 `http://127.0.0.1:3000/api-docs/openapi.json`。后端已经实现基础 note、field、tag 和 health 接口。当前 CLI 只支持通过本地 SQLite 配置连接数据库，本需求希望新增 httpclient，让 CLI 可以通过 HTTP 模式连接后端数据库服务。

## 已确认需求

| 项目 | 结论 |
| --- | --- |
| HTTP 模式配置 | 通过已有 `.zembra.env` TOML 配置读取体系完成，放在 `[cli]` 分节 |
| HTTP 客户端依赖 | 新增 `httpx`，采用现代 HTTP client 实现 |
| `init` 命令行为 | 保持现状，只负责本地 SQLite 初始化 |
| CLI 命令行为 | 优先复用现有命令面，不新增重复的 HTTP 专用命令 |
| 后端服务地址 | 开发验证以 `http://127.0.0.1:3000` 为目标 |

## API 可用性判断

| 检查项 | 结果 |
| --- | --- |
| `GET /api-docs/openapi.json` | 返回 `200 OK`，OpenAPI JSON 可解析 |
| `GET /health` | 返回 `status=ok`，`database_initialized=true` |
| `GET /tags` | 返回 tags 与 names |
| `GET /fields` | 返回 fields 与 names |
| `GET /notes?limit=3` | 返回 notes |
| `POST /notes` 空内容探测 | 返回 `422 validation_error`，说明请求校验生效 |

## API 文档问题

OpenAPI 中 `/fields` 和 `/tags` 的 `limit`、`all` 参数标注为 `in: path`，但路径本身没有 `{limit}` 或 `{all}` 占位符。实际接口接受 query 参数，也支持不传参数直接访问。

本需求实现手写 httpclient，可以按实际可用接口调用，不依赖 OpenAPI generator。后续如果需要生成客户端，应先修复后端 OpenAPI 参数位置。

## CLI 与 API 对照

| CLI 能力 | 当前实现 | API 对应 | 结论 |
| --- | --- | --- | --- |
| `zembra-cli add` | `ZembraRepository.create_note` | `POST /notes` | 可覆盖 |
| `zembra-cli list tags` | `ZembraRepository.list_tags` | `GET /tags` | 可覆盖 |
| `zembra-cli list fields` | `ZembraRepository.list_fields` | `GET /fields` | 可覆盖 |
| `zembra-cli run` | 启动读取 note 数量，循环创建 note | `GET /notes`、`POST /notes` | 可覆盖 |
| note 引用解析辅助 | 本地 prefix 查询 | 后端 note_ref 接口内部处理 | 当前无 CLI 命令依赖，不阻塞 |
| update、archive、delete、revisions、note tags | Repository 已有，CLI 未暴露 | API 已提供 | 作为后续扩展能力 |

## 范围边界

本需求只让现有 CLI 命令支持 HTTP 模式连接数据库。远端服务启动、远端数据库初始化、认证、安全传输、重试策略和未来未暴露命令不纳入本次实现。

## 验收标准

| 场景 | 预期 |
| --- | --- |
| `.zembra.env` 配置 direct 模式 | CLI 读取 `[database].path` 并直接访问本地 SQLite |
| `.zembra.env` 配置 HTTP 模式 | `add`、`list tags`、`list fields`、`run` 通过 HTTP 访问后端 |
| `.zembra.env` 缺少 `[cli].mode` | 配置错误，不根据 `[database].path` 推断模式 |
| 后端不可达 | CLI 输出清晰错误并返回非 `0` |
| 后端返回结构化错误 | CLI 输出后端错误 message 或 code |
| 现有测试 | direct 模式下现有本地 SQLite 行为保持通过 |
| 新增测试 | HTTP client 和 CLI 模式切换有覆盖 |
