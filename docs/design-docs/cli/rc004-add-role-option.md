# Add 命令 role 参数设计文档

日期：2026.04.27

需求澄清文档：`docs/request-clarify/cli/rc004-add-role-option.md`

## 核心功能

`zembra-cli add` 支持 `--role` 参数，让用户在创建笔记时指定 `Human` 或 `Agent` 创建角色。

## 设计要点

| 项目 | 设计 |
| --- | --- |
| 参数位置 | `add` 命令局部参数 `--role` |
| 默认值 | CLI 默认接收 `Human` |
| 解析函数 | 新增 `parse_role_value()`，集中处理输入变体 |
| 支持变体 | `Agent`、`agent`、`a` 映射为 `Agent`；`Human`、`human`、`h` 映射为 `Human` |
| 错误处理 | 非法输入通过 `fail_command()` 输出可读错误 |
| 输出 | 成功 JSON 中的 `note.role` 来自模型，`metadata.role` 记录归一化值 |

## 预期改动范围

| 文件 | 改动 |
| --- | --- |
| `src/zembra_cli/cli.py` | 增加 role 解析和 `add --role` |
| `tests/test_cli.py` | 覆盖默认值、大小写、缩写和非法输入 |

## 验证方式

| 命令 | 预期 |
| --- | --- |
| `uv run pytest` | 全量测试通过 |
| `uv run ruff check .` | 静态检查通过 |
