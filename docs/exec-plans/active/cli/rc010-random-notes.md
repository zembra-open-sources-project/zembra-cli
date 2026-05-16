# Random Notes CLI 实现计划

> **给 Claude：** 必需工作流：使用 superpowers:executing-plans 逐任务实现此计划。

**目标：** 为 `zembra-cli` 增加 direct 和 HTTP 双模式随机笔记命令，支持普通随机、tag 分组随机、field 分组随机，并提供人类可读与 JSON 输出。

**需求澄清文档：** `docs/request-clarify/cli/rc010-random-notes.md`

**相关设计文档：** `docs/design-docs/cli/rc010-random-notes.md`

**架构：** 在 repository 协议中新增 random 查询能力，direct 模式由 SQLite repository 直接查询可见笔记并聚合 field/tags，HTTP 模式调用后端 `/random/*` 接口并补齐 CLI 输出所需 metadata。CLI 层只依赖统一 DTO 和协议，负责参数校验、人类可读输出与 JSON 输出。

**技术栈：** Python 3.12、Typer、Rich、Pydantic、httpx、SQLite、pytest、uv。

**范围 / 非范围：** 本计划只覆盖 `random notes`、`random tags`、`random fields`、双模式实现、输出格式和自动化测试；不修改后端、不增加 TUI、不实现 note 管理命令、不做 schema 迁移。

---

## Phase #1: 共享模型与 direct 随机查询

### Task #1: 新增 random 输出 DTO

**状态：** Finished

**文件：**

- 修改：`src/zembra_cli/models.py`
- 修改：`src/zembra_cli/repository/protocol.py`
- 验证：`tests/test_models.py`

- 功能：新增 CLI random 输出所需的结构化模型，让 direct 和 HTTP 模式返回统一形状。
- 实现说明：在 `models.py` 增加 `NoteWithMetadata`、`TaggedNotesGroup`、`FieldNotesGroup`，字段分别引用现有 `NoteRecord`、`FieldRecord`、`TagRecord`。在 `CliRepository` 协议中增加 `random_notes(number)`、`random_tagged_notes(number, count)`、`random_field_notes(number, count)`。
- 预期验证结果：模型可以通过 Pydantic 校验，JSON dump 包含完整 note、field、tags；现有模型测试不回归。
- 完成时间：2026.05.16

### Task #2: 实现 direct random notes

**状态：** Finished

**文件：**

- 修改：`src/zembra_cli/repository/notes.py`
- 验证：`tests/test_repository.py`

- 功能：在 SQLite repository 中实现 `random_notes(number)`。
- 实现说明：只查询 `deleted_at IS NULL AND archived_at IS NULL` 的可见笔记，使用 `ORDER BY RANDOM() LIMIT ?`。为每条 note 通过 `field_id` 读取 field，通过既有 `list_note_tags(note.id)` 读取 tags，返回 `NoteWithMetadata`。
- 预期验证结果：返回数量不超过 number；软删除和归档笔记不会返回；返回项包含完整 content、field、tags。
- 完成时间：2026.05.16

### Task #3: 实现 direct random tags / fields

**状态：** Finished

**文件：**

- 修改：`src/zembra_cli/repository/notes.py`
- 验证：`tests/test_repository.py`

- 功能：在 SQLite repository 中实现 `random_tagged_notes(number, count)` 与 `random_field_notes(number, count)`。
- 实现说明：随机 group 只从至少有关联可见笔记的 tag/field 中选择。`count` 作为跨分组累计笔记数上限，按 group 顺序消耗剩余 quota。每条 note 返回 `NoteWithMetadata`，分组返回 `TaggedNotesGroup` 或 `FieldNotesGroup`。
- 预期验证结果：分组数不超过 number；累计 note 数不超过 count；没有可见笔记的 tag/field 不会出现；返回笔记包含完整 metadata。
- 完成时间：2026.05.16

## Phase #2: HTTP random 与 CLI 命令

### Task #4: 实现 HTTP random 方法

**状态：** Finished

**文件：**

- 修改：`src/zembra_cli/http_client.py`
- 验证：`tests/test_http_client.py`

- 功能：在 `HttpZembraRepository` 中实现三类 random 方法。
- 实现说明：`random_notes` 请求 `/random/notes?n={number}`；`random_tagged_notes` 请求 `/random/tags?n={number}&count={count}`；`random_field_notes` 请求 `/random/fields?n={number}&count={count}`。解析后端 response，并用 `/notes/{note_ref}/tags` 与 `/fields` 补齐每条 note 的 tags 和 field。
- 预期验证结果：MockTransport 捕获到正确 path 和 query；响应解析为统一 DTO；缺字段或非法形状继续抛出 `ZembraHttpClientError`。
- 完成时间：2026.05.16

### Task #5: 新增 random CLI 子命令与输出格式

**状态：** Finished

**文件：**

- 修改：`src/zembra_cli/cli.py`
- 验证：`tests/test_cli.py`

- 功能：新增 `zembra-cli random notes`、`zembra-cli random tags`、`zembra-cli random fields`。
- 实现说明：新增 `random_app` 并挂载到主 app。`notes` 支持 `-n/--number` 默认 3 和 `--json`；`tags`、`fields` 支持 `-n/--number` 默认 2、`--count` 默认 5 和 `--json`。CLI 层校验参数大于等于 1。人类可读输出展示完整 note id、role、field、tags、created_at、updated_at、完整 content；JSON 输出使用 `ensure_ascii=False`，字段名对齐 `notes`、`tagged_notes`、`field_notes`。
- 预期验证结果：direct 和 HTTP 模式都能执行 random 命令；默认输出不截断 content；`--json` 输出可解析 JSON 且不混入 Rich 样式文本；参数错误返回非 0。
- 完成时间：2026.05.16

## Phase #3: 验证、记录与提交准备

### Task #6: 补齐自动化测试

**状态：** Designed

**文件：**

- 修改：`tests/test_models.py`
- 修改：`tests/test_repository.py`
- 修改：`tests/test_http_client.py`
- 修改：`tests/test_cli.py`

- 功能：覆盖模型、direct repository、HTTP repository 和 CLI 命令行为。
- 实现说明：repository 测试构造带 field/tag、归档、删除的笔记，验证可见笔记语义。HTTP 测试用 `httpx.MockTransport` 验证请求和 metadata 补齐。CLI 测试覆盖 direct / HTTP、默认输出、`--json`、参数错误。
- 预期验证结果：定向测试全部通过，且断言覆盖完整 content、field、tags。
- 完成时间：

### Task #7: 运行验证并更新计划状态

**状态：** Designed

**文件：**

- 修改：`docs/exec-plans/active/cli/rc010-random-notes.md`
- 验证：`uv run pytest -q`

- 功能：运行验证命令，记录验证结果，并按实际完成情况更新本计划状态。
- 实现说明：至少运行 `uv run pytest tests/test_repository.py tests/test_http_client.py tests/test_cli.py -q`，最终运行 `uv run pytest -q`。如果项目已有 lint 命令且不引入额外配置成本，可补充运行。
- 预期验证结果：相关测试和全量测试通过；验证记录写入本计划；等待用户验收，未经用户允许不移动到 completed。
- 完成时间：

## 提交计划

| 阶段 | 提交点 | Commit message |
| --- | --- | --- |
| Phase #1 | direct repository random 能力和模型测试完成后 | `feat: add direct random note queries` |
| Phase #2 | HTTP random 和 CLI 命令测试完成后 | `feat: expose random note CLI commands` |
| Phase #3 | 全量验证与计划记录完成后 | `test: cover random note CLI flows` |

提交前必须先检查 staged diff，commit message 必须满足仓库 Conventional Commit 防火墙。

## 验证记录

待执行。
