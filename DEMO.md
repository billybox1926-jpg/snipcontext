# SnipContext Demo

This guide walks you through a typical SnipContext workflow.

## Setup

```bash
# Install SnipContext
pip install snipcontext

# Initialize configuration (optional)
snipcontext config init

# Start the web API (for editor integrations)
snipcontext serve
```

## Saving a Snippet

Save your first snippet from the command line:

```bash
snipcontext add --title "Python fibonacci" --language python --tags "algorithm, recursion"
```

Or from an editor:
- VS Code: select code, right-click -> "Save Selection as Snippet"
- Neovim: visually select, then `:SnipcontextSave`

## Searching

Search for snippets semantically:

```bash
snipcontext search "fibonacci function"
```

Hybrid search (semantic + keyword):

```bash
snipcontext search "fibonacci" --hybrid
```

## Exporting for LLMs

Generate a context file for Claude:

```bash
snipcontext export --format claude --tags "algorithm" > context.xml
```

Or for ChatGPT:

```bash
snipcontext export --format openai --language python
```

## Using Editor Integrations

### VS Code
- Open the SnipContext sidebar (icon in activity bar).
- Click any snippet to insert it at the cursor.
- Right-click editor -> "Save Selection as Snippet".

### Neovim
- `:SnipcontextList` - open a fuzzy-finder to select and insert a snippet.
- `:SnipcontextSave` - save current selection or entire buffer.
- Default keymaps: `<leader>si` to list, `<leader>ss` to save.

## Managing Your Snippets

List all snippets:

```bash
snipcontext list
```

View stats:

```bash
snipcontext stats
snipcontext stats --verbose
```

## Watching for Changes

Auto-rebuild the search index when files change:

```bash
snipcontext serve --watch
```

## Migration

If you're upgrading from an older version, check the migration guide:

```bash
snipcontext migrate --dry-run
```

---

Now you're ready to build your own LLM-friendly second brain!
