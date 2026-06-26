# HTTP 优先回退直连执行计划

日期：2026-06-26

需求澄清文档：`docs/request-clarify/cli/rc012-http-first-fallback.md`

设计文档：`docs/design-docs/cli/rc012-http-first-fallback.md`

## Stage 1：配置与连接选择

### Task 1.1：放宽 `cli.mode` 必填校验

状态：已完成

修改：`src/zembra_cli/config.py`、`tests/test_config.py`

验证：配置中只有 `database.path` 和 `workspace.id` 时可加载 direct 材料；配置中只有 `cli.http_base_url` 和 `workspace.id` 时可加载 HTTP 材料；非法 `cli.mode` 仍报错。

### Task 1.2：实现 HTTP 优先回退 repository

状态：已完成

修改：`src/zembra_cli/cli.py`、`tests/test_cli.py`

验证：有 `http_base_url` 时优先调用 HTTP repository；HTTP repository 抛出 `ZembraHttpClientError` 时自动打开 direct repository 并重试，同时 stderr 输出回退提示。

## Stage 2：文档与整体验证

### Task 2.1：更新用户文档

状态：已完成

修改：`README.md`

验证：README 不再要求用户通过 `mode` 指定 HTTP 或 direct，说明 HTTP 优先和本地回退规则。

### Task 2.2：运行验证并提交

状态：已完成

验证：运行 `uv run pytest tests/test_config.py tests/test_cli.py -q`、`uv run pytest -q` 和 `uv run ruff check .`，通过后 stage 并提交。

## 验证记录

2026-06-26：已运行 `uv run pytest tests/test_config.py tests/test_cli.py -q`，71 个测试通过。

2026-06-26：已运行 `uv run pytest -q`，146 个测试通过。

2026-06-26：已运行 `uv run ruff check .`，检查通过。

2026-06-26：根据用户反馈补充 HTTP 回退时的 stderr 提示，已运行 `uv run pytest tests/test_cli.py::test_add_command_falls_back_to_direct_after_http_error tests/test_config.py tests/test_cli.py -q`，71 个测试通过；已运行 `uv run pytest -q`，146 个测试通过；已运行 `uv run ruff check .`，检查通过。
