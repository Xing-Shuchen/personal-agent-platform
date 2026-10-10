import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import { createServer } from 'node:net';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { test } from 'node:test';
import { ViewerAuth } from '../../apps/server/src/viewer-auth.ts';

test('viewer ticket requires the configured secret and never appears in page HTML', () => {
  const auth = new ViewerAuth('a-long-private-observer-secret', true);
  assert.equal(auth.unlock('wrong'), false);
  assert.equal(auth.unlock('a-long-private-observer-secret'), true);
  const cookie = auth.setCookie();
  assert.match(cookie, /HttpOnly; Secure/);
  assert.equal(auth.authorized({ headers: { cookie } }), true);
  assert.equal(auth.authorized({ headers: { cookie: 'pap_office_viewer=wrong' } }), false);
  assert.equal(auth.authorized({ headers: { cookie: `pap_office_viewer=${'é'.repeat(43)}` } }), false);
  assert.throws(() => new ViewerAuth('short', false), /24 characters/);
});

async function freePort(): Promise<number> {
  const server = createServer();
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('no test port');
  await new Promise<void>(resolve => server.close(() => resolve()));
  return address.port;
}

test('portal mode protects state, identities, tasks, progress, SSE and assets', { timeout: 10000 }, async () => {
  const port = await freePort();
  const base = `http://127.0.0.1:${port}`;
  const directory = await mkdtemp(join(tmpdir(), 'pap-office-viewer-'));
  const rejected = spawnSync(process.execPath, ['--import', 'tsx', 'apps/server/src/index.ts'], {
    cwd: resolve(import.meta.dirname, '../..'), encoding: 'utf8', timeout: 5000,
    env: { ...process.env, PORT: String(port), PUBLIC_URL: base,
      PAP_OFFICE_PORTAL_MODE: '1', PAP_OFFICE_VIEWER_SECRET: 'a-long-private-observer-secret',
      PAP_OFFICE_EMBED_ORIGIN: 'http://control.example', PAP_OFFICE_CONFIG: join(directory, 'absent.json'),
      OPENCLAW_GATEWAY_TOKEN: '' }
  });
  assert.notEqual(rejected.status, 0);
  assert.match(rejected.stderr, /HTTPS or loopback HTTP origin/);
  const child = spawn(process.execPath, ['--import', 'tsx', 'apps/server/src/index.ts'], {
    cwd: resolve(import.meta.dirname, '../..'),
    env: { ...process.env, PORT: String(port), PUBLIC_URL: base,
      PAP_OFFICE_PORTAL_MODE: '1', PAP_OFFICE_VIEWER_SECRET: 'a-long-private-observer-secret',
      PAP_OFFICE_EMBED_ORIGIN: base,
      PAP_OFFICE_CONFIG: join(directory, 'absent.json'), OPENCLAW_GATEWAY_TOKEN: '' },
    stdio: 'ignore'
  });
  try {
    let ready = false;
    for (let i = 0; i < 50; i++) {
      try { ready = (await fetch(`${base}/healthz`)).ok; if (ready) break; } catch { /* Starting. */ }
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    assert.equal(ready, true, 'portal-mode server started');
    const page = await fetch(base);
    assert.equal(page.status, 200);
    assert.match(await page.text(), /观察口令/);
    assert.equal(page.headers.get('referrer-policy'), 'same-origin');
    assert.ok((page.headers.get('content-security-policy') ?? '').includes(`frame-ancestors 'self' ${base}`));
    assert.match(page.headers.get('content-security-policy') ?? '', /form-action 'self'/);
    for (const path of ['/api/floor/state', '/api/floor/identities', '/api/floor/coverage', '/api/pap/tasks',
      '/api/floor/progress?id=anything', '/api/floor/events', '/index.html']) {
      assert.equal((await fetch(`${base}${path}`)).status, 401, path);
    }
    const wrongOrigin = await fetch(`${base}/api/office/unlock`, { method: 'POST',
      headers: { Origin: 'http://untrusted.invalid', 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'secret=a-long-private-observer-secret', redirect: 'manual' });
    assert.equal(wrongOrigin.status, 403);
    const unforwardedNull = await fetch(`${base}/api/office/unlock`, { method: 'POST',
      headers: { Origin: 'null', 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'secret=a-long-private-observer-secret', redirect: 'manual' });
    assert.equal(unforwardedNull.status, 403);
    const wrongForwardedHost = await fetch(`${base}/api/office/unlock`, { method: 'POST',
      headers: { Origin: 'null', 'Content-Type': 'application/x-www-form-urlencoded',
        'X-Forwarded-Host': 'untrusted.invalid', 'X-Forwarded-Proto': 'http', 'X-Forwarded-For': '127.0.0.1' },
      body: 'secret=a-long-private-observer-secret', redirect: 'manual' });
    assert.equal(wrongForwardedHost.status, 403);
    const wrongSecret = await fetch(`${base}/api/office/unlock`, { method: 'POST',
      headers: { Origin: base, 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'secret=wrong', redirect: 'manual' });
    assert.equal(wrongSecret.status, 401);
    assert.equal(wrongSecret.headers.get('referrer-policy'), 'same-origin');
    const unlocked = await fetch(`${base}/api/office/unlock`, { method: 'POST',
      headers: { Origin: base, 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'secret=a-long-private-observer-secret', redirect: 'manual' });
    assert.equal(unlocked.status, 303);
    const proxyForm = await fetch(`${base}/api/office/unlock`, { method: 'POST',
      headers: { Origin: 'null', 'Content-Type': 'application/x-www-form-urlencoded',
        'X-Forwarded-Host': new URL(base).host, 'X-Forwarded-Proto': 'http', 'X-Forwarded-For': '127.0.0.1' },
      body: 'secret=a-long-private-observer-secret', redirect: 'manual' });
    assert.equal(proxyForm.status, 303);
    const cookie = unlocked.headers.get('set-cookie');
    if (!cookie?.includes('HttpOnly')) throw new Error('missing HttpOnly viewer cookie');
    assert.equal((await fetch(`${base}/api/floor/state`, { headers: { Cookie: cookie } })).status, 200);
    const coverage = await fetch(`${base}/api/floor/coverage`, { headers: { Cookie: cookie } });
    assert.deepEqual(await coverage.json(), { target: 0, leased: 0, queuedReads: 0, syncing: false, unsupported: false });
    assert.equal((await fetch(`${base}/api/floor/state`, { headers: { Cookie: cookie, 'X-Forwarded-For': '192.0.2.10' } })).status, 200);
    const stream = await fetch(`${base}/api/floor/events`, { headers: { Cookie: cookie } });
    assert.equal(stream.status, 200);
    assert.equal(stream.headers.get('content-type'), 'text/event-stream; charset=utf-8');
    await stream.body?.cancel();
  } finally {
    child.kill();
    await rm(directory, { recursive: true, force: true });
  }
});
