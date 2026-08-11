import * as vscode from 'vscode';
import { listSnippets, SnippetSummary } from './snippetApi';

export class SnippetTreeItem extends vscode.TreeItem {
  constructor(
    public readonly snippet: SnippetSummary,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState
  ) {
    super(snippet.title, collapsibleState);
    this.tooltip = `${snippet.language || 'no language'}\nTags: ${(snippet.tags || []).join(', ')}`;
    this.description = snippet.language || '';
    this.id = snippet.id;
    this.command = {
      command: 'snipcontext.insertSnippet',
      title: 'Insert Snippet',
      arguments: [snippet.id]
    };
  }
}

export class SnippetTreeProvider implements vscode.TreeDataProvider<SnippetTreeItem> {
  private _onDidChangeTreeData: vscode.EventEmitter<SnippetTreeItem | undefined | void> = new vscode.EventEmitter();
  readonly onDidChangeTreeData: vscode.Event<SnippetTreeItem | undefined | void> = this._onDidChangeTreeData.event;

  private snippets: SnippetSummary[] = [];

  async refresh(): Promise<void> {
    this.snippets = await listSnippets();
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: SnippetTreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: SnippetTreeItem): Thenable<SnippetTreeItem[]> {
    if (!element) {
      return Promise.resolve(
        this.snippets.map(s => new SnippetTreeItem(s, vscode.TreeItemCollapsibleState.None))
      );
    }
    return Promise.resolve([]);
  }
}
