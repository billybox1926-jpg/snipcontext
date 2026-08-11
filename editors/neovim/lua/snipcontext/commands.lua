-- User commands for SnipContext
local M = {}

function M.insert_snippet()
  local pickers = require("snipcontext.pickers")
  local api = require("snipcontext.api")
  pickers.pick_snippet(function(id)
    if not id then return end
    local snippet, err = api.get_snippet(id)
    if err then
      vim.notify("SnipContext: " .. tostring(err), vim.log.levels.ERROR)
      return
    end
    local row, col = unpack(vim.api.nvim_win_get_cursor(0))
    vim.api.nvim_buf_set_text(0, row - 1, col, row - 1, col, { snippet.content or "" })
  end)
end

function M.save_selection()
  local mode = vim.fn.mode()
  local text
  if mode == "v" or mode == "V" or mode == "\22" then
    local start_pos = vim.fn.getpos("'<")
    local end_pos = vim.fn.getpos("'>")
    local lines = vim.api.nvim_buf_get_text(
      0,
      start_pos[2] - 1,
      start_pos[3] - 1,
      end_pos[2] - 1,
      end_pos[3] - 1
    )
    text = table.concat(lines, "\n")
  else
    text = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
  end

  if not text or text == "" then
    vim.notify("No text to save", vim.log.levels.WARN)
    return
  end

  local default_title = vim.fn.expand("%:t")
  if default_title == "" then
    default_title = "snippet"
  end

  vim.ui.input({ prompt = "Enter snippet title: ", default = default_title }, function(title)
    if not title or title == "" then return end
    local api = require("snipcontext.api")
    local data = {
      title = title,
      content = text,
      language = vim.bo.filetype or "",
      tags = {},
    }
    local ok, err = api.create_snippet(data)
    if not ok then
      vim.notify("SnipContext: " .. tostring(err), vim.log.levels.ERROR)
    else
      vim.notify("Snippet saved: " .. title, vim.log.levels.INFO)
    end
  end)
end

return M
