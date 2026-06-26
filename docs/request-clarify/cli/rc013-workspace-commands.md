# Workspace 命令需求澄清

日期：2026-06-26

## 背景

当前 CLI 已经通过 `~/.zembra/config.cli.toml` 的 `[workspace].id` 保存默认 workspace，业务命令会使用该 workspace 访问 HTTP backend 或本地 SQLite。用户希望新增 workspace 管理命令，通过已配置的 HTTP backend 动态查询 workspace 列表，并把选中的 workspace 写回 CLI 配置作为默认 workspace。

## 范围

| 项目 | 结论 |
| --- | --- |
| 命令组 | 新增 `zembra-cli workspaces` |
| 列表命令 | `zembra-cli workspaces list` 动态请求后端 workspace 列表 |
| 默认 workspace 命令 | `zembra-cli workspaces set-default <hash-or-name>` 根据输入匹配 workspace 并写入 CLI 配置 |
| 后端地址来源 | 只允许从配置读取 `cli.http_base_url`，未配置时命令报错，不写死任何默认 URL |
| 列表接口 | 使用当前后端的 `GET /workspaces` |
| 后端响应字段 | 使用 `workspace_id`、`workspace_name`、`short_hash`、`visible_note_count`、`latest_note_created_at` |
| 默认输出 | `workspaces list` 默认使用表格输出 |
| JSON 输出 | `workspaces list --json` 输出后端 workspace 数据及当前默认标记 |
| 当前默认标记 | 列表输出需要根据 CLI 配置中的 `[workspace].id` 标记当前默认 workspace |
| 匹配规则 | `set-default` 支持完整 `workspace_id`、`short_hash` 前缀和 `workspace_name` 精确匹配 |
| 歧义处理 | 输入匹配多个 workspace 时命令失败，并列出候选项 |
| 配置写入 | 只写入 `~/.zembra/config.cli.toml`，不写入或迁移 `~/.zembra.env` |
| workspace name 写入 | 后端返回 `workspace_name` 时写入 `[workspace].name`；返回 `null` 时删除旧的 `[workspace].name` |

## 仓库现状关联

当前配置读取集中在 `src/zembra_cli/config.py`，`load_cascading_config()` 会合并 CLI 配置和全局配置，但 workspace 字段只从 CLI 配置读取。当前配置写入函数 `write_database_path()` 可以写入 workspace 字段，但它绑定了数据库路径写入语义，本需求需要新增更聚焦的 workspace 默认值写入能力，避免 `set-default` 修改数据库路径。

当前 HTTP 访问集中在 `src/zembra_cli/http_client.py` 的 `HttpZembraRepository`，已有请求封装、错误处理和模型解析工具。本需求需要补充 workspace 列表查询能力。当前 CLI 命令入口集中在 `src/zembra_cli/cli.py`，已有 `config`、`list`、`random` 子命令组，可按同样方式新增 `workspaces` 子命令组。

当前本机后端已验证 `GET /workspaces` 返回如下结构：顶层对象包含 `workspaces` 数组，数组元素包含 workspace 标识、短 hash、显示名、可见 note 数和最近 note 创建时间。本需求以该接口结构作为当前实现依据。

## 验收标准

| 场景 | 预期 |
| --- | --- |
| 配置存在 `cli.http_base_url` | `workspaces list` 请求该地址的 `/workspaces` 并展示结果 |
| 配置缺少 `cli.http_base_url` | `workspaces list` 和 `set-default` 失败，提示需要配置后端地址 |
| 默认表格输出 | 展示短 hash、名称、完整 ID、可见 note 数、最近 note 时间和默认标记 |
| JSON 输出 | `workspaces list --json` 输出 JSON，不混入表格文本 |
| 当前默认存在于列表中 | 表格和 JSON 均标记该 workspace 为默认 |
| 当前默认不在列表中 | 列表仍正常展示，并不标记默认 workspace |
| 使用完整 ID 设置默认 | 配置写入对应 workspace ID 和名称 |
| 使用短 hash 前缀设置默认 | 唯一匹配时配置写入对应 workspace ID 和名称 |
| 使用 workspace 名称设置默认 | 名称精确唯一匹配时配置写入对应 workspace ID 和名称 |
| 匹配不到 workspace | 命令失败并提示没有匹配项 |
| 匹配多个 workspace | 命令失败并列出候选 workspace |
| 后端返回 `workspace_name = null` | 配置写入 `[workspace].id` 并移除旧的 `[workspace].name` |

## 非目标

- 不新增创建、重命名、归档或删除 workspace 命令。
- 不实现本地 SQLite 直连读取 workspace 列表。
- 不改变 note、field、tag 等业务命令的 workspace 隔离逻辑。
- 不改变后端 `/workspaces` 接口。
- 不自动补写或猜测 `cli.http_base_url`。
