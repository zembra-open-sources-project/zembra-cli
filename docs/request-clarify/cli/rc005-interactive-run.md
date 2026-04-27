# Run 交互式笔记录入需求澄清

日期：2026.04.27

## 需求结论

为 `zembra-cli` 增加 `run` 命令，启动一个持久化命令行交互程序。程序启动后使用 Rich 展示漂亮的 intro 界面，包含 Zembra 文本 TUI Logo、数据库路径和笔记统计信息。随后用户进入一行式笔记录入流程，输入内容后按 Enter 提交笔记，输入 `/exit` 退出程序。

## 已确认规则

| 问题 | 结论 |
| --- | --- |
| 启动命令 | `zembra-cli run` |
| UI 技术 | 本阶段先使用 Rich，不引入 Textual |
| 提交快捷键 | Enter 直接提交当前输入 |
| 输入模式 | 一行输入，一次提交一条笔记 |
| 退出命令 | `/exit` |
| 帮助命令 | `/help` |
| 启动信息 | 展示数据库路径和笔记统计，不展示最近笔记摘要 |
| 保存反馈 | 成功后显示 `Saved note <短ID> · <时间>` |
| 配置缺失 | 启动时直接失败，并沿用现有修复提示 |
| 数据库未初始化 | 启动时直接失败，并沿用现有修复提示 |

## 输入解析规则

交互输入需要支持从用户正文中解析 field 和 tag：

```text
I learn how to use codex today @dev #gpt
```

解析结果：

| 项目 | 结果 |
| --- | --- |
| note content | `I learn how to use codex today` |
| field | `dev` |
| tags | `["gpt"]` |

### 字段规则

| 规则 | 结论 |
| --- | --- |
| field 标记 | 使用 `@field` |
| 默认 field | 未输入 `@field` 时使用 `inbox` |
| field 数量 | 每条笔记使用一个 field |
| 多个 field | 本阶段暂不定义，设计阶段需要给出清晰失败或取值策略 |
| field 缺失 | 使用默认 field `inbox` |

### 标签规则

| 规则 | 结论 |
| --- | --- |
| tag 标记 | 使用 `#tag` |
| tag 数量 | 允许零个或多个 tag |
| 多个 tag | 解析为按输入顺序排列的 tag 列表 |
| 重复 tag | 设计阶段沿用现有 CLI 去重策略 |

## 本阶段范围

| 对象 | 操作 |
| --- | --- |
| CLI | 新增 `run` 命令 |
| Rich intro | 展示 Zembra Logo、数据库路径、笔记统计 |
| 交互循环 | 支持输入、保存、反馈、退出、帮助 |
| 输入解析 | 从正文解析 `@field` 和 `#tag` |
| Repository 调用 | 复用现有 `create_note()` 写入数据库 |
| 测试 | 覆盖解析逻辑、命令行为和错误路径 |

## 暂不包含

- Textual 全屏应用
- 多行笔记录入
- 最近笔记摘要展示
- 自动初始化数据库
- 交互式编辑已保存笔记
- 交互式选择 field 或 tags
- `/search`、`/delete`、`/list` 等更多命令
