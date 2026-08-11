# SnipContext VS Code Extension

Manage and insert code snippets from your local SnipContext store directly in VS Code.

## Requirements

- VS Code >= 1.85.0
- `snipcontext serve` running locally at `http://localhost:8000`

## Features

- Browse snippets in the Activity Bar sidebar
- Click a snippet to insert it at the cursor
- Save selected text as a new snippet via context menu or `Ctrl+Alt+S`

## Development

```bash
cd editors/vscode
npm install
npm run compile
```

## Usage

1. Run `snipcontext serve` in a terminal.
2. Open the SnipContext sidebar from the Activity Bar.
3. Browse snippets and click to insert.
4. Select text, right-click, and choose "Save Selection as Snippet".
