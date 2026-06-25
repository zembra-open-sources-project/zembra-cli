# PROGRESS
- (afd4f56) : 2026.04.26 引入 zembra-schema 作为 vendor/zembra-schema Git submodule，并固定到远程 tag v0.1.0 对应的共享契约版本；README 已补充命令行客户端定位、技术栈、submodule 初始化方式、schema 升级流程和破坏性变更兼容性提醒，避免在本仓库复制维护数据表设计正文。
- [rc001] (27d03e0) : 2026.04.26 完成 docs/exec-plans/active/cli/rc001-cli-add-command.md 对应开发，统一 zembra-cli 入口，实现 add 命令、tags 解析、固定数据库路径、JSON 返回和错误处理，并整理 cli 与 database 需求编号文档。
- [rb003] (76f557f9) : 2026.04.27 完成 docs/exec-plans/active/database/rb003-schema-020-upgrade.md 对应升级，将 vendor/zembra-schema 固定到 v0.2.0，适配 notes.role 的 Human/Agent 创建角色，补充模型、Repository 和 SQLite 约束测试，并创建主仓库 v0.2.0 tag。
- [rc004] (52f125a6) : 2026.04.27 完成 docs/exec-plans/active/cli/rc004-add-role-option.md 对应开发，为 add 命令增加 --role 参数，默认 Human，支持 Agent、Human、agent、human、a、h 输入并归一化写入，输出 metadata.role，并补充 CLI 回归测试。
- [rc006] (1082cf41) : 2026.04.27 完成 docs/exec-plans/completed/cli/rc006-init-command.md 对应开发，新增 init 命令自动创建数据库、初始化 schema 并写入配置；同时将顶层 db.py 迁移为 database 子包，统一导入边界，已通过验收可正常新增笔记。
- [bfx001] (a65c4611) : 2026.04.27 完成 docs/bugfix/bfx001-unicode-backspace.md 对应 bugfix，将 zembra-cli run 的生产输入从内置 input 切换为 prompt_toolkit.prompt，保留 input_func 测试注入口并更新依赖锁文件，已通过 ruff、pytest 和用户中文退格验收。
- [rc008] (06e862ea) : 2026.05.03 完成 docs/exec-plans/completed/cli/rc008-slash-command-help.md 对应开发，为 zembra-cli run 增加斜杠命令候选能力，使用 prompt_toolkit completer 在输入以 / 开头时临时展示 /help 与 /exit 说明，避免 Rich 表格刷屏，并通过 ruff、pytest 和用户交互验收。
- [rc010] (98cade76) : 2026.05.16 完成 docs/exec-plans/completed/cli/rc010-random-notes.md 对应开发，为 zembra-cli 增加 random notes、random tags、random fields 三类命令，支持 direct 与 HTTP 双模式、JSON 输出和 Rich Markdown 人类可读渲染，并将 random notes 默认数量调整为非 JSON 三条、JSON 二十条；已通过 ruff 与全量 pytest 验证。
- [rc009] (f4d1fa40) : 2026.05.28 根据 localhost:3000 后端 OpenAPI 复核 HTTP 模式，修正 taxonomy 列表请求为 all=true。2026.06.25 根据后端新增 workspace id 的 CRUD 接口调整 HTTP 请求，要求 HTTP 模式配置 `[workspace].id`，notes、random 和 note tags 请求统一携带 `workspace_id`，并补齐本地模型 workspace 上下文。
