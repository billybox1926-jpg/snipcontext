import * as vscode from 'vscode';
import { SnipContextClient, Snippet } from '../client/snipcontextClient';
import { SnippetsTreeProvider } from '../providers/snippetsTreeProvider';

export function registerSearchCommand(
  context: vscode.ExtensionContext,
  client: SnipContextClient,
  treeProvider: SnippetsTreeProvider
) {
  context.subscriptions.push(
    vscode.commands.registerCommand('snipcontext.search', async () => {
      const query = await vscode.window.showInputBox({
        prompt: 'Search SnipContext snippets',
      });

      if (!query) {
        return;
      }

      try {
        const snippets = await client.searchSnippets(query);

        if (!snippets.length) {
          vscode.window.showInformationMessage('No snippets found.');
          return;
        }

        const selection = await vscode.window.showQuickPick(
          snippets.map((snippet) => ({
            label: snippet.title,
            description: snippet.language,
            detail: snippet.tags?.join(', '),
            snippet,
          })),
          { placeHolder: 'Select a snippet to insert' }
        );

        if (!selection) {
          return;
        }

        await vscode.commands.executeCommand('snipcontext.insert', selection.snippet);
        treeProvider.setSnippets(snippets);
      } catch (error) {
        vscode.window.showErrorMessage(`Search failed: ${String(error)}`);
      }
    })
  );
}
