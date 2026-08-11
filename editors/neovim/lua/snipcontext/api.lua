-- HTTP client for snipcontext API
local M = {}

local API_BASE = vim.g.snipcontext_api_base or "http://localhost:8000"
local TIMEOUT = 3000 -- ms

-- Simple cache
local cache = {
  snippets = nil,
  last_fetch = 0,
  ttl = 30, -- seconds
}

local function http_request(method, path, data)
  local url = API_BASE .. path
  local curl_cmd = {"curl", "-s", "-X", method, "--max-time", tostring(TIMEOUT // 1000 + 1)}
  if data then
    table.insert(curl_cmd, "-H")
    table.insert(curl_cmd, "Content-Type: application/json")
    table.insert(curl_cmd, "-d")
    table.insert(curl_cmd, vim.fn.json_encode(data))
  end
  table.insert(curl_cmd, url)

  local output = vim.fn.system(curl_cmd)
  local rc = vim.v.shell_error
  if rc ~= 0 or not output or output == "" then
    return nil, "Empty or failed response from API (rc=" .. tostring(rc) .. ")"
  end
  local ok, parsed = pcall(vim.fn.json_decode, output)
  if not ok then
    return nil, "Invalid JSON: " .. tostring(output)
  end
  return parsed, nil
end

function M.list_snippets(force_refresh)
  local now = vim.fn.localtime()
  if not force_refresh and cache.snippets and (now - cache.last_fetch) < cache.ttl then
    return cache.snippets, nil
  end
  local result, err = http_request("GET", "/snippets")
  if err then return nil, err end
  cache.snippets = result.items or {}
  cache.last_fetch = now
  return cache.snippets, nil
end

function M.get_snippet(id)
  local result, err = http_request("GET", "/snippets/" .. tostring(id))
  if err then return nil, err end
  return result, nil
end

function M.create_snippet(data)
  local result, err = http_request("POST", "/snippets", data)
  if err then return nil, err end
  -- Invalidate cache after creation
  cache.snippets = nil
  return result, nil
end

function M.refresh_cache()
  cache.snippets = nil
  cache.last_fetch = 0
end

return M
