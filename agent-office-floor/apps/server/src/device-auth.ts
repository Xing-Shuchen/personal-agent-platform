import { createHash, createPrivateKey, createPublicKey, generateKeyPairSync, randomUUID, sign } from 'node:crypto';
import { closeSync, fstatSync, fsyncSync, lstatSync, mkdirSync, openSync, readFileSync, renameSync, unlinkSync, writeFileSync, constants } from 'node:fs';
import { join } from 'node:path';
import type { DeviceIdentity, GatewayClientHostDeps } from '@openclaw/gateway-client';

const identityFile = 'device-identity.json';
const tokenFile = 'device-token.json';
const ed25519SpkiPrefix = Buffer.from('302a300506032b6570032100', 'hex');

function readPrivateFile(path: string): string | null {
  let fd: number;
  try { fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW); }
  catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return null;
    throw error;
  }
  try {
    const info = fstatSync(fd);
    if (!info.isFile() || (info.mode & 0o077) !== 0) throw new Error('office device auth file is not private');
    return readFileSync(fd, 'utf8');
  } finally { closeSync(fd); }
}

function writeNewPrivateFile(path: string, content: string): void {
  const fd = openSync(path, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o600);
  try { writeFileSync(fd, content); fsyncSync(fd); }
  finally { closeSync(fd); }
}

function replacePrivateFile(path: string, content: string): void {
  const temporary = `${path}.${randomUUID()}.tmp`;
  try { writeNewPrivateFile(temporary, content); renameSync(temporary, path); }
  finally { try { unlinkSync(temporary); } catch (error) { if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error; } }
}

function publicKeyRaw(publicKeyPem: string): Buffer {
  const key = createPublicKey(publicKeyPem);
  if (key.asymmetricKeyType !== 'ed25519') throw new Error('office device key must be Ed25519');
  const der = key.export({ format: 'der', type: 'spki' });
  if (!Buffer.isBuffer(der) || der.length !== ed25519SpkiPrefix.length + 32 ||
      !der.subarray(0, ed25519SpkiPrefix.length).equals(ed25519SpkiPrefix))
    throw new Error('invalid Ed25519 public key');
  return der.subarray(ed25519SpkiPrefix.length);
}

function validateIdentity(value: unknown): DeviceIdentity {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('invalid office device identity');
  const record = value as Record<string, unknown>;
  if (record.version !== 1 || typeof record.deviceId !== 'string' ||
      typeof record.privateKeyPem !== 'string' || typeof record.publicKeyPem !== 'string')
    throw new Error('invalid office device identity');
  const privateKey = createPrivateKey(record.privateKeyPem);
  if (privateKey.asymmetricKeyType !== 'ed25519' ||
      createPublicKey(privateKey).export({ format: 'pem', type: 'spki' }) !== record.publicKeyPem ||
      createHash('sha256').update(publicKeyRaw(record.publicKeyPem)).digest('hex') !== record.deviceId)
    throw new Error('office device identity key mismatch');
  return { deviceId: record.deviceId, privateKeyPem: record.privateKeyPem, publicKeyPem: record.publicKeyPem };
}

function loadOrCreateIdentity(directory: string): DeviceIdentity {
  const path = join(directory, identityFile);
  const existing = readPrivateFile(path);
  if (existing !== null) return validateIdentity(JSON.parse(existing));
  const keys = generateKeyPairSync('ed25519');
  const publicKeyPem = keys.publicKey.export({ format: 'pem', type: 'spki' }).toString();
  const privateKeyPem = keys.privateKey.export({ format: 'pem', type: 'pkcs8' }).toString();
  const deviceId = createHash('sha256').update(publicKeyRaw(publicKeyPem)).digest('hex');
  try { writeNewPrivateFile(path, JSON.stringify({ version: 1, deviceId, privateKeyPem, publicKeyPem })); }
  catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'EEXIST') throw error;
    const raced = readPrivateFile(path);
    if (raced === null) throw error;
    return validateIdentity(JSON.parse(raced));
  }
  return { deviceId, privateKeyPem, publicKeyPem };
}

type StoredToken = { version: 1; gatewayId: string; gatewayUrl: string; deviceId: string; role: string; token: string; scopes: string[] };
function readOnlyScopes(scopes: unknown): scopes is ['operator.read'] {
  return Array.isArray(scopes) && scopes.length === 1 && scopes[0] === 'operator.read';
}
function readToken(directory: string): StoredToken | null {
  const contents = readPrivateFile(join(directory, tokenFile));
  if (contents === null) return null;
  const value: unknown = JSON.parse(contents);
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('invalid office device token');
  const record = value as Record<string, unknown>;
  if (record.version !== 1 || !['gatewayId','gatewayUrl','deviceId','role','token'].every(key =>
    typeof record[key] === 'string' && (record[key] as string).length > 0) ||
    !readOnlyScopes(record.scopes))
    throw new Error('invalid office device token');
  return record as StoredToken;
}

/** Local host-owned credentials for the pinned GatewayClient; no OpenClaw profile is read. */
export function createOfficeDeviceAuth(directory: string, gatewayId: string, gatewayUrl: string): {
  deviceIdentity: DeviceIdentity; hostDeps: GatewayClientHostDeps; hasStoredToken: boolean;
} {
  mkdirSync(directory, { recursive: true, mode: 0o700 });
  const info = lstatSync(directory);
  if (!info.isDirectory() || (info.mode & 0o077) !== 0) throw new Error('office device auth directory is not private');
  const deviceIdentity = loadOrCreateIdentity(directory);
  const matches = (record: StoredToken | null, deviceId: string, role: string) =>
    record?.gatewayId === gatewayId && record.gatewayUrl === gatewayUrl &&
    record.deviceId === deviceId && record.role === role;
  const hostDeps: GatewayClientHostDeps = {
    signDevicePayload: (privateKeyPem, payload) => sign(null, Buffer.from(payload, 'utf8'), privateKeyPem).toString('base64url'),
    publicKeyRawBase64UrlFromPem: publicKeyPem => publicKeyRaw(publicKeyPem).toString('base64url'),
    loadDeviceAuthToken: ({ deviceId, role }) => {
      const record = readToken(directory);
      return matches(record, deviceId, role) ? { token: record!.token, scopes: record!.scopes } : null;
    },
    storeDeviceAuthToken: ({ deviceId, role, token, scopes }) => {
      if (deviceId !== deviceIdentity.deviceId || role !== 'operator') return;
      if (typeof token !== 'string' || !token || !readOnlyScopes(scopes))
        throw new Error('office auth requires operator.read token only');
      replacePrivateFile(join(directory, tokenFile), JSON.stringify({ version: 1, gatewayId, gatewayUrl,
        deviceId, role, token, scopes } satisfies StoredToken));
    },
    clearDeviceAuthToken: ({ deviceId, role }) => {
      if (!matches(readToken(directory), deviceId, role)) return;
      try { unlinkSync(join(directory, tokenFile)); }
      catch (error) { if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error; }
    }
  };
  return { deviceIdentity, hostDeps, hasStoredToken: matches(readToken(directory), deviceIdentity.deviceId, 'operator') };
}
