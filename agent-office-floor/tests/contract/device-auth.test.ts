import assert from 'node:assert/strict';
import { createPublicKey, verify } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { createOfficeDeviceAuth } from '../../apps/server/src/device-auth.ts';

test('device identity and approved token persist privately for one Gateway', () => {
  const directory = mkdtempSync(join(tmpdir(), 'pap-office-auth-'));
  try {
    const first = createOfficeDeviceAuth(directory, 'gateway-a', 'ws://127.0.0.1:18789');
    assert.equal(first.hasStoredToken, false);
    assert.equal(statSync(join(directory, 'device-identity.json')).mode & 0o077, 0);
    assert.equal(statSync(directory).mode & 0o077, 0);
    const payload = 'challenge-bound payload';
    const signature = first.hostDeps.signDevicePayload!(first.deviceIdentity.privateKeyPem, payload);
    assert.equal(verify(null, Buffer.from(payload), createPublicKey(first.deviceIdentity.publicKeyPem), Buffer.from(signature, 'base64url')), true);
    const raw = first.hostDeps.publicKeyRawBase64UrlFromPem!(first.deviceIdentity.publicKeyPem);
    assert.equal(Buffer.from(raw, 'base64url').length, 32);
    first.hostDeps.storeDeviceAuthToken!({ deviceId: first.deviceIdentity.deviceId, role: 'operator', token: 'issued-token', scopes: ['operator.read'] });
    assert.equal(statSync(join(directory, 'device-token.json')).mode & 0o077, 0);
    const second = createOfficeDeviceAuth(directory, 'gateway-a', 'ws://127.0.0.1:18789');
    assert.equal(second.deviceIdentity.deviceId, first.deviceIdentity.deviceId);
    assert.equal(second.hasStoredToken, true);
    assert.deepEqual(second.hostDeps.loadDeviceAuthToken!({ deviceId: second.deviceIdentity.deviceId, role: 'operator' }),
      { token: 'issued-token', scopes: ['operator.read'] });
    const other = createOfficeDeviceAuth(directory, 'gateway-b', 'ws://127.0.0.1:18790');
    assert.equal(other.hasStoredToken, false);
    assert.equal(other.hostDeps.loadDeviceAuthToken!({ deviceId: other.deviceIdentity.deviceId, role: 'operator' }), null);
    second.hostDeps.clearDeviceAuthToken!({ deviceId: second.deviceIdentity.deviceId, role: 'operator' });
    assert.equal(createOfficeDeviceAuth(directory, 'gateway-a', 'ws://127.0.0.1:18789').hasStoredToken, false);
  } finally { rmSync(directory, { recursive: true, force: true }); }
});

test('invalid stored identity fails closed without replacing the keypair', () => {
  const directory = mkdtempSync(join(tmpdir(), 'pap-office-auth-'));
  try {
    createOfficeDeviceAuth(directory, 'gateway-a', 'ws://127.0.0.1:18789');
    const path = join(directory, 'device-identity.json');
    const saved = JSON.parse(readFileSync(path, 'utf8')) as Record<string, unknown>;
    saved.deviceId = 'wrong';
    writeFileSync(path, JSON.stringify(saved));
    assert.throws(() => createOfficeDeviceAuth(directory, 'gateway-a', 'ws://127.0.0.1:18789'), /key mismatch/);
  } finally { rmSync(directory, { recursive: true, force: true }); }
});

test('device tokens with broader scopes are neither saved nor reused', () => {
  const directory = mkdtempSync(join(tmpdir(), 'pap-office-auth-'));
  try {
    const auth = createOfficeDeviceAuth(directory, 'gateway-a', 'ws://127.0.0.1:18789');
    const input = { deviceId: auth.deviceIdentity.deviceId, role: 'operator', token: 'issued-token',
      scopes: ['operator.read', 'operator.admin'] };
    assert.throws(() => auth.hostDeps.storeDeviceAuthToken!(input), /operator.read token only/);
    assert.equal(createOfficeDeviceAuth(directory, 'gateway-a', 'ws://127.0.0.1:18789').hasStoredToken, false);
    const path = join(directory, 'device-token.json');
    writeFileSync(path, JSON.stringify({ version: 1, gatewayId: 'gateway-a', gatewayUrl: 'ws://127.0.0.1:18789',
      ...input }), { mode: 0o600 });
    assert.throws(() => createOfficeDeviceAuth(directory, 'gateway-a', 'ws://127.0.0.1:18789'), /invalid office device token/);
  } finally { rmSync(directory, { recursive: true, force: true }); }
});
