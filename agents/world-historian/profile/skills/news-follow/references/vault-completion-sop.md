# Vault completion SOP

A follow or capture run that wrote or changed any vault file must finish this
before returning. Skip it only when no vault file changed.

Governing skills:

- `/home/xingzeng/.openclaw/workspace-feishu3/skills/obsidian-remotely-save-sync/SKILL.md`
  — trigger, fallback, and the COS verification script.
- `/home/xingzeng/.openclaw/agents/feishu3/agent/workshop-skills/vault-annotation-guard/SKILL.md`
  — the pre-commit 「手工批注」 guard for regenerated projections.

Order (2026-09-02 rule: remote first, then local, then remote again):

1. Trigger the Remotely Save pull with the Obsidian CLI (`HOME=/home/xingzeng`)
   and verify with `verify_sync_diff.py`; ignore `_debug_remotely_save/` entries.
2. Run the annotation guard for every changed file: compare its 「手工批注」
   section with the `HEAD` version and restore the text from git when a file
   lost its annotation (a whole-file diff hides this).
3. Commit the vault changes grouped by theme with Chinese messages and explicit
   `git add <path group>`; never one big commit across themes.
4. Push.
5. Trigger Remotely Save again and verify the objects landed on COS.