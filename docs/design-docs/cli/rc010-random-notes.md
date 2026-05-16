# Random Notes CLI 设计文档

日期：2026.05.16

需求澄清文档：`docs/request-clarify/cli/rc010-random-notes.md`

## 核心功能（WHAT）

为 `zembra-cli` 增加 `random` 子命令组，支持在 direct SQLite 模式和 HTTP 模式下随机读取可见笔记，并提供普通笔记、按 tag 分组、按 field 分组三种随机视图。

## 需求背景（WHY）

后端已经通过 OpenAPI 暴露随机笔记接口，但 CLI 仍只能新增笔记、列出 taxonomy 和进入交互写入模式。用户需要在命令行中随机回看已有笔记，并且输出必须保留完整内容与关联元数据，不能用摘要替代原文。

## 需求目标（GOAL）

| 目标 | 说明 |
| --- | --- |
| 命令完整 | 增加 `random notes`、`random tags`、`random fields` |
| 双模式一致 | direct 和 HTTP 模式都支持相同命令与输出结构 |
| 内容忠实 | 人类可读输出展示完整 content、field、tags，不截断、不摘要 |
| 脚本友好 | 每个 random 命令支持 `--json` 输出可解析 JSON |
| 后端对齐 | HTTP 模式调用后端现有 `/random/*` 接口 |
| 现有能力不回归 | `add`、`list`、`run` 和配置模式切换保持现状 |

## 范围边界

| 纳入范围 | 不纳入范围 |
| --- | --- |
| `zembra-cli random notes -n 3` | 后端随机接口实现修改 |
| `zembra-cli random tags -n 2 --count 5` | Web UI 或 TUI 随机浏览 |
| `zembra-cli random fields -n 2 --count 5` | note 编辑、归档、删除命令 |
| `--json` 结构化输出 | 认证、安全传输、重试策略 |
| direct SQLite 随机查询 | 性能优化或缓存策略 |
| HTTP random endpoint 解析 | 数据库 schema 迁移 |
| 自动化测试 | 用户手工 UI 测试 |

## 实现流程（HOW）

### 命令设计

新增 `random_app = typer.Typer(help="Show random zembra notes.")`，并挂载到主 app：

| 命令 | 参数 | 行为 |
| --- | --- | --- |
| `random notes` | `-n/--number`，默认 `3`；`--json` | 返回随机可见笔记 |
| `random tags` | `-n/--number`，默认 `2`；`--count`，默认 `5`；`--json` | 随机选 tag 并返回分组笔记 |
| `random fields` | `-n/--number`，默认 `2`；`--count`，默认 `5`；`--json` | 随机选 field 并返回分组笔记 |

参数校验放在 CLI 层，`number` 和 `count` 必须大于等于 1。校验失败时沿用 `fail_command(...)` 输出清晰错误并返回非 0。

### 数据模型设计

为 random 输出增加轻量 Pydantic DTO，建议放在 `src/zembra_cli/models.py`，复用现有 `NoteRecord`、`FieldRecord`、`TagRecord`。

| 模型 | 字段 | 说明 |
| --- | --- | --- |
| `NoteWithMetadata` | `note: NoteRecord`、`field: FieldRecord | None`、`tags: list[TagRecord]` | CLI 展示单条笔记所需完整信息 |
| `TaggedNotesGroup` | `tag: TagRecord`、`notes: list[NoteWithMetadata]` | tag 分组随机结果 |
| `FieldNotesGroup` | `field: FieldRecord`、`notes: list[NoteWithMetadata]` | field 分组随机结果 |

JSON 输出保持和后端顶层字段一致：

| 命令 | JSON 顶层字段 |
| --- | --- |
| `random notes --json` | `notes` |
| `random tags --json` | `tagged_notes` |
| `random fields --json` | `field_notes` |

`notes` 中的每个元素使用 `NoteWithMetadata` 的完整结构。HTTP 后端当前 `/random/notes` 只返回 note record，CLI 需要为 HTTP 模式补充每条 note 的 field 和 tags；direct 模式也返回同样结构。

### Repository 协议设计

扩展 `CliRepository` 协议，使 CLI 不关心 direct 或 HTTP 实现。

| 方法 | 返回 | 用途 |
| --- | --- | --- |
| `random_notes(number)` | `list[NoteWithMetadata]` | `random notes` |
| `random_tagged_notes(number, count)` | `list[TaggedNotesGroup]` | `random tags` |
| `random_field_notes(number, count)` | `list[FieldNotesGroup]` | `random fields` |

### Direct 模式设计

在 `ZembraRepository` 中实现随机查询，语义与后端保持一致：只返回 `deleted_at IS NULL AND archived_at IS NULL` 的可见笔记。

| 能力 | 实现方式 |
| --- | --- |
| 随机笔记 | `SELECT * FROM notes WHERE deleted_at IS NULL AND archived_at IS NULL ORDER BY RANDOM() LIMIT ?` |
| 笔记 field | 根据 `note.field_id` 查询 `fields` |
| 笔记 tags | 复用 `list_note_tags(note.id)` |
| 随机 tag | 从至少关联一条可见笔记的 tag 中 `ORDER BY RANDOM() LIMIT ?` |
| tag 下笔记 | 查询该 tag 下可见笔记，按随机或稳定顺序取剩余 `count` |
| 随机 field | 从至少关联一条可见笔记的 field 中 `ORDER BY RANDOM() LIMIT ?` |
| field 下笔记 | 查询该 field 下可见笔记，按随机或稳定顺序取剩余 `count` |

`count` 是跨分组的累计笔记上限。实现时按随机选出的 group 顺序分配剩余数量；剩余数量为 0 后停止追加笔记。

### HTTP 模式设计

在 `HttpZembraRepository` 中新增 random 方法。

| 方法 | HTTP 请求 | 响应处理 |
| --- | --- | --- |
| `random_notes(number)` | `GET /random/notes?n={number}` | 解析 `notes`，再补齐 metadata |
| `random_tagged_notes(number, count)` | `GET /random/tags?n={number}&count={count}` | 解析 `tagged_notes`，再补齐每条 note metadata |
| `random_field_notes(number, count)` | `GET /random/fields?n={number}&count={count}` | 解析 `field_notes`，再补齐每条 note metadata |

后端已有 `GET /notes/{note_ref}/tags` 可以补齐 tags。field 需要根据 note 的 `field_id` 与 `/fields` 返回的 field 列表匹配；为避免每条 note 重复请求，HTTP repository 在一次 random 方法调用中读取一次 `/fields` 并建立 `field_id -> FieldRecord` 映射。

### 输出设计

CLI 层新增格式化函数，保证 direct 和 HTTP 共用输出。

| 函数 | 用途 |
| --- | --- |
| `note_with_metadata_to_dict(...)` | 生成 JSON 兼容字典 |
| `render_random_notes(...)` | 人类可读展示普通随机笔记 |
| `render_random_tagged_notes(...)` | 人类可读展示 tag 分组 |
| `render_random_field_notes(...)` | 人类可读展示 field 分组 |

人类可读输出使用简单稳定文本，不使用表格承载 content，避免长文本或多行笔记被表格压缩。建议格式：

```text
abcd1234...  Human
Field: dev
Tags: cli, notes
Created: 1777279791
Updated: 1777279791
Content:
完整笔记内容
```

分组输出先展示 group 标题，再展示组内笔记：

```text
# tag: cli

abcd1234...  Human
Field: dev
Tags: cli, notes
Created: 1777279791
Updated: 1777279791
Content:
完整笔记内容
```

JSON 输出使用 `json.dumps(..., ensure_ascii=False)`，不混入 Rich 样式文本。

### 错误处理

| 场景 | 处理 |
| --- | --- |
| `number < 1` | CLI 输出 `Number must be greater than or equal to 1.` |
| `count < 1` | CLI 输出 `Count must be greater than or equal to 1.` |
| HTTP 后端不可达 | 沿用 `ZembraHttpClientError` |
| HTTP 响应缺字段 | 沿用 HTTP client response shape 错误 |
| 无随机结果 | 命令成功输出空结果；JSON 输出空列表 |
| direct 数据库未初始化 | 沿用现有 direct 模式数据库检查 |

## 测试用例

### 编译检查

| 检查 | 预期 |
| --- | --- |
| `uv run pytest tests/test_http_client.py -q` | HTTP random 方法测试通过 |
| `uv run pytest tests/test_repository.py -q` | direct random 查询测试通过 |
| `uv run pytest tests/test_cli.py -q` | CLI random 命令测试通过 |
| `uv run pytest -q` | 全量测试通过 |

### 自动化测试

| 测试 | 预期 |
| --- | --- |
| direct `random_notes` | 只返回未删除、未归档笔记，并包含 field、tags |
| direct `random_tagged_notes` | 只选择有可见笔记的 tag，累计笔记数不超过 count |
| direct `random_field_notes` | 只选择有可见笔记的 field，累计笔记数不超过 count |
| HTTP `random_notes` | 请求 `/random/notes?n=3`，解析 notes 并补齐 field/tags |
| HTTP `random_tagged_notes` | 请求 `/random/tags?n=2&count=5`，解析分组并补齐 metadata |
| HTTP `random_field_notes` | 请求 `/random/fields?n=2&count=5`，解析分组并补齐 metadata |
| CLI `random notes --json` | 输出可解析 JSON，包含完整 content、field、tags |
| CLI `random notes` | 默认输出完整 content，不截断 |
| CLI 参数校验 | 非正数参数返回非 0 和清晰错误 |

### 回归检查

| 场景 | 预期 |
| --- | --- |
| `zembra-cli add` | direct 和 HTTP 模式行为保持现状 |
| `zembra-cli list tags` | 输出不变化 |
| `zembra-cli list fields` | 输出不变化 |
| `zembra-cli run` | 启动和保存逻辑不变化 |
