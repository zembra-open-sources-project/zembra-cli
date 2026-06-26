# rc014 run 启动信息框上下文展示需求澄清

日期：2026-06-26

## 背景

`zembra-cli run` 启动交互式笔记会话时会显示一个 Rich 信息框，当前包含数据位置、笔记数量和默认 field。用户希望该信息框额外显示当前 workspace uuid 以及 HTTP backend URL 信息，便于确认本次交互会话写入的 workspace 和连接的后端。

## 范围

本需求只调整 `zembra-cli run` 启动信息框的展示内容，不改变交互式输入、笔记保存、HTTP fallback、workspace 选择、配置读取优先级和其他命令输出。当前 workspace uuid 取自级联合并后的 CLI 配置中的 `workspace.id`；HTTP backend URL 取自级联合并后的 `cli.http_base_url`，未配置时显示为未配置状态。

## 验收标准

执行 `zembra-cli run` 时，启动信息框中显示当前 workspace uuid。配置了 HTTP backend URL 时，启动信息框中显示该 backend URL；未配置 HTTP backend URL 时，启动信息框明确显示未配置。既有 database/location、note count 和默认 field 展示保持可见。
