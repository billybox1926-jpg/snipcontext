if vim.g.loaded_snipcontext then
  return
end
vim.g.loaded_snipcontext = 1

local commands = require("snipcontext.commands")

-- Refresh helper
local function refresh_cache()
  local api = require("snipcontext.api")
  api.refresh_cache()
  vim.notify("SnipContext cache refreshed", vim.log.levels.INFO)
end

-- User commands
vim.api.nvim_create_user_command("SnipcontextList", function()
  commands.insert_snippet()
end, {})

vim.api.nvim_create_user_command("SnipcontextInsert", function()
  commands.insert_snippet()
end, {})

vim.api.nvim_create_user_command("SnipcontextSave", function()
  commands.save_selection()
end, { range = true })

vim.api.nvim_create_user_command("SnipcontextRefresh", function()
  refresh_cache()
end, {})

-- Default keymaps (opt-in via g:snipcontext_no_default_keymaps to disable)
if vim.g.snipcontext_no_default_keymaps then
  return
end

vim.keymap.set("n", "<leader>si", "<cmd>SnipcontextList<CR>", { noremap = true, silent = true, desc = "SnipContext: list snippets" })
vim.keymap.set("v", "<leader>ss", "<cmd>SnipcontextSave<CR>", { noremap = true, silent = true, desc = "SnipContext: save selection" })
vim.keymap.set("n", "<leader>sr", "<cmd>SnipcontextRefresh<CR>", { noremap = true, silent = true, desc = "SnipContext: refresh cache" })
