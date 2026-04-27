# bfx001 中文退格异常修复

日期：2026-04-27

## 需求澄清

用户在 `zembra-cli run` 交互模式中输入中文后按退格，观察到退格行为不合理，只删除了半个字符或留下异常显示痕迹。该问题影响交互式笔记录入体验，不影响 `zembra-cli add` 这类由 shell 传参的非交互命令。

本次修复范围限定为交互式输入行编辑能力：

| 项目 | 结论 |
| --- | --- |
| 影响命令 | `zembra-cli run` |
| 影响场景 | 中文、多字节 Unicode 字符输入后的退格 |
| 非目标 | 不改动 note 解析、数据库写入、field/tag 语义 |
| 验收重点 | 中文退格每次删除一个完整字符，保存逻辑保持不变 |

## 问题分析

当前交互循环位于 `src/zembra_cli/interactive.py`，`run_interactive_session()` 默认使用 Python 内置 `input()` 读取整行。内置 `input()` 的行编辑能力依赖运行环境中的终端/readline 行为，对中文这类宽字符、多字节字符的光标刷新和退格处理不稳定，容易出现视觉上“删半个字”或残留错位。

业务解析函数 `parse_interactive_note_input()` 接收的已经是完整 Python `str`，没有按字节切分 Unicode 字符，因此问题根因在输入行编辑层，不在 note 内容解析或数据库保存层。

## 设计方案

推荐将生产环境输入函数从内置 `input()` 切换为 `prompt_toolkit.prompt()`。`prompt_toolkit` 是成熟的 Python 命令行输入库，能按 Unicode 字符和显示宽度处理光标移动、退格、刷新等行为。

| 模块 | 改动 |
| --- | --- |
| `pyproject.toml` | 新增 `prompt-toolkit` 依赖 |
| `src/zembra_cli/interactive.py` | 新增 `read_interactive_line()`，默认输入函数改为该函数 |
| `tests/test_interactive.py` | 增加默认输入 provider 接线测试 |
| `uv.lock` | 通过 `uv lock` 更新锁文件 |

`run_interactive_session()` 继续保留 `input_func` 参数，测试和未来自动化场景仍可注入自定义输入函数。

## 开发计划

### Stage 1：输入层改造

| Task | 状态 | 功能 | 实现要点 | 预期测试结果 |
| --- | --- | --- | --- | --- |
| Task 1 | Finished | 引入 Unicode 友好输入函数 | 新增 `read_interactive_line()` 并调用 `prompt_toolkit.prompt()` | 默认交互输入不再使用内置 `input()` |
| Task 2 | Finished | 保持测试注入口 | `run_interactive_session()` 保留 `input_func` 参数 | 现有交互测试继续通过 |

### Stage 2：验证

| Task | 状态 | 功能 | 实现要点 | 预期测试结果 |
| --- | --- | --- | --- | --- |
| Task 1 | Finished | 单元测试覆盖 | 新增默认输入函数接线测试 | `tests/test_interactive.py` 通过 |
| Task 2 | Finished | 全量测试回归 | 运行项目 pytest | 所有测试通过 |

## 验收记录

- `uv run pytest`：通过。
- 手工验收建议：运行 `uv run zembra-cli run`，输入 `你好世界` 后连续退格，确认每次删除一个完整中文字符。
