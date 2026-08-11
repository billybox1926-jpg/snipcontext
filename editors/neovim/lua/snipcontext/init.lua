-- SnipContext Neovim plugin module

local M = {}

function M.setup(opts)
  opts = opts or {}
  if opts.api_base then
    vim.g.snipcontext_api_base = opts.api_base
  end
  if opts.no_default_keymaps ~= nil then
    vim.g.snipcontext_no_default_keymaps = opts.no_default_keymaps and 1 or nil
  end
end

return M
