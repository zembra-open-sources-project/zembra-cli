# Local MCP Server 需求澄清

日期：2026.06.11

## 背景

用户希望在 `zembra-cli` 仓库中实现 MCP 服务，并明确通信链路为 `MCP Server -> Database`。启动 MCP 服务时，应由本仓库内的 MCP Server 直接访问本地 Zembra SQLite 数据库，不依赖 `zembra-backend-rust` 或其他 backend 服务。

## 已确认需求

| 项目 | 结论 |
| --- | --- |
| MCP 服务定位 | `zembra-cli` 内置本地 MCP Server |
| 启动入口 | 新增 `zembra-cli mcp` 子命令 |
| 通信链路 | `MCP Client -> zembra-cli MCP Server -> SQLite Database` |
| backend 依赖 | 不依赖 HTTP backend，不走 `HttpZembraRepository` |
| 数据库配置 | 沿用当前 `.zembra.env` direct 模式中的 `[database].path` |
| 暴露能力 | 第一批只暴露 MCP Tools |
| 首批 tools | `create_note`、`list_notes`、`list_tags`、`list_fields`、`random_notes` |
| 写入 role | MCP 创建 note 默认使用 `Agent` |
| 模块归属 | 新增 `mcp` 模块，编号前缀使用 `rmNNN` |

## 需求目标

| 目标 | 说明 |
| --- | --- |
| 本地自治 | MCP Server 可在没有 backend 的情况下直接读写本地数据库 |
| 复用现有数据层 | MCP tools 复用 `ZembraRepository` 和现有 Pydantic model |
| 客户端友好 | MCP tools 返回结构化、可解析的结果 |
| 写入来源清晰 | 通过 MCP 创建的 note 默认标记为 `Agent` |
| 不破坏 CLI | 现有 `add`、`list`、`random`、`run`、HTTP 模式保持现状 |

## 范围边界

| 纳入范围 | 不纳入范围 |
| --- | --- |
| `zembra-cli mcp` 启动 stdio MCP Server | HTTP/SSE/Streamable HTTP MCP 服务 |
| MCP Tools 暴露基础 note/taxonomy 能力 | MCP Resources 和 Prompts |
| direct SQLite 配置读取与数据库初始化校验 | backend 代理、远程数据库代理 |
| `create_note` 默认 role 为 `Agent` | 用户体系、鉴权、多租户 |
| 自动化测试覆盖 MCP tool 与 direct 数据库链路 | 数据库 schema 迁移 |
| README 或相关文档补充 MCP 启动示例 | GUI、TUI 或 Web UI |

## 验收标准

| 场景 | 预期 |
| --- | --- |
| direct 配置有效且数据库已初始化 | `zembra-cli mcp` 能启动 MCP Server |
| MCP 调用 `create_note` | 数据库新增 note，`role` 为 `Agent` |
| MCP 调用 `list_notes` | 返回本地数据库中的 note 结构化数据 |
| MCP 调用 `list_tags` / `list_fields` | 返回本地数据库中的 taxonomy 数据 |
| MCP 调用 `random_notes` | 返回本地数据库随机可见 notes，包含 field 与 tags |
| `.zembra.env` 为 HTTP 模式 | MCP Server 拒绝启动或返回清晰配置错误，不连接 HTTP backend |
| 数据库文件不存在或核心表缺失 | MCP Server 启动失败并给出清晰错误 |
| 现有 CLI 测试 | 现有 CLI direct/HTTP 行为不回归 |

