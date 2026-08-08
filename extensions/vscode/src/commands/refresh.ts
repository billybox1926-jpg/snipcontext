import * as vscode from 'vscode';
import { SnippetsTreeProvider } from '../providers/snippetsTreeProvider';

export function registerRefreshCommand(context: vscode.ExtensionContext, treeProvider: SnippetsTreeProvider) {
  context.subscriptions.push(
    vscode.commands.registerCommand('snipcontext.refresh', async () => {
      try {
        await treeProvider.refresh();
        vscode.window.showInformationMessage('SnipContext snippet list refreshed.');
      } catch (error) {
        vscode.window.showErrorMessage(`Failed to refresh snippets: ${String(error)}`);
      }
    })
  );
}
