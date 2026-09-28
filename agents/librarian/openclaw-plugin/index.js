import { spawn } from "node:child_process";
import { readFile, realpath, stat } from "node:fs/promises";
import { delimiter, isAbsolute } from "node:path";

const MAX_IMAGE_BYTES = 20 * 1024 * 1024;
const MAX_BATCH_BYTES = 50 * 1024 * 1024;

function ownerFor(config, event, ctx) {
  if (!ctx?.channelId || !ctx?.accountId || !event?.senderId) return null;
  const matches = (config.ownerMappings ?? []).filter((entry) =>
    entry.channelId === ctx.channelId && entry.accountId === ctx.accountId &&
    entry.senderId === event.senderId);
  return matches.length === 1 ? matches[0].ownerId : null;
}

async function runBridge(config, message) {
  const python = config.python ?? "python3";
  const child = spawn(python, ["-m", "agents.librarian.runtime.gateway_bridge",
    "--root", config.stateRoot], {
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
      mime_type: media.contentType, data_b64: (await readFile(path)).toString("base64") });
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
    api.on("message_received", async (event, ctx) => {
      try {
        const receipt = await acceptMessage(config, event, ctx);
        if (receipt) api.logger.info(`Librarian accepted ${receipt.capture_ids.length} image(s)`);
      } catch (error) {
        const code = typeof error?.code === "string" && /^[A-Z_]+$/.test(error.code)
          ? error.code : "HOOK_FAILED";
        api.logger.warn(`Librarian image intake failed: ${code}`);
      }
    });
  },
};
