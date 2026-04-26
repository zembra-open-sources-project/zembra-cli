# 命令行设计

## 命令行操作（非交互式）

### 新增笔记

```shell
zembra-cli add <note-string-content> --tags <multi-tags> --field <field>
```

- `--tags` 使用列表配置多个tag
- `--field` 匹配一个 field
- `<note-string-content>` 接受长文本，注意可能包含转义字符

Return: json with note and metadata ； 失败返回失败原因自然语言描述

### 删除笔记

```shell
zembra-cli delete note_id
```

