# SnipContext VS Code Extension

A Visual Studio Code extension for searching, inserting, and saving SnipContext snippets directly from the editor.

## Features

- Search snippets from SnipContext and insert them into the active editor.
- Save selected code as a new SnipContext snippet.
- Sidebar tree view showing available snippets.
- Configurable path to the SnipContext CLI.

## Commands

- `SnipContext: Search Snippets`
- `SnipContext: Insert Snippet`
- `SnipContext: Save Selection as Snippet`

## Configuration

- `snipcontext.cliPath`: Path to the SnipContext CLI executable. Defaults to `snipcontext`.

## Development

1. Install dependencies:

```bash
cd extensions/vscode
npm install
```

2. Compile the extension:

```bash
npm run compile
```

3. Launch the extension in a new Extension Development Host by pressing `F5` in VS Code.

## Notes

This extension currently uses the SnipContext CLI for snippet search and save operations. The command line tool must be available on your path or configured via `snipcontext.cliPath`.
