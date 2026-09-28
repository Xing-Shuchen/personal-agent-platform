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
the current trace index through `runtime/gateway_search.py`. The tool is
created only for the dedicated `librarian` agent when OpenClaw supplies a
matching channel, account and sender. Its arguments contain a query and limit,
never an owner ID. With `ownerMappings: []`, the tool is absent. A normal CLI
agent turn also has no mapped sender and cannot read the private store.

From the PAP repository root, install the linked local plugin:

```bash
openclaw plugins install --link --force --accept-capabilities ./agents/librarian/openclaw-plugin
```

Configure absolute repository, private state and Vault paths, an OCR-capable
Python interpreter, and an explicit owner mapping. Install the package's
`librarian-ocr` extra in that interpreter. Put an owner-supplied EPUB at
`stateRoot/source-books/<isbn13>.epub` before processing a photographed book.
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
openclaw plugins enable pap-librarian-intake
openclaw plugins inspect pap-librarian-intake --runtime --json
```

`stateRoot` must stay outside Git. The Gateway process needs read access to
its staged media and write access to `stateRoot` and `vaultRoot`. The Python
bridge and worker use `jsonschema`, Pillow, RapidOCR, ONNX Runtime and OpenCV.

Optional native digital sync runs with the same five-minute recovery service.
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
then aligns printed text to the EPUB, detects long underlines, refines small
handwriting crops, writes current traces and a review note under
`2Area/40 学习与阅读/阅读笔记`, and sends one Feishu message after both stores are
written. The first-book five-photo run and replay passed. The separate
pp.159/166/171/184 M1 acceptance set remains deferred. The official OpenClaw
[message hook contract](https://docs.openclaw.ai/plugins/hooks/messages)
defines the staged `media` fields used here.
