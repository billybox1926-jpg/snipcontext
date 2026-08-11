import * as vscode from 'vscode';
import { getSnippet, createSnippet } from './snippetApi';

export async function insertSnippet(id: string) {
  try {
    const snippet = await getSnippet(id);
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showErrorMessage('No active editor');
      return;
    }
    editor.edit(editBuilder => {
      const position = editor.selection.active;
      editBuilder.insert(position, snippet.content);
    });
  } catch (error) {
    vscode.window.showErrorMessage(`Failed to insert snippet: ${error}`);
  }
}

export async function saveSelection() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showErrorMessage('No active editor');
    return;
  }
  const selection = editor.selection;
  const text = editor.document.getText(selection);
  if (!text.trim()) {
    vscode.window.showInformationMessage('No text selected');
    return;
  }

  const title = await vscode.window.showInputBox({ prompt: 'Enter snippet title', value: text.slice(0, 20) });
  if (!title) {
    return;
  }

  const language = editor.document.languageId;

  try {
    await createSnippet({ title, content: text, language, tags: [] });
    vscode.window.showInformationMessage(`Snippet "${title}" saved`);
    vscode.commands.executeCommand('snipcontext.refreshSidebar');
  } catch (error) {
    vscode.window.showErrorMessage(`Failed to save snippet: ${error}`);
  }
}
