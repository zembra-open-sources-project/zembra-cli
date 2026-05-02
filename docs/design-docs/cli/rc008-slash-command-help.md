# Slash 命令即时帮助设计文档

日期：2026.05.02

需求澄清文档：`docs/request-clarify/cli/rc008-slash-command-help.md`

## 核心功能（WHAT）

在 `zembra-cli run` 的交互输入模式中增加斜杠命令即时帮助。用户当前输入以 `/` 开头时，系统根据前缀匹配已有命令，并使用 prompt_toolkit 的临时候选菜单展示命令和帮助说明。该能力只提示现有 `/help` 与 `/exit`，不新增命令，不改变 Enter 提交后的命令处理逻辑。

### 需求背景（WHY）

现有交互模式已经支持 `/help` 与 `/exit`，但用户需要知道命令并按 Enter 后才能看到帮助。即时提示可以让交互输入更容易发现，尤其是在快速记录笔记时，用户输入 `/` 就能看到当前可用控制命令。

### 需求目标（GOAL）

| 目标 | 说明 |
| --- | --- |
| 即时提示 | 输入内容以 `/` 开头时立即展示候选命令 |
| 前缀匹配 | `/` 展示全部，`/h` 只展示 `/help`，`/e` 只展示 `/exit` |
| 复用命令源 | 候选命令只来自现有 `/help` 与 `/exit` |
| 临时候选菜单 | 使用 prompt_toolkit completer 展示候选和简短帮助 |
| 非侵入 | 普通笔记录入、field/tag 解析、命令提交逻辑保持不变 |

### 范围边界

#### In Scope

| 模块 | 改动 |
| --- | --- |
| `src/zembra_cli/interactive.py` | 新增命令候选数据结构、前缀匹配函数和 prompt_toolkit completer |
| `tests/test_interactive.py` | 覆盖候选匹配、completer 输出和普通输入不触发 |

#### Out of Scope

| 项目 | 原因 |
| --- | --- |
| 新增斜杠命令 | 本阶段只提示已有命令 |
| Textual 全屏 TUI | 当前交互模式仍使用 Rich + prompt_toolkit |
| 模糊匹配 | 已确认使用前缀匹配 |
| 正文中间 `/` 触发 | 已确认只在输入以 `/` 开头时触发 |
| Rich 表格打印候选 | 会污染终端历史输出，不符合 Codex 风格交互 |

## 实现流程（HOW）

### 当前架构

`run_interactive_session()` 通过 `input_func("zembra> ")` 读取完整输入行，提交后再处理 `/help`、`/exit`、未知命令或普通笔记保存。生产输入函数 `read_interactive_line()` 使用 `prompt_toolkit.prompt()`，Rich 输出集中在 `render_intro()` 与 `render_help()`。

### 技术决策

将即时帮助放在输入读取层实现。`run_interactive_session()` 仍只负责提交后的命令和保存分发，避免把“输入过程中提示”与“Enter 后执行命令”混在一起。生产环境通过 prompt_toolkit `Completer` 生成候选，候选菜单由 prompt_toolkit 管理，随输入刷新，不写入终端历史输出。

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
| `SlashCommandCompleter` | 将匹配结果转换为 prompt_toolkit `Completion`，展示命令和说明 |

### 即时渲染策略

| 场景 | 策略 |
| --- | --- |
| 输入 `/` | 候选菜单显示全部命令 |
| 输入前缀变化 | 候选菜单随前缀刷新 |
| 输入不以 `/` 开头 | 不提供候选 |
| 匹配结果为空 | 不提供候选，提交后的未知命令提示保持不变 |

候选菜单不使用 `console.print()`，避免每个按键留下历史表格。测试层直接测试匹配函数和 completer 输出。

### 帮助输出关系

`render_help()` 继续负责 Enter 提交 `/help` 后展示完整帮助，包括命令和笔记输入示例。输入过程中的候选菜单只展示斜杠命令候选，不包含 `note @dev #gpt` 等普通输入示例。

## 测试用例

### 编译检查

| 命令 | 预期 |
| --- | --- |
| `uv run ruff check .` | 静态检查通过 |
| `uv run pytest` | 全量测试通过 |

### 手工检查

| 场景 | 预期 |
| --- | --- |
| `zembra-cli run` 后输入 `/` | 输入行下方展示 `/help` 与 `/exit` 候选菜单 |
| 输入 `/h` | 候选菜单只包含 `/help` |
| 输入 `/e` | 候选菜单只包含 `/exit` |
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
