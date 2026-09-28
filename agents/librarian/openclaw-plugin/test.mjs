import assert from "node:assert/strict";
import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { acceptMessage } from "./index.js";

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
    assert.equal(Buffer.from(received.attachments[0].data_b64, "base64").toString(),
      "synthetic image bytes");
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
