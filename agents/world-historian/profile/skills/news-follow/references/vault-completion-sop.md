# Optional local vault projection

The Chronicle database is authoritative. Configure the local Obsidian projection
in `var/config/world-historian.yaml` with `vault_dir: <absolute vault area path>`
or set `WORLD_HISTORIAN_VAULT_DIR`. The environment variable takes precedence;
an explicit empty value disables projection. If neither is configured, skip
vault work. Scheduled pap runs project touched threads automatically because
the runtime reads this machine-local file; Gateway-hosted exec does not inherit
`PAP_*` variables from the `openclaw agent` process. When files are written,
preserve the manual annotation section and report errors through local run
records. Do not commit, push, or invoke an external sync service automatically.
