---
name: chronicle-snapshot
description: 每日把 Chronicle 库的一致性快照同步进 Obsidian vault（git + Remotely Save COS）。纯脚本任务，无 LLM 调用。
---

# Chronicle 快照同步（world-chronicle-snapshot）

**这是 runner: command 的脚本任务**（`agents/world-historian/agent.yaml` 的
`world-chronicle-snapshot`），本 SKILL.md 只作说明与排障参考——pap 不会为本任务
构建提示词，也不调用模型。

脚本：`scripts/sync_chronicle_snapshot.sh`

## 做什么

1. `sqlite3 <实时库> ".backup /tmp/chronicle-snap.*.sqlite"` 取**一致性快照**
   （实时库 `var/world-historian/chronicle.sqlite` 因 pap `.gitignore`（`/var/*`、`*.sqlite`）不入 git）。
2. 与 vault 内旧快照 sha256 比对：**相同即退出 0**（不产生空提交）。
3. vault SOP「先远后本」：`HOME=/home/xingzeng obsidian command id=remotely-save:start-sync` 拉远端 → 落盘快照。
4. `git add -- 4Archive/world-historian/{chronicle.sqlite,README.md}` → 中文提交 → `git push origin main`。
5. 再次触发 Remotely Save 同步；随后 6×25s 轮询 COS，确认对象尺寸等于本地尺寸。
6. 全程追加日志到 `var/state/chronicle-snapshot.log`（`OK/SKIP/DONE/FAIL/WARN` 前缀）。

## 手工执行 / 排障

```bash
# 直接跑脚本（幂等：无变化即跳过）
/home/xingzeng/personal-agent-platform/scripts/sync_chronicle_snapshot.sh

# 走 pap 的 job 路径（等同调度触发）
cd /home/xingzeng/personal-agent-platform
.venv/bin/pap job run world-historian world-chronicle-snapshot

tail -20 var/state/chronicle-snapshot.log
```

## 坑

- **手工用 boto3 查 COS 必须 `Config(signature_version='s3v4', s3={'addressing_style':'virtual'})`**：
  默认 path-style 会报 `PathStyleDomainForbidden`，看起来像「对象不存在」，极易误判成
  Remotely Save 没上传。
- **Remotely Save 需要 Obsidian 应用在运行**；应用没跑时脚本只记 `WARN`（git 腿照常完成，
  文件留在本地，应用下次自动/手动同步会补upload）。
- 脚本用 `flock` 单实例；重叠 tick 直接 `SKIP`。
- gitcode 侧仓库 LFS 体积已超 2.0 GiB 上限（2026-09-28 告警），后续 push 可能被拒——
  与本任务无关但会一并暴露，遇到时需在项目设置里压缩仓库。