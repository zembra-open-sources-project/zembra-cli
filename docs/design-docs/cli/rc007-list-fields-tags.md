# CLI List Fields Tags 设计文档

日期：2026.04.27

需求澄清文档：`docs/request-clarify/cli/rc007-list-fields-tags.md`

## 核心功能

为 zembra-cli 增加 `list` 命令组，支持通过 `zembra-cli list tags` 和 `zembra-cli list fields` 紧凑浏览当前数据库中的 tag 与 field 名称。

## 设计目标

| 目标 | 说明 |
| --- | --- |
| 只读浏览 | 命令只读取数据库，不创建或修改记录 |
| 紧凑输出 | 多个名称输出在同一行，使用两个空格分隔 |
| 复用仓储 | 复用现有 Repository 的 `name ASC` 排序能力 |
| 参数明确 | `-a` 输出全部，`-n` 控制限制数量，`-a` 优先 |
| 脚本友好 | 空数据输出空内容并返回退出码 `0` |

## 命令设计

| CLI 命令 | 代码对象 | 说明 |
| --- | --- | --- |
| `zembra-cli list` | `list_app` | Typer 子应用 |
| `zembra-cli list tags` | `list_tags` | 输出 tag 名称 |
| `zembra-cli list fields` | `list_fields` | 输出 field 名称 |

## 参数设计

| 参数 | 类型 | 默认值 | 规则 |
| --- | --- | --- | --- |
| `-n` / `--number` | `int` | `5` | 必须大于等于 `1` |
| `-a` / `--all` | `bool` | `False` | 为 `True` 时输出全部并忽略 `-n` |

## 数据读取

| 子命令 | Repository 方法 | 排序 |
| --- | --- | --- |
| `tags` | `ZembraRepository.list_tags()` | `name ASC` |
| `fields` | `ZembraRepository.list_fields()` | `name ASC` |

现有 `FieldTagRepository` 已经提供对应方法，`ZembraRepository` 继承该能力。CLI 层只负责连接数据库、读取列表、按参数截断和格式化输出。

## 输出设计

| 场景 | 输出 |
| --- | --- |
| 默认数量 | 前 5 个名称，两个空格分隔 |
| `-n 10` | 前 10 个名称，两个空格分隔 |
| `-a` | 全部名称，两个空格分隔 |
| 空数据 | 输出空内容 |

示例：

```text
cli  draft  idea  python  work
```

## 错误处理

| 场景 | 处理 |
| --- | --- |
| 配置缺失 | 沿用现有 `load_config` 错误处理 |
| 数据库不存在 | 沿用 `require_initialized_database` 错误处理 |
| 数据库未初始化 | 沿用 `require_initialized_database` 错误处理 |
| SQLite 读取失败 | 输出自然语言错误并返回非 `0` |
| `-n` 小于 `1` | 输出自然语言错误并返回非 `0` |

## 预期改动范围

| 文件 | 改动 |
| --- | --- |
| `src/zembra_cli/cli.py` | 新增 `list_app`、参数校验、输出格式化和两个子命令 |
| `tests/test_cli.py` | 新增 list 命令测试 |

## 测试设计

| 用例 | 预期 |
| --- | --- |
| `list tags` | 默认输出前 5 个 tag name |
| `list fields` | 默认输出前 5 个 field name |
| `list tags -n 10` | 输出前 10 个 tag name |
| `list fields -a` | 输出全部 field name |
| `list tags -n 10 -a` | 输出全部 tag name |
| 空 tags | 输出空内容，退出码 `0` |
| 空 fields | 输出空内容，退出码 `0` |
| `-n 0` | 报错，退出码非 `0` |
| 数据库缺失 | 报错，退出码非 `0` |
