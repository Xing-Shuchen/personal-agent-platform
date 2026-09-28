import { spawn } from "node:child_process";
import { realpath, stat } from "node:fs/promises";
import { delimiter, isAbsolute } from "node:path";

const MAX_IMAGE_BYTES = 20 * 1024 * 1024;
const MAX_BATCH_BYTES = 100 * 1024 * 1024;

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
    description: "Search this authenticated sender's stored Librarian reading traces. Return provenance-backed hits or no supporting hits in this owner scope.",
    parameters: { type: "object", properties: {
      query: { type: "string", minLength: 1, maxLength: 256 },
      limit: { type: "integer", minimum: 1, maximum: 20 },
    }, required: ["query"], additionalProperties: false },
    async execute(_id, params) {
      const result = await bridge(config, { owner_id: ownerId,
        query: params.query, limit: params.limit ?? 10 });
      return { content: [{ type: "text", text: JSON.stringify(result) }],
        details: result };
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
    api.registerTool((ctx) => librarianSearchTool(config, ctx),
      { name: "librarian_search" });
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
    }, stop: () => clearInterval(recoveryTimer) });
    api.on("message_received", async (event, ctx) => {
      try {
        const receipt = await acceptMessage(config, event, ctx);
        if (receipt) {
          api.logger.info(`Librarian accepted ${receipt.capture_ids.length} image(s)`);
          startWorker(config, ownerFor(config, event, ctx));
        }
      } catch (error) {
        const code = typeof error?.code === "string" && /^[A-Z_]+$/.test(error.code)
          ? error.code : "HOOK_FAILED";
        api.logger.warn(`Librarian image intake failed: ${code}`);
      }
    });
  },
};
