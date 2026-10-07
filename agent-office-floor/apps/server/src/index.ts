import { createServer } from 'node:http';
import { createReadStream, existsSync, readFileSync } from 'node:fs';
import { extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { FloorStore, GatewayObserver } from '@pap/openclaw-adapter';
import type { ObserverConfig } from '@pap/openclaw-adapter';
import { createOfficeDeviceAuth } from './device-auth.ts';
import { contentPolicy, staticFileWithin } from './http-policy.ts';
import { ViewerPresence } from './viewer-presence.ts';
import { readPapTasks } from './pap-tasks.ts';
import { selectedIdentityBindings, selectedIdentityRoster, type OfficeIdentity } from './identity-bindings.ts';
import { SseBatcher } from './sse-batcher.ts';
import { ViewerAuth, loginPage } from './viewer-auth.ts';
import { BrowserProjection } from './browser-projection.ts';

const store = new FloorStore();
const browserProjection = new BrowserProjection();
let observer: GatewayObserver | null = null;
let identityRoster: OfficeIdentity[] = [];
const defaultConfig = fileURLToPath(new URL('../../../../var/office-floor/config.json', import.meta.url));
const configPath = process.env.PAP_OFFICE_CONFIG ?? defaultConfig;
if (existsSync(configPath)) {
  const parsed: unknown = JSON.parse(readFileSync(configPath, 'utf8'));
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('invalid office config');
  const value = parsed as Record<string, unknown>;
  if (typeof value.gatewayId !== 'string' || typeof value.gatewayUrl !== 'string' ||
      !Array.isArray(value.selectedAgentIds) || !value.selectedAgentIds.every(x => typeof x === 'string')) throw new Error('invalid office config');
  const bindings = selectedIdentityBindings(value.selectedAgentIds, value.bindings);
  identityRoster = selectedIdentityRoster(value.selectedAgentIds, bindings, value.feishuAgentIds);
  const config: ObserverConfig = { gatewayId: value.gatewayId, gatewayUrl: value.gatewayUrl,
    selectedAgentIds: value.selectedAgentIds, token: process.env.OPENCLAW_GATEWAY_TOKEN,
    bindings,
    deviceAuth: value.selectedAgentIds.length ? createOfficeDeviceAuth(fileURLToPath(new URL('../../../../var/office-floor/', import.meta.url)), value.gatewayId, value.gatewayUrl) : undefined };
  observer = new GatewayObserver(config, store);
} else {
  store.setConnection({ mode: 'none', state: 'degraded', lastConfirmedAtMs: null, reason: '尚未配置要展示的专员' });
}

const port = Number(process.env.PORT ?? 4174);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('invalid PORT');
const portalMode = process.env.PAP_OFFICE_PORTAL_MODE === '1';
if (portalMode && !process.env.PUBLIC_URL) throw new Error('portal mode requires token-free PUBLIC_URL');
const portalUrl = portalMode ? new URL(process.env.PUBLIC_URL!) : null;
if (portalUrl && portalUrl.protocol !== 'https:' &&
    !(portalUrl.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(portalUrl.hostname))) {
  throw new Error('portal PUBLIC_URL must use HTTPS or local HTTP');
}
if (portalUrl && (portalUrl.username || portalUrl.password || portalUrl.search || portalUrl.hash)) {
  throw new Error('portal PUBLIC_URL must not contain credentials, query or fragment');
}
const viewerAuth = portalMode ? new ViewerAuth(process.env.PAP_OFFICE_VIEWER_SECRET ?? '', portalUrl!.protocol === 'https:') : null;
const embedOrigin = process.env.PAP_OFFICE_EMBED_ORIGIN;
const embedUrl = embedOrigin ? new URL(embedOrigin) : null;
if (embedUrl && (!portalMode || embedUrl.origin !== embedOrigin ||
    !(embedUrl.protocol === 'https:' || (embedUrl.protocol === 'http:' &&
      ['localhost', '127.0.0.1', '[::1]'].includes(embedUrl.hostname))))) {
  throw new Error('PAP_OFFICE_EMBED_ORIGIN must be an HTTPS or loopback HTTP origin in portal mode');
}
const csp = embedOrigin ? contentPolicy.replace("frame-ancestors 'self'", `frame-ancestors 'self' ${embedOrigin}`) : contentPolicy;
observer?.start();
const root = fileURLToPath(new URL('../../web/dist/', import.meta.url));
const types: Record<string, string> = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml', '.json': 'application/json' };
const viewers = new ViewerPresence(visible => observer?.setVisibleViewer(visible));
const viewerSweep = setInterval(() => viewers.expire(), 15000);
viewerSweep.unref();

const server = createServer((req, res) => {
  const remote = req.socket.remoteAddress;
  const local = remote === '127.0.0.1' || remote === '::1' || remote === '::ffff:127.0.0.1';
  const host = req.headers.host ?? '';
  const localHost = /^(127\.0\.0\.1|localhost|\[::1\]):\d+$/.test(host);
  // A portal reverse proxy is deliberately refused until visitor identity and origin are validated.
  if (!local || !localHost || (!portalMode && (req.headers.forwarded || req.headers['x-forwarded-host'] || req.headers['x-forwarded-for']))) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' }).end('访问被拒绝');
    return;
  }
  const headers = { 'Cache-Control': 'no-store', 'Content-Security-Policy': csp, 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer' };
  // Chromium sends Origin: null for a form POST from a no-referrer document.
  // The login form needs its same-origin Origin header for the unlock check.
  const loginHeaders = { ...headers, 'Referrer-Policy': 'same-origin' };
  const url = new URL(req.url ?? '/', `http://${host}`);
  if (url.pathname === '/healthz' && req.method === 'GET') {
    res.writeHead(200, { ...headers, 'Content-Type': 'application/json' }).end('{"ok":true}');
    return;
  }
  if (url.pathname === '/api/office/unlock' && req.method === 'POST' && viewerAuth) {
    // The pinned OpenClaw portal rewrites Host to localhost, adds forwarded
    // origin headers, and forces Referrer-Policy: no-referrer. Chrome can then
    // submit the same-origin login form with Origin: null.
    const portalFormOrigin = req.headers.origin === 'null' &&
      req.headers['x-forwarded-host'] === portalUrl!.host &&
      req.headers['x-forwarded-proto'] === portalUrl!.protocol.slice(0, -1) &&
      typeof req.headers['x-forwarded-for'] === 'string' && req.headers['x-forwarded-for'].length > 0;
    if (!(req.headers.origin === portalUrl!.origin || portalFormOrigin) ||
        req.headers['content-type'] !== 'application/x-www-form-urlencoded') {
      res.writeHead(403, headers).end(); return;
    }
    let body = '', tooLarge = false;
    req.on('data', chunk => { body += String(chunk); if (body.length > 1024) tooLarge = true; });
    req.on('end', () => {
      if (tooLarge) { res.writeHead(413, headers).end(); return; }
      const values = new URLSearchParams(body).getAll('secret');
      if (values.length !== 1 || !viewerAuth.unlock(values[0])) {
        res.writeHead(401, { ...loginHeaders, 'Content-Type': 'text/html; charset=utf-8' }).end(loginPage);
        return;
      }
      res.writeHead(303, { ...headers, 'Set-Cookie': viewerAuth.setCookie(), Location: '/' }).end();
    });
    return;
  }
  if (viewerAuth && !viewerAuth.authorized(req)) {
    if (url.pathname === '/' && req.method === 'GET')
      res.writeHead(200, { ...loginHeaders, 'Content-Type': 'text/html; charset=utf-8' }).end(loginPage);
    else res.writeHead(401, headers).end();
    return;
  }
  if (url.pathname === '/api/floor/view' && req.method === 'POST') {
    if (req.headers.origin !== (portalUrl?.origin ?? `http://${host}`) || req.headers['content-type'] !== 'application/json') {
      res.writeHead(403, headers).end(); return;
    }
    let body = '';
    req.on('data', chunk => { body += String(chunk); if (body.length > 256) req.destroy(); });
    req.on('end', () => {
      try {
        const value: unknown = JSON.parse(body);
        if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('invalid view');
        const hint = value as Record<string, unknown>;
        if (typeof hint.id !== 'string' || !/^[0-9a-f-]{36}$/.test(hint.id) || typeof hint.visible !== 'boolean') throw new Error('invalid view');
        viewers.report(hint.id, hint.visible);
        res.writeHead(204, headers).end();
      } catch { res.writeHead(400, headers).end(); }
    });
    return;
  }
  if (req.method !== 'GET') { res.writeHead(405, headers).end(); return; }
  if (url.pathname === '/api/floor/state') {
    res.writeHead(200, { ...headers, 'Content-Type': 'application/json' }).end(JSON.stringify(browserProjection.state(store.snapshot())));
    return;
  }
  if (url.pathname === '/api/floor/identities') {
    res.writeHead(200, { ...headers, 'Content-Type': 'application/json' }).end(JSON.stringify(identityRoster));
    return;
  }
  if (url.pathname === '/api/floor/coverage') {
    res.writeHead(200, { ...headers, 'Content-Type': 'application/json' }).end(JSON.stringify(
      observer?.subscriptionCoverage() ?? { target: 0, leased: 0, queuedReads: 0, syncing: false, unsupported: false }));
    return;
  }
  if (url.pathname === '/api/pap/tasks') {
    void readPapTasks().then(json => { if (!res.writableEnded) res.writeHead(200,
      { ...headers, 'Content-Type': 'application/json' }).end(json); })
      .catch(() => { if (!res.writableEnded) res.writeHead(503, headers).end(); });
    return;
  }
  if (url.pathname === '/api/floor/progress') {
    const id = url.searchParams.get('id');
    if (!id || id.length > 128 || !store.snapshot().agents[id] || !observer) {
      res.writeHead(404, headers).end(); return;
    }
    void observer.refreshProgress(id).then(ok => {
      if (!res.writableEnded) res.writeHead(ok ? 204 : 503, headers).end();
    }).catch(() => { if (!res.writableEnded) res.writeHead(503, headers).end(); });
    return;
  }
  if (url.pathname === '/api/floor/events') {
    res.writeHead(200, { ...headers, 'Content-Type': 'text/event-stream; charset=utf-8', 'Connection': 'keep-alive' });
    const batcher = new SseBatcher(update => res.write(`event: floor\ndata: ${JSON.stringify(update)}\n\n`));
    const off = store.observe(update => batcher.push(browserProjection.update(update)));
    const heartbeat = setInterval(() => res.write('event: heartbeat\ndata: {}\n\n'), 15000);
    res.on('close', () => { clearInterval(heartbeat); off(); batcher.close(); });
    return;
  }
  const pathname = url.pathname === '/' ? '/index.html' : url.pathname;
  const filepath = staticFileWithin(root, pathname);
  if (!filepath) {
    res.writeHead(404, headers).end(); return;
  }
  res.writeHead(200, { ...headers, 'Content-Type': types[extname(filepath)] ?? 'application/octet-stream' });
  createReadStream(filepath).pipe(res);
});
server.listen(port, '127.0.0.1', () => {
  process.stdout.write(`Agent Office Floor listening on http://127.0.0.1:${port}\n`);
});
