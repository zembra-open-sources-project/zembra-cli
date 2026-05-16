# Random Notes CLI 需求澄清

日期：2026.05.16

## 背景

当前后端服务运行在 `http://127.0.0.1:3000`，OpenAPI 文档地址为 `http://127.0.0.1:3000/api-docs/openapi.json`。后端已经实现随机笔记相关接口，CLI 当前已支持 direct 和 HTTP 两种连接模式，但尚未暴露随机笔记命令。

## 已确认需求

| 项目 | 结论 |
| --- | --- |
| 主命令 | 使用 `zembra-cli random notes -n 3` |
| 随机普通笔记 | 支持从全部可见笔记中随机返回指定数量笔记 |
| 随机 tag 分组 | 同时支持按随机 tag 分组返回笔记 |
| 随机 field 分组 | 同时支持按随机 field 分组返回笔记 |
| 连接模式 | direct SQLite 模式和 HTTP 模式都必须支持 |
| 默认输出 | 默认使用人类可读格式 |
| JSON 输出 | 增加 `--json`，返回 JSON 形式内容 |
| 内容完整性 | 默认人类可读输出也必须忠实返回笔记完整内容，不做摘要截断 |
| 元数据完整性 | 输出必须包含笔记关联的 field 和 tags |
| 摘要概念 | 不引入内容摘要概念 |

## 后端 OpenAPI 对照

| 能力 | HTTP 接口 | 参数 | 响应 |
| --- | --- | --- | --- |
| 随机笔记 | `GET /random/notes` | `n`：返回笔记数量，必填 | `{ "notes": [...] }` |
| 随机 tag 分组 | `GET /random/tags` | `n`：随机 tag 数量；`count`：累计笔记数上限 | `{ "tagged_notes": [...] }` |
| 随机 field 分组 | `GET /random/fields` | `n`：随机 field 数量；`count`：累计笔记数上限 | `{ "field_notes": [...] }` |

后端接口返回的笔记为可见笔记，即非删除、非归档笔记。CLI direct 模式需要保持同样语义。

## CLI 命令范围

| 命令 | 说明 |
| --- | --- |
| `zembra-cli random notes -n 3` | 返回 3 条随机可见笔记 |
| `zembra-cli random notes -n 3 --json` | 以 JSON 返回随机可见笔记 |
| `zembra-cli random tags -n 2 --count 5` | 随机选 2 个 tag，累计返回最多 5 条可见笔记 |
| `zembra-cli random tags -n 2 --count 5 --json` | 以 JSON 返回随机 tag 分组笔记 |
| `zembra-cli random fields -n 2 --count 5` | 随机选 2 个 field，累计返回最多 5 条可见笔记 |
| `zembra-cli random fields -n 2 --count 5 --json` | 以 JSON 返回随机 field 分组笔记 |

## 输出规则

| 输出模式 | 规则 |
| --- | --- |
| 人类可读 | 展示完整 note id、完整 content、role、field、tags、created_at、updated_at |
| 人类可读分组 | 先展示 tag 或 field 名称，再展示该组下每条笔记完整信息 |
| JSON | 输出结构化 JSON，包含 notes 或分组列表 |
| field | 输出 field 名称；无 field 时返回 `null` 或等价空值 |
| tags | 输出 tag 名称列表；无 tag 时返回空列表 |
| 内容 | 不截断、不压缩、不摘要；保留笔记完整内容 |

## 仓库现状关联

| 模块 | 当前状态 | 本需求关系 |
| --- | --- | --- |
| `src/zembra_cli/cli.py` | 已有 Typer app、`list` 子命令和 repository 工厂 | 新增 `random` 子命令组 |
| `src/zembra_cli/http_client.py` | 已实现 HTTP repository 基础请求和响应解析 | 新增 random 接口方法 |
| `src/zembra_cli/repository/protocol.py` | 当前协议只覆盖 add、list、run 依赖方法 | 扩展 random 相关协议 |
| `src/zembra_cli/repository/notes.py` | 已能 list notes，但没有随机查询和关联元数据聚合 | 新增 direct 模式随机查询能力 |
| `src/zembra_cli/repository/field_tag.py` | 已能读取 note tags 和 fields | 为 random 输出补齐 field 和 tags |
| `src/zembra_cli/models.py` | 已有 `NoteRecord`、`FieldRecord`、`TagRecord` | 可能需要新增 CLI 输出 DTO |
| `tests/test_http_client.py` | 已覆盖 HTTP repository 基础能力 | 增加 random endpoint 测试 |
| `tests/test_cli.py` | 已覆盖 CLI direct / HTTP 模式切换 | 增加 random 命令测试 |

## 本阶段范围

| 纳入 | 不纳入 |
| --- | --- |
| random notes、random tags、random fields 三类命令 | Web UI 随机笔记功能 |
| direct 和 HTTP 双模式 | 后端接口实现修改 |
| 人类可读和 JSON 双输出 | 交互式随机浏览 TUI |
| 完整 note content、field、tags 输出 | note 编辑、归档、删除等管理命令 |
| 参数校验和错误输出 | 认证、安全传输、重试策略 |
| 单元测试覆盖 direct、HTTP 和 CLI 输出 | 性能优化或缓存策略 |

## 待设计确认点

| 问题 | 当前建议 |
| --- | --- |
| `-n` 默认值 | 设计阶段结合命令易用性确定，建议 notes 默认为 3，tags/fields 默认为 2 |
| `--count` 默认值 | 设计阶段结合后端默认行为确定，建议 CLI 显式给出合理默认值 |
| JSON 字段名 | 优先贴近后端：`notes`、`tagged_notes`、`field_notes` |
| direct 随机算法 | 使用 SQLite 随机排序能力实现，与后端可见笔记语义保持一致 |

## 验收标准

| 场景 | 预期 |
| --- | --- |
| HTTP 模式执行 `random notes -n 3` | 调用 `/random/notes?n=3`，输出 3 条以内完整可见笔记 |
| HTTP 模式执行 `random tags -n 2 --count 5` | 调用 `/random/tags?n=2&count=5`，输出随机 tag 分组及完整笔记 |
| HTTP 模式执行 `random fields -n 2 --count 5` | 调用 `/random/fields?n=2&count=5`，输出随机 field 分组及完整笔记 |
| direct 模式执行三类 random 命令 | 直接查询 SQLite，输出语义与 HTTP 模式一致 |
| 增加 `--json` | 输出可解析 JSON，不混入 Rich 样式文本 |
| 默认输出 | 人类可读，包含完整 content、field 和 tags |
| `-n` 或 `--count` 非正数 | CLI 返回清晰参数错误并以非 0 退出 |
| 无匹配数据 | 命令成功返回空列表或空分组，不报错 |
| 后端不可达 | HTTP 模式沿用现有清晰错误输出 |
| 现有命令 | `add`、`list tags`、`list fields`、`run` 行为不回归 |
