# Maintenance log

## 2026-09-09 — PAP scheduling consolidation and runtime hygiene

### Scheduling architecture

- PAP agent declarations in `agents/*/agent.yaml` are the source of truth for
  PAP jobs. The system crontab invokes `pap tick` once per minute.
- PAP executes scheduled work through the OpenClaw Gateway and delivers
  user-facing output through the OpenClaw Feishu `feishu4` account. PAP uses
  exact `NO_REPLY` as the intentional-silence marker.
- Do not create OpenClaw automations for PAP work. Existing OpenClaw
  automations remain reserved for unrelated operational or personal tasks.

### Model assignments

- PAP `intelligence-pulse` and `serendipity-pulse` use `zai/glm-5.3`.
  Gateway connectivity was verified on 2026-09-09.
- Other PAP agents use
  `deepseek/deepseek-v4.1-flash-expires-on-0910`.
- All OpenClaw `agentTurn` automations explicitly use
  `deepseek/deepseek-v4.1-flash-expires-on-0910`.
- A one-shot OpenClaw reminder is scheduled for 2026-09-10 09:00
  Asia/Shanghai, executed and delivered through the OpenClaw `feishu3`
  profile/account. It reminds the user to replace the expiring DeepSeek model
  and must not modify configuration itself.

### Hermes and OpenClaw operations

- Only `hermes-gateway-feishu1.service` is enabled and active. Other Hermes
  gateway services are disabled.
- The hourly `hermes-db-watch` OpenClaw automation checks only the feishu1
  profile: its `state.db`, `hermes-gateway-feishu1.service`, and recent
  feishu1 gateway/error logs. It is silent unless a new anomaly is found.
- OpenClaw non-PAP automations include diary reminders, personal-history
  collection, health monitoring, one-shot reminders, and skill-collection
  reviews. `skill-collection-review-feishu2` is currently expected to fail
  because that writable skill collection exceeds OpenClaw's 240 KB review
  limit; it is not a PAP workload and has no user delivery.

### World Historian

- Added Chronicle migration `0004_thread_background_priority` so the
  biweekly `world-follow-background` job can use the `background` priority.
- `world-follow-*` jobs share a strict delivery contract: no material event or
  claim correction means exact `NO_REPLY`; a material update reports the
  affected thread and event, then lists all active tracked threads. Lifecycle
  demotions/closures and operational read failures are silent.
- Added a privacy-bounded local personal lookup adapter for `world-crosslink`.
  It reads only the three approved personal observation exports, returns
  redacted candidate metadata, filters existing links, and never exposes raw
  personal text to the model.

### Verification

- Repository test suite: `97 passed` after the final PAP configuration and
  World Historian delivery-contract changes.
