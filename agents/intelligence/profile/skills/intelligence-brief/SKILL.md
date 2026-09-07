# Intelligence Brief

## Fixed evidence paths and search boundary

This job has a fixed local evidence boundary. Use only:

- Intelligence memory: `/home/xingzeng/.openclaw/workspace-intelligence/memory/YYYY-MM-DD.md`
  for today and the previous four dates only.
- Gate state: `/home/xingzeng/personal-agent-platform/var/state/gate-state.json`
- Gate log: `/home/xingzeng/personal-agent-platform/var/state/gate-log.jsonl`
- Recent user context: up to three `session_search` calls, restricted to the current scan window.
- External developments: `web_search`/`web_fetch` only for a concrete watchlist or
  open-question candidate, using authoritative sources.

Do not discover paths at runtime. Construct the exact dated memory filenames;
do not list the workspace. Never run `ls`, `find`, or broad `rg` against
`/home/xingzeng`, `/`, `.hermes`, `.openclaw`, a whole repository, or system
logs. Do not inspect Hermes/OpenClaw logs, git history, automation state, or
unrelated files unless the current watchlist item explicitly names that exact
path. Missing fixed files are simply skipped. Limit each run to five memory
files, three session searches, ten external candidates, and fifteen read/search
tool calls total; stop once one evidence-backed candidate is ready or no
candidate remains.

Scheduled procedure:

1. Inspect watchlists, open questions and prior alert history.
2. Collect developments since the previous scan window from appropriate authoritative sources.
3. Cluster duplicate coverage into underlying events/claims.
4. Compare each development with personal context:
   - does it answer an unresolved question?
   - alter a prior belief?
   - affect an active project?
   - create a new high-value opportunity/risk?
5. Reject generic relevance based only on keyword overlap.
6. Select at most one interruption-worthy item per run.
7. Create a stable dedupe key for the underlying development.
8. Call (absolute paths — cron sessions have no repo cwd):

   `/home/xingzeng/personal-agent-platform/.venv/bin/pap gate --agent intelligence --dedupe-key '<key>' --priority <0..100> --message '<brief>' --db /home/xingzeng/personal-agent-platform/var/state/gate-state.json`

9. If denied or no worthy item exists, output exactly `[SILENT]`.
10. If allowed, output a compact brief:
    - what changed;
    - why it matters specifically;
    - what prior question/belief/project it connects to;
    - source/evidence references;
    - uncertainty if material.

Do not produce a ten-item news list unless explicitly asked.

## Output language

The final brief MUST be written in Chinese (simplified). Source titles, evidence anchors and identifiers stay in their original language.
