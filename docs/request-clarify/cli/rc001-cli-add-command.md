# CLI Add Command 需求澄清

日期：2026.04.26

## 需求结论

为程序新增统一的 `zembra-cli` 命令行入口，并实现新增命令：

```shell
zembra-cli add <note-string-content> --tags <multi-tags> --field <field>
```

该命令用于将一段用户输入的长文本保存为 note，并关联用户指定的 field 和 tags。命令成功时返回只包含当前 note 相关信息的 JSON；失败时返回自然语言失败原因，并使用非 0 退出码。

## 已确认规则

| 问题 | 结论 |
| --- | --- |
| 命令行入口 | 统一为 `zembra-cli` |
| 数据库路径 | 固定使用 `~/.zembra/zembra.sqlite3` |
| tags 输入 | 同时兼容重复参数写法和逗号分隔写法 |
| field 匹配 | field 不存在时自动创建 |
| tag 匹配 | tag 不存在时自动创建 |
| 返回格式 | 成功返回 JSON，只包含当前 note 及与 note 直接相关的 metadata |
| metadata 内容 | 只返回用户输入的 field 名称和 tag 名称列表 |
| 失败处理 | 输出自然语言失败原因，退出码为非 0 |
| 长文本处理 | 不主动解码转义字符，按 shell 传入内容原样保存 |

## 输入约定

| 输入 | 规则 |
| --- | --- |
| `<note-string-content>` | 必填位置参数，接收长文本，允许包含 shell 已处理后的换行、引号、反斜杠等字符 |
| `--tags` | 可重复传入，也可在单个参数中用英文逗号分隔多个 tag |
| `--field` | 匹配一个 field 名称，不存在时自动创建 |

### tags 示例

重复参数写法：

```shell
zembra-cli add "hello" --tags python --tags cli --tags idea --field work
```

逗号分隔写法：

```shell
zembra-cli add "hello" --tags python,cli,idea --field work
```

混合写法：

```shell
zembra-cli add "hello" --tags python,cli --tags idea --field work
```

## 成功返回

成功返回 JSON，结构只暴露当前 note 以及与本次创建直接相关的用户输入 metadata。

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
    "tags": ["python", "cli", "idea"]
  }
}
```

## 失败返回

失败时输出自然语言原因，并返回非 0 退出码。失败原因应面向 CLI 用户，可直接描述问题。

示例：

```text
Database is not initialized at ~/.zembra/zembra.sqlite3
```

## 本阶段范围

| 模块 | 范围 |
| --- | --- |
| CLI 入口 | 将项目脚本入口统一为 `zembra-cli` |
| add 命令 | 创建 note，绑定 field 和 tags |
| 数据库连接 | 使用固定本地数据库路径 |
| JSON 输出 | 输出 note 和用户输入 metadata |
| 自动化测试 | 覆盖入口、参数解析、JSON 输出和失败场景 |

## 暂不包含

- 新增 `--db` 参数
- 主动解码 `\n`、`\t` 等转义序列
- 返回全量 field/tag record
- 查询、更新、删除等其他 CLI 命令
- TUI/API 接入
- 数据库迁移系统
- 用户手工 UI 测试
