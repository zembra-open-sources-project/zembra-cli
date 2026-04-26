# Note ID Prefix Resolution 设计文档

日期：2026.04.26

需求澄清文档：`docs/request-clarify/cli/rc003-note-id-prefix-resolution.md`

## 核心功能（WHAT）

为 Zembra 增加 note id 前缀解析能力。用户在需要定位笔记的操作中，可以输入完整 32 位 note id，也可以输入不少于 4 位的 note id 前缀；当前缀唯一匹配一条未删除笔记时，系统解析出完整 note id 并继续执行后续操作。

### 需求背景（WHY）

Zembra 当前 note id 默认由 `uuid.uuid4().hex` 生成，完整 id 为 32 位小写十六进制字符串。完整 id 在命令行中输入和辨认成本较高。git、docker 等工具允许用户通过足够短且唯一的 hash 前缀定位对象，Zembra 可以采用同样思路，让日常笔记操作更轻快。

### 需求目标（GOAL）

| 目标 | 说明 |
| --- | --- |
| 支持短 ID | 输入不少于 4 位的 note id 前缀时，可以解析到唯一未删除笔记 |
| 保持完整 ID 兼容 | 完整 32 位 note id 继续按现有精确查询语义工作 |
| 只关注未删除笔记 | 常规短 ID 解析不命中软删除笔记 |
| 冲突可理解 | 多条笔记匹配同一前缀时，返回明确冲突错误和候选提示 |
| 错误可复用 | 仓储层提供结构化错误，CLI 层转换为自然语言输出 |
| 后续命令复用 | `show`、`edit`、`archive`、`delete` 等命令可共用同一解析逻辑 |

### 范围边界

#### In Scope

| 模块 | 改动 |
| --- | --- |
| `src/zembra_cli/repository/notes.py` | 增加 note id 前缀解析能力 |
| `src/zembra_cli/repository/exceptions.py` | 增加短 ID 输入过短、前缀冲突等仓储错误 |
| `src/zembra_cli/cli.py` | 增加 CLI 层可复用解析辅助函数，供后续 note 命令调用 |
| `tests/test_repository.py` | 覆盖唯一匹配、无匹配、过短、冲突、软删除过滤和完整 ID 兼容 |
| `tests/test_cli.py` | 覆盖 CLI 辅助函数或接入命令的错误输出 |

#### Out of Scope

| 项目 | 原因 |
| --- | --- |
| 改变 note id 生成规则 | 当前 UUID hex 已满足前缀匹配需求 |
| 匹配软删除笔记 | 用户已确认所有常规操作只关注未删除笔记 |
| 新增恢复软删除能力 | 不属于本需求 |
| 新增完整 note 管理命令 | 本需求聚焦短 ID 解析能力，具体命令可在后续需求中接入 |
| 数据库 schema 迁移 | `notes.id` 已存在，无需新增字段 |

## 实现流程（HOW）

### 技术决策

短 ID 解析放在 Repository 层，CLI 层不直接写 SQL。Repository 负责校验输入、查询未删除笔记、判断唯一性并返回完整 `NoteRecord` 或完整 id；CLI 层只负责把用户输入传给 Repository，并把仓储错误转换成可读的命令行错误。

### 当前架构触点

| 层级 | 当前职责 | 本需求设计 |
| --- | --- | --- |
| CLI | 参数解析、配置加载、数据库连接、错误输出 | 增加可复用 note 引用解析辅助函数 |
| Repository | note CRUD 和 SQLite 查询 | 增加 note id 前缀解析方法 |
| Exceptions | 仓储错误表达 | 增加前缀解析专用错误 |
| Tests | 覆盖 CLI 和仓储行为 | 新增短 ID 解析行为测试 |

### Repository API 设计

推荐新增方法：

| 方法 | 输入 | 输出 | 说明 |
| --- | --- | --- | --- |
| `resolve_note_id(note_ref, include_deleted=False)` | 用户输入的完整 id 或短前缀 | 完整 note id 字符串 | 只负责把引用解析成唯一完整 id |
| `get_note_by_ref(note_ref, include_deleted=False)` | 用户输入的完整 id 或短前缀 | `NoteRecord | None` | 可选便利方法，内部调用 `resolve_note_id` 后读取 note |

`include_deleted` 默认保持 `False`。虽然当前常规操作只关注未删除笔记，但保留参数可以让内部测试和未来审计工具明确表达边界。

### 输入校验规则

| 输入 | 行为 |
| --- | --- |
| 空字符串 | 抛出无效 note 引用错误 |
| 少于 4 位 | 抛出前缀过短错误 |
| 非十六进制字符 | 抛出无效 note 引用错误 |
| 4 到 31 位十六进制字符串 | 作为短前缀查询 |
| 32 位十六进制字符串 | 先按完整 id 精确查询；找不到时返回未找到 |
| 大写十六进制字符 | 统一转换为小写后查询 |

完整 32 位输入不走模糊匹配，避免用户输入完整 id 时被其他异常数据误判为冲突。

### SQL 查询设计

短前缀查询使用 `LIKE` 或 SQLite 字符串前缀匹配：

| 条件 | 说明 |
| --- | --- |
| `id LIKE ?` | 参数为 `normalized_prefix + "%"` |
| `deleted_at IS NULL` | 默认只匹配未删除笔记 |
| `ORDER BY updated_at DESC, created_at DESC, id ASC` | 冲突候选输出稳定 |
| `LIMIT` | 可限制候选数量，避免错误消息过长 |

冲突判断至少需要知道是否超过一条匹配。实现时可以查询前若干条候选，例如 6 条，用于错误提示和测试稳定性。

### 错误模型设计

| 错误类型 | 触发条件 | 携带信息 |
| --- | --- | --- |
| `InvalidNoteReferenceError` | 空字符串或非十六进制输入 | 原始输入、原因 |
| `NoteReferenceTooShortError` | 输入少于 4 位 | 原始输入、最短长度 |
| `AmbiguousNoteReferenceError` | 前缀匹配多条未删除笔记 | 原始输入、候选 note 列表 |
| `RecordNotFoundError` | 完整 id 或前缀无匹配 | 表名、原始输入 |

错误类型放在 `repository/exceptions.py`，保持仓储层错误统一。CLI 层捕获这些错误并输出自然语言。

### 冲突候选展示

候选展示推荐包含：

| 字段 | 说明 |
| --- | --- |
| 短 id | 默认展示前 8 位，足够帮助用户继续输入 |
| 内容摘要 | 从 note content 取前一段文本，去掉换行并截断 |

CLI 提示示例：

```text
Note reference "abcd" is ambiguous. Use more characters.
Matches:
- abcd1234  first note summary
- abcd5678  second note summary
```

Repository 只提供候选数据，不负责拼接最终 CLI 文案。

### CLI 接入策略

在 `cli.py` 中新增内部辅助函数，用于后续所有需要 note 引用的命令：

| 函数 | 职责 |
| --- | --- |
| `resolve_note_reference(repository, note_ref)` | 调用 Repository 解析 note id，捕获仓储错误并转换成 CLI 失败 |
| `summarize_note_content(content, max_length=...)` | 生成冲突候选摘要 |

当前仓库还没有 `show/edit/delete/archive` 命令。本需求可以先实现并测试解析辅助能力；后续命令只接收一个 `note_ref` 参数，不需要区分完整 id 和短前缀。

### 关键约束

| 约束 | 处理方式 |
| --- | --- |
| 最短 4 位 | Repository 层强制校验 |
| 只匹配未删除 | 默认查询带 `deleted_at IS NULL` |
| 完整 ID 兼容 | 32 位输入优先精确查询 |
| 大小写兼容 | 输入统一小写化 |
| CLI 不写 SQL | 所有查询逻辑放在 Repository |
| 错误消息稳定 | 冲突候选排序固定，摘要截断规则固定 |

## 测试用例

### 编译检查

| 用例 | 预期 |
| --- | --- |
| `uv run pytest` | 通过 |

### 回归检查

| 用例 | 预期 |
| --- | --- |
| 完整 id 查询 | `resolve_note_id(full_id)` 返回同一个完整 id |
| 4 位唯一前缀 | 返回唯一匹配 note 的完整 id |
| 大写前缀 | 大写输入能解析到小写完整 id |
| 3 位前缀 | 抛出 `NoteReferenceTooShortError` |
| 非 hex 输入 | 抛出 `InvalidNoteReferenceError` |
| 无匹配前缀 | 抛出 `RecordNotFoundError` |
| 多匹配前缀 | 抛出 `AmbiguousNoteReferenceError`，包含候选 note |
| 软删除过滤 | 前缀只匹配软删除 note 时按未找到处理 |
| 完整 id 不冲突 | 32 位完整 id 精确命中时不受其他相同前缀 note 影响 |
| CLI 错误转换 | CLI 辅助函数把过短、无匹配、冲突转换为可读错误和非 0 退出 |
