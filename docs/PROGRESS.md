# PROGRESS
- (afd4f56) : 2026.04.26 引入 zembra-schema 作为 vendor/zembra-schema Git submodule，并固定到远程 tag v0.1.0 对应的共享契约版本；README 已补充命令行客户端定位、技术栈、submodule 初始化方式、schema 升级流程和破坏性变更兼容性提醒，避免在本仓库复制维护数据表设计正文。
- [rc001] (27d03e0) : 2026.04.26 完成 docs/exec-plans/active/cli/rc001-cli-add-command.md 对应开发，统一 zembra-cli 入口，实现 add 命令、tags 解析、固定数据库路径、JSON 返回和错误处理，并整理 cli 与 database 需求编号文档。
- [rb003] (76f557f9) : 2026.04.27 完成 docs/exec-plans/active/database/rb003-schema-020-upgrade.md 对应升级，将 vendor/zembra-schema 固定到 v0.2.0，适配 notes.role 的 Human/Agent 创建角色，补充模型、Repository 和 SQLite 约束测试，并创建主仓库 v0.2.0 tag。
- [rc004] (52f125a6) : 2026.04.27 完成 docs/exec-plans/active/cli/rc004-add-role-option.md 对应开发，为 add 命令增加 --role 参数，默认 Human，支持 Agent、Human、agent、human、a、h 输入并归一化写入，输出 metadata.role，并补充 CLI 回归测试。
