# Run 交互式笔记录入设计文档

日期：2026.04.27

需求澄清文档：`docs/request-clarify/cli/rc005-interactive-run.md`

## 核心功能（WHAT）

为 `zembra-cli` 增加 `run` 命令，提供一个轻量持久化命令行交互程序。用户启动 `zembra-cli run` 后，先看到 Rich 渲染的 Zembra intro 界面，再进入持续输入循环。每次输入一行内容并按 Enter 后，程序解析正文中的 `@field` 和 `#tag`，调用现有 Repository 写入笔记，并继续等待下一条输入。

### 需求背景（WHY）

当前 CLI 已具备 `add` 命令、共享配置读取、数据库初始化校验和 `ZembraRepository.create_note()` 能力。`run` 命令把“一次命令创建一条笔记”扩展为“启动后持续记录”，更适合快速捕获连续想法，同时保持本阶段实现轻量，不引入 Textual 全屏应用。

### 需求目标（GOAL）

| 目标 | 说明 |
| --- | --- |
| 持久交互 | `zembra-cli run` 启动后持续接收用户输入 |
| 漂亮 intro | 使用 Rich 展示 Zembra 文本 Logo、数据库路径和统计信息 |
| 快速保存 | Enter 直接提交当前输入为一条笔记 |
| 内容解析 | 从输入中解析 `@field` 和 `#tag` |
| 默认 field | 缺少 `@field` 时使用 `inbox` |
| 命令控制 | 支持 `/help` 和 `/exit` |
| 保存反馈 | 成功后显示 `Saved note <短ID> · <时间>` |
| 错误一致 | 配置或数据库不可用时沿用现有 CLI 失败路径 |

### 范围边界

#### In Scope

| 模块 | 改动 |
| --- | --- |
| `src/zembra_cli/cli.py` | 新增 `run` 命令入口，编排配置加载、数据库校验和交互循环 |
| `src/zembra_cli/interactive.py` | 新增交互展示、输入解析和保存循环逻辑 |
| `tests/test_cli.py` | 覆盖 `run` 命令启动失败路径和可测试交互行为 |
| `tests/test_interactive.py` | 覆盖输入解析、intro 数据模型和命令处理 |

#### Out of Scope

| 项目 | 原因 |
| --- | --- |
| Textual 全屏 TUI | 本阶段先使用 Rich 验证体验 |
| 多行输入 | 已确认 Enter 直接提交 |
| 最近笔记摘要 | 启动页只展示统计 |
| 自动初始化数据库 | 保持现有显式初始化和配置习惯 |
| 更多交互命令 | 本阶段只包含 `/help` 和 `/exit` |
| 笔记编辑、搜索、删除 | 与当前快速录入目标无关 |

## 实现流程（HOW）

### 技术决策

继续使用 Typer 作为命令入口，Rich 负责 intro 和交互输出。交互能力拆到独立 `interactive.py`，避免 `cli.py` 继续膨胀。数据库写入仍只通过 `ZembraRepository.create_note()` 完成，交互层只负责输入解析和调用编排。

### run 命令流程

| 步骤 | 说明 |
| --- | --- |
| 1 | 调用 `load_config(default_config_path())` 读取数据库路径 |
| 2 | 调用 `require_initialized_database()` 校验数据库存在且核心表完整 |
| 3 | 打开 SQLite connection 并创建 `ZembraRepository` |
| 4 | 读取统计信息，渲染 Rich intro |
| 5 | 进入输入循环，识别 `/help`、`/exit` 和普通笔记 |
| 6 | 普通笔记解析为 content、field、tags 后写入数据库 |
| 7 | 保存成功后打印短 ID 与时间，继续循环 |

### intro 设计

| 区域 | 内容 |
| --- | --- |
| Logo | Rich 文本绘制的 `Zembra` TUI Logo |
| 数据库 | 展示展开后的 SQLite 数据库路径 |
| 统计 | 展示当前有效笔记总数 |
| 输入提示 | 提示可使用 `@field`、`#tag`、`/help`、`/exit` |

统计只使用非删除笔记数量。若当前 Repository 只有 `list_notes()`，本阶段可以先用该方法统计，后续再根据性能需要增加 count 查询。

### 输入解析设计

| 输入片段 | 处理 |
| --- | --- |
| 普通文本 | 保留到 note content |
| `@field` | 解析为 field 名称，不进入 note content |
| `#tag` | 解析为 tag 名称，不进入 note content |
| 无 `@field` | 使用默认 field `inbox` |
| 多个 `#tag` | 按输入顺序解析并去重 |
| 重复 `#tag` | 沿用 `parse_tag_values()` 的去重语义 |
| 多个 `@field` | 使用最后一个 field，前面的 field 标记不进入正文 |

本阶段只解析独立 token，`hello@dev` 不视为 field，`#gpt,` 中的逗号不进入 tag 名称。解析后正文会压缩标记移除造成的多余空白，但保留普通词序。

建议新增数据模型：

| 名称 | 字段 | 说明 |
| --- | --- | --- |
| `InteractiveNoteInput` | `content: str` | 移除 field/tag 标记后的笔记正文 |
| `InteractiveNoteInput` | `field: str` | 解析出的 field，默认 `inbox` |
| `InteractiveNoteInput` | `tags: list[str]` | 解析出的去重 tag 列表 |

### 命令处理

| 输入 | 行为 |
| --- | --- |
| `/exit` | 打印简短退出信息并结束循环 |
| `/help` | 打印可用命令与输入格式 |
| 空白输入 | 不保存，提示继续输入 |
| 其他 `/xxx` | 提示未知命令，可输入 `/help` |

### 错误处理

| 场景 | 处理 |
| --- | --- |
| 配置文件缺失 | 沿用现有 `ConfigError.message`，退出码非 0 |
| 数据库文件缺失 | 沿用 `require_initialized_database()`，退出码非 0 |
| 数据库核心表缺失 | 沿用 `require_initialized_database()`，退出码非 0 |
| SQLite 写入失败 | 输出自然语言失败原因，保留交互循环可恢复 |
| 解析后正文为空 | 不写入数据库，提示用户输入正文 |

## 测试用例

### 编译检查

| 命令 | 预期 |
| --- | --- |
| `uv run ruff check .` | 静态检查通过 |
| `uv run pytest` | 全量测试通过 |

### 手工检查

| 场景 | 预期 |
| --- | --- |
| `zembra-cli run` | 展示 Zembra intro、数据库路径和统计 |
| 输入 `I learn codex @dev #gpt` | 保存到 field `dev`，tag 为 `gpt` |
| 输入 `quick note` | 保存到 field `inbox` |
| 输入 `/help` | 展示帮助内容并继续交互 |
| 输入 `/exit` | 正常退出 |

### 回归检查

| 用例 | 预期 |
| --- | --- |
| 配置缺失 | 与现有数据库命令一致，提示创建配置 |
| 数据库未初始化 | 与现有数据库命令一致，启动失败 |
| 输入解析 | 覆盖默认 field、显式 field、多个 tag、重复 tag、多个 field |
| 保存反馈 | 成功后包含短 ID 和时间 |
