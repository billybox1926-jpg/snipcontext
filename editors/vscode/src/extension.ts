import * as vscode from 'vscode';
import { SnippetTreeProvider } from './sidebarProvider';
import { insertSnippet, saveSelection } from './commands';

export function activate(context: vscode.ExtensionContext) {
  console.log('SnipContext extension activated');

  const provider = new SnippetTreeProvider();
  const treeView = vscode.window.createTreeView('snipcontextSidebar', {
    treeDataProvider: provider,
    showCollapseAll: true
  });

  const insertCmd = vscode.commands.registerCommand('snipcontext.insertSnippet', (id: string) => {
    insertSnippet(id);
  });

  const saveCmd = vscode.commands.registerCommand('snipcontext.saveSelection', () => {
    saveSelection();
  });

  const refreshCmd = vscode.commands.registerCommand('snipcontext.refreshSidebar', () => {
    provider.refresh();
  });

  provider.refresh();

  context.subscriptions.push(treeView, insertCmd, saveCmd, refreshCmd);
}

export function deactivate() {}
