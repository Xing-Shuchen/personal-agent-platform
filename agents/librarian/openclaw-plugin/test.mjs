import assert from "node:assert/strict";
import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { acceptMessage, librarianSearchTool, workerArgs } from "./index.js";

const config = { ownerMappings: [{ channelId: "telegram", accountId: "bot",
  senderId: "person", ownerId: "owner_fixture" }] };
const ctx = { channelId: "telegram", accountId: "bot", conversationId: "chat" };

test("staged images use trusted sender mapping and source order", async () => {
  const dir = await mkdtemp(join(tmpdir(), "librarian-hook-"));
  try {
    const file = join(dir, "photo.png");
    await writeFile(file, Buffer.from("synthetic image bytes"));
    const event = { senderId: "person", messageId: "msg-42", media: [
      { contentType: "text/plain", path: file },
      { contentType: "image/png", path: file },
    ] };
    let received;
    const result = await acceptMessage(config, event, ctx, async (_config, message) => {
      received = message;
      return { capture_ids: ["capture_fixture"] };
    });
    assert.deepEqual(result, { capture_ids: ["capture_fixture"] });
    assert.equal(received.owner_id, "owner_fixture");
    assert.deepEqual(received.source, { transport: "telegram", account_id: "bot",
      conversation_id: "chat", source_event_id: "msg-42" });
    assert.equal(received.attachments[0].source_item_id, "msg-42:1");
    assert.equal(received.attachments[0].data_path, file);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

test("unmapped or unstaged media is not ingested", async () => {
  const bridge = () => { throw new Error("bridge should not run"); };
  const event = { senderId: "stranger", messageId: "msg-1",
    media: [{ contentType: "image/png", path: "/tmp/unknown.png" }] };
  assert.equal(await acceptMessage(config, event, ctx, bridge), null);
  assert.equal(await acceptMessage(config, { ...event, senderId: "person",
    mediaStagingPending: true, media: undefined,
    originalMedia: event.media }, ctx, bridge), null);
  assert.equal(await acceptMessage(config, { ...event, senderId: "person",
    messageId: undefined }, ctx, bridge), null);
});

test("search tool requires exact trusted sender, account, channel and agent", async () => {
  const trusted = { agentId: "librarian", requesterSenderId: "person",
    messageChannel: "telegram", agentAccountId: "bot",
    deliveryContext: { channel: "telegram", accountId: "bot" } };
  const calls = [];
  const bridge = async (_config, message) => {
    calls.push(message);
    return { hits: [], next_cursor: null, index_state: "ready" };
  };
  const tool = librarianSearchTool(config, trusted, bridge);
  assert.equal(tool.name, "librarian_search");
  const result = await tool.execute("tool-call", { query: "Parsons", limit: 5 });
  assert.deepEqual(result.details.hits, []);
  assert.deepEqual(calls, [{ owner_id: "owner_fixture", query: "Parsons", limit: 5 }]);
  for (const changed of [
    { requesterSenderId: "stranger" }, { agentAccountId: "other" },
    { messageChannel: "discord" }, { agentId: "main" },
    { requesterSenderId: undefined }, { agentAccountId: undefined,
      deliveryContext: undefined },
  ]) {
    assert.equal(librarianSearchTool(config, { ...trusted, ...changed }, bridge), null);
  }
  assert.equal(librarianSearchTool({ ownerMappings: [] }, trusted, bridge), null);
  assert.equal(librarianSearchTool({ ownerMappings: [...config.ownerMappings,
    ...config.ownerMappings] }, trusted, bridge), null);
});

test("a second owner cannot inherit a shared digital source or Vault", async () => {
  const one = { ...config, stateRoot: "/state", vaultRoot: "/vault",
    digitalSources: { ownerId: "owner_fixture", koodo: {
      sourceId: "koodo", booksDb: "/private/books.db", notesDb: "/private/notes.db" } } };
  assert.ok(workerArgs(one, "owner_fixture").includes("--koodo-books-db"));
  const two = { ...one, ownerMappings: [...one.ownerMappings,
    { channelId: "telegram", accountId: "bot", senderId: "another", ownerId: "owner_b" }] };
  assert.equal(workerArgs(two, "owner_fixture"), null);
  assert.equal(workerArgs(two, "owner_b"), null);
  assert.equal(librarianSearchTool(two, { agentId: "librarian", requesterSenderId: "another",
    messageChannel: "telegram", agentAccountId: "bot" }), null);
  assert.equal(await acceptMessage(two, { senderId: "another", messageId: "m",
    media: [] }, ctx, () => { throw new Error("bridge must remain closed"); }), null);
});

test("worker runs without a Vault and binds a configurable vision model", () => {
  const args = workerArgs({ ...config, stateRoot: "/state", visionModel: "fixture/vision" },
    "owner_fixture");
  assert.ok(args);
  assert.ok(!args.includes("--vault"));
  assert.equal(args[args.indexOf("--vision-model") + 1], "fixture/vision");
});
