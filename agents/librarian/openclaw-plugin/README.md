# OpenClaw Librarian image intake

This local OpenClaw plugin observes `message_received` and accepts staged
`image/*` attachments into the Librarian capture store. It does not read
`originalMedia`, fetch remote URLs, or infer an owner from message text. A
channel/account/sender must have exactly one explicit owner mapping.

The plugin uses the inbound `messageId` as source event identity and the
original media array index as attachment identity. A retry of that message
returns the same capture receipt; changed bytes under the same identity fail
with `IDEMPOTENCY_CONFLICT`. The hook passes staged local paths to the bridge,
which durably copies originals before acknowledging intake. It then starts
the background worker; a Gateway service periodically recovers unfinished
batches. The ordinary chat turn can continue.

The same mapping gates `librarian_search`, a read-only agent tool that queries
the current trace index through `runtime/gateway_search.py` by text, book title
and/or printed page number. The tool is
created only for the dedicated `librarian` agent when OpenClaw supplies a
matching channel, account and sender. Its arguments contain a query and limit,
never an owner ID. With `ownerMappings: []`, the tool is absent. A normal CLI
agent turn also has no mapped sender and cannot read the private store.
`librarian_session` applies an explicit reading-session instruction using the
trusted inbound message ID and conversation scope. The model supplies only
the requested action, title or reported page. `librarian_evidence` reads an
owner-scoped physical trace, sends a temporary cropped original to the
current bound conversation, then removes the temporary file; originals remain
in the private object store and never enter the Vault. `librarian_review` lists
pending extraction conflicts and compares current traces with proposed groups
without changing stored records. Configure the dedicated
OpenClaw agent with `tools.allow` set to
`["librarian_search", "librarian_session", "librarian_evidence", "librarian_review", "session_status"]`. Image intake and background processing run through the
plugin service, so the chat agent needs no shell or filesystem tool. This
prevents a model from bypassing owner-scoped search through local SQLite.

From the PAP repository root, install the linked local plugin:

```bash
openclaw plugins install --link --force --accept-capabilities ./agents/librarian/openclaw-plugin
```

Configure absolute repository and private state paths, an OCR-capable Python
interpreter, and an explicit owner mapping. Vault is optional. Install the
package's `librarian-ocr` extra in that interpreter. An owner-supplied EPUB at
`stateRoot/source-books/<isbn13>.epub` enables local OCR alignment; without it,
the worker still runs local OCR for printed lines and underlines, then uses the
configured image-capable OpenClaw model only when local OCR finds no mark.
Unknown books and page numbers remain unresolved in stored observations.
Replace the example channel, account, sender and owner IDs with trusted values
from your OpenClaw deployment:

Until those IDs are established, use `"ownerMappings":[]`; the plugin will
load but cannot ingest any sender's images. A dedicated Librarian
agent/profile is declared at `agents/librarian/agent.yaml` and
`agents/librarian/profile/`. Register the OpenClaw agent separately with
`openclaw agents add librarian --non-interactive --workspace
~/.openclaw/workspace-librarian --model MODEL_ID`, then bind it to a dedicated
channel account when routing is decided. On this PC it is bound to the
`feishu:librarian` account, with DM pairing enabled and group chats disabled.
The sender is paired and the mapping is active for the first-book run.

```bash
openclaw config set plugins.entries.pap-librarian-intake.config '{"repoRoot":"/absolute/path/to/personal-agent-platform","stateRoot":"/absolute/path/to/personal-agent-platform/var/librarian","vaultRoot":"/absolute/path/to/Obsidian/Second_Brain","python":"/absolute/path/to/personal-agent-platform/.venv/bin/python","ownerMappings":[{"channelId":"feishu","accountId":"librarian","senderId":"paired-user-open-id","ownerId":"owner_local"}]}' --strict-json
openclaw plugins enable pap-librarian-intake --accept-capabilities
openclaw plugins inspect pap-librarian-intake --runtime --json
```

`stateRoot` must stay outside Git. The Gateway process needs read access to
its staged media and write access to `stateRoot` and `vaultRoot`. The Python
bridge and worker use `jsonschema`, Pillow, RapidOCR, ONNX Runtime and OpenCV.

Optional native digital sync runs on a separate worker schedule and lock.
Set `digitalSources.ownerId` to the sole configured owner before enabling any
digital source; multiple distinct owners fail closed until per-owner roots and
routing are implemented.
Configure `digitalSources.koodo` with a stable source ID and Koodo's read-only
`books.db` and `notes.db` paths. Configure `digitalSources.weread` with a stable
source ID, the local Obsidian WeRead plugin `data.json` path and explicit book
IDs. The worker reads the Agent API key from that private file; do not put it
in OpenClaw config. Each source reports success or an error code in
`stateRoot/digital-sync-status.json`. A digital source error does not stop
physical photo processing. The WeRead book list is explicit; adding books
requires updating this config.

Run local tests:

```bash
node --test agents/librarian/openclaw-plugin/test.mjs
PYTHONPATH=. python3 -m pytest tests/test_librarian_gateway_bridge.py -q
PYTHONPATH=. python3 -m pytest tests/test_librarian_gateway_search.py -q
```

This hook accepts original bytes and creates a capture receipt. The worker
waits for a short upload quiet period and groups consecutive images in the
same conversation. It then aligns printed text to the EPUB, corrects
upside-down scans for analysis, detects long underlines, refines small
handwriting crops, writes current traces and a review note under
`2Area/40 学习与阅读/阅读笔记`, and sends a Feishu review message after both stores are
written. Existing generated blocks are consolidated into one WeRead-style
note only after verifying their trace anchors and exact generated text.
The first-book five-photo run and a later 22-photo burst were processed;
unresolved page labels and one conflicting old extraction remain for review.
The separate
pp.159/166/171/184 M1 acceptance set remains deferred. The official OpenClaw
[message hook contract](https://docs.openclaw.ai/plugins/hooks/messages)
defines the staged `media` fields used here.
