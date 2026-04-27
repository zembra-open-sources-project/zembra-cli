# Init 命令需求澄清

日期：2026.04.27

## 需求结论

为 `zembra-cli` 增加 `init` 命令，用于一键完成本地 zembra 使用前准备：创建 SQLite 数据库、执行共享 schema 初始化，并写入系统共享配置文件 `~/.zembra.env`。初始化完成后，`zembra-cli add` 和 `zembra-cli run` 可以直接读取配置并使用该数据库。

## 已确认规则

| 问题 | 结论 |
| --- | --- |
| 启动命令 | `zembra-cli init` |
| 默认数据库路径 | `~/.zembra/zembra.sqlite3` |
| 自定义数据库路径 | 支持 `zembra-cli init --database /path/to/zembra.sqlite3` |
| 配置文件路径 | 沿用 `~/.zembra.env` |
| 自动创建目录 | 允许自动创建数据库父目录，例如 `~/.zembra/` |
| 配置写入 | 写入或更新 `[database].path`，保留配置文件已有其他字段 |
| 成功输出 | 使用自然语言输出数据库路径、配置路径和初始化状态 |
| `--force` | 本阶段不支持 |

## 数据库已存在规则

| 场景 | 行为 |
| --- | --- |
| 数据库文件不存在 | 创建文件并执行共享 schema 初始化 |
| 数据库文件存在且 schema 完整 | 跳过 schema 初始化，报告 already initialized |
| 数据库文件存在但 schema 不完整 | 直接失败，不覆盖、不删除、不重建 |
| 数据库路径父目录不存在 | 自动创建父目录 |

## 配置已存在规则

| 场景 | 行为 |
| --- | --- |
| `~/.zembra.env` 不存在 | 创建配置文件并写入 `[database].path` |
| `~/.zembra.env` 已存在且合法 | 更新 `[database].path`，保留其他字段 |
| `~/.zembra.env` TOML 格式错误 | 失败并输出自然语言错误 |
| `~/.zembra.env` 父目录不存在 | 沿用现有配置写入错误处理 |

## 本阶段范围

| 对象 | 操作 |
| --- | --- |
| CLI | 新增 `init` 命令 |
| 数据库 | 自动创建数据库父目录和 SQLite schema |
| 配置 | 自动写入或更新 `~/.zembra.env` |
| 输出 | 展示数据库和配置初始化状态 |
| 测试 | 覆盖新建、已初始化、schema 不完整、自定义路径、配置保留字段 |

## 暂不包含

- `--force` 覆盖或重建数据库
- 数据库迁移升级
- 数据恢复或修复不完整 schema
- 自定义配置文件路径
- 初始化默认 field、tag 或 seed 数据
