import * as vscode from 'vscode';
import { SnipContextClient, Snippet } from '../client/snipcontextClient';

export class SnippetTreeItem extends vscode.TreeItem {
  constructor(public readonly snippet: Snippet) {
    super(snippet.title, vscode.TreeItemCollapsibleState.None);
    this.description = snippet.language;
    this.tooltip = snippet.tags?.join(', ');
    this.command = {
      command: 'snipcontext.insert',
      title: 'Insert Snippet',
      arguments: [snippet],
    };
  }
}

export class SnippetsTreeProvider implements vscode.TreeDataProvider<SnippetTreeItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<SnippetTreeItem | undefined | void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
  private snippets: Snippet[] = [];

  constructor(private client: SnipContextClient) {}

  public async refresh(): Promise<void> {
    await this.reload();
    this._onDidChangeTreeData.fire();
  }

  public async reload(): Promise<void> {
    try {
      this.snippets = await this.client.searchSnippets('');
    } catch (error) {
      vscode.window.showErrorMessage(`SnipContext load failed: ${String(error)}`);
      this.snippets = [];
    }
  }

  public setSnippets(snippets: Snippet[]) {
    this.snippets = snippets;
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: SnippetTreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(): Thenable<SnippetTreeItem[]> {
    return Promise.resolve(this.snippets.map((snippet) => new SnippetTreeItem(snippet)));
  }
}
