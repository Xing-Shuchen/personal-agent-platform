import { spawn } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import { constants } from "node:fs";
import { chmod, copyFile, lstat, mkdir, readdir, realpath, rename, stat, unlink, writeFile } from "node:fs/promises";
import { delimiter, dirname, isAbsolute, resolve } from "node:path";

const MAX_IMAGE_BYTES = 20 * 1024 * 1024;
const MAX_EPUB_BYTES = 30 * 1024 * 1024;
const MAX_BATCH_BYTES = 100 * 1024 * 1024;
const EVIDENCE_TTL_MS = 60 * 60 * 1000;
const INBOUND_SESSIONS = Symbol.for("pap.librarian.inboundSessions");

async function pruneEvidenceMedia(directory) {
  for (const name of await readdir(directory)) {
    if (!/^evidence-[0-9a-f-]{36}\.jpg$/.test(name)) continue;
    const path = resolve(directory, name);
    const info = await stat(path).catch(() => null);
    if (info?.isFile() && Date.now() - info.mtimeMs > EVIDENCE_TTL_MS) {
      await unlink(path).catch(() => {});
    }
  }
}

async function pruneSourceBookMedia(directory) {
  for (const name of await readdir(directory)) {
    if (!/^sourcebook-\d{13}-[0-9a-f-]{36}\.epub$/.test(name)) continue;
    const path = resolve(directory, name);
    const info = await stat(path).catch(() => null);
    if (info?.isFile() && Date.now() - info.mtimeMs > EVIDENCE_TTL_MS) {
      await unlink(path).catch(() => {});
    }
  }
}

// OpenClaw can load hook and tool registrations through separate plugin instances.
// Keep the short-lived inbound binding in the process realm shared by both.
function inboundSessions() {
  return globalThis[INBOUND_SESSIONS] ??= new Map();
}

const configuredOwnerIds = (config) =>
  [...new Set((config.ownerMappings ?? []).map((entry) => entry.ownerId))];

function ownerFor(config, event, ctx) {
  if (configuredOwnerIds(config).length !== 1) return null;
  if (!ctx?.channelId || !ctx?.accountId || !event?.senderId) return null;
  const matches = (config.ownerMappings ?? []).filter((entry) =>
    entry.channelId === ctx.channelId && entry.accountId === ctx.accountId &&
    entry.senderId === event.senderId);
  return matches.length === 1 ? matches[0].ownerId : null;
}

export async function writeIntakeStatus(config, event, ctx, state, error = null,
                                        captureIds = []) {
  const ownerId = ownerFor(config, event, ctx);
  if (!ownerId || !event?.messageId || !config.stateRoot ||
      !["accepted", "failed"].includes(state)) return;
  const directory = resolve(config.stateRoot, "intake-status");
  await mkdir(directory, { recursive: true, mode: 0o700 });
  const directoryInfo = await lstat(directory);
  if (!directoryInfo.isDirectory() || directoryInfo.isSymbolicLink())
    throw new Error("intake status directory is unsafe");
  await chmod(directory, 0o700);
  const identity = [ownerId, ctx.channelId, ctx.accountId, event.messageId];
  const key = createHash("sha256").update(JSON.stringify(identity)).digest("hex");
  const target = resolve(directory, `${key}.json`);
  const temporary = resolve(directory, `${key}.${randomUUID()}.tmp`);
  const code = typeof error?.code === "string" && /^[A-Z_]+$/.test(error.code)
    ? error.code : "HOOK_FAILED";
  const stage = typeof error?.stage === "string" && /^gateway\.[a-z_]+$/.test(error.stage)
    ? error.stage : "gateway.intake";
  const record = { owner_id: ownerId, channel_id: ctx.channelId,
    account_id: ctx.accountId, message_id: event.messageId,
    state, code: state === "failed" ? code : null,
    stage: state === "failed" ? stage : null,
    retryable: state === "failed" ? error?.retryable !== false : null,
    capture_ids: state === "accepted" ? captureIds : [],
    updated_at: new Date().toISOString() };
  try {
    await writeFile(temporary, JSON.stringify(record), { mode: 0o600, flag: "wx" });
    await rename(temporary, target);
  } finally {
    await unlink(temporary).catch(() => {});
  }
}

function bridgeFailure(module, error) {
  const valid = error && typeof error === "object" &&
    typeof error.code === "string" && /^[A-Z_]+$/.test(error.code) &&
    typeof error.stage === "string" && /^gateway\.[a-z_]+$/.test(error.stage) &&
    typeof error.retryable === "boolean" &&
    typeof error.message === "string" && error.message.length > 0 &&
    error.details && typeof error.details === "object" && !Array.isArray(error.details);
  const result = valid ? {
    code: error.code, stage: error.stage, retryable: error.retryable,
    message: error.message, details: error.details,
  } : {
    code: "BRIDGE_FAILED", stage: module.split(".").at(-1), retryable: true,
    message: "The Librarian bridge failed.", details: {},
  };
  const failure = new Error(`${result.message} (${result.code}; stage=${result.stage}; retryable=${result.retryable})`);
  Object.assign(failure, { code: result.code, stage: result.stage,
    retryable: result.retryable, publicMessage: result.message,
    details: result.details, errorResult: result });
  return failure;
}

export async function runPythonBridge(config, module, message) {
  const python = config.python ?? "python3";
  const child = spawn(python, ["-m", module, "--root", config.stateRoot], {
    cwd: config.repoRoot,
    env: { ...process.env, PYTHONPATH: [config.repoRoot, process.env.PYTHONPATH ?? ""].join(delimiter) },
    stdio: ["pipe", "pipe", "pipe"],
  });
  const stdout = [];
  let size = 0;
  let oversized = false;
  child.stdout.on("data", (chunk) => {
    size += chunk.length;
    if (size > 1024 * 1024) {
      oversized = true;
      child.kill();
    }
    else stdout.push(chunk);
  });
  child.stderr.resume(); // Never log private paths or model data from the bridge.
  const completed = new Promise((resolve, reject) => {
    child.once("error", reject);
    child.once("close", (code) => resolve(code));
  });
  child.stdin.on("error", () => {}); // An early bridge exit can close stdin.
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; child.kill(); }, 60_000);
  child.stdin.end(JSON.stringify(message));
  try {
    let code;
    try {
      code = await completed;
    } catch {
      throw bridgeFailure(module);
    }
    if (timedOut || oversized) throw bridgeFailure(module);
    let result;
    try {
      result = JSON.parse(Buffer.concat(stdout).toString("utf8"));
    } catch {
      throw bridgeFailure(module);
    }
    if (!result || typeof result !== "object" || Array.isArray(result)) {
      throw bridgeFailure(module);
    }
    if (code !== 0 || result.error) {
      throw bridgeFailure(module, result.error);
    }
    return result;
  } finally {
    clearTimeout(timer);
  }
}

const runBridge = (config, message) => runPythonBridge(
  config, "agents.librarian.runtime.gateway_bridge", message);
const runSearchBridge = (config, message) => runPythonBridge(
  config, "agents.librarian.runtime.gateway_search", message);
const runSessionBridge = (config, message) => runPythonBridge(
  config, "agents.librarian.runtime.gateway_session", message);
const runEvidenceBridge = (config, message) => runPythonBridge(
  config, "agents.librarian.runtime.gateway_evidence", message);
const runSourceBookBridge = (config, message) => runPythonBridge(
  config, "agents.librarian.runtime.gateway_source_book", message);
const runReviewBridge = (config, message) => runPythonBridge(
  config, "agents.librarian.runtime.gateway_review", message);
const runReviewDecisionBridge = (config, message) => runPythonBridge(
  config, "agents.librarian.runtime.gateway_review_decision", message);
const runReviewFinalizeBridge = (config, message) => runPythonBridge(
  config, "agents.librarian.runtime.gateway_review_finalize", message);

export function workerArgs(config, ownerId) {
  if (!ownerId || configuredOwnerIds(config).length !== 1 ||
      configuredOwnerIds(config)[0] !== ownerId) return null;
  const args = ["-m", "agents.librarian.runtime.worker",
    "--root", config.stateRoot, "--owner", ownerId,
    "--vision-model", config.visionModel ?? "zai/glm-5.3-flash"];
  if (config.vaultRoot) args.push("--vault", config.vaultRoot);
  const digital = config.digitalSources ?? {};
  if (digital.ownerId === ownerId && digital.koodo) args.push("--koodo-source-id", digital.koodo.sourceId,
    "--koodo-books-db", digital.koodo.booksDb, "--koodo-notes-db", digital.koodo.notesDb);
  if (digital.ownerId === ownerId && digital.weread) {
    args.push("--weread-source-id", digital.weread.sourceId,
      "--weread-plugin-data", digital.weread.pluginData);
    for (const bookId of digital.weread.bookIds) args.push("--weread-book-id", bookId);
  }
  return args;
}

function startWorker(config, ownerId, mode = "physical") {
  if (mode === "physical" && config.physicalWorkerEnabled === false) return;
  const args = workerArgs(config, ownerId);
  if (!args) return;
  args.push(mode === "digital" ? "--digital-only" : "--physical-only");
  const child = spawn(config.python ?? "python3", args, {
    cwd: config.repoRoot,
    env: { ...process.env, PYTHONPATH: [config.repoRoot, process.env.PYTHONPATH ?? ""].join(delimiter),
      ...(config.bookscanPython ? { LIBRARIAN_BOOKSCAN_PYTHON: config.bookscanPython } : {}) },
    stdio: "ignore",
    detached: true,
  });
  child.on("error", () => {});
  child.unref();
}

export function librarianSearchTool(config, ctx, bridge = runSearchBridge) {
  if (ctx?.agentId !== "librarian" || !ctx.requesterSenderId) return null;
  const route = ctx.deliveryContext ?? {};
  if ((ctx.messageChannel && route.channel && ctx.messageChannel !== route.channel) ||
      (ctx.agentAccountId && route.accountId && ctx.agentAccountId !== route.accountId)) return null;
  const channelId = ctx.messageChannel ?? route.channel;
  const accountId = ctx.agentAccountId ?? route.accountId;
  const ownerId = ownerFor(config, { senderId: ctx.requesterSenderId },
    { channelId, accountId });
  if (!ownerId) return null;
  return {
    name: "librarian_search",
    label: "Librarian search",
    description: "Search this authenticated sender's reading traces by quoted text, book title, and/or printed page number. For page questions pass book and page. Results can also include newer pending_evidence scan candidates; these are unreviewed and must not be described as stored traces.",
    parameters: { type: "object", properties: {
      query: { type: "string", minLength: 1, maxLength: 256 },
      book: { type: "string", minLength: 1, maxLength: 200 },
      page: { type: "integer", minimum: 1, maximum: 9999 },
      limit: { type: "integer", minimum: 1, maximum: 20 },
    }, anyOf: [{ required: ["query"] }, { required: ["book"] },
      { required: ["page"] }], additionalProperties: false },
    async execute(_id, params) {
      const result = await bridge(config, { owner_id: ownerId,
        query: params.query, book: params.book, page: params.page,
        limit: params.limit ?? 10 });
      return { content: [{ type: "text", text: JSON.stringify(result) }],
        details: result };
    },
  };
}

export function librarianEvidenceTool(config, ctx, bridge = runEvidenceBridge) {
  if (ctx?.agentId !== "librarian" || !ctx.requesterSenderId || !ctx.delivery?.send ||
      !config.deliveryMediaRoot || !isAbsolute(config.deliveryMediaRoot)) return null;
  const route = ctx.deliveryContext ?? {};
  if ((ctx.messageChannel && route.channel && ctx.messageChannel !== route.channel) ||
      (ctx.agentAccountId && route.accountId && ctx.agentAccountId !== route.accountId)) return null;
  const ownerId = ownerFor(config, { senderId: ctx.requesterSenderId },
    { channelId: ctx.messageChannel ?? route.channel,
      accountId: ctx.agentAccountId ?? route.accountId });
  if (!ownerId) return null;
  return {
    name: "librarian_evidence",
    label: "Librarian photo evidence",
    description: "Queue an owner-scoped crop to this conversation. Use trace_id for a stored trace; capture_id plus candidate_id for a pending candidate; or capture_id, pending_run_id and gap_index from the current review for an OCR gap. Candidate indexes can shift after reprocessing; prefer candidate_id. A queue receipt does not prove platform delivery or approve a pending candidate.",
    parameters: { type: "object", properties: {
      trace_id: { type: "string", pattern: "^rt_[A-Za-z0-9_-]+$" },
      capture_id: { type: "string", pattern: "^capture_[A-Za-z0-9_-]+$" },
      candidate_id: { type: "string", pattern: "^candidate_[A-Za-z0-9_-]+$" },
      candidate_index: { type: "integer", minimum: 0 },
      pending_run_id: { type: "string", pattern: "^run_[A-Za-z0-9_-]+$" },
      gap_index: { type: "integer", minimum: 0 },
    }, oneOf: [{ required: ["trace_id"] },
      { required: ["capture_id", "candidate_id"] },
      { required: ["capture_id", "candidate_index"] },
      { required: ["capture_id", "pending_run_id", "gap_index"] }], additionalProperties: false },
    async execute(_id, params) {
      const result = await bridge(config, { owner_id: ownerId,
        ...(params.trace_id ? { trace_id: params.trace_id } :
          { capture_id: params.capture_id,
            ...(params.candidate_id ? { candidate_id: params.candidate_id } :
              params.gap_index !== undefined ?
                { pending_run_id: params.pending_run_id, gap_index: params.gap_index } :
                { candidate_index: params.candidate_index }) }) });
      const path = resolve(result.media_path);
      if (dirname(path) !== resolve(config.stateRoot, "delivery-evidence")) {
        throw new Error("invalid evidence path");
      }
      const deliveryRoot = resolve(config.deliveryMediaRoot);
      const outbound = resolve(deliveryRoot, `evidence-${randomUUID()}.jpg`);
      let queued = false;
      try {
        const info = await stat(path);
        if (!info.isFile() || info.size < 1 || info.size > MAX_IMAGE_BYTES) {
          throw new Error("invalid evidence file");
        }
        await mkdir(deliveryRoot, { recursive: true, mode: 0o700 });
        await chmod(deliveryRoot, 0o700);
        await pruneEvidenceMedia(deliveryRoot);
        await copyFile(path, outbound, constants.COPYFILE_EXCL);
        await chmod(outbound, 0o600);
        await ctx.delivery.send({ text: result.source_status === "pending_review" ?
          `扫描件待审核候选原图局部：${result.capture_id} ${result.candidate_id ?? result.candidate_index}` :
          result.source_status === "pending_ocr_gap" ?
            `扫描件 OCR 缺口原图局部：${result.capture_id} 缺口 ${result.gap_index}` :
            `原图局部证据：${result.trace_id}`,
          mediaUrl: outbound });
        queued = true;
        // send may only queue the payload; the channel can open mediaUrl later.
        setTimeout(() => unlink(outbound).catch(() => {}), EVIDENCE_TTL_MS).unref();
      } finally {
        await unlink(path).catch(() => {});
        if (!queued) await unlink(outbound).catch(() => {});
      }
      return { content: [{ type: "text", text: JSON.stringify({
        trace_id: result.trace_id ?? null, capture_id: result.capture_id,
        candidate_id: result.candidate_id ?? null,
        candidate_index: result.candidate_index ?? null,
        gap_index: result.gap_index ?? null,
        source_status: result.source_status ?? "stored_trace",
        delivery_status: "queued" }) }] };
    },
  };
}

export function librarianSourceBookTool(config, ctx, bridge = runSourceBookBridge) {
  if (ctx?.agentId !== "librarian" || !ctx.requesterSenderId || !ctx.delivery?.send ||
      !config.deliveryMediaRoot || !isAbsolute(config.deliveryMediaRoot)) return null;
  const route = ctx.deliveryContext ?? {};
  if ((ctx.messageChannel && route.channel && ctx.messageChannel !== route.channel) ||
      (ctx.agentAccountId && route.accountId && ctx.agentAccountId !== route.accountId)) return null;
  const ownerId = ownerFor(config, { senderId: ctx.requesterSenderId },
    { channelId: ctx.messageChannel ?? route.channel,
      accountId: ctx.agentAccountId ?? route.accountId });
  if (!ownerId) return null;
  return {
    name: "librarian_source_book",
    label: "Send catalogued Librarian EPUB",
    description: "Queue the exact EPUB used for OCR alignment for a book owned by this sender. Use only when the user asks for the EPUB file. Returns a queue receipt, not proof of client delivery.",
    parameters: { type: "object", properties: {
      book: { type: "string", minLength: 1, maxLength: 200 },
    }, required: ["book"], additionalProperties: false },
    async execute(_id, params) {
      const result = await bridge(config, { owner_id: ownerId, book: params.book });
      const path = resolve(result.media_path);
      const expected = resolve(config.stateRoot, "source-books", `${result.isbn13}.epub`);
      if (!/^\d{13}$/.test(result.isbn13) || path !== expected) {
        throw new Error("invalid source book path");
      }
      const info = await stat(path);
      if (!info.isFile() || info.size < 1 || info.size > MAX_EPUB_BYTES ||
          info.size !== result.byte_size) throw new Error("invalid source book file");
      const deliveryRoot = resolve(config.deliveryMediaRoot);
      const outbound = resolve(deliveryRoot,
        `sourcebook-${result.isbn13}-${randomUUID()}.epub`);
      let queued = false;
      try {
        await mkdir(deliveryRoot, { recursive: true, mode: 0o700 });
        await chmod(deliveryRoot, 0o700);
        await pruneSourceBookMedia(deliveryRoot);
        await copyFile(path, outbound, constants.COPYFILE_EXCL);
        await chmod(outbound, 0o600);
        await ctx.delivery.send({ text: `《${result.book_title}》EPUB 原文件`,
          mediaUrl: outbound });
        queued = true;
        setTimeout(() => unlink(outbound).catch(() => {}), EVIDENCE_TTL_MS).unref();
      } finally {
        if (!queued) await unlink(outbound).catch(() => {});
      }
      return { content: [{ type: "text", text: JSON.stringify({
        book_title: result.book_title, isbn13: result.isbn13,
        delivery_status: "queued" }) }] };
    },
  };
}

export function librarianReviewTool(config, ctx, bridge = runReviewBridge) {
  if (ctx?.agentId !== "librarian" || !ctx.requesterSenderId) return null;
  const route = ctx.deliveryContext ?? {};
  if ((ctx.messageChannel && route.channel && ctx.messageChannel !== route.channel) ||
      (ctx.agentAccountId && route.accountId && ctx.agentAccountId !== route.accountId)) return null;
  const ownerId = ownerFor(config, { senderId: ctx.requesterSenderId },
    { channelId: ctx.messageChannel ?? route.channel,
      accountId: ctx.agentAccountId ?? route.accountId });
  if (!ownerId) return null;
  return {
    name: "librarian_review",
    label: "Librarian pending extraction review",
    description: "Read pending extraction conflicts for this authenticated sender. With no capture_id, list pending captures and recent image-intake failures. With a capture_id, compare current traces and proposed groups; this tool never changes stored traces.",
    parameters: { type: "object", properties: {
      capture_id: { type: "string", pattern: "^capture_[A-Za-z0-9_-]+$" },
    }, additionalProperties: false },
    async execute(_id, params) {
      const result = await bridge(config, { owner_id: ownerId,
        capture_id: params.capture_id });
      return { content: [{ type: "text", text: JSON.stringify(result) }],
        details: result };
    },
  };
}

export function librarianReviewDecisionTool(config, ctx, recent,
                                            bridge = runReviewDecisionBridge,
                                            now = Date.now()) {
  if (ctx?.agentId !== "librarian" || !ctx.sessionKey || !ctx.requesterSenderId) return null;
  const entry = recent.get(ctx.sessionKey);
  const route = ctx.deliveryContext ?? {};
  if (!entry || now - entry.at > 10 * 60_000 || now < entry.at ||
      entry.senderId !== ctx.requesterSenderId ||
      entry.channelId !== (ctx.messageChannel ?? route.channel) ||
      entry.accountId !== (ctx.agentAccountId ?? route.accountId) ||
      (ctx.messageChannel && route.channel && ctx.messageChannel !== route.channel) ||
      (ctx.agentAccountId && route.accountId && ctx.agentAccountId !== route.accountId) ||
      ownerFor(config, { senderId: entry.senderId },
        { channelId: entry.channelId, accountId: entry.accountId }) !== entry.ownerId) return null;
  return {
    name: "librarian_review_decision",
    label: "Record Librarian review decision",
    description: "Record an explicit user accept/reject decision for one pending scan candidate. Requires the current run and stable candidate ID. This records review evidence only; it does not put text into Library or Vault.",
    parameters: { type: "object", properties: {
      capture_id: { type: "string", pattern: "^capture_[A-Za-z0-9_-]+$" },
      pending_run_id: { type: "string", pattern: "^run_[A-Za-z0-9_-]+$" },
      candidate_id: { type: "string", pattern: "^candidate_[a-f0-9]{24}$" },
      decision: { type: "string", enum: ["accept", "reject"] },
      corrected_text: { type: "string", minLength: 1, maxLength: 2000 },
    }, required: ["capture_id", "pending_run_id", "candidate_id", "decision"],
    additionalProperties: false },
    async execute(_id, params) {
      const result = await bridge(config, { owner_id: entry.ownerId,
        actor_id: entry.senderId,
        source: { transport: entry.channelId, account_id: entry.accountId,
          conversation_id: entry.conversationId, source_event_id: entry.messageId },
        ...params });
      return { content: [{ type: "text", text: JSON.stringify(result) }], details: result };
    },
  };
}

export function librarianReviewFinalizeTool(config, ctx, recent,
                                            bridge = runReviewFinalizeBridge,
                                            now = Date.now()) {
  if (ctx?.agentId !== "librarian" || !ctx.sessionKey || !ctx.requesterSenderId) return null;
  const entry = recent.get(ctx.sessionKey);
  const route = ctx.deliveryContext ?? {};
  if (!entry || now - entry.at > 10 * 60_000 || now < entry.at ||
      entry.senderId !== ctx.requesterSenderId ||
      entry.channelId !== (ctx.messageChannel ?? route.channel) ||
      entry.accountId !== (ctx.agentAccountId ?? route.accountId) ||
      (ctx.messageChannel && route.channel && ctx.messageChannel !== route.channel) ||
      (ctx.agentAccountId && route.accountId && ctx.agentAccountId !== route.accountId) ||
      ownerFor(config, { senderId: entry.senderId },
        { channelId: entry.channelId, accountId: entry.accountId }) !== entry.ownerId) return null;
  return {
    name: "librarian_review_finalize",
    label: "Finalize Librarian scan review",
    description: "Apply a user's explicit instruction to replace all current trace groups for one scan with its completely reviewed candidate set. Requires every candidate decision, the current run ID, and exact old trace revisions. Preserves source evidence and triggers a Vault export worker.",
    parameters: { type: "object", properties: {
      capture_id: { type: "string", pattern: "^capture_[A-Za-z0-9_-]+$" },
      pending_run_id: { type: "string", pattern: "^run_[A-Za-z0-9_-]+$" },
      expected_current: { type: "array", items: { type: "object", properties: {
        trace_id: { type: "string", pattern: "^rt_[A-Za-z0-9_-]+$" },
        revision: { type: "integer", minimum: 1 },
      }, required: ["trace_id", "revision"], additionalProperties: false } },
      replace_all_current: { type: "boolean", const: true },
    }, required: ["capture_id", "pending_run_id", "expected_current", "replace_all_current"],
    additionalProperties: false },
    async execute(_id, params) {
      const result = await bridge(config, { owner_id: entry.ownerId,
        actor_id: entry.senderId,
        source: { transport: entry.channelId, account_id: entry.accountId,
          conversation_id: entry.conversationId, source_event_id: entry.messageId },
        ...params });
      if (result.status === "reconciled") startWorker(config, entry.ownerId);
      return { content: [{ type: "text", text: JSON.stringify(result) }], details: result };
    },
  };
}

export function rememberInboundSession(config, recent, event, ctx, now = Date.now()) {
  const ownerId = ownerFor(config, event, ctx);
  if (!ownerId || !ctx.sessionKey || !event.messageId) return;
  for (const [key, entry] of recent) {
    if (now - entry.at > 10 * 60_000) recent.delete(key);
  }
  recent.set(ctx.sessionKey, { ownerId, senderId: event.senderId,
    channelId: ctx.channelId, accountId: ctx.accountId,
    conversationId: ctx.sessionKey, messageId: event.messageId, at: now });
}

export function librarianSessionTool(config, ctx, recent, bridge = runSessionBridge,
                                     now = Date.now()) {
  if (ctx?.agentId !== "librarian" || !ctx.sessionKey || !ctx.requesterSenderId) return null;
  const entry = recent.get(ctx.sessionKey);
  const route = ctx.deliveryContext ?? {};
  if (!entry || now - entry.at > 10 * 60_000 || now < entry.at ||
      entry.senderId !== ctx.requesterSenderId ||
      entry.channelId !== (ctx.messageChannel ?? route.channel) ||
      entry.accountId !== (ctx.agentAccountId ?? route.accountId) ||
      (ctx.messageChannel && route.channel && ctx.messageChannel !== route.channel) ||
      (ctx.agentAccountId && route.accountId && ctx.agentAccountId !== route.accountId) ||
      ownerFor(config, { senderId: entry.senderId },
        { channelId: entry.channelId, accountId: entry.accountId }) !== entry.ownerId) return null;
  return {
    name: "librarian_session",
    label: "Librarian session",
    description: "Apply an explicit reading-session instruction from this authenticated inbound message. start needs a physical book title or ISBN; progress needs a page number.",
    parameters: { type: "object", properties: {
      action: { type: "string", enum: ["start", "progress", "pause", "resume", "close", "status"] },
      book: { type: "string", minLength: 1, maxLength: 200 },
      page: { type: "integer", minimum: 1, maximum: 9999 },
    }, required: ["action"], additionalProperties: false },
    async execute(_id, params) {
      const result = await bridge(config, { owner_id: entry.ownerId,
        actor_id: entry.senderId,
        source: { transport: entry.channelId, account_id: entry.accountId,
          conversation_id: entry.conversationId, source_event_id: entry.messageId },
        action: params.action, book: params.book, page: params.page });
      return { content: [{ type: "text", text: JSON.stringify(result) }], details: result };
    },
  };
}

export async function acceptMessage(config, event, ctx, bridge = runBridge) {
  const ownerId = ownerFor(config, event, ctx);
  if (!ownerId || event.mediaStagingPending || !event.messageId || !ctx.conversationId ||
      !Array.isArray(event.media)) return null;
  const attachments = [];
  let total = 0;
  for (const [index, media] of event.media.entries()) {
    if (!media.contentType?.startsWith("image/")) continue;
    if (!media.path || !isAbsolute(media.path)) return null; // Only staged local paths.
    const path = await realpath(media.path);
    const info = await stat(path);
    if (!info.isFile() || info.size < 1 || info.size > MAX_IMAGE_BYTES) return null;
    total += info.size;
    if (total > MAX_BATCH_BYTES) return null;
    attachments.push({ source_item_id: `${event.messageId}:${index}`,
      mime_type: media.contentType, data_path: path });
  }
  if (!attachments.length) return null;
  return bridge(config, { owner_id: ownerId, actor_id: event.senderId,
    source: { transport: ctx.channelId, account_id: ctx.accountId,
      conversation_id: ctx.conversationId, source_event_id: event.messageId },
    attachments });
}

export default {
  id: "pap-librarian-intake",
  name: "PAP Librarian Image Intake",
  register(api) {
    const config = api.pluginConfig ?? {};
    let recoveryTimer;
    let intakeTimer;
    const recentInbound = inboundSessions();
    api.registerTool((ctx) => {
      const tool = librarianSearchTool(config, ctx);
      if (ctx?.agentId === "librarian") api.logger.info(
        `Librarian tool scope: sender=${Boolean(ctx.requesterSenderId)} ` +
        `channel=${ctx.messageChannel ?? ctx.deliveryContext?.channel ?? "missing"} ` +
        `account=${ctx.agentAccountId ?? ctx.deliveryContext?.accountId ?? "missing"} ` +
        `session=${Boolean(ctx.sessionKey)} search=${Boolean(tool)} ` +
        `ownerCount=${configuredOwnerIds(config).length} ` +
        `senderMatch=${config.ownerMappings?.some((m) => m.senderId === ctx.requesterSenderId) ?? false} ` +
        `routeMatch=${config.ownerMappings?.some((m) => m.channelId === (ctx.messageChannel ?? ctx.deliveryContext?.channel) &&
          m.accountId === (ctx.agentAccountId ?? ctx.deliveryContext?.accountId)) ?? false}`);
      return tool;
    },
      { name: "librarian_search" });
    api.registerTool((ctx) => {
      const tool = librarianSessionTool(config, ctx, recentInbound);
      if (ctx?.agentId === "librarian") api.logger.info(
        `Librarian session tool scope: recent=${Boolean(recentInbound.get(ctx.sessionKey))} ` +
        `entries=${recentInbound.size} ` +
        `available=${Boolean(tool)}`);
      return tool;
    }, { name: "librarian_session" });
    api.registerTool((ctx) => librarianEvidenceTool(config, ctx),
      { name: "librarian_evidence" });
    api.registerTool((ctx) => librarianSourceBookTool(config, ctx),
      { name: "librarian_source_book" });
    api.registerTool((ctx) => librarianReviewTool(config, ctx),
      { name: "librarian_review" });
    api.registerTool((ctx) => librarianReviewDecisionTool(config, ctx, recentInbound),
      { name: "librarian_review_decision" });
    api.registerTool((ctx) => librarianReviewFinalizeTool(config, ctx, recentInbound),
      { name: "librarian_review_finalize" });
    api.registerService({ id: "pap-librarian-worker", start: () => {
      const recover = () => {
        for (const ownerId of configuredOwnerIds(config)) {
          startWorker(config, ownerId, "physical");
          if (config.digitalSources?.ownerId === ownerId) {
            startWorker(config, ownerId, "digital");
          }
        }
      };
      recover();
      recoveryTimer = setInterval(recover, 300_000);
    }, stop: () => { clearInterval(recoveryTimer); clearTimeout(intakeTimer); } });
    api.on("message_received", async (event, ctx) => {
      try {
        if (ctx.accountId === "librarian") api.logger.info(
          `Librarian inbound: sender=${Boolean(event.senderId)} ` +
          `message=${Boolean(event.messageId)} session=${Boolean(ctx.sessionKey)} ` +
          `conversation=${Boolean(ctx.conversationId)} ` +
          `media=${Array.isArray(event.media) ? event.media.length : "absent"} ` +
          `staging=${Boolean(event.mediaStagingPending)}`);
        rememberInboundSession(config, recentInbound, event, ctx);
        if (ctx.accountId === "librarian") api.logger.info(
          `Librarian inbound binding: owner=${Boolean(ownerFor(config, event, ctx))} ` +
          `saved=${Boolean(recentInbound.get(ctx.sessionKey))} entries=${recentInbound.size}`);
        const receipt = await acceptMessage(config, event, ctx);
        if (receipt) {
          await writeIntakeStatus(config, event, ctx, "accepted", null,
            receipt.capture_ids).catch(() => api.logger.warn("Librarian intake status write failed"));
          api.logger.info(`Librarian accepted ${receipt.capture_ids.length} image(s)`);
          clearTimeout(intakeTimer);
          intakeTimer = setTimeout(() => startWorker(config, ownerFor(config, event, ctx)),
            60_000);
        }
      } catch (error) {
        const code = typeof error?.code === "string" && /^[A-Z_]+$/.test(error.code)
          ? error.code : "HOOK_FAILED";
        await writeIntakeStatus(config, event, ctx, "failed", error)
          .catch(() => api.logger.warn("Librarian intake status write failed"));
        api.logger.warn(`Librarian image intake failed: ${code}`);
      }
    });
  },
};
