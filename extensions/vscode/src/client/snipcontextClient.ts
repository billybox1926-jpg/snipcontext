import { spawn } from 'child_process';

export interface Snippet {
  id: string;
  title: string;
  content: string;
  language?: string;
  tags?: string[];
}

export class SnipContextClient {
  constructor(private cliPath: string) {}

  public updateCliPath(cliPath: string) {
    this.cliPath = cliPath;
  }

  private runCliCommand(args: string[], input?: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const childProc = spawn(this.cliPath, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
      });

      if (input) {
        childProc.stdin.write(input, 'utf8');
        childProc.stdin.end();
      }

      const stdoutChunks: Buffer[] = [];
      const stderrChunks: Buffer[] = [];

      childProc.stdout.on('data', (chunk: Buffer) => stdoutChunks.push(Buffer.from(chunk)));
      childProc.stderr.on('data', (chunk: Buffer) => stderrChunks.push(Buffer.from(chunk)));

      childProc.on('error', (error: Error) => reject(error));
      childProc.on('close', (code: number | null) => {
        const stdout = Buffer.concat(stdoutChunks).toString('utf8').trim();
        const stderr = Buffer.concat(stderrChunks).toString('utf8').trim();

        if (code !== 0) {
          reject(new Error(stderr || `Command failed with exit code ${code}`));
          return;
        }

        resolve(stdout);
      });
    });
  }

  public async searchSnippets(query: string): Promise<Snippet[]> {
    const output = await this.runCliCommand(['search', '--json', query]);
    try {
      return JSON.parse(output) as Snippet[];
    } catch (error) {
      throw new Error(`Unable to parse search results: ${String(error)}`);
    }
  }

  public async saveSnippet(content: string, title: string, tags: string[], language?: string): Promise<void> {
    const args = ['add', '--title', title];

    if (tags.length > 0) {
      args.push('--tags', tags.join(','));
    }

    if (language) {
      args.push('--language', language);
    }

    await this.runCliCommand(args, content);
  }
}
