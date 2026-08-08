import * as vscode from 'vscode';
import { Snippet } from '../client/snipcontextClient';

export function registerInsertCommand(context: vscode.ExtensionContext) {
  context.subscriptions.push(
    vscode.commands.registerCommand('snipcontext.insert', (snippet: Snippet) => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showErrorMessage('No active editor to insert snippet into.');
        return;
      }

      editor.edit((editBuilder) => {
        editBuilder.insert(editor.selection.active, snippet.content);
      });
    })
  );
}
