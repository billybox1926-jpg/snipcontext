# SnipContext TUI

Interactive terminal shell for browsing, searching, and managing snippets without leaving the console.

## Usage

```bash
sc repl
```

Optional install:

```bash
pip install snipcontext[tui]
```

## Features

- Browse snippets with rich rendering
- Search with hybrid/keyword/semantic modes
- Add, edit, and delete snippets interactively
- Tab completion for commands, flags, and snippet IDs
- Command history navigation
- Export snippets via REPL commands

## Commands

| Command | Aliases | Description |
|---------|---------|-------------|
| `add` | `a` | Add a snippet |
| `get` | `show` | Show a snippet |
| `list` | `ls` | List snippets |
| `edit` | `update` | Edit a snippet |
| `delete` | `rm` | Delete a snippet |
| `search` | `find` | Search snippets |
| `export` | `ex` | Export snippets |
| `config` | `cfg` | Config subcommands |
| `stats` | `stat` | Show stats |
| `watch` | — | Watch snippets directory |
| `index` | — | Index all snippets |
| `build-index` | `build` | Build search index |
| `providers` | — | List providers |

## Navigation

- `help` or `?` — show help
- `help <command>` — detailed usage hints
- `exit` or `quit` — leave the shell
- `Ctrl+D` — exit
- `Up`/`Down` — command history
- `Tab` — completion
