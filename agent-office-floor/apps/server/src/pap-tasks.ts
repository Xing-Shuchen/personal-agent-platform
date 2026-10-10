import { execFile } from 'node:child_process';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const papRoot = fileURLToPath(new URL('../../../../', import.meta.url));
const python = join(papRoot, '.venv/bin/python');
const script = fileURLToPath(new URL('../../../scripts/pap_tasks.py', import.meta.url));
let cache: { at: number; json: string } | null = null;
let pending: Promise<string> | null = null;

/** The Python projector whitelists metadata before it reaches this HTTP layer. */
export function readPapTasks(): Promise<string> {
  if (cache && Date.now() - cache.at < 15000) return Promise.resolve(cache.json);
  if (pending) return pending;
  pending = new Promise<string>((resolve, reject) => {
    execFile(python, [script, '--root', papRoot], { timeout: 5000, maxBuffer: 1024 * 1024 },
      (error, stdout) => error ? reject(error) : resolve(stdout));
  }).then(json => { cache = { at: Date.now(), json }; return json; })
    .finally(() => { pending = null; });
  return pending;
}
