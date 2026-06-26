# rc014 run 启动信息框上下文展示设计

日期：2026-06-26

需求澄清文档：docs/request-clarify/cli/rc014-run-context-panel.md

## 设计目标

`zembra-cli run` 在打开 repository 时已经读取完整 CLI 配置，因此启动信息框应复用这份配置上下文，避免在渲染层重复读取配置。展示内容保持为纯状态信息，不参与 repository 行为决策。

## 字段设计

| 字段 | 来源 | 展示规则 |
| --- | --- | --- |
| Workspace UUID | `load_cascading_config(...).workspace_id` | 必须存在；沿用 `open_cli_repository` 当前缺失即失败的规则 |
| HTTP backend URL | `load_cascading_config(...).http_base_url` | 有值时显示 URL；无值时显示 `not configured` |
| Repository location | 现有 repository location | 保持现有展示，direct 模式为数据库路径，HTTP 模式为 backend 与 fallback 描述 |

## 实现方案

新增一个轻量上下文对象承载 repository、location、workspace uuid 和 HTTP backend URL，由 `open_cli_repository` 统一产出。`run` 将上下文传给 `render_intro_for_repository`，`render_intro_for_repository` 再把字段传给 `render_intro`。这样 CLI 配置读取仍集中在 `open_cli_repository`，交互模块只负责渲染。

## 测试策略

在 `tests/test_interactive.py` 覆盖 `render_intro` 对 workspace uuid 和 HTTP backend URL 的展示。在 `tests/test_cli.py` 覆盖 `run` 从配置读取上下文并传递给 intro renderer，避免只测渲染函数而漏掉命令层连接。
