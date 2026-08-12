export const PROVIDERS = [
  {
    value: "generic",
    label: "Generic Markdown",
    description: "Universal Markdown format — works with any LLM",
    format: "markdown",
  },
  {
    value: "claude",
    label: "Claude XML",
    description: "Anthropic Claude XML format — optimal context structure",
    format: "xml",
  },
  {
    value: "cursor",
    label: "Cursor IDE",
    description: "Cursor IDE format — file-like context headers",
    format: "markdown",
  },
  {
    value: "openai",
    label: "OpenAI Prompt",
    description: "OpenAI prompt format — structured for API consumption",
    format: "prompt",
  },
  {
    value: "ollama",
    label: "Ollama Prompt",
    description: "Ollama prompt format — structured for local models",
    format: "prompt",
  },
] as const

export type ProviderValue = (typeof PROVIDERS)[number]["value"]
