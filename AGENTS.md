# AGENTS

## Codex 持续开发工作流

### 开发流程约

本项目的所有需求开发，除非用户在 Prompt 中指定特殊流程，否则严格遵守如下步骤完成：

1. 需求澄清：接到用户需求后，首先进行需求澄清，确认功能范围。需求澄清过程以用户多轮交互的方式完成，澄清结束后，按模块写入 docs/request-clarify/ 下对应目录，写入方式为新建文件。
2. 基于需求澄清结果，完成方案设计，必要时和用户交互完成方案决策，按模块新建文件写入 docs/design-docs/ 下对应目录，该文件中需要记录需求澄清文档位置。写入后提醒用户审阅。设计文档中禁止堆砌代码，涉及接口设计、字段设计等内容时，以表格形式清晰说明即可，必要时可使用函数签名，但不要在文档中列举代码实现。
3. 根据技术设计结果，制定执行计划，按模块新建文件写入到 docs/exec-plans/active/ 下对应目录，提醒用户审核修改。开发计划必须记录需求澄清文档和设计文档的路径，开发计划中根据需求的工作量，划分为不同 Stage，并在 Stage 根据必要性划分为不同的 Task。
4. 根据执行计划进行开发，并更新执行计划中的任务状态，完成每个 Stage 后，如果修改了任何代码，必须进行一次 git 提交。
5. 用户验证后，将开发计划移动到 docs/exec-plans/completed/，并更新`docs/PROGRESS.md`文件。在未经用户允许，禁止擅自归档
6. 所有文档使用 markdown 格式撰写，语言为简体中文，关键术语、函数接口等信息可保留英文

### 初始化规则
- 初始化命令只创建缺失目录和文件。
- 已存在目录和文件必须 SKIP，禁止覆盖、删除、重命名或改写已有内容。
- 初始化输出只报告新建和跳过的目录/文件，不输出项目业务内容。
- 初始化只建立持续开发工作流骨架，不执行具体需求开发。

### 文档系统说明
- AGENTS.md 记录全局工作流、文档阅读顺序、产物落点、禁止事项和关键入口。
- ARCHITECTURE.md 描述系统全局结构、模块边界、依赖方向和不变量。
- docs/request-clarify/ 存放需求澄清结果，可按模块建立子目录。
- docs/design-docs/ 存放设计决策、设计理念和子系统方案，可按模块建立子目录。
- docs/product-specs/ 存放功能规格、用户流程、验收标准。
- docs/exec-plans/active/ 存放进行中的执行计划，可按模块建立子目录。
- docs/exec-plans/completed/ 存放已完成且已通过用户验收的执行计划，可按模块建立子目录。
- docs/exec-plans/tech-debt-tracker.md 记录项目的技术债。
- docs/references/ 存放外部依赖、协议、框架和工具参考资料摘要。
- docs/generated/ 存放自动生成文档；默认只读，不手工维护。
- `docs/PROGRESS.md` 项目进度追踪文件，包含两个章节。`项目流程记录` 章节记录项目计划与阶段推进状态，针对每个需求，记录需求编号、git HEAD id（保留前八位），然后使用连续的、不超过200字的简体中文描述本次开发实现的计划以及实现情况，每个需求只允许记录一个条目，如果存在该条目，则在已有内容基础上追加。
- docs/DESIGN.md 记录项目的设计规则，包括 UI 设计、功能设计规范。
- docs/FRONTEND.md 记录项目的前端设计架构。
- docs/PRODUCT_SENSE.md 记录产品判断和体验原则。
- docs/QUALITY_SCORE.md 记录质量评估标准。
- docs/RELIABILITY.md 记录项目可靠性设计。
- docs/SECURITY.md 记录项目安全规范。

阅读规则
- 开始任何任务时先读 AGENTS.md。
- 涉及结构、分层、依赖、模块边界时读 ARCHITECTURE.md 和相关 design docs。
- 涉及需求范围和澄清结论时读 docs/request-clarify/。
- 涉及功能目标、用户流程、验收条件时读 docs/product-specs/。
- 涉及中大改动时先在 docs/exec-plans/active/ 创建或更新执行计划，再开始实施。
- 涉及外部依赖、框架、协议时先读 docs/references/。
- 涉及生成物时只读 docs/generated/，不手工修改 generated 下的内容。

写回规则：
- 需求澄清结果写入 docs/request-clarify/。
- 技术设计和方案决策写入 docs/design-docs/。
- 执行计划、阶段进度、决策日志写入 docs/exec-plans/active/。
- 当前专注任务、流程记录、验证记录和归档索引写入 docs/PROGRESS.md。
- 遗留问题和明确未解决事项写入 docs/exec-plans/tech-debt-tracker.md。
- 工具或脚本生成的摘要写入 docs/generated/。

模块化文档落点：
- docs/request-clarify/、docs/design-docs/、docs/exec-plans/active/ 和 docs/exec-plans/completed/ 支持按模块建立子目录。
- 模块子目录命名应与代码模块、业务域或长期维护边界一致。
- 同一需求的澄清、设计、计划文档应使用同名文件，分别落入对应文档层。

文档命名规则：
- 默认命名格式为 rNNN-request-desc.md。
- 启用模块编号时，使用 r + 模块前缀 + 三位递增编号 + request-desc 的格式，例如 rb001-database-infrastructure.md。
- 当前模块前缀：database 使用 rbNNN，cli 使用 rcNNN。
- 新增模块前缀必须先写入 AGENTS.md，再创建对应需求文档。
- 同一需求在 request-clarify、design-docs、exec-plans 中使用同名文件。
- 日期只允许写在文档头部，不放入文件名。

命名真源规则：
- `zembra` 是本项目、笔记系统、Python 包和 CLI 命名的唯一真源。
- 遇到 `zambra`、`Zambra`、`.zambra.env` 等拼写时，必须自动对齐为 `zembra`、`Zembra`、`.zembra.env`，除非用户明确要求讨论历史拼写错误本身。
- 文档、代码、配置文件、命令示例和测试断言都必须使用 `zembra` 拼写。

执行计划状态规则：
- docs/exec-plans/active/ 只放当前进行中或等待验收的执行计划。
- 未经用户验收的执行计划不得自动移动到 docs/exec-plans/completed/。
- 用户验收通过后，才能把对应执行计划归档到 docs/exec-plans/completed/，并更新 docs/PROGRESS.md。

### 子目录 AGENTS.md 渐进披露
- 子目录 AGENTS.md 只能补充或收紧当前目录及其子树的局部规则。
- 子目录 AGENTS.md 不能覆盖、放宽或删除根 AGENTS.md 中的全局安全规则。
- 规则冲突时，以更严格的安全规则为准。

## Git 安全规则

- commit message 必须遵守 Conventional Commits：feat、fix、docs、style、refactor、perf、test、build、ci、chore、revert。
- 除非用户提示，否则禁止使用 git commit --amend。
- git 操作必须串行执行，避免并发 git add、commit、merge、rebase、checkout、switch。
- 执行 git checkout、git switch 或任何会改变当前分支的操作前，必须先运行 git worktree list，并确认当前 worktree 归属和目标分支占用情况。
