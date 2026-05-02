# Slash 命令即时帮助设计文档

日期：2026.05.02

需求澄清文档：`docs/request-clarify/cli/rc008-slash-command-help.md`

## 核心功能（WHAT）

在 `zembra-cli run` 的交互输入模式中增加斜杠命令即时帮助。用户当前输入以 `/` 开头时，系统根据前缀匹配已有命令，并立即用 Rich 表格展示候选命令和帮助说明。该能力只提示现有 `/help` 与 `/exit`，不新增命令，不改变 Enter 提交后的命令处理逻辑。

### 需求背景（WHY）

现有交互模式已经支持 `/help` 与 `/exit`，但用户需要知道命令并按 Enter 后才能看到帮助。即时提示可以让交互输入更容易发现，尤其是在快速记录笔记时，用户输入 `/` 就能看到当前可用控制命令。

### 需求目标（GOAL）

| 目标 | 说明 |
| --- | --- |
| 即时提示 | 输入内容以 `/` 开头时立即展示候选命令 |
| 前缀匹配 | `/` 展示全部，`/h` 只展示 `/help`，`/e` 只展示 `/exit` |
| 复用命令源 | 候选命令只来自现有 `/help` 与 `/exit` |
| Rich 表格 | 使用 Rich 输出候选列表和简短帮助 |
| 非侵入 | 普通笔记录入、field/tag 解析、命令提交逻辑保持不变 |

### 范围边界

#### In Scope

| 模块 | 改动 |
| --- | --- |
| `src/zembra_cli/interactive.py` | 新增命令候选数据结构、前缀匹配函数、候选帮助渲染函数和输入读取回调 |
| `tests/test_interactive.py` | 覆盖候选匹配、候选表格输出和普通输入不触发 |

#### Out of Scope

| 项目 | 原因 |
| --- | --- |
| 新增斜杠命令 | 本阶段只提示已有命令 |
| Textual 全屏 TUI | 当前交互模式仍使用 Rich + prompt_toolkit |
| 模糊匹配 | 已确认使用前缀匹配 |
| 正文中间 `/` 触发 | 已确认只在输入以 `/` 开头时触发 |
| 自动补全选择 | 已确认展示 Rich help 表格，不做候选选择补全 |

## 实现流程（HOW）

### 当前架构

`run_interactive_session()` 通过 `input_func("zembra> ")` 读取完整输入行，提交后再处理 `/help`、`/exit`、未知命令或普通笔记保存。生产输入函数 `read_interactive_line()` 使用 `prompt_toolkit.prompt()`，Rich 输出集中在 `render_intro()` 与 `render_help()`。

### 技术决策

将即时帮助放在输入读取层实现。`run_interactive_session()` 仍只负责提交后的命令和保存分发，避免把“输入过程中提示”与“Enter 后执行命令”混在一起。生产环境通过 prompt_toolkit 的输入变化回调观察当前 buffer 文本；当文本以 `/` 开头且匹配结果变化时，用 Rich 打印候选帮助表格。

### 命令候选模型

| 名称 | 字段 | 说明 |
| --- | --- | --- |
| `SlashCommandHelp` | `command: str` | 命令文本，例如 `/help` |
| `SlashCommandHelp` | `description: str` | 命令说明 |

候选真源定义在 `interactive.py`，包含：

| command | description |
| --- | --- |
| `/help` | Show this help |
| `/exit` | Exit the interactive session |

### 前缀匹配

| 输入 | 匹配结果 |
| --- | --- |
| `/` | `/help`、`/exit` |
| `/h` | `/help` |
| `/e` | `/exit` |
| `/x` | 空列表 |
| `note / text` | 不触发匹配 |

建议新增函数：

| 函数 | 职责 |
| --- | --- |
| `match_slash_commands(input_text: str) -> list[SlashCommandHelp]` | 当输入以 `/` 开头时返回前缀匹配命令，否则返回空列表 |
| `render_slash_command_help(console: Console, matches: list[SlashCommandHelp]) -> None` | 用 Rich 表格展示候选命令和说明 |

### 即时渲染策略

| 场景 | 策略 |
| --- | --- |
| 输入 `/` | 渲染包含全部候选的 Rich 表格 |
| 输入前缀变化 | 重新渲染匹配结果 |
| 输入不以 `/` 开头 | 不渲染候选 |
| 匹配结果为空 | 渲染空候选提示或不渲染新表格，提交后的未知命令提示保持不变 |

为了避免每个按键重复刷屏，输入回调应记录上一次已展示的前缀或候选集合，只在匹配状态变化时打印。测试层可以直接测试匹配函数和渲染函数；生产回调只做薄封装。

### 帮助输出关系

`render_help()` 继续负责 Enter 提交 `/help` 后展示完整帮助，包括命令和笔记输入示例。即时候选表格只展示斜杠命令候选，不包含 `note @dev #gpt` 等普通输入示例。

## 测试用例

### 编译检查

| 命令 | 预期 |
| --- | --- |
| `uv run ruff check .` | 静态检查通过 |
| `uv run pytest` | 全量测试通过 |

### 手工检查

| 场景 | 预期 |
| --- | --- |
| `zembra-cli run` 后输入 `/` | 立即展示 `/help` 与 `/exit` 候选表格 |
| 输入 `/h` | 候选表格只包含 `/help` |
| 输入 `/e` | 候选表格只包含 `/exit` |
| 输入 `note / text` | 不展示斜杠候选，Enter 后保存普通笔记 |
| 提交 `/help` | 继续展示完整帮助并留在交互会话 |
| 提交 `/exit` | 正常退出交互会话 |

### 回归检查

| 用例 | 预期 |
| --- | --- |
| 空输入 | 仍提示 `Write a note, or use /help.` |
| 未知命令 | 提交后仍提示 `Unknown command. Use /help.` |
| 普通笔记保存 | field/tag 解析和保存反馈不变 |
| Unicode 输入 | prompt_toolkit 输入读取能力不回退 |
