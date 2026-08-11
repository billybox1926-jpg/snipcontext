import axios from 'axios';

const API_BASE = 'http://localhost:8000';

export interface SnippetSummary {
  id: string;
  title: string;
  language?: string;
  tags: string[];
}

export interface Snippet extends SnippetSummary {
  content: string;
}

export async function listSnippets(): Promise<SnippetSummary[]> {
  const resp = await axios.get(`${API_BASE}/snippets`);
  return resp.data.items ?? [];
}

export async function createSnippet(data: {
  title: string;
  content: string;
  language?: string;
  tags?: string[];
}) {
  await axios.post(`${API_BASE}/snippets`, {
    title: data.title,
    content: data.content,
    description: '',
    language: data.language || '',
    tags: data.tags || [],
  });
}

export async function getSnippet(id: string): Promise<Snippet> {
  const resp = await axios.get(`${API_BASE}/snippets/${id}`);
  return {
    id: resp.data.id,
    title: resp.data.title,
    content: resp.data.content,
    language: resp.data.language,
    tags: resp.data.tags,
  };
}
