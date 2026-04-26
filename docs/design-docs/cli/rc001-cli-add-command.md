# CLI Add Command 设计文档

日期：2026.04.26

需求澄清文档：`docs/request-clarify/cli/rc001-cli-add-command.md`

## 核心功能（WHAT）

为 zembra-cli 增加统一命令行入口 `zembra-cli`，并实现 `add` 命令。用户通过该命令输入 note 正文、一个 field 和多个 tags，程序将数据写入固定本地 SQLite 数据库，并返回当前 note 相关 JSON。

### 需求背景（WHY）

项目当前已经具备 Typer CLI 骨架、SQLite 初始化能力、Pydantic record 模型和 `ZembraRepository.create_note` 仓储方法。新增 `add` 命令可以让现有 Repository 能力通过命令行被真实调用，并为后续更多 CLI 命令建立统一输出和错误处理方式。

### 需求目标（GOAL）

| 目标 | 说明 |
| --- | --- |
| 统一入口 | 项目安装后提供 `zembra-cli` 命令 |
| 创建 note | `add` 命令调用 Repository 创建 note |
| 绑定分类信息 | 支持一个 field 和多个 tags，缺失时自动创建 |
| 固定数据位置 | 使用 `~/.zembra/zembra.sqlite3` |
| 输出 JSON | 成功时返回 note 和用户输入 metadata |
| 错误可读 | 失败时输出自然语言原因，退出码非 0 |
| 原样保存文本 | 不主动解码 shell 传入字符串中的转义序列 |

### 范围边界

#### In Scope

| 模块 | 改动 |
| --- | --- |
| `pyproject.toml` | 将 console script 统一为 `zembra-cli` |
| `src/zembra_cli/cli.py` | 新增 `add` 命令、参数解析、JSON 输出和错误处理 |
| `src/zembra_cli/db.py` | 如有必要，补充默认数据库路径或初始化检查辅助函数 |
| `tests/test_cli.py` | 覆盖入口行为、参数解析、JSON 输出和失败场景 |

#### Out of Scope

| 项目 | 原因 |
| --- | --- |
| `--db` 参数 | 用户已确认固定本地路径 |
| 返回 field/tag 全量记录 | 用户要求只返回用户输入名称列表 |
| 主动转义解码 | 用户已确认不主动解码 |
| 其他 note 命令 | 本需求只实现 `add` |
| UI/TUI | 本需求只涉及 CLI |

## 实现流程（HOW）

### 技术决策

继续使用现有 Typer 应用作为 CLI 入口，使用 `ZembraRepository.create_note` 承接写入逻辑。CLI 层只负责参数解析、数据库连接、调用仓储、格式化 JSON 和错误输出，不在 CLI 中重复实现 note、field、tag 的持久化规则。

### CLI 入口设计

| 项目 | 设计 |
| --- | --- |
| Console script | `zembra-cli = "zembra_cli.cli:app"` |
| Typer app name | `zembra-cli` |
| 版本输出 | 保留 `--version` |
| 旧入口 `zembra` | 移除项目脚本配置中的旧入口 |

### add 命令设计

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `note_string_content` | `str` | 是 | note 正文，按 shell 传入内容原样保存 |
| `--tags` | `list[str]` | 否 | 支持重复传入和逗号分隔，解析后得到 tag 名称列表 |
| `--field` | `str` | 是 | field 名称，不存在时自动创建 |

命令签名建议：

```python
def add(note_string_content: str, tags: list[str], field: str) -> None
```

### tags 解析规则

| 输入 | 解析结果 |
| --- | --- |
| `--tags python --tags cli` | `["python", "cli"]` |
| `--tags python,cli` | `["python", "cli"]` |
| `--tags python,cli --tags idea` | `["python", "cli", "idea"]` |

解析时按英文逗号拆分，去除每个 tag 两端空白，过滤空字符串。返回 metadata 中的 tags 使用解析后的列表，顺序保留用户输入顺序。是否去重由 CLI 层保持保守处理：传给 Repository 前可去重，metadata 返回去重后的有效 tag 列表，避免响应中出现重复 tag。

### 数据库路径与初始化检查

固定数据库路径为：

```text
~/.zembra/zembra.sqlite3
```

CLI 执行时展开用户目录并连接该数据库。若数据库文件不存在或缺少核心表，命令失败并返回自然语言说明。`add` 命令不隐式初始化数据库，避免在用户未准备好本地库时创建结构不完整或误写位置。

### Repository 调用

| 步骤 | 说明 |
| --- | --- |
| 1 | 展开并检查默认数据库路径 |
| 2 | 建立 SQLite connection |
| 3 | 校验核心表存在 |
| 4 | 创建 `ZembraRepository` |
| 5 | 调用 `create_note(content, field_name=field, tag_names=parsed_tags)` |
| 6 | 输出 JSON |

### JSON 输出设计

成功输出：

```json
{
  "note": {
    "id": "...",
    "content": "...",
    "field_id": "...",
    "created_at": 123,
    "updated_at": 123,
    "archived_at": null,
    "deleted_at": null,
    "current_revision_id": "..."
  },
  "metadata": {
    "field": "work",
    "tags": ["python", "cli"]
  }
}
```

| 字段 | 来源 |
| --- | --- |
| `note` | `NoteRecord.model_dump()` |
| `metadata.field` | 用户传入的 `--field` |
| `metadata.tags` | 解析后的有效 tag 名称列表 |

### 错误处理

| 场景 | 处理 |
| --- | --- |
| 数据库文件不存在 | 输出自然语言失败原因，退出码非 0 |
| 数据库未初始化 | 输出自然语言失败原因，退出码非 0 |
| SQLite 写入失败 | 输出自然语言失败原因，退出码非 0 |
| 参数缺失 | 使用 Typer 默认参数错误处理 |
| field 为空字符串 | 使用参数校验或自然语言失败原因 |
| tags 为空或缺失 | 允许创建无 tag note |

### 关键约束

| 约束 | 处理方式 |
| --- | --- |
| 模块化开发 | CLI 层只编排，不复制 Repository 逻辑 |
| 不泄漏无关数据 | JSON 只包含当前 note 和用户输入 metadata |
| 固定本地路径 | 使用 `Path.home() / ".zembra" / "zembra.sqlite3"` |
| 长文本保存 | 不对 `\n`、`\t` 等字符串做额外解码 |
| 失败码 | 业务失败使用非 0 退出码 |

## 测试用例

### 编译检查

| 用例 | 预期 |
| --- | --- |
| `uv run ruff check .` | 通过 |
| `uv run pytest` | 通过 |

### 回归检查

| 用例 | 预期 |
| --- | --- |
| `--version` | 输出 `zembra-cli` 版本信息 |
| `add` 基础创建 | 返回合法 JSON，note content 与输入一致 |
| 重复 tags 参数 | `--tags python --tags cli` 解析为两个 tag |
| 逗号 tags 参数 | `--tags python,cli` 解析为两个 tag |
| 混合 tags 参数 | `--tags python,cli --tags idea` 顺序解析为三个 tag |
| tag 空白过滤 | `--tags "python, cli"` 去除 tag 两端空白 |
| 重复 tag | metadata 不重复，数据库关联不重复 |
| field 自动创建 | field 不存在时创建并关联 note |
| 长文本输入 | 保存 shell 传入内容，不主动解码转义序列 |
| 数据库不存在 | 输出自然语言失败原因，退出码非 0 |
| 数据库未初始化 | 输出自然语言失败原因，退出码非 0 |
