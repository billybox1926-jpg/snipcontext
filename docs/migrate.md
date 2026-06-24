# Migrating to SnipContext

This guide helps you migrate your existing snippet collections from other tools into SnipContext.

## From VS Code Snippets

VS Code stores language snippets in JSON files. You can copy the useful ones into SnipContext manually or with a small conversion step.

1. Export / locate your VS Code snippets:
   - Global snippets are usually under:
     - Windows: `%APPDATA%\Code\User\snippets\`
     - macOS: `~/Library/Application Support/Code/User/snippets/`
     - Linux: `~/.config/Code/User/snippets/`
2. Open each `.code-snippets` JSON file and copy the snippet content you want to keep.
3. Add each snippet via the CLI, for example:
   ```bash
   sc add "your snippet body here" --title "My Snippet" --tag vscode --tag python
   ```
4. Repeat for each snippet you want to preserve.

Tip: if you already have many snippets exported as JSON, you can script `sc add --batch` calls as a lightweight import path until a dedicated `sc import` command exists.

## From SnippetsLab

SnippetsLab exports snippets as JSON. The general approach is:

1. Export your library from SnippetsLab as JSON.
2. Convert each exported snippet into one or more `sc add` calls.
3. If you want to preserve labels, map them to tags with `--tag`.

A dedicated importer for SnippetsLab may be added later; for now a small script or manual copy-paste works.

## From Pieces

Pieces exposes an API to fetch stored snippets. To migrate:

1. Retrieve snippets from Pieces via its API or export flow.
2. Translate each item to a SnipContext snippet body + tags.
3. Import with `sc add`.

If you want a reusable migration script for Pieces, open an issue in the repo and we can turn this note into a maintained converter.

## Generic Approach

If your existing tool can export JSON, Markdown, or plain text:

1. Export the snippets.
2. Convert each entry into a plain code body with a short title.
3. Import using the CLI:
   ```bash
   sc add "snippet body" --title "Title" --tag one --tag two
   ```

For larger collections, write a short script that calls the CLI for each item. Future docs may include example converters for popular formats.

If your tool is not listed here, feel free to request a migration note in an issue.
