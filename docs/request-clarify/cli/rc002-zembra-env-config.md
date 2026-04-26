# Zembra Env Config 需求澄清

日期：2026.04.26

## 需求结论

为 zembra 笔记系统新增共享环境配置文件 `.zembra.env`，该文件遵循 TOML 格式规范，默认路径为：

```text
~/.zembra.env
```

本阶段在 `zembra-cli` Python 程序中完成配置文件读取、加载与写入能力，并新增命令：

```shell
zembra-cli config database <file-path>
```

该命令用于写入数据库路径配置。CLI 中需要访问数据库的命令在执行前默认加载 `~/.zembra.env`；若配置文件不存在，则失败并提示用户使用 config 命令新建配置。

## 已确认规则

| 问题 | 结论 |
| --- | --- |
| 命名边界 | `zembra` 是整个笔记系统名，`zembra-cli` 是 Python CLI 程序名 |
| 配置文件名 | 使用系统共享配置文件 `~/.zembra.env` |
| 配置格式 | TOML |
| 当前字段 | 只配置数据库路径 |
| TOML 结构 | 使用分组结构 |
| 写入命令 | `zembra-cli config database <file-path>` |
| 写入行为 | 配置文件不存在时创建，存在时只更新数据库路径字段并保留未来其他字段 |
| 父目录行为 | 配置文件父目录不存在时报错，不自动创建复杂目录 |
| 加载范围 | 只对需要数据库的命令强制加载配置 |
| 非数据库命令 | `--version`、`--help`、`hello`、`config database` 不要求配置文件存在 |
| 缺失配置提示 | 配置文件不存在时报错并提示使用 `zembra-cli config database <file-path>` 新建 |

## 配置文件结构

默认配置文件路径：

```text
~/.zembra.env
```

TOML 内容：

```toml
[database]
path = "/path/to/zembra.sqlite3"
```

## 命令行为

### 写入配置

```shell
zembra-cli config database /path/to/zembra.sqlite3
```

写入结果：

```toml
[database]
path = "/path/to/zembra.sqlite3"
```

### 加载配置

需要数据库的命令，例如 `add`，启动后默认从 `~/.zembra.env` 读取数据库路径，再连接对应 SQLite 数据库。

### 缺失配置

当需要数据库的命令执行时，如果 `~/.zembra.env` 不存在，返回自然语言错误：

```text
Config file is missing at ~/.zembra.env. Create it with: zembra-cli config database <file-path>
```

## 本阶段范围

| 模块 | 范围 |
| --- | --- |
| 配置读取 | 读取并解析 `~/.zembra.env` TOML 文件 |
| 配置模型 | 表达当前唯一字段 `[database].path` |
| 配置写入 | 新增 `zembra-cli config database <file-path>` |
| CLI 加载 | 数据库命令执行前加载配置文件 |
| add 命令迁移 | `add` 使用配置中的数据库路径，不再使用固定 `~/.zembra/zembra.sqlite3` |
| 自动化测试 | 覆盖读取、写入、缺失配置、保留未知字段和 add 命令读取配置 |

## 暂不包含

- 自动初始化数据库
- 自动创建数据库父目录
- 自动创建配置文件父目录
- 配置文件路径 CLI 覆盖参数
- 环境变量覆盖配置文件路径
- 多 profile 或多数据库配置
- 校验数据库文件必须已存在之外的复杂策略
- TUI/API 接入
