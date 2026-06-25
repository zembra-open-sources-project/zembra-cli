# CLI 级联配置需求澄清

日期：2026.06.25

## 需求结论

为 `zembra-cli` 增加独立 CLI 配置文件 `~/.zembra/config.cli.toml`。该文件使用 TOML 格式，只维护 CLI 运行有关的字段。读取配置时保留现有全局配置 `~/.zembra.env` 作为低优先级来源，按字段级合并形成最终配置；写入配置时只写新的 CLI 配置文件，不迁移、不改写旧全局配置。

## 已确认规则

| 问题 | 结论 |
| --- | --- |
| CLI 配置文件路径 | `~/.zembra/config.cli.toml` |
| 旧全局配置文件路径 | `~/.zembra.env` |
| 配置格式 | TOML |
| 读取优先级 | `~/.zembra/config.cli.toml` 高于 `~/.zembra.env` |
| 合并粒度 | 字段级合并 |
| `database.path` | 参与字段级级联发现 |
| `cli.mode` | 参与字段级级联发现 |
| `cli.http_base_url` | 参与字段级级联发现 |
| 自动迁移 | 禁止自动迁移旧全局配置 |
| `config database` 写入目标 | 改为写入 `~/.zembra/config.cli.toml` |
| `init` 写入目标 | 改为写入 `~/.zembra/config.cli.toml` |
| `init` 目录行为 | 自动创建 `~/.zembra/` |
| 缺失配置错误 | 提示已检查 `~/.zembra/config.cli.toml` 和 `~/.zembra.env` |

## 字段级级联规则

最终运行配置由 CLI 配置和全局配置合并得到。读取某个字段时，先读取 `~/.zembra/config.cli.toml` 中的同名字段；如果该字段不存在，再读取 `~/.zembra.env` 中的同名字段。CLI 配置文件存在但字段不完整时，不会阻止全局配置补齐缺失字段。

| CLI 配置字段 | 全局配置字段 | 最终结果 |
| --- | --- | --- |
| `cli.mode = "direct"` | `database.path = "/old/zembra.sqlite3"` | direct 模式，数据库路径来自全局配置 |
| `cli.mode = "http"` | `cli.http_base_url = "http://127.0.0.1:3000"` | HTTP 模式，URL 来自全局配置 |
| `database.path = "/new/zembra.sqlite3"` | `database.path = "/old/zembra.sqlite3"` | 数据库路径使用 CLI 配置 |
| 缺失 | 缺失 | 按现有必填字段规则报错 |

## 当前实现关联点

当前实现把配置读写集中在 `src/zembra_cli/config.py`，默认配置路径为 `~/.zembra.env`。本需求需要把读取路径从单文件改为双文件字段级合并，并增加 CLI 配置路径函数。`src/zembra_cli/cli.py` 中的 `init` 和 `config database` 需要改为写入 `~/.zembra/config.cli.toml`。`add`、`list`、`random`、`run` 和 `mcp` 等读取配置的入口需要使用合并后的最终配置。

## 本阶段范围

| 对象 | 操作 |
| --- | --- |
| 配置读取 | 新增 CLI 配置和全局配置的字段级级联读取 |
| 配置写入 | `config database` 写入 `~/.zembra/config.cli.toml` |
| 初始化 | `init` 自动创建 `~/.zembra/` 并写入 `config.cli.toml` |
| 错误提示 | 找不到可用配置时提示已检查两个配置路径 |
| CLI 命令 | 数据库命令、HTTP 模式命令和 MCP 入口使用合并配置 |
| 文档 | 更新 README 和相关设计说明中的默认配置路径描述 |
| 测试 | 覆盖字段级合并、写入目标、初始化行为、错误提示和旧全局配置回退 |

## 暂不包含

- 自动迁移 `~/.zembra.env` 到 `~/.zembra/config.cli.toml`
- 删除对 `~/.zembra.env` 的读取支持
- 改动默认数据库路径 `~/.zembra/zembra.sqlite3`
- 新增多 profile 配置
- 改动后端或 Web 端配置规则
