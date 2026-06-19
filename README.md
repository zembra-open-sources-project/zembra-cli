# zembra-cli

`zembra-cli` is the command-line client for Zembra, a local-first note system. It
can create notes, browse existing fields and tags, run an interactive capture
session, and expose the local note database to MCP clients.

## Install

This project uses Python 3.12 and `uv`.

```bash
uv sync
```

Run the CLI from the repository:

```bash
uv run zembra-cli --help
```

## Initialize Local Storage

For local direct mode, initialize a SQLite database and write the shared Zembra
config file:

```bash
uv run zembra-cli init
```

Use a custom database path when needed:

```bash
uv run zembra-cli init --database /path/to/zembra.sqlite3
```

The default config file is `~/.zembra.env`.

## Basic Usage

Create a note:

```bash
uv run zembra-cli add "Remember to review the sync plan" --field Inbox --tags cli,review
```

Create an Agent-authored note:

```bash
uv run zembra-cli add "Drafted by an agent" --field Inbox --role Agent
```

Start the interactive capture session:

```bash
uv run zembra-cli run
```

List taxonomy values:

```bash
uv run zembra-cli list tags --all
uv run zembra-cli list fields --all
```

Show random notes:

```bash
uv run zembra-cli random notes
uv run zembra-cli random tags
uv run zembra-cli random fields
```

Add `--json` to random commands when structured output is needed.

## HTTP Mode

`zembra-cli` can also connect to a Zembra HTTP backend. Configure `~/.zembra.env`
with HTTP mode:

```toml
[cli]
mode = "http"
http_base_url = "http://127.0.0.1:3000"
```

The same user-facing commands are used in both direct and HTTP mode.

## MCP Server

Start the local stdio MCP server:

```bash
uv run zembra-cli mcp
```

The MCP server uses direct SQLite mode and talks to the local database without
starting an HTTP backend.

Available tools:

- `create_note`
- `list_notes`
- `list_tags`
- `list_fields`
- `random_notes`

## Development

Run tests:

```bash
uv run pytest
```

Run lint checks:

```bash
uv run ruff check .
```

The shared data contract lives in the `vendor/zembra-schema` submodule. After a
fresh clone, initialize submodules before working with schema-backed database
features:

```bash
git submodule update --init --recursive
```
