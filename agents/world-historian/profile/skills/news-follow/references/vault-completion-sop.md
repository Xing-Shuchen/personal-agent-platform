# Optional local vault projection

The Chronicle database is authoritative. The projection directory is configured
machine-locally in `var/config/world-historian.yaml` (`vault_dir`). On this
machine it is:

```
/home/xingzeng/文档/Obsidian/Second_Brain/2Area/41 新闻及事件
```

Scheduled pap runs project touched threads automatically because the runtime
reads this machine-local file; Gateway-hosted exec does not inherit `PAP_*`
variables from the `openclaw agent` process. When files are written, preserve
the manual annotation section and report errors through local run records.
Do not commit, push, or invoke an external sync service automatically.

## Hard rules (2026-11-22 incident fix)

1. **Never pass `--db` to `store-bundle` or `sync`.** The mandatory `--db` in
   `SKILL.md` applies to read-only queries such as `feeds recent` only. With
   `--db`, the runtime skips the built-in vault projection
   (`"skipped": true, "reason": "non-default --db without
   WORLD_HISTORIAN_VAULT_DIR"`). Without `--db`, the CLI uses the same default
   database AND projects automatically through the config above.
2. **Never set `WORLD_HISTORIAN_VAULT_DIR` to the vault root**
   (`…/Second_Brain`). The environment variable overrides the config, and
   pointing it at the root renders thread notes and `原文素材/` into the vault
   root instead of `2Area/41 新闻及事件/`. If an env override is truly
   unavoidable, copy the exact `vault_dir` value from
   `var/config/world-historian.yaml` — do not improvise a path.
3. If a `store-bundle` result shows `"skipped": true` for the reason above,
   re-run the same bundle **without `--db`**, or re-render the touched threads
   with `cli.py sync --thread <id>` (also without `--db`). Do not "fix" the
   skip by exporting a vault-root env var.

Incident record: on 2026-11-15 03:48 (follow-normal) and 2026-11-20 15:38
(follow-high), runs set `WORLD_HISTORIAN_VAULT_DIR` to the vault root and
rendered 11 stale thread notes + 93 `原文素材` files there. The duplicates
propagated to COS via Remotely Save and were removed on 2026-11-22 (local
backup: `/tmp/vault-root-dupes-20261122/`). Canonical notes in
`2Area/41 新闻及事件/` were unaffected.
