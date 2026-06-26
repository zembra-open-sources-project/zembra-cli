# zembra-cli

`zembra-cli` 是 Zembra 本地优先笔记系统的命令行客户端。它可以创建笔记、浏览已有 field 和 tag、启动交互式记录会话，也可以把本地笔记数据库以 MCP Server 的形式暴露给 MCP 客户端。

## 安装

`zembra-cli` 是标准 Python 包，需要 Python 3.12 或更高版本。

作为隔离的命令行工具安装：

```bash
pipx install zembra-cli
```

或安装到当前 Python 环境：

```bash
python -m pip install zembra-cli
```

检查命令是否可用：

```bash
zembra-cli --help
```

## 初始化本地存储

使用本地 direct 模式前，先初始化 SQLite 数据库并写入 Zembra 共享配置文件：

```bash
zembra-cli init
```

需要自定义数据库路径时：

```bash
zembra-cli init --database /path/to/zembra.sqlite3
```

默认 CLI 配置文件路径是 `~/.zembra/config.cli.toml`。已有的 `~/.zembra.env` 仍会作为低优先级回退来源读取缺失字段。

## 基础用法

创建一条笔记：

```bash
zembra-cli add "Remember to review the sync plan" --field Inbox --tags cli,review
```

创建一条由 Agent 写入的笔记：

```bash
zembra-cli add "Drafted by an agent" --field Inbox --role Agent
```

启动交互式记录会话：

```bash
zembra-cli run
```

列出 taxonomy 值：

```bash
zembra-cli list tags --all
zembra-cli list fields --all
```

随机展示笔记、tag 或 field：

```bash
zembra-cli random notes
zembra-cli random tags
zembra-cli random fields
```

需要结构化输出时，可以为 random 命令添加 `--json`。

列出后端 workspace 并设置 CLI 默认 workspace：

```bash
zembra-cli workspaces list
zembra-cli workspaces list --json
zembra-cli workspaces set-default 550e8400
```

workspace 命令只从配置读取后端地址，不使用默认 URL。命令优先读取级联合并后的 `cli.http_base_url`，也可以使用配置中的 `server.host` 和 `server.port` 组装后端地址。`set-default` 接受完整 workspace ID、短 hash 前缀或精确 workspace 名称，然后把选中的 workspace 写入 `~/.zembra/config.cli.toml`。

## HTTP 模式

`zembra-cli` 也可以连接到 Zembra HTTP backend。需要优先尝试 HTTP 时，把 backend URL 写入 `~/.zembra/config.cli.toml`：

```toml
[cli]
http_base_url = "http://127.0.0.1:3000"
```

HTTP 和本地存储使用同一套面向用户的命令。配置 `http_base_url` 后，命令会优先尝试 HTTP；HTTP 请求失败时，如果配置了 SQLite 数据库路径，会回退到本地数据库。

## MCP Server

启动本地 stdio MCP Server：

```bash
zembra-cli mcp
```

MCP Server 使用 direct SQLite 模式，直接访问本地数据库，不需要启动 HTTP backend。

可用 tools：

- `create_note`
- `list_notes`
- `list_tags`
- `list_fields`
- `random_notes`

## 开发

本仓库使用 `uv` 进行本地开发。

安装开发依赖：

```bash
uv sync
```

从仓库内运行 CLI：

```bash
uv run zembra-cli --help
```

运行测试：

```bash
uv run pytest
```

运行 lint 检查：

```bash
uv run ruff check .
```

共享数据契约位于 `vendor/zembra-schema` submodule。新 clone 仓库后，在开发 schema 相关数据库功能前需要先初始化 submodule：

```bash
git submodule update --init --recursive
```
