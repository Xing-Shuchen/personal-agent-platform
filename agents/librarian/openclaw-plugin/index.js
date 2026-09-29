import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { constants } from "node:fs";
import { chmod, copyFile, mkdir, realpath, stat, unlink } from "node:fs/promises";
import { delimiter, dirname, isAbsolute, resolve } from "node:path";

const MAX_IMAGE_BYTES = 20 * 1024 * 1024;
const MAX_BATCH_BYTES = 100 * 1024 * 1024;
const INBOUND_SESSIONS = Symbol.for("pap.librarian.inboundSessions");

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

async function runPythonBridge(config, module, message) {
  const python = config.python ?? "python3";
  const child = spawn(python, ["-m", module, "--root", config.stateRoot], {
    cwd: config.repoRoot,
    env: { ...process.env, PYTHONPATH: [config.repoRoot, process.env.PYTHONPATH ?? ""].join(delimiter) },
    stdio: ["pipe", "pipe", "pipe"],
  });
  const stdout = [];
  let size = 0;
  child.stdout.on("data", (chunk) => {
    size += chunk.length;
    if (size > 1024 * 1024) child.kill();
    else stdout.push(chunk);
  });
  child.stderr.resume(); // Never log private paths or model data from the bridge.
  const completed = new Promise((resolve, reject) => {
    child.once("error", reject);
    child.once("close", (code) => resolve(code));
  });
  child.stdin.on("error", () => {}); // An early bridge exit can close stdin.
  const timer = setTimeout(() => child.kill(), 60_000);
  child.stdin.end(JSON.stringify(message));
  try {
    const code = await completed;
    const result = JSON.parse(Buffer.concat(stdout).toString("utf8"));
    if (code !== 0 || result.error) {
      const failure = new Error("bridge failed");
      failure.code = result.error?.code ?? "BRIDGE_FAILED";
      throw failure;
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
const runReviewBridge = (config, message) => runPythonBridge(
  config, "agents.librarian.runtime.gateway_review", message);

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
  const args = workerArgs(config, ownerId);
  if (!args) return;
  args.push(mode === "digital" ? "--digital-only" : "--physical-only");
  const child = spawn(config.python ?? "python3", args, {
    cwd: config.repoRoot,
    env: { ...process.env, PYTHONPATH: [config.repoRoot, process.env.PYTHONPATH ?? ""].join(delimiter) },
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
    description: "Queue an owner-scoped crop to this conversation. Use trace_id for a stored trace, or capture_id plus candidate_id from current search pending_evidence for a newer unreviewed scan. Candidate indexes can shift after reprocessing; prefer candidate_id. A queue receipt does not prove platform delivery or approve a pending candidate.",
    parameters: { type: "object", properties: {
      trace_id: { type: "string", pattern: "^rt_[A-Za-z0-9_-]+$" },
      capture_id: { type: "string", pattern: "^capture_[A-Za-z0-9_-]+$" },
      candidate_id: { type: "string", pattern: "^candidate_[A-Za-z0-9_-]+$" },
      candidate_index: { type: "integer", minimum: 0 },
    }, oneOf: [{ required: ["trace_id"] },
      { required: ["capture_id", "candidate_id"] },
      { required: ["capture_id", "candidate_index"] }], additionalProperties: false },
    async execute(_id, params) {
      const result = await bridge(config, { owner_id: ownerId,
        ...(params.trace_id ? { trace_id: params.trace_id } :
          { capture_id: params.capture_id,
            ...(params.candidate_id ? { candidate_id: params.candidate_id } :
              { candidate_index: params.candidate_index }) }) });
      const path = resolve(result.media_path);
      if (dirname(path) !== resolve(config.stateRoot, "delivery-evidence")) {
        throw new Error("invalid evidence path");
      }
      const deliveryRoot = resolve(config.deliveryMediaRoot);
      const outbound = resolve(deliveryRoot, `evidence-${randomUUID()}.jpg`);
      try {
        const info = await stat(path);
        if (!info.isFile() || info.size < 1 || info.size > MAX_IMAGE_BYTES) {
          throw new Error("invalid evidence file");
        }
        await mkdir(deliveryRoot, { recursive: true, mode: 0o700 });
        await chmod(deliveryRoot, 0o700);
        await copyFile(path, outbound, constants.COPYFILE_EXCL);
        await chmod(outbound, 0o600);
        await ctx.delivery.send({ text: result.source_status === "pending_review" ?
          `扫描件待审核候选原图局部：${result.capture_id} ${result.candidate_id ?? result.candidate_index}` :
          `原图局部证据：${result.trace_id}`,
          mediaUrl: outbound });
      } finally {
        await unlink(path).catch(() => {});
        await unlink(outbound).catch(() => {});
      }
      return { content: [{ type: "text", text: JSON.stringify({
        trace_id: result.trace_id ?? null, capture_id: result.capture_id,
        candidate_id: result.candidate_id ?? null,
        candidate_index: result.candidate_index ?? null,
        source_status: result.source_status ?? "stored_trace",
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
    description: "Read pending extraction conflicts for this authenticated sender. With no capture_id, list pending captures. With a capture_id, compare current traces and proposed groups; this tool never changes stored traces.",
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
    api.registerTool((ctx) => librarianReviewTool(config, ctx),
      { name: "librarian_review" });
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
          api.logger.info(`Librarian accepted ${receipt.capture_ids.length} image(s)`);
          clearTimeout(intakeTimer);
          intakeTimer = setTimeout(() => startWorker(config, ownerFor(config, event, ctx)),
            60_000);
        }
      } catch (error) {
        const code = typeof error?.code === "string" && /^[A-Z_]+$/.test(error.code)
          ? error.code : "HOOK_FAILED";
        api.logger.warn(`Librarian image intake failed: ${code}`);
      }
    });
  },
};
