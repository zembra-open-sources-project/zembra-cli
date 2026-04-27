# Init 命令设计文档

日期：2026.04.27

需求澄清文档：`docs/request-clarify/cli/rc006-init-command.md`

## 核心功能（WHAT）

为 `zembra-cli` 增加 `init` 命令，一键完成本地 zembra 使用前准备。命令负责创建数据库父目录、初始化 SQLite schema，并写入或更新 `~/.zembra.env` 中的 `[database].path`。初始化完成后，`add` 和 `run` 等数据库命令可以直接读取配置并访问数据库。

### 需求背景（WHY）

当前项目已经具备 SQLite schema 初始化函数、配置读写函数，以及依赖配置的 `add`、`run` 命令。用户第一次使用时仍需要手动组合数据库初始化和配置写入步骤。`init` 命令将这些步骤整合为可重复执行的安全初始化入口，降低首次使用成本。同时，现有 `src/zembra_cli/db.py` 已经承载连接、schema、表检查等多类数据库职责，本需求需要顺手把它迁入 `database` 子包，形成清晰的数据库模块边界。

### 需求目标（GOAL）

| 目标 | 说明 |
| --- | --- |
| 一键初始化 | `zembra-cli init` 创建默认数据库并写入配置 |
| 默认路径 | 默认数据库路径为 `~/.zembra/zembra.sqlite3` |
| 自定义路径 | 支持 `--database /path/to/zembra.sqlite3` |
| 自动建目录 | 数据库父目录不存在时自动创建 |
| 安全幂等 | 已初始化数据库不重复执行 schema |
| 保护数据 | 已存在但 schema 不完整的数据库直接失败 |
| 配置保留 | 更新 `[database].path` 时保留配置文件其他字段 |
| 输出清晰 | 输出数据库和配置的 created/skipped/updated 状态 |

### 范围边界

#### In Scope

| 模块 | 改动 |
| --- | --- |
| `src/zembra_cli/database/` | 新建 database 子包，承接原 `db.py` 的连接、schema 和初始化能力 |
| `src/zembra_cli/database/core.py` | 放置 SQLite 连接、schema 读取、初始化、核心表检查和 init helper |
| `src/zembra_cli/database/__init__.py` | 导出 database 子模块对外 API |
| `src/zembra_cli/cli.py` | 新增 `init` 命令和自然语言输出 |
| `tests/test_db.py` | 更新导入并覆盖初始化 helper 的新建、跳过和失败场景 |
| `tests/test_cli.py` | 覆盖 `init` 命令默认路径、自定义路径和配置保留 |

#### Out of Scope

| 项目 | 原因 |
| --- | --- |
| `--force` | 本阶段不覆盖、不删除、不重建用户数据库 |
| 数据库迁移升级 | 当前只初始化共享 initial schema |
| 修复不完整 schema | 需要单独设计数据保护与恢复策略 |
| 自定义配置文件路径 | 当前配置路径真源仍为 `~/.zembra.env` |
| seed 数据 | 初始化只创建结构，不创建默认 field、tag 或 note |
| 拆分多个 database 文件 | 本阶段只建立子包边界，避免过度拆分 |

## 实现流程（HOW）

### 技术决策

把 `src/zembra_cli/db.py` 迁移为 `src/zembra_cli/database/` 子包，先用 `core.py` 收拢现有数据库基础能力和新增 init helper。CLI、测试和其他调用方改为从 `zembra_cli.database` 导入公开 API。这样数据库职责拥有清晰子模块边界，后续再增长迁移、检查、维护能力时，可以在 `database` 子包内部继续拆分，而不是继续堆到顶层 `db.py`。

配置写入复用现有 `write_database_path()`，保持保留未知字段、TOML 校验和错误输出规则一致。

### database 子包结构

| 路径 | 职责 |
| --- | --- |
| `src/zembra_cli/database/__init__.py` | 对外导出数据库公共 API，保持调用方导入稳定 |
| `src/zembra_cli/database/core.py` | 当前承载连接、schema 读取、初始化、表检查和安全 init helper |

迁移后不再保留 `src/zembra_cli/db.py` 作为数据库入口，避免形成两个并行真源。

### 命令设计

```shell
zembra-cli init
zembra-cli init --database /path/to/zembra.sqlite3
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--database` | `Path` | `DEFAULT_DATABASE_PATH` | 要创建并写入配置的 SQLite 数据库路径 |

### 数据库初始化状态

建议新增初始化结果模型：

| 名称 | 字段 | 说明 |
| --- | --- | --- |
| `DatabaseInitResult` | `database_path: Path` | 展开后的数据库路径 |
| `DatabaseInitResult` | `status: Literal["created", "skipped"]` | 新建初始化或已完整跳过 |

建议新增错误类型：

| 名称 | 触发条件 | CLI 输出 |
| --- | --- | --- |
| `DatabaseInitializationError` | 初始化流程失败 | 输出 `message` |
| `DatabaseSchemaIncompleteError` | 文件存在但缺少核心表 | 提示数据库已存在但 schema 不完整 |

### 数据库 helper 流程

建议函数签名：

```python
def initialize_database_file(database_path: str | Path) -> DatabaseInitResult
```

| 步骤 | 行为 |
| --- | --- |
| 1 | 展开 `database_path` |
| 2 | 自动创建数据库父目录 |
| 3 | 若数据库文件不存在，连接 SQLite 并执行 `initialize_database()` |
| 4 | 若数据库文件存在，连接后检查 `missing_core_tables()` |
| 5 | 若缺表为空，返回 `skipped` |
| 6 | 若缺表非空，抛出 `DatabaseSchemaIncompleteError` |

### CLI init 流程

| 步骤 | 行为 |
| --- | --- |
| 1 | 解析 `--database`，默认使用 `DEFAULT_DATABASE_PATH` |
| 2 | 调用 `initialize_database_file()` |
| 3 | 调用 `write_database_path(database_path, default_config_path())` |
| 4 | 输出数据库路径、配置路径、数据库状态和配置状态 |

配置状态建议使用 `created` 或 `updated`，通过写入前 `default_config_path().exists()` 判断。

### 输出设计

成功输出示例：

```text
Initialized zembra.
Database: /Users/example/.zembra/zembra.sqlite3 (created)
Config: /Users/example/.zembra.env (created)
```

已有完整数据库时：

```text
Initialized zembra.
Database: /Users/example/.zembra/zembra.sqlite3 (already initialized)
Config: /Users/example/.zembra.env (updated)
```

### 错误处理

| 场景 | 处理 |
| --- | --- |
| 数据库父目录无法创建 | 输出自然语言错误，退出码非 0 |
| SQLite 无法打开或初始化 | 输出自然语言错误，退出码非 0 |
| 数据库文件存在但 schema 不完整 | 失败，不覆盖、不删除、不执行 schema |
| 配置文件 TOML 格式错误 | 沿用 `ConfigError.message`，退出码非 0 |
| 配置文件父目录不存在 | 沿用 `write_database_path()` 的错误 |

## 测试用例

### 编译检查

| 命令 | 预期 |
| --- | --- |
| `uv run ruff check .` | 静态检查通过 |
| `uv run pytest` | 全量测试通过 |

### 手工检查

| 场景 | 预期 |
| --- | --- |
| `zembra-cli init` | 创建默认数据库和配置，输出 created |
| 再次执行 `zembra-cli init` | 数据库 skipped，配置 updated |
| `zembra-cli init --database /tmp/zembra.sqlite3` | 初始化指定数据库并写入配置 |
| 对不完整数据库执行 init | 失败且不覆盖原文件 |

### 回归检查

| 用例 | 预期 |
| --- | --- |
| 默认路径初始化 | 自动创建数据库父目录，核心表齐全 |
| 自定义路径初始化 | 配置文件写入自定义数据库路径 |
| 已完整数据库 | 不重复初始化，返回 already initialized |
| 不完整数据库 | 报错并列出缺失核心表 |
| 配置保留字段 | 已有未知字段在 init 后仍保留 |
| 后续 add/run | 初始化后数据库命令可通过配置读取路径 |
