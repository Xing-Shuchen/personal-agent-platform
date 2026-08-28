# Intelligence Brief

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
