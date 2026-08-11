# SnipContext Neovim Plugin

Lightweight Neovim integration for [SnipContext](https://github.com/billybox1926-jpg/snipcontext).

## Requirements

- Neovim >= 0.9
- `snipcontext serve` running at `http://localhost:8000`

Optional, for richer picker UI:
- [telescope.nvim](https://github.com/nvim-telescope/telescope.nvim)

## Installation

### lazy.nvim

```lua
{
  "billybox1926-jpg/snipcontext",
  build = "echo 'Neovim plugin is pure Lua; no build step required.'",
  init = function()
    vim.g.snipcontext_api_base = "http://localhost:8000"
  end,
  keys = {
    { "<leader>si", "<cmd>SnipcontextList<CR>", desc = "SnipContext: list snippets" },
    { "<leader>ss", "<cmd>SnipcontextSave<CR>", desc = "SnipContext: save selection", mode = "v" },
    { "<leader>sr", "<cmd>SnipcontextRefresh<CR>", desc = "SnipContext: refresh cache" },
  },
  cmd = { "SnipcontextList", "SnipcontextSave", "SnipcontextRefresh" },
}
```

### packer.nvim

```lua
use({
  "billybox1926-jpg/snipcontext",
  opt = true,
  run = "echo 'Neovim plugin is pure Lua; no build step required.'",
  config = function()
    vim.g.snipcontext_api_base = "http://localhost:8000"
  end,
})
```

## Commands

- `:SnipcontextList` / `:SnipcontextInsert` – browse snippets and insert at cursor
- `:SnipcontextSave` – save selection or buffer as a snippet
- `:SnipcontextRefresh` – refresh cached snippet list

## Configuration

- `vim.g.snipcontext_api_base` – API base URL, default `http://localhost:8000`
- `vim.g.snipcontext_no_default_keymaps` – set to `1` to disable default keymaps

## Usage

1. Start the API:
   ```bash
   snipcontext serve
   ```

2. In Neovim, run `:SnipcontextList` and pick a snippet.

## License

MIT
