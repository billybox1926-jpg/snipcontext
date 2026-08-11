# SnipContext: Your Local LLM-Optimized Code Snippet Manager

I have thousands of code snippets scattered across files, chat logs, and notes. Finding the right one for a prompt was a nightmare — until I built SnipContext.

## The Problem

Existing snippet managers are either cloud-based, don't support semantic search, or aren't designed for LLM workflows. Most developers still:
- Copy-paste from old projects
- Search through chat logs
- Maintain fragmented notes

This is slow, error-prone, and wastes high-value context when feeding code to LLMs.

## The Solution

[SnipContext](https://github.com/billybox1926-jpg/snipcontext) is a local-first code snippet manager built for the AI era.

- **Local-first** — Your snippets stay on your machine. No accounts, no cloud sync, no vendor lock-in.
- **Semantic search** — Finds code by meaning, not just keywords. Powered by sentence-transformers and FAISS.
- **Hybrid search** — Combines semantic and keyword search with configurable weights.
- **LLM-optimized exports** — Formats snippets for Claude, OpenAI, Cursor, Ollama, and more.
- **Editor integrations** — VS Code sidebar and Neovim plugin for instant insertion.
- **Git-friendly storage** — One JSON file per snippet, easy to diff and version.

## Why Local-First Matters

Privacy, offline use, git tracking, and ownership matter. SnipContext stores everything in standard formats under `~/.local/share/SnipContext` or a project-local `.snipcontext/` directory. You can back it up, diff it, or put it under version control.

## Who It's For

- Developers who curate reusable code
- Prompt engineers building context libraries
- AI researchers assembling reproducible datasets
- Teams sharing boilerplate and patterns

## Getting Started

```bash
pip install snipcontext
pip install "snipcontext[semantic]"  # for semantic search

snipcontext config init
snipcontext add --title "Read CSV" --language python --tags pandas,csv
snipcontext search "how to read a CSV file"
```

For editor integration, run `snipcontext serve` and install the VS Code or Neovim plugin.

## What's Next

The project is actively evolving. Upcoming areas:
- More export providers
- Improved scaling and sharding
- Additional editor integrations
- Performance benchmarks

If this resonates, I'd love your feedback. Star the repo, try it out, and open an issue.

---

*Posted on [dev.to](https://dev.to) / [Medium](https://medium.com) / personal blog. Adjust links before publishing.*
