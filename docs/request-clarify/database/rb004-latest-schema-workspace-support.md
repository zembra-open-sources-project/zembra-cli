# 最新 Schema 与 Workspace 支持需求澄清

日期：2026.06.25

## 需求结论

将 `vendor/zembra-schema` 更新到远端最新版本，并更新 `zembra-cli` 的数据库基础设施、模型和 Repository，使本仓库只支持最新 schema。最新 schema 引入 `workspaces` 表、业务表 `workspace_id` 隔离、层级 tag 字段和同步相关表；本需求不保留旧 schema 兼容代码，不实现旧数据库迁移。

## 已确认规则

| 问题 | 结论 |
| --- | --- |
| schema 来源 | `vendor/zembra-schema` 远端最新 `origin/master`，当前对应 tag `0.5.1`，schema 契约版本为 `0.5.0` |
| 旧 schema 支持 | 禁止保留旧版本 schema 兼容代码 |
| 旧数据库迁移 | 不实现 |
| workspace 来源 | CLI direct 模式只从 `~/.zembra/config.cli.toml` 读取 workspace 配置 |
| workspace 级联 | 禁止从 `~/.zembra.env` 读取或补齐 workspace 字段 |
| init 默认 workspace ID | 未显式传参时随机生成符合规范的 UUID |
| workspace 显示名 | 新增 `--workspace-name` 参数；未传时配置中省略 `workspace.name`，运行模型和数据库写入 NULL |
| tag 适配 | 本轮只把现有 tag 输入创建为根 tag，`parent_tag_id = NULL`、`path = name`、`depth = 0` |
| sync 表 | 初始化和模型可识别最新 schema；不实现 sync 业务写入流程 |

## 配置规则

`~/.zembra/config.cli.toml` 新增 CLI 专属 workspace 配置。该配置不参与全局配置级联，不能从 `~/.zembra.env` 回退。

```toml
[workspace]
id = "550e8400-e29b-41d4-a716-446655440000"
```

`zembra-cli init` 创建数据库时，如果用户没有传入 workspace ID，则生成 UUID 并写入 `[workspace].id`。如果用户没有传入 `--workspace-name`，由于 TOML 标准不支持 `null` 字面量，配置文件中省略 `[workspace].name`，运行配置中的 `workspace_name` 为 `None`，数据库 `workspaces.workspace_name` 写入 NULL。

## 当前实现关联点

当前 `zembra-cli` 已经有 CLI 独立配置文件和字段级级联读取能力，但配置模型还没有 workspace 字段。当前 Repository 不携带 workspace 上下文，所有 `fields`、`tags`、`notes`、`note_tags` 和 `note_revisions` SQL 都是旧 schema 结构。更新到最新 schema 后，如果不注入 workspace ID 并在写入时填充 `workspace_id`，基础命令会违反 `NOT NULL` 和外键约束。

## 本阶段范围

| 对象 | 操作 |
| --- | --- |
| schema submodule | 更新到远端最新指针 |
| 配置层 | 新增只从 CLI 配置读取的 workspace 字段 |
| init 命令 | 创建数据库、创建 workspace 记录、写入 workspace 配置 |
| Repository | 初始化时接收 workspace ID，所有本地读写限定当前 workspace |
| Pydantic models | 对齐最新 schema 字段 |
| tag 处理 | 现有 tag 输入创建根 tag |
| 数据库测试 | 验证最新表、workspace 字段、层级 tag 字段和 sync 表 |
| CLI/MCP 测试 | 验证 direct 模式在 workspace 下正常创建、读取和随机查询 |
| 文档 | 更新 README、需求澄清、设计文档和执行计划 |

## 暂不包含

- 旧 schema 数据库迁移或自动升级
- 兼容缺少 `workspace_id` 的旧表
- 多 workspace 切换命令
- 层级 tag 的创建、移动、重命名和路径维护命令
- sync_changes、sync_state、sync_conflicts 的业务写入和同步流程
- Supabase/Postgres 后端适配
