import * as vscode from 'vscode';
import { SnipContextClient } from './client/snipcontextClient';
import { SnippetsTreeProvider } from './providers/snippetsTreeProvider';
import { registerSearchCommand } from './commands/search';
import { registerInsertCommand } from './commands/insert';
import { registerSaveSelectionCommand } from './commands/saveSelection';
import { registerRefreshCommand } from './commands/refresh';

export function activate(context: vscode.ExtensionContext) {
  const config = vscode.workspace.getConfiguration('snipcontext');
  const cliPath = config.get<string>('cliPath', 'snipcontext');
  const client = new SnipContextClient(cliPath);
  const snippetsTreeProvider = new SnippetsTreeProvider(client);

  context.subscriptions.push(
    vscode.window.registerTreeDataProvider('snipcontextSnippets', snippetsTreeProvider)
  );

  registerSearchCommand(context, client, snippetsTreeProvider);
  registerInsertCommand(context);
  registerSaveSelectionCommand(context, client, snippetsTreeProvider);
  registerRefreshCommand(context, snippetsTreeProvider);

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration('snipcontext.cliPath')) {
        const updatedPath = vscode.workspace.getConfiguration('snipcontext').get<string>('cliPath', 'snipcontext');
        client.updateCliPath(updatedPath);
      }
    })
  );
}

export function deactivate(): void {
  // no cleanup required for this extension
}
