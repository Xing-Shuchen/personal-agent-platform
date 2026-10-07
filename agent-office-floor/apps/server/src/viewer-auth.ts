import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';
import type { IncomingMessage } from 'node:http';

const COOKIE = 'pap_office_viewer';

function digest(value: string): Buffer {
  return createHash('sha256').update(value).digest();
}

/** A single in-memory observer session for an explicitly enabled portal launch. */
export class ViewerAuth {
  private readonly secretHash: Buffer;
  private readonly session = randomBytes(32).toString('base64url');
  constructor(secret: string, private readonly secureCookie: boolean) {
    if (secret.length < 24) throw new Error('PAP_OFFICE_VIEWER_SECRET must contain at least 24 characters');
    this.secretHash = digest(secret);
  }

  unlock(candidate: string): boolean {
    return timingSafeEqual(this.secretHash, digest(candidate));
  }

  authorized(request: Pick<IncomingMessage, 'headers'>): boolean {
    const cookie = request.headers.cookie;
    if (!cookie) return false;
    const value = cookie.split(';').map(part => part.trim()).find(part => part.startsWith(`${COOKIE}=`))?.slice(COOKIE.length + 1);
    if (!value || !/^[A-Za-z0-9_-]{43}$/.test(value)) return false;
    return timingSafeEqual(Buffer.from(value), Buffer.from(this.session));
  }

  setCookie(): string {
    return `${COOKIE}=${this.session}; Path=/; HttpOnly${this.secureCookie ? '; Secure; SameSite=None' : '; SameSite=Lax'}`;
  }
}

export const loginPage = `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>专员办公室 · 访问验证</title><main><h1>专员办公室</h1><p>请输入本机配置的观察口令。</p><form method="post" action="/api/office/unlock"><label>观察口令 <input name="secret" type="password" autocomplete="current-password" required autofocus></label><button type="submit">进入办公室</button></form></main></html>`;
