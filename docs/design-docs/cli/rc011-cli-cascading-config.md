# CLI 级联配置设计文档

日期：2026.06.25

需求澄清文档：`docs/request-clarify/cli/rc011-cli-cascading-config.md`

## 核心功能（WHAT）

为 `zembra-cli` 增加独立 CLI 配置文件 `~/.zembra/config.cli.toml`，并保留旧全局配置 `~/.zembra.env` 作为低优先级回退来源。配置读取采用字段级合并，写入侧只写 CLI 配置文件。

### 需求背景（WHY）

当前 `zembra-cli` 使用 `~/.zembra.env` 同时承载 CLI 连接模式和数据库路径。随着 zembra 系统内不同程序逐步拆分配置职责，CLI 需要维护自己的配置文件，同时继续兼容已经存在的全局配置，避免一次性推翻用户已有配置。

### 需求目标（GOAL）

| 目标 | 说明 |
| --- | --- |
| 独立 CLI 配置 | 固定使用 `~/.zembra/config.cli.toml` 维护 CLI 字段 |
| 兼容旧配置 | `~/.zembra.env` 继续作为低优先级读取来源 |
| 字段级合并 | CLI 配置缺失字段时可以从全局配置补齐 |
| 写入边界清晰 | CLI 命令只写 `config.cli.toml`，不迁移、不改写 `.zembra.env` |
| 行为不回归 | direct、HTTP、MCP、init 和 config database 保持现有功能语义 |
| 错误清晰 | 找不到可用配置时说明已检查两个配置路径 |

### 范围边界

| 纳入范围 | 不纳入范围 |
| --- | --- |
| `~/.zembra/config.cli.toml` 路径常量和函数 | 自动迁移旧配置 |
| `~/.zembra.env` 低优先级读取回退 | 删除旧配置读取 |
| `cli.mode` 字段级合并 | 多 profile 配置 |
| `cli.http_base_url` 字段级合并 | 后端配置体系调整 |
| `database.path` 字段级合并 | 默认数据库路径调整 |
| `config database` 写入 CLI 配置 | 保留旧文件注释格式 |
| `init` 写入 CLI 配置并创建 `~/.zembra/` | 新增配置导入导出命令 |
| README、测试和相关文档更新 | Web UI 或后端改动 |

## 实现流程（HOW）

### 配置路径设计

| 名称 | 路径 | 用途 |
| --- | --- | --- |
| CLI 配置 | `Path.home() / ".zembra" / "config.cli.toml"` | 高优先级 CLI 专属配置 |
| 全局配置 | `Path.home() / ".zembra.env"` | 低优先级兼容配置 |

在 `src/zembra_cli/config.py` 中新增 `default_cli_config_path()` 和 `default_global_config_path()`。删除旧的 `default_config_path()` 和 `load_config()` 公共入口，不保留兼容函数；新代码统一通过 `load_cascading_config()` 读取最终运行配置。

### 配置模型设计

现有 `ZembraConfig` 可以继续表达合并后的最终配置。

| 字段 | 类型 | 来源 |
| --- | --- | --- |
| `cli_mode` | `"direct" | "http"` | `cli.mode` 字段级合并结果 |
| `database_path` | `Path | None` | direct 模式下的 `database.path` 字段级合并结果 |
| `http_base_url` | `str | None` | HTTP 模式下的 `cli.http_base_url` 字段级合并结果 |

### 读取设计

新增级联读取函数，例如 `load_cascading_config(cli_config_path=None, global_config_path=None)`。该函数分别尝试读取 CLI 配置和全局配置，忽略不存在的文件，解析存在的 TOML 文件；任何存在但 TOML 非法的配置文件都应报错并指出具体路径。读取后按字段级规则合并，再复用现有 `_config_from_data()` 或等价校验逻辑生成 `ZembraConfig`。

字段级合并规则如下：

| 字段 | 优先级 |
| --- | --- |
| `cli.mode` | CLI 配置优先，缺失时读取全局配置 |
| `cli.http_base_url` | CLI 配置优先，缺失时读取全局配置 |
| `database.path` | CLI 配置优先，缺失时读取全局配置 |

如果两个文件都不存在，或合并后仍缺少当前模式必需字段，返回现有配置错误类型或新增更清晰的级联配置错误。缺少可用配置时，错误消息必须说明已检查 `~/.zembra/config.cli.toml` 和 `~/.zembra.env`。

### 写入设计

`write_database_path()` 应默认写入 CLI 配置路径。为了降低改动面，可以保留显式 `config_path` 参数用于测试和少量调用者覆盖。写入时仍然只更新 `[database].path`，当 `set_direct_mode=True` 时写入 `[cli].mode = "direct"`。写入前如果 `~/.zembra/` 不存在，普通 `config database` 命令推荐创建目录，因为 CLI 配置固定落在该目录下。

| 命令 | 写入目标 | 行为 |
| --- | --- | --- |
| `zembra-cli config database <path>` | `~/.zembra/config.cli.toml` | 创建或更新 `[database].path` |
| `zembra-cli init` | `~/.zembra/config.cli.toml` | 初始化数据库，写入 `[cli].mode = "direct"` 和 `[database].path` |

### 命令接入设计

| 入口 | 调整 |
| --- | --- |
| `open_cli_repository()` | 使用级联读取后的 `ZembraConfig` |
| `zembra-cli init` | 创建数据库父目录和 `~/.zembra/`，写入 CLI 配置 |
| `zembra-cli config database` | 写入 CLI 配置 |
| `zembra-cli mcp` | 使用级联配置，仍只接受 direct 模式 |
| `add/list/random/run` | 通过统一 repository 打开逻辑使用级联配置 |

### 错误处理设计

| 场景 | 处理 |
| --- | --- |
| 两个配置文件都不存在 | 报错说明已检查 `~/.zembra/config.cli.toml` 和 `~/.zembra.env` |
| CLI 配置 TOML 非法 | 报错指出 CLI 配置文件路径和 TOML 错误 |
| 全局配置 TOML 非法 | 报错指出全局配置文件路径和 TOML 错误 |
| 合并后缺少 `cli.mode` | 沿用 CLI mode 缺失错误，并在外层提示配置来源不足 |
| direct 模式缺少 `database.path` | 沿用数据库路径缺失错误 |
| HTTP 模式缺少 `cli.http_base_url` | 沿用 HTTP base URL 缺失错误 |

### 文档更新设计

README 中默认配置文件描述需要改为 `~/.zembra/config.cli.toml`，同时说明 `~/.zembra.env` 仍作为兼容回退来源。历史设计文档不需要改写结论，但本需求文档需要明确新规则覆盖旧规则。

## 测试用例

### 编译检查

| 用例 | 预期 |
| --- | --- |
| `uv run ruff check .` | 通过 |
| `uv run pytest` | 通过 |

### 回归检查

| 用例 | 预期 |
| --- | --- |
| 只有 CLI 配置 | 读取 CLI 配置成功 |
| 只有全局配置 | 读取全局配置成功 |
| 两个配置同时存在 | CLI 配置字段覆盖全局配置字段 |
| CLI 配置缺少 `database.path` | direct 模式可从全局配置补齐 |
| CLI 配置缺少 `cli.http_base_url` | HTTP 模式可从全局配置补齐 |
| 两个配置都不存在 | 错误提示已检查两个路径 |
| CLI 配置 TOML 非法 | 错误指出 CLI 配置路径 |
| `config database` | 写入 `~/.zembra/config.cli.toml` |
| `init` | 自动创建 `~/.zembra/` 并写入 CLI 配置 |
| MCP direct 模式 | 使用级联配置打开本地数据库 |
| HTTP 模式 | 使用级联配置连接 HTTP backend |
