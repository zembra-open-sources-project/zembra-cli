# zembra-cli

本应用为 Zembra 笔记系统的命令行客户端。

## 技术栈

- Python 3.12
- uv
- rich
- Typer

## 共享数据表设计

本仓库通过 Git submodule 引入共享数据表契约：

```text
vendor/zembra-schema
```

该目录来自远程仓库：

```text
https://github.com/gawainx/zembra-schema.git
```

当前固定版本为 `v0.2.0`，对应 submodule commit `cd37a7e`。本仓库不复制维护数据表设计正文，数据表说明、SQLite DDL、JSON Schema 和 migration 都以 `vendor/zembra-schema` 为准。

首次拉取本仓库后，需要初始化 submodule：

```bash
git submodule update --init --recursive
```

升级共享 schema 时，在 `vendor/zembra-schema` 内切换到目标 tag 或 commit，再回到本仓库提交 submodule 指针变更：

```bash
cd vendor/zembra-schema
git fetch origin --tags
git checkout tags/<target-version>
cd ../..
git add .gitmodules vendor/zembra-schema README.md
git commit -m "docs: update shared schema reference"
```

提交前需要确认 schema 版本兼容性；如果数据结构有破坏性变化，需要同步更新本仓库的数据访问逻辑和迁移策略。

## 开发

安装依赖：

```bash
uv sync
```

运行 CLI：

```bash
uv run zembra-cli --help
```

## MCP Server

`zembra-cli` 可以作为本地 MCP Server 启动，链路为 MCP Client -> `zembra-cli` -> 本地 SQLite 数据库，不需要启动 HTTP backend。

启动前需要先初始化 direct 模式数据库：

```bash
uv run zembra-cli init
```

启动 stdio MCP Server：

```bash
uv run zembra-cli mcp
```

首批 MCP tools：

- `create_note`：创建 note，默认 `role` 为 `Agent`
- `list_notes`：列出本地 notes
- `list_tags`：列出本地 tags
- `list_fields`：列出本地 fields
- `random_notes`：随机返回可见 notes，并包含 field 与 tags

运行测试：

```bash
uv run pytest
```
