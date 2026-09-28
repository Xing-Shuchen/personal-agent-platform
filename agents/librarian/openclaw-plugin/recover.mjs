// Recover a staged OpenClaw inbound event missed before the intake mapping existed.
// The event is submitted through the same owner mapping and idempotent bridge as live media.
import { spawnSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { acceptMessage } from "./index.js";

const [database, sessionId, sequence, conversationId] = process.argv.slice(2);
if (!database || !sessionId || !sequence || !conversationId) {
  throw new Error("usage: node recover.mjs DB SESSION_ID SEQ CONVERSATION_ID");
}
const lookup = spawnSync("python3", ["-c", `
import json, sqlite3, sys
db, session, seq = sys.argv[1:]
row = sqlite3.connect(db).execute(
    "SELECT event_json FROM transcript_events WHERE session_id=? AND seq=?",
    (session, int(seq))).fetchone()
if row is None: raise SystemExit("event not found")
print(row[0])
`, database, sessionId, sequence], { encoding: "utf8", maxBuffer: 1024 * 1024 });
if (lookup.status !== 0) throw new Error("OpenClaw transcript lookup failed");
const record = JSON.parse(lookup.stdout);
const message = record.message?.__openclaw;
if (!message || record.message?.role !== "user" || !message.transport?.messageId ||
    message.transport.channel !== "feishu") throw new Error("unsupported inbound event");
const config = JSON.parse(await readFile(`${process.env.HOME}/.openclaw/openclaw.json`, "utf8"))
  .plugins.entries["pap-librarian-intake"].config;
const event = { senderId: message.senderId, messageId: message.transport.messageId,
  media: message.media, mediaStagingPending: false };
const ctx = { channelId: "feishu", accountId: "librarian", conversationId };
const receipt = await acceptMessage(config, event, ctx);
if (!receipt) throw new Error("event did not match the trusted intake route");
process.stdout.write(JSON.stringify(receipt) + "\n");
