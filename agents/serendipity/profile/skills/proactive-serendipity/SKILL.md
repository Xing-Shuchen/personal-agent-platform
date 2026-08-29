# Proactive Serendipity

Use this skill only for scheduled or event-triggered serendipity evaluation.

Procedure:

1. Inspect recent personal-context evidence since the previous meaningful evaluation window.
2. For each strong recent concept/event, retrieve older material from deliberately different time ranges and domains.
3. Generate a small candidate set. Do not optimize recall.
4. Reject candidates that are:
   - obvious;
   - purely lexical;
   - already stated by the user;
   - unsupported by concrete evidence;
   - merely "X is like Y" without a useful structural correspondence.
5. For surviving candidates, assign:
   - novelty 0..100;
   - personal relevance 0..100;
   - evidence strength 0..100;
   - surprise 0..100.
6. Choose at most one candidate.
7. Create a stable dedupe key from the two concepts/events, not from message wording.
8. Call the shared gate (absolute paths — cron sessions have no repo cwd):

   `/home/xingzeng/personal-agent-platform/.venv/bin/pap gate --agent serendipity --dedupe-key '<key>' --priority <0..100> --message '<candidate message>' --db /home/xingzeng/personal-agent-platform/var/state/gate-state.json`

9. If gate denies, final response must be exactly `[SILENT]`. Same for a zero-candidate run with no gate call: the ENTIRE final response must be the single marker `[SILENT]` — no summary, no rejection notes, no「保持静默」prose. Hermes suppresses delivery only when the whole response is exactly the marker; any surrounding text makes it a normal delivery. Record rejected candidates and categories in the local audit file `/home/xingzeng/personal-agent-platform/var/state/serendipity-audit.jsonl` (one JSON line per run) instead.
10. If gate allows, output only a concise user-facing observation containing:
    - the connection;
    - why it is structurally interesting;
    - enough evidence anchors to make it inspectable.

Do not mention the gate, score, cron, or internal procedure to the user.

## Output language

The final user-facing observation MUST be in Chinese (simplified). Evidence anchors (paths, identifiers, quotes) stay in their original language.
