# rc014 run 启动信息框上下文展示执行计划

日期：2026-06-26

需求澄清文档：docs/request-clarify/cli/rc014-run-context-panel.md

设计文档：docs/design-docs/cli/rc014-run-context-panel.md

## Stage 1 测试锁定

- [x] Task 1：补充 `render_intro` 展示 workspace uuid 和 HTTP backend URL 的测试。验证：新增测试在实现前失败，失败点指向缺失展示字段。
- [x] Task 2：补充 `run` 命令传递 workspace uuid 和 HTTP backend URL 上下文的测试。验证：新增测试在实现前失败，失败点指向调用参数不匹配。

## Stage 2 最小实现

- [x] Task 1：让 `open_cli_repository` 返回包含 repository、location、workspace uuid 和 HTTP backend URL 的上下文。验证：`run` 命令测试通过。
- [x] Task 2：让启动信息框渲染 workspace uuid 和 HTTP backend URL。验证：`render_intro` 测试通过。

## Stage 3 验证与提交

- [x] Task 1：运行相关测试和 lint。验证：命令退出码为 0。
- [x] Task 2：更新计划任务状态并提交。验证：`git status --short` 只剩预期状态或为空。
