# zembra-cli

`zembra-cli` is the command-line client for Zembra, a local-first note system. It can create notes, browse existing fields and tags, run an interactive capture session, and expose the local note database to MCP clients.

## Install

`zembra-cli` is a standard Python package. It requires Python 3.12 or newer.

Install it as an isolated command-line tool:

```bash
pipx install zembra-cli
```

Or install it into the current Python environment:

```bash
python -m pip install zembra-cli
```

Check the installed command:

```bash
zembra-cli --help
```

## Initialize Local Storage

For local direct mode, initialize a SQLite database and write the shared Zembra config file:

```bash
zembra-cli init
```

Use a custom database path when needed:

```bash
zembra-cli init --database /path/to/zembra.sqlite3
```

The default config file is `~/.zembra.env`.

## Basic Usage

Create a note:

```bash
zembra-cli add "Remember to review the sync plan" --field Inbox --tags cli,review
```

Create an Agent-authored note:

```bash
zembra-cli add "Drafted by an agent" --field Inbox --role Agent
```

Start the interactive capture session:

```bash
zembra-cli run
```

List taxonomy values:

```bash
zembra-cli list tags --all
zembra-cli list fields --all
```

Show random notes:

```bash
zembra-cli random notes
zembra-cli random tags
zembra-cli random fields
```

Add `--json` to random commands when structured output is needed.

## HTTP Mode

`zembra-cli` can also connect to a Zembra HTTP backend. Configure `~/.zembra.env` with HTTP mode:

```toml
[cli]
mode = "http"
http_base_url = "http://127.0.0.1:3000"
```

The same user-facing commands are used in both direct and HTTP mode.

## MCP Server

Start the local stdio MCP server:

```bash
zembra-cli mcp
```

The MCP server uses direct SQLite mode and talks to the local database without starting an HTTP backend.

Available tools:

- `create_note`
- `list_notes`
- `list_tags`
- `list_fields`
- `random_notes`

## Development

This repository uses `uv` for local development.

Install development dependencies:

```bash
uv sync
```

Run the CLI from the repository:

```bash
uv run zembra-cli --help
```

Run tests:

```bash
uv run pytest
```

Run lint checks:

```bash
uv run ruff check .
```

The shared data contract lives in the `vendor/zembra-schema` submodule. After a fresh clone, initialize submodules before working with schema-backed database features:

```bash
git submodule update --init --recursive
```
