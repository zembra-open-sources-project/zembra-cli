# Zembra Env Config 设计文档

日期：2026.04.26

需求澄清文档：`docs/request-clarify/cli/rc002-zembra-env-config.md`

## 核心功能（WHAT）

为 zembra 笔记系统增加共享 TOML 配置文件 `~/.zembra.env`，并让 `zembra-cli` 支持读取、加载和写入该配置。当前配置只包含数据库路径，CLI 中需要数据库的命令通过配置文件确定 SQLite 数据库位置。

### 需求背景（WHY）

`rc001` 中 `add` 命令使用固定数据库路径 `~/.zembra/zembra.sqlite3`。随着 zembra 系统后续可能包含多个程序，数据库路径需要进入系统级共享配置，避免每个程序各自硬编码路径。`.zembra.env` 用 TOML 表达配置，兼顾人工可读和后续字段扩展。

### 需求目标（GOAL）

| 目标 | 说明 |
| --- | --- |
| 系统共享配置 | 使用 `~/.zembra.env` 作为 zembra 系统配置 |
| TOML 解析 | Python 程序能读取并校验 `[database].path` |
| TOML 写入 | `config database` 能创建或更新数据库路径 |
| 保留扩展字段 | 更新配置时保留已有未知字段 |
| 数据库命令加载配置 | `add` 等需要数据库的命令先读配置再连接数据库 |
| 友好错误 | 配置缺失时提示用户新建配置 |
| 边界清晰 | 非数据库命令不强制要求配置文件存在 |

### 范围边界

#### In Scope

| 模块 | 改动 |
| --- | --- |
| `src/zembra_cli/config.py` | 新增配置路径、读取、校验、写入和错误类型 |
| `src/zembra_cli/cli.py` | 新增 `config database` 命令，并让数据库命令通过配置获取路径 |
| `tests/test_config.py` | 覆盖配置读取、缺失、格式错误、写入和保留字段 |
| `tests/test_cli.py` | 覆盖 `config database` 与 `add` 配置加载行为 |

#### Out of Scope

| 项目 | 原因 |
| --- | --- |
| 数据库初始化 | 本需求只管理路径配置 |
| 配置路径覆盖 | 用户已确认默认路径为 `~/.zembra.env` |
| 自动创建父目录 | 用户已接受父目录不存在时报错 |
| 多配置项 | 当前只配置数据库路径 |
| 多配置 profile | 不属于当前阶段 |

## 实现流程（HOW）

### 技术决策

使用 Python 3.12 标准库 `tomllib` 读取 TOML。写入 TOML 当前可以使用轻量手写序列化，因为本阶段字段很少；为了保留未来其他字段，写入时读取现有 TOML 到字典，只更新 `database.path`，再输出完整 TOML。若后续需要保留注释和原始格式，再引入专门 TOML 写库。

### 配置路径

| 项目 | 设计 |
| --- | --- |
| 默认路径 | `Path.home() / ".zembra.env"` |
| 文件格式 | TOML |
| 当前配置字段 | `[database].path` |
| 路径类型 | 字符串，加载后转为 `Path` |

### 配置模型

推荐新增轻量数据结构：

| 名称 | 字段 | 说明 |
| --- | --- | --- |
| `ZembraConfig` | `database_path: Path` | CLI 运行时使用的配置对象 |

### 配置文件示例

```toml
[database]
path = "/path/to/zembra.sqlite3"
```

### 配置读取设计

| 函数 | 输入 | 输出 | 说明 |
| --- | --- | --- | --- |
| `default_config_path()` | 无 | `Path` | 返回 `~/.zembra.env` |
| `load_config(config_path=None)` | 可选配置路径 | `ZembraConfig` | 读取 TOML 并校验 `[database].path` |
| `write_database_path(database_path, config_path=None)` | 数据库路径、可选配置路径 | `ZembraConfig` | 创建或更新配置，并返回新配置 |

### 配置错误设计

| 错误类型 | 触发条件 | CLI 提示 |
| --- | --- | --- |
| 配置文件缺失 | `~/.zembra.env` 不存在 | `Config file is missing at ~/.zembra.env. Create it with: zembra-cli config database <file-path>` |
| TOML 格式错误 | 文件不能被 TOML 解析 | 输出自然语言格式错误 |
| 数据库路径缺失 | `[database].path` 不存在或为空 | 提示使用 `zembra-cli config database <file-path>` 设置 |
| 父目录缺失 | 写入配置时配置文件父目录不存在 | 输出自然语言失败原因 |

### config database 命令设计

命令：

```shell
zembra-cli config database <file-path>
```

行为：

| 步骤 | 说明 |
| --- | --- |
| 1 | 读取现有 `~/.zembra.env`，不存在则使用空配置 |
| 2 | 检查 `~/.zembra.env` 父目录存在 |
| 3 | 设置或更新 `[database].path` |
| 4 | 写回 TOML |
| 5 | 输出自然语言成功信息 |

写入时不校验数据库文件是否已经存在；数据库存在性与 schema 校验仍由需要数据库的命令在实际执行时处理。

### add 命令迁移

`add` 命令执行路径调整为：

| 步骤 | 说明 |
| --- | --- |
| 1 | 调用 `load_config()` |
| 2 | 从 `ZembraConfig.database_path` 获取数据库路径 |
| 3 | 检查数据库文件存在 |
| 4 | 连接 SQLite 并检查核心表 |
| 5 | 调用 `ZembraRepository.create_note` |
| 6 | 输出 JSON |

`--version`、`--help`、`hello` 和 `config database` 不调用 `load_config()`。

### TOML 写入策略

| 约束 | 处理 |
| --- | --- |
| 保留未来字段 | 读取现有配置字典后只更新 `database.path` |
| 输出格式稳定 | 写回标准 TOML 结构，字符串使用 JSON 风格转义 |
| 不保留注释 | 当前阶段不承诺保留注释 |
| 父目录缺失 | 失败并输出自然语言原因 |

### 关键约束

| 约束 | 处理方式 |
| --- | --- |
| zembra 与 zembra-cli 命名 | 配置文件使用 zembra，CLI 命令仍使用 zembra-cli |
| 数据库路径来源 | 需要数据库的命令只从配置文件读取数据库路径 |
| 错误输出 | CLI 层捕获配置错误并输出自然语言 |
| 模块化开发 | 配置读写放入独立 config 模块，CLI 只编排 |

## 测试用例

### 编译检查

| 用例 | 预期 |
| --- | --- |
| `uv run ruff check .` | 通过 |
| `uv run pytest` | 通过 |

### 回归检查

| 用例 | 预期 |
| --- | --- |
| 读取有效配置 | 返回 `ZembraConfig.database_path` |
| 配置缺失 | 抛出配置缺失错误 |
| TOML 格式错误 | 抛出格式错误 |
| `[database].path` 缺失 | 抛出路径缺失错误 |
| `config database` 新建配置 | 生成 `~/.zembra.env` 并写入 `[database].path` |
| `config database` 更新配置 | 更新 path 并保留其他字段 |
| 配置父目录缺失 | 写入失败并返回自然语言错误 |
| `add` 读取配置路径 | 使用配置中的数据库路径创建 note |
| `add` 配置缺失 | 失败并提示 `zembra-cli config database <file-path>` |
| 非数据库命令 | `--version`、`hello` 不要求配置文件存在 |
