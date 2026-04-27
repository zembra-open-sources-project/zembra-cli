# Add 命令 role 参数开发计划

日期：2026.04.27

## Related Design Doc

`docs/design-docs/cli/rc004-add-role-option.md`

需求澄清文档：`docs/request-clarify/cli/rc004-add-role-option.md`

## Stage #1: CLI role 解析

### Task #1: 新增 role 解析函数

**Status:** Finished

**Files:** Modify `src/zembra_cli/cli.py`; Modify `tests/test_cli.py`

**Function:** 支持 `Agent`、`Human`、`agent`、`human`、`a`、`h` 输入，并归一化到 `Agent` 或 `Human`。

**Implementation Notes:** 解析函数只接受当前 schema 枚举及其短别名；非法值使用 CLI 失败路径返回清晰提示。

**Expected Verification Result:** 单元测试覆盖所有允许变体和非法值。

## Stage #2: Add 命令接入

### Task #2: 将 `--role` 接入 note 创建

**Status:** Finished

**Files:** Modify `src/zembra_cli/cli.py`; Modify `tests/test_cli.py`

**Function:** `add` 命令新增 `--role`，默认 `Human`，创建 note 时传入归一化 role。

**Implementation Notes:** 成功输出中保留 `note.role`，并在 `metadata.role` 中返回归一化值，方便 CLI 调用方确认。

**Expected Verification Result:** 默认创建为 `Human`，传入 `--role a` 创建为 `Agent`。

## Stage #3: 验证与提交

### Task #3: 回归验证

**Status:** Finished

**Files:** Verify full repository

**Function:** 运行测试和 lint，确认 CLI 入口适配无回归。

**Implementation Notes:** 执行 `uv run pytest` 和 `uv run ruff check .`。

**Expected Verification Result:** 所有测试通过，ruff 通过，完成后提交本阶段改动。

## 验证记录

- 2026.04.27：`uv run pytest`，62 passed。
- 2026.04.27：`uv run ruff check .`，All checks passed。
