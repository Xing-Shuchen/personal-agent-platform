# OpenClaw Librarian image intake

This local OpenClaw plugin observes `message_received` and accepts staged
`image/*` attachments into the Librarian capture store. It does not read
`originalMedia`, fetch remote URLs, or infer an owner from message text. A
channel/account/sender must have exactly one explicit owner mapping.

The plugin uses the inbound `messageId` as source event identity and the
original media array index as attachment identity. A retry of that message
returns the same capture receipt; changed bytes under the same identity fail
with `IDEMPOTENCY_CONFLICT`. The hook does not claim the message or wait for
vision extraction, so the ordinary chat turn can continue.

From the PAP repository root, install the linked local plugin:

```bash
openclaw plugins install --link --force --accept-capabilities ./agents/librarian/openclaw-plugin
```

Configure an absolute repository path, private state path, and an explicit
owner mapping. Replace the example channel, account, sender and owner IDs with
trusted values from your OpenClaw deployment:

Until those IDs are established, use `"ownerMappings":[]`; the plugin will
load but cannot ingest any sender's images. A dedicated unbound Librarian
agent/profile is declared at `agents/librarian/agent.yaml` and
`agents/librarian/profile/`. Register the OpenClaw agent separately with
`openclaw agents add librarian --non-interactive --workspace
~/.openclaw/workspace-librarian --model MODEL_ID`, leaving channel bindings
empty until routing is decided.

```bash
openclaw config set plugins.entries.pap-librarian-intake.config '{"repoRoot":"/absolute/path/to/personal-agent-platform","stateRoot":"/absolute/path/to/personal-agent-platform/var/librarian","ownerMappings":[{"channelId":"telegram","accountId":"my-bot","senderId":"my-user-id","ownerId":"owner_local"}]}' --strict-json
openclaw plugins enable pap-librarian-intake
openclaw plugins inspect pap-librarian-intake --runtime --json
```

`stateRoot` must stay outside Git. The Gateway process needs read access to
its staged media and write access to `stateRoot`. The Python bridge uses the
repository's `jsonschema` and Pillow dependencies; set the optional `python`
plugin config field if the Gateway's default `python3` lacks them.

Run local tests:

```bash
node --test agents/librarian/openclaw-plugin/test.mjs
PYTHONPATH=. python3 -m pytest tests/test_librarian_gateway_bridge.py -q
```

This hook accepts original bytes and creates a capture receipt. Extraction is
a later step and still needs a production vision adapter and real annotated
photos for the v0.8 M1 acceptance test. The official OpenClaw
[message hook contract](https://docs.openclaw.ai/plugins/hooks/messages)
defines the staged `media` fields used here.
