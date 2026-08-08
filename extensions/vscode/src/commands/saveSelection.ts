import * as vscode from 'vscode';
import { SnipContextClient } from '../client/snipcontextClient';
import { SnippetsTreeProvider } from '../providers/snippetsTreeProvider';

export function registerSaveSelectionCommand(
  context: vscode.ExtensionContext,
  client: SnipContextClient,
  treeProvider: SnippetsTreeProvider
) {
  context.subscriptions.push(
    vscode.commands.registerCommand('snipcontext.saveSelection', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showErrorMessage('No active editor available.');
        return;
      }

      const selection = editor.selection;
      if (selection.isEmpty) {
        vscode.window.showErrorMessage('Select code before saving it as a snippet.');
        return;
      }

      const content = editor.document.getText(selection);
      const title = await vscode.window.showInputBox({
        prompt: 'Snippet title',
        placeHolder: 'Enter a title for the snippet',
      });
      if (!title) {
        return;
      }

      const tagInput = await vscode.window.showInputBox({
        prompt: 'Snippet tags (comma-separated)',
        placeHolder: 'e.g. python, api, helper',
      });
      const tags = tagInput?.split(',').map((tag) => tag.trim()).filter(Boolean) ?? [];
      const language = editor.document.languageId;

      try {
        await client.saveSnippet(content, title, tags, language);
        await treeProvider.refresh();
        vscode.window.showInformationMessage('Snippet saved to SnipContext.');
      } catch (error) {
        vscode.window.showErrorMessage(`Failed to save snippet: ${String(error)}`);
      }
    })
  );
}
