export const contentPolicy = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'";

import { realpathSync, statSync } from 'node:fs';
import { isAbsolute, relative, resolve, sep } from 'node:path';

export function staticFileWithin(root: string, pathname: string): string | null {
  try {
    const directory = realpathSync(root);
    const decoded = decodeURIComponent(pathname);
    const candidate = realpathSync(resolve(directory, `.${decoded}`));
    const offset = relative(directory, candidate);
    if (!offset || offset === '..' || offset.startsWith(`..${sep}`) || isAbsolute(offset)) return null;
    return statSync(candidate).isFile() ? candidate : null;
  } catch {
    return null;
  }
}
