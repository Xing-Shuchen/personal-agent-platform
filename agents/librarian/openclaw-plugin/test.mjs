import assert from "node:assert/strict";
import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { acceptMessage, librarianEvidenceTool, librarianReviewTool, librarianReviewDecisionTool, librarianReviewFinalizeTool, librarianSearchTool, librarianSessionTool,
  rememberInboundSession, workerArgs } from "./index.js";
import librarianPlugin from "./index.js";

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
  assert.deepEqual(calls, [{ owner_id: "owner_fixture", query: "Parsons",
    book: undefined, page: undefined, limit: 5 }]);
  await tool.execute("page-call", { book: "社会理论二十讲", page: 39 });
  assert.deepEqual(calls[1], { owner_id: "owner_fixture", query: undefined,
    book: "社会理论二十讲", page: 39, limit: 10 });
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
  const mismatched = { ...one, digitalSources: { ...one.digitalSources,
    ownerId: "owner_b" } };
  assert.ok(!workerArgs(mismatched, "owner_fixture").includes("--koodo-books-db"));
});

test("worker runs without a Vault and binds a configurable vision model", () => {
  const args = workerArgs({ ...config, stateRoot: "/state", visionModel: "fixture/vision" },
    "owner_fixture");
  assert.ok(args);
  assert.ok(!args.includes("--vault"));
  assert.equal(args[args.indexOf("--vision-model") + 1], "fixture/vision");
});

test("session tool carries only trusted inbound source identity", async () => {
  const recent = new Map();
  const inbound = { channelId: "telegram", accountId: "bot",
    sessionKey: "agent:librarian:chat" };
  rememberInboundSession(config, recent, { senderId: "person", messageId: "msg-77" }, inbound, 1000);
  const trusted = { agentId: "librarian", sessionKey: inbound.sessionKey,
    requesterSenderId: "person", messageChannel: "telegram", agentAccountId: "bot" };
  let seen;
  const bridge = async (_config, message) => { seen = message; return { status: "active" }; };
  const tool = librarianSessionTool(config, trusted, recent, bridge, 1001);
  assert.equal(tool.name, "librarian_session");
  await tool.execute("call", { action: "start", book: "Synthetic Work" });
  assert.deepEqual(seen, { owner_id: "owner_fixture", actor_id: "person",
    source: { transport: "telegram", account_id: "bot",
      conversation_id: "agent:librarian:chat",
      source_event_id: "msg-77" }, action: "start", book: "Synthetic Work", page: undefined });
  assert.equal(librarianSessionTool(config, { ...trusted, requesterSenderId: "other" },
    recent, bridge, 1001), null);
  assert.equal(librarianSessionTool(config, trusted, recent, bridge, 601001), null);
  assert.equal(librarianSessionTool(config, { ...trusted, agentAccountId: "other" },
    recent, bridge, 1001), null);
});

test("inbound binding survives separate hook and tool plugin registrations", async () => {
  const registrations = [];
  for (let i = 0; i < 2; i++) {
    const hooks = new Map();
    const tools = new Map();
    librarianPlugin.register({ pluginConfig: config, logger: { info() {}, warn() {} },
      registerTool(factory, options) { tools.set(options.name, factory); },
      registerService() {}, on(name, handler) { hooks.set(name, handler); } });
    registrations.push({ hooks, tools });
  }
  const sessionKey = "agent:librarian:cross-registration-fixture";
  await registrations[0].hooks.get("message_received")(
    { senderId: "person", messageId: "msg-cross-registration" },
    { channelId: "telegram", accountId: "bot", sessionKey });
  const tool = registrations[1].tools.get("librarian_session")({
    agentId: "librarian", sessionKey, requesterSenderId: "person",
    messageChannel: "telegram", agentAccountId: "bot" });
  assert.equal(tool?.name, "librarian_session");
});

test("review decisions require a fresh bound inbound message", async () => {
  const recent = new Map();
  const sessionKey = "agent:librarian:review-fixture";
  rememberInboundSession(config, recent,
    { senderId: "person", messageId: "msg-review" },
    { channelId: "telegram", accountId: "bot", sessionKey }, 1000);
  const trusted = { agentId: "librarian", sessionKey, requesterSenderId: "person",
    messageChannel: "telegram", agentAccountId: "bot" };
  let sent;
  const bridge = async (_config, message) => { sent = message; return { status: "recorded" }; };
  const tool = librarianReviewDecisionTool(config, trusted, recent, bridge, 1001);
  assert.equal(tool?.name, "librarian_review_decision");
  await tool.execute("call", { capture_id: "capture_one", pending_run_id: "run_one",
    candidate_id: "candidate_" + "a".repeat(24), decision: "reject" });
  assert.equal(sent.source.source_event_id, "msg-review");
  assert.equal(sent.owner_id, "owner_fixture");
  assert.equal(librarianReviewDecisionTool(config,
    { ...trusted, requesterSenderId: "stranger" }, recent, bridge, 1001), null);
  assert.equal(librarianReviewDecisionTool(config, trusted, recent, bridge, 601001), null);
});

test("review finalization requires a fresh bound inbound message", async () => {
  const recent = new Map();
  const sessionKey = "agent:librarian:finalize-fixture";
  rememberInboundSession(config, recent,
    { senderId: "person", messageId: "msg-finalize" },
    { channelId: "telegram", accountId: "bot", sessionKey }, 1000);
  const trusted = { agentId: "librarian", sessionKey, requesterSenderId: "person",
    messageChannel: "telegram", agentAccountId: "bot" };
  let sent;
  const bridge = async (_config, message) => { sent = message; return { status: "fixture" }; };
  const tool = librarianReviewFinalizeTool(config, trusted, recent, bridge, 1001);
  assert.equal(tool?.name, "librarian_review_finalize");
  await tool.execute("call", { capture_id: "capture_one", pending_run_id: "run_one",
    expected_current: [{ trace_id: "rt_old", revision: 2 }], replace_all_current: true });
  assert.equal(sent.source.source_event_id, "msg-finalize");
  assert.deepEqual(sent.expected_current, [{ trace_id: "rt_old", revision: 2 }]);
  assert.equal(librarianReviewFinalizeTool(config,
    { ...trusted, requesterSenderId: "stranger" }, recent, bridge, 1001), null);
});

test("evidence tool retains queued media for channel delivery and removes bridge media", async () => {
  const stateRoot = await mkdtemp(join(tmpdir(), "librarian-evidence-"));
  try {
    const evidenceDir = join(stateRoot, "delivery-evidence");
    const deliveryMediaRoot = join(stateRoot, "allowed-media");
    await import("node:fs/promises").then(({ mkdir }) => mkdir(evidenceDir));
    const mediaPath = join(evidenceDir, "evidence-fixture.jpg");
    await writeFile(mediaPath, Buffer.from("synthetic crop"));
    const sent = [];
    const trusted = { agentId: "librarian", requesterSenderId: "person",
      messageChannel: "telegram", agentAccountId: "bot",
      deliveryContext: { channel: "telegram", accountId: "bot" },
      delivery: { send: async (payload) => {
        const bytes = await import("node:fs/promises").then(({ readFile }) => readFile(payload.mediaUrl));
        assert.deepEqual(bytes, Buffer.from("synthetic crop"));
        const info = await import("node:fs/promises").then(({ stat }) => stat(payload.mediaUrl));
        assert.equal(info.mode & 0o777, 0o600);
        sent.push(payload);
      } } };
    const bridge = async (_config, message) => {
      assert.deepEqual(message, { owner_id: "owner_fixture", trace_id: "rt_fixture" });
      return { trace_id: "rt_fixture", capture_id: "capture_fixture", media_path: mediaPath };
    };
    const tool = librarianEvidenceTool({ ...config, stateRoot, deliveryMediaRoot }, trusted, bridge);
    const receipt = await tool.execute("call", { trace_id: "rt_fixture" });
    assert.equal(sent.length, 1);
    assert.ok(sent[0].mediaUrl.startsWith(deliveryMediaRoot + "/evidence-"));
    assert.equal(JSON.parse(receipt.content[0].text).delivery_status, "queued");
    await assert.rejects(() => import("node:fs/promises").then(({ stat }) => stat(mediaPath)));
    const deferredBytes = await import("node:fs/promises").then(({ readFile }) =>
      readFile(sent[0].mediaUrl));
    assert.deepEqual(deferredBytes, Buffer.from("synthetic crop"));
    assert.equal(librarianEvidenceTool({ ...config, stateRoot },
      { ...trusted, requesterSenderId: "other" }, bridge), null);
    assert.equal(librarianEvidenceTool({ ...config, stateRoot, deliveryMediaRoot },
      { ...trusted, delivery: undefined }, bridge), null);
  } finally {
    await rm(stateRoot, { recursive: true, force: true });
  }
});

test("evidence tool cleans media when channel queueing fails", async () => {
  const stateRoot = await mkdtemp(join(tmpdir(), "librarian-evidence-failure-"));
  try {
    const evidenceDir = join(stateRoot, "delivery-evidence");
    const deliveryMediaRoot = join(stateRoot, "allowed-media");
    await import("node:fs/promises").then(({ mkdir }) => mkdir(evidenceDir));
    const mediaPath = join(evidenceDir, "evidence-fixture.jpg");
    await writeFile(mediaPath, Buffer.from("synthetic crop"));
    const trusted = { agentId: "librarian", requesterSenderId: "person",
      messageChannel: "telegram", agentAccountId: "bot",
      deliveryContext: { channel: "telegram", accountId: "bot" },
      delivery: { send: async () => { throw new Error("channel unavailable"); } } };
    const bridge = async () => ({ trace_id: "rt_fixture", capture_id: "capture_fixture",
      media_path: mediaPath });
    const tool = librarianEvidenceTool({ ...config, stateRoot, deliveryMediaRoot }, trusted, bridge);
    await assert.rejects(() => tool.execute("call", { trace_id: "rt_fixture" }),
      /channel unavailable/);
    const files = await import("node:fs/promises").then(({ readdir }) =>
      readdir(deliveryMediaRoot));
    assert.deepEqual(files, []);
    await assert.rejects(() => import("node:fs/promises").then(({ stat }) => stat(mediaPath)));
  } finally {
    await rm(stateRoot, { recursive: true, force: true });
  }
});

test("evidence tool labels pending scan crop without calling it a stored trace", async () => {
  const stateRoot = await mkdtemp(join(tmpdir(), "librarian-pending-scan-"));
  try {
    const evidenceDir = join(stateRoot, "delivery-evidence");
    const deliveryMediaRoot = join(stateRoot, "allowed-media");
    await import("node:fs/promises").then(({ mkdir }) => mkdir(evidenceDir));
    const mediaPath = join(evidenceDir, "pending.jpg");
    await writeFile(mediaPath, Buffer.from("scan crop"));
    const sent = [];
    const context = { agentId: "librarian", requesterSenderId: "person",
      messageChannel: "telegram", agentAccountId: "bot",
      deliveryContext: { channel: "telegram", accountId: "bot" },
      delivery: { send: async (payload) => sent.push(payload) } };
    const bridge = async (_config, message) => {
      assert.deepEqual(message, { owner_id: "owner_fixture", capture_id: "capture_scan",
        candidate_id: "candidate_fixture" });
      return { capture_id: "capture_scan", candidate_index: 1,
        candidate_id: "candidate_fixture",
        source_status: "pending_review", media_path: mediaPath };
    };
    const tool = librarianEvidenceTool({ ...config, stateRoot, deliveryMediaRoot }, context, bridge);
    const result = await tool.execute("call", { capture_id: "capture_scan", candidate_id: "candidate_fixture" });
    assert.match(sent[0].text, /待审核/);
    assert.equal(JSON.parse(result.content[0].text).source_status, "pending_review");
  } finally {
    await rm(stateRoot, { recursive: true, force: true });
  }
});

test("evidence tool sends a run-bound OCR gap crop for review", async () => {
  const stateRoot = await mkdtemp(join(tmpdir(), "librarian-ocr-gap-"));
  try {
    const evidenceDir = join(stateRoot, "delivery-evidence");
    const deliveryMediaRoot = join(stateRoot, "allowed-media");
    await import("node:fs/promises").then(({ mkdir }) => mkdir(evidenceDir));
    const mediaPath = join(evidenceDir, "gap.jpg");
    await writeFile(mediaPath, Buffer.from("gap crop"));
    const sent = [];
    const context = { agentId: "librarian", requesterSenderId: "person",
      messageChannel: "telegram", agentAccountId: "bot",
      deliveryContext: { channel: "telegram", accountId: "bot" },
      delivery: { send: async (payload) => sent.push(payload) } };
    const bridge = async (_config, message) => {
      assert.deepEqual(message, { owner_id: "owner_fixture", capture_id: "capture_scan",
        pending_run_id: "run_current", gap_index: 0 });
      return { capture_id: "capture_scan", pending_run_id: "run_current",
        gap_index: 0, source_status: "pending_ocr_gap", media_path: mediaPath };
    };
    const tool = librarianEvidenceTool({ ...config, stateRoot, deliveryMediaRoot }, context, bridge);
    const result = await tool.execute("call", { capture_id: "capture_scan",
      pending_run_id: "run_current", gap_index: 0 });
    assert.match(sent[0].text, /OCR 缺口/);
    assert.equal(JSON.parse(result.content[0].text).source_status, "pending_ocr_gap");
  } finally {
    await rm(stateRoot, { recursive: true, force: true });
  }
});

test("review tool is read-only and owner-bound", async () => {
  const trusted = { agentId: "librarian", requesterSenderId: "person",
    messageChannel: "telegram", agentAccountId: "bot",
    deliveryContext: { channel: "telegram", accountId: "bot" } };
  let seen;
  const bridge = async (_config, message) => {
    seen = message;
    return { pending: [{ capture_id: "capture_fixture" }] };
  };
  const tool = librarianReviewTool(config, trusted, bridge);
  assert.equal(tool.name, "librarian_review");
  await tool.execute("call", { capture_id: "capture_fixture" });
  assert.deepEqual(seen, { owner_id: "owner_fixture", capture_id: "capture_fixture" });
  assert.equal(librarianReviewTool(config, { ...trusted, requesterSenderId: "other" }, bridge), null);
  assert.equal(librarianReviewTool(config, { ...trusted, agentAccountId: "other" }, bridge), null);
});
