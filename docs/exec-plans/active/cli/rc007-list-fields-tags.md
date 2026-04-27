# CLI List Fields Tags 执行计划

日期：2026.04.27

需求澄清文档：`docs/request-clarify/cli/rc007-list-fields-tags.md`

设计文档：`docs/design-docs/cli/rc007-list-fields-tags.md`

## Stage 1：CLI 命令实现

### Task 1.1：新增 list 命令组

状态：Finished

功能：在 Typer 应用中新增 `list_app`，并注册为 CLI 的 `list` 命令组。

实现要点：

| 项目 | 说明 |
| --- | --- |
| 命名 | 代码对象使用 `list_app` |
| 注册 | `app.add_typer(list_app, name="list")` |
| 子命令 | 新增 `tags` 和 `fields` |

预期测试结果：`zembra-cli list --help` 能展示 `tags` 和 `fields` 子命令。

### Task 1.2：实现字段与标签读取

状态：Finished

功能：实现 `zembra-cli list tags` 和 `zembra-cli list fields`。

实现要点：

| 项目 | 说明 |
| --- | --- |
| 数据库配置 | 复用现有 `load_config(default_config_path())` |
| 初始化检查 | 复用 `require_initialized_database` |
| 仓储方法 | 使用 `ZembraRepository.list_tags()` 和 `ZembraRepository.list_fields()` |
| 排序 | 沿用 Repository 的 `name ASC` |

预期测试结果：两个子命令能从测试数据库读取已有名称。

### Task 1.3：实现参数与输出格式

状态：Finished

功能：支持 `-n` 默认 5 条、`-a` 全量输出和紧凑单行格式。

实现要点：

| 项目 | 说明 |
| --- | --- |
| 默认数量 | `-n` 默认为 `5` |
| 全部输出 | `-a` 为 `True` 时忽略 `-n` |
| 参数校验 | `-n` 必须大于等于 `1` |
| 输出格式 | 只输出 `name`，用两个空格连接 |
| 空数据 | 输出空内容并返回 `0` |

预期测试结果：默认、指定数量、全量、空数据和非法 `-n` 都符合需求。

## Stage 2：测试与验证

### Task 2.1：补充 CLI 测试

状态：Finished

功能：在 `tests/test_cli.py` 中增加 list 命令覆盖。

实现要点：

| 测试范围 | 说明 |
| --- | --- |
| 默认数量 | 验证只输出前 5 个 |
| 指定数量 | 验证 `-n` 截断 |
| 全量输出 | 验证 `-a` 覆盖 `-n` |
| 空数据 | 验证空输出和退出码 `0` |
| 非法参数 | 验证 `-n 0` 报错 |

预期测试结果：新增测试通过。

### Task 2.2：运行验证

状态：Finished

功能：运行项目测试，确认新增命令和已有行为未回归。

实现要点：

| 命令 | 预期 |
| --- | --- |
| `uv run pytest` | 全部通过 |

预期测试结果：测试通过后更新本执行计划中的任务状态和验证记录。

## 验证记录

2026.04.27：已运行 `uv run pytest`，全部 88 个测试通过。
