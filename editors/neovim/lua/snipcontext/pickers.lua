-- Picker integration: Telescope preferred, fallback to vim.ui.select
local M = {}

local function format_snippet(s)
  local language = s.language or ""
  local tags = ""
  if s.tags and #s.tags > 0 then
    tags = " [" .. table.concat(s.tags, ", ") .. "]"
  end
  return string.format("%s (%s)%s", s.title, language, tags)
end

function M.pick_snippet(callback)
  local api = require("snipcontext.api")
  local snippets, err = api.list_snippets()
  if err then
    vim.notify("SnipContext: " .. tostring(err), vim.log.levels.ERROR)
    return
  end
  if not snippets or #snippets == 0 then
    vim.notify("No snippets found", vim.log.levels.INFO)
    return
  end

  local has_telescope, _ = pcall(require, "telescope")
  if has_telescope then
    M._pick_telescope(snippets, callback)
    return
  end

  M._pick_fallback(snippets, callback)
end

function M._pick_telescope(snippets, callback)
  local pickers = require("telescope.pickers")
  local finders = require("telescope.finders")
  local conf = require("telescope.config").values

  pickers.new({}, {
    prompt_title = "SnipContext Snippets",
    finder = finders.new_table {
      results = snippets,
      entry_maker = function(s)
        return {
          value = s,
          display = format_snippet(s),
          ordinal = s.title .. " " .. (s.language or ""),
        }
      end,
    },
    sorter = conf.generic_sorter({}),
    attach_mappings = function(prompt_bufnr, map)
      local actions = require("telescope.actions")
      map("i", "<CR>", function()
        local selection = actions.get_selected_entry(prompt_bufnr)
        if selection then
          callback(selection.value.id)
        end
        actions.close(prompt_bufnr)
      end)
      return true
    end,
  }):find()
end

function M._pick_fallback(snippets, callback)
  local items = {}
  for _, s in ipairs(snippets) do
    table.insert(items, {
      text = format_snippet(s),
      value = s.id,
    })
  end

  vim.ui.select(items, {
    prompt = "Select snippet:",
    format_item = function(item) return item.text end,
  }, function(choice)
    if choice then callback(choice.value) end
  end)
end

return M
