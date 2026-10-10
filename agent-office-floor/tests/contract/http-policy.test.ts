import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { staticFileWithin } from '../../apps/server/src/http-policy.ts';

test('static files stay inside the real site root', () => {
  const parent = mkdtempSync(join(tmpdir(), 'pap-office-static-'));
  const root = join(parent, 'dist');
  const sibling = join(parent, 'dist-private');
  try {
    mkdirSync(root);
    mkdirSync(sibling);
    writeFileSync(join(root, 'index.html'), 'office');
    writeFileSync(join(sibling, 'secret.txt'), 'private');
    symlinkSync(join(sibling, 'secret.txt'), join(root, 'linked.txt'));
    assert.equal(staticFileWithin(root, '/index.html'), join(root, 'index.html'));
    assert.equal(staticFileWithin(root, '/%69ndex.html'), join(root, 'index.html'));
    assert.equal(staticFileWithin(root, '/../dist-private/secret.txt'), null);
    assert.equal(staticFileWithin(root, '/linked.txt'), null);
    assert.equal(staticFileWithin(root, '/%00'), null);
    assert.equal(staticFileWithin(root, '/%zz'), null);
  } finally {
    rmSync(parent, { recursive: true, force: true });
  }
});
