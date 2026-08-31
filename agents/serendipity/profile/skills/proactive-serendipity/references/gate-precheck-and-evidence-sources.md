# Gate pre-check and evidence sources — proactive-serendipity

## Step 1 evidence sources (what actually worked)

The skill says "inspect recent personal-context evidence" without naming files. In this deployment the inspectable evidence is:

| Source | Path / tool | What it gives |
|---|---|---|
| Gate state | `/home/xingzeng/personal-agent-platform/var/state/gate-state.json` | `agents.serendipity.delivered` (key → ts): what was already surfaced and is inside the 168h dedupe TTL; `agents.serendipity.attempts` tail: last attempt, allowed/denied, reason (backoff math) |
| Gate log | `/home/xingzeng/personal-agent-platform/var/state/gate-log.jsonl` | `message-preview` lines: full text of prior candidate messages — a denied candidate's idea is already on record, so check it against TTL/backoff state before re-deriving it |
| Session DB | `session_search` (FTS5) | Recent user-authored messages, decisions, open questions |
| Cross-domain older material | Other active repos, e.g. `~/personal-historian-handoff` (docs/PRINCIPLES.md, docs/DECISIONS.md, `historian/derivation/engine.py`, daily-collection commit history) | The deliberately-different-time/different-domain material step 2 asks for |
| Obsidian Second Brain vault | `/home/xingzeng/文档/Obsidian/Second_Brain/Dairies/<YYYY>/YYYY-MM-DD.md` (ethnography-daily, e.g. `Dairies/2026/2026-08-29.md`) | Richest personal-context source: YAML frontmatter carries `sleep_hours`, `day_type`, `threads`, `people`; body sections 对影成/怪现状/观自在 carry open questions and self-interpretations usable as concept pairs |
| Obsidian Second Brain vault (domains) | `2Area/` topic files, e.g. `2Area/10 健康与体能/训练记录.md` | Domain state for cross-domain pairing (health logs, projects, interests) |
| Obsidian WeRead highlights | `2Area/WeRead Notes/<书名>.md` (e.g. `中国历史地理十五讲.md`, 📌 highlight lines; plugin-synced, mtimes can be months old) | The "deliberately different time range" vein for step 2: an old reading highlight pairs with a fresh diary event (worked 2026-08-30: May 高亮 × 8-29 diary 敕勒歌 → 战败叙事 structure). `rg` the vault for topical keys to find these |

## Zero-candidate runs: silence without gate calls

An allowed last attempt means no backoff is active — but that does not oblige a gate call. If the best honest candidate cannot reach the active priority bar (≥90 in quiet hours, ≥70 daytime), calling the gate is a guaranteed denial that escalates the floor and harms the NEXT run. With the 240m serendipity cadence, up to three consecutive runs land inside quiet hours (e.g. 22:37 → 02:43 → 06:43): a doomed call at 02:43 sets the floor to ~06:43+ and, since 06:43 is still quiet hours, the next honest shot effectively slides past the 08:00 daytime boundary. Correct action: append one JSON line recording the rejected candidates and their categories (obvious / purely lexical / already stated / unsupported) to the local audit file `/home/xingzeng/personal-agent-platform/var/state/serendipity-audit.jsonl` (e.g. `{"ts": "...", "window_since": "...", "rejected": [{"pair": "a+b", "category": "obvious"}], "gate_calls": 0}`), make zero gate calls, and end the run with a final response of exactly `[SILENT]`.

**Silence contract (hard rule).** Hermes suppresses delivery ONLY when the ENTIRE final response is exactly one silence marker — `[SILENT]`, `SILENT`, `NO_REPLY`, `NO REPLY` — canonicalized and ≤64 chars (see `gateway/response_filters.py: is_intentional_silence_response`). Any prose before/after the marker — an evaluation summary, rejection categories, or a Chinese「保持静默」note — makes the message a normal delivery. Never write explanations in the final response of a silent run; the audit file is the only record. Observed failure (2026-08-30 02:43 run): the model wrote a full rejection-report paragraph instead of the marker and the "silent" run was delivered to the user. Denial-free silence costs nothing — the dedupe TTL is only consumed by allowed deliveries, so a rejected-later-in-daytime candidate stays fully alive.

## Gate pre-check before any `pap gate` call

A submission during an active denial-backoff window is **guaranteed-denied AND escalates the silence floor**. From `personal-agent-platform/pap/gate.py` `decide()`: floor = min(4 · 2^(streak−1), 32) hours, where streak counts trailing denied attempts for the agent. A doomed call is worse than a wasted call — it pushes future delivery further out.

Pre-check recipe (read-only, no gate interaction):

1. Read `agents.serendipity.attempts` tail from gate-state.json.
2. Last attempt **allowed** → no backoff applies; proceed to the normal gate call (step 8 of the skill).
3. Last attempt **denied** → streak = trailing denied attempts; floor = min(4 · 2^(streak−1), 32) h; floor_until = last attempt ts + floor.
4. now < floor_until → end the run `[SILENT]` **without calling the gate**. No priority is high enough to pass: the backoff check runs before the priority bar and is priority-independent.

   **Compute floor_until arithmetically — never eyeball it.** Observed failure (2026-08-30 11:14 run): the attempts tail showed the last denial at "07:02" and the model assumed the 4h floor had long passed — but the denial was 07:02:43 and the streak was already 2 (the 07:01 quiet-hours denial before it), so floor was 8h → floor_until 15:02:43. The doomed gate call was denied in-floor, streak went 2→3, floor became 16h, pushing the next legitimate daytime shot into the 15:02–22:00 window. Verify with a one-liner before ANY gate call:
   `python3 -c "from datetime import datetime,timedelta; last=datetime.fromisoformat('<last-denied-ts>'); floor_h=<floor>; print(last+timedelta(hours=floor_h), 'elapsed:', datetime.now().astimezone()>=last+timedelta(hours=floor_h))"`.
   The tail shows only the last attempt: the streak (and hence floor length) counts ALL trailing denials — consecutive cron runs each landing a denial double the floor every time.

## Worked example (2026-08-29 02:16 CST)

State read: attempts tail = 17:27:21 denied (dedupe: key delivered 0.0h ago), 22:00:59 denied (quiet-hours: priority 85 < 90). Trailing denials = 2 → floor = 4·2¹ = 8h from 22:00:59 → floor_until 06:00:59. Run started 02:16 — inside the floor. Correct action: `[SILENT]`, zero gate calls. A naive submission (the cron fires every 4h, so one was "due") would have been denied → streak 3 → floor 16h → serendipity silent until ~14:00.

Floor elapsed ≠ clear to call. The backoff window and the quiet-hours bar are independent gates, and they can decouple: e.g. last denial 22:00:59, streak 2 → floor_until 06:00:59; a run at 06:18 finds the floor elapsed but is still inside quiet hours (22:00–08:00, bar ≥90). If the best honest candidate scores 70–89 (the 22:00 held candidate scores 85), a call now is still guaranteed-denied and would step the streak to 3 → 16h floor, destroying that candidate's 08:00+ daytime shot. Pre-check must therefore pass BOTH conditions: floor elapsed AND (daytime OR honest priority ≥90). In the 06:00–08:00 decoupled gap, hold — every-4h scheduling lands the next run in daylight.

Note the denied 22:00 candidate (honest priority 85, quiet-hours bar 90): a quiet-hours denial does **not** consume the dedupe TTL — only allowed deliveries set `delivered[key]`. After the floor elapses, that candidate can pass in daytime (bar ≥70) at its honest score. Keep the honest score; never inflate priority to beat a time-of-day bar — the gate auto-detects quiet hours from local time, so inflating only games the audit log, and the whole system runs on the audit log.

## Dedupe key hygiene

- Key the concept pair, not the wording (`gate-silence+absence-coverage-licensing`, not a phrase from the message).
- The `delivered` map is the TTL source of truth: a key present there is silenced for 168h regardless of how differently the new message is phrased.
- An allowed attempt resets the denial streak; after a floor elapses, one honest passing call clears the ladder.

## Rejection-category discipline (step 4 of the skill)

Tag every discarded candidate with the exact category it fails — this is what makes a zero-delivery run auditable in the local audit file (`serendipity-audit.jsonl`), **not** in the user-facing response. Worked examples (2026-08-30 02:43 run, quiet hours):

- Health-consultation topic (tadalafil + hot bath, session `20260829_223919_ee6cd61d`) × consecutive sleep debt (Dairies 8-28: 凌晨两三点睡/5h) + next-morning drive → the "be careful with BP/fatigue before driving" add-on is the obvious extension of the consult's own risk section → **obvious**.
- Location pun: user was literally staying in 热水塘镇 while asking about hot-bath interaction → **purely lexical**.
- Diary thread 把个人事务交给 Agent quietly extending into health/body domain → the diary's own 对影成 section already predicts the extension into controlling the physical world → **already stated** (self-predicted by the user).
- Reusing any pair already listed in `agents.serendipity.delivered` under a new paraphrase → silenced by TTL before scoring; check the delivered map first.

Rejection test order that worked in practice: delivered-map TTL → category screen (obvious first — it kills the most) → only then score survivors. Scoring candidates that would fail the category screen wastes the run.
