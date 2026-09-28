#!/usr/bin/env bash
# 每日把 Chronicle 库（world-historian）的一致性快照同步进 Obsidian vault，
# 并按 vault SOP 完成「先拉 → 提交推送 → 后同步」。
#
# 纯脚本、无 LLM 调用。由 pap 以 runner: command 调度
# （job: world-historian/world-chronicle-snapshot，见 agents/world-historian/agent.yaml）。
# 手工执行：/home/xingzeng/personal-agent-platform/scripts/sync_chronicle_snapshot.sh
set -uo pipefail

PAP_ROOT=/home/xingzeng/personal-agent-platform
LIVE_DB="$PAP_ROOT/var/world-historian/chronicle.sqlite"
VAULT=/home/xingzeng/文档/Obsidian/Second_Brain
REL=4Archive/world-historian
DEST="$VAULT/$REL/chronicle.sqlite"
REAL_HOME=/home/xingzeng
OBSIDIAN_CLI="$REAL_HOME/.local/bin/obsidian"
PY=/home/xingzeng/.hermes/hermes-agent/venv/bin/python
LOG="$PAP_ROOT/var/state/chronicle-snapshot.log"
LOCK=/tmp/chronicle-snapshot.lock

export HOME="$REAL_HOME"
# cron 的最小环境里没有 ~/.local/bin（git-lfs 在那里），补上路径
# 否则 vault 的 LFS pre-push 钩子会失败、push 被拒。
export PATH="/home/xingzeng/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

log() { printf '%s %s\n' "$(/usr/bin/date '+%F %T%z')" "$*" >>"$LOG"; }
say() { printf '%s\n' "$*"; log "$*"; }

# 单实例锁：重叠的 tick 不并行跑
exec 9>"$LOCK" || exit 1
/usr/bin/flock -n 9 || { say "SKIP 另一实例持有锁"; exit 0; }

TMP="$(/usr/bin/mktemp /tmp/chronicle-snap.XXXXXX.sqlite)"
trap 'rm -f "$TMP"' EXIT

# 1) 一致性快照：.backup 走 SQLite 备份 API，避免抓到半写状态
if ! /usr/bin/sqlite3 "$LIVE_DB" ".backup '$TMP'"; then
  say "FAIL sqlite .backup 失败（源库：$LIVE_DB）"; exit 1
fi
NEW_SUM="$(/usr/bin/sha256sum "$TMP" | /usr/bin/cut -d' ' -f1)"
OLD_SUM=""
[ -f "$DEST" ] && OLD_SUM="$(/usr/bin/sha256sum "$DEST" | /usr/bin/cut -d' ' -f1)"

if [ "$NEW_SUM" = "$OLD_SUM" ]; then
  say "OK 快照无变化 sha=${NEW_SUM:0:12}，跳过提交与同步"; exit 0
fi

# 2) 先拉：vault SOP 的「先远后本」，避免 git 先固化旧本地状态
"$OBSIDIAN_CLI" command id=remotely-save:start-sync >/dev/null 2>&1 \
  || say "WARN Remotely Save 拉取触发失败（应用可能未运行，继续）"
/usr/bin/sleep 25

# 3) 落盘快照
cp -f "$TMP" "$DEST" || { say "FAIL 复制快照到 vault 失败"; exit 1; }

# 4) 提交 + 推送（只涉及本目录）
git -C "$VAULT" add -- "$REL/chronicle.sqlite" "$REL/README.md" \
  || { say "FAIL git add 失败"; exit 1; }
if git -C "$VAULT" diff --cached --quiet; then
  say "OK 无待提交变更"
else
  git -C "$VAULT" commit -q -m "db(world-historian): chronicle.sqlite 快照更新 $(/usr/bin/date '+%F')" \
    || { say "FAIL git commit 失败"; exit 1; }
  if git -C "$VAULT" push -q origin main; then
    say "OK 已推送 git $(git -C "$VAULT" rev-parse --short HEAD)"
  else
    say "FAIL git push 失败"; exit 1
  fi
fi

# 5) 后推：把 git 产生的变更同步上 COS
"$OBSIDIAN_CLI" command id=remotely-save:start-sync >/dev/null 2>&1 \
  || say "WARN COS 同步触发失败（应用可能未运行）"

# 6) 核验 COS 落盘（最多等 150s）
NEW_SIZE="$(/usr/bin/stat -c%s "$DEST")"
for i in $(/usr/bin/seq 1 6); do
  if "$PY" - "$NEW_SIZE" <<'PY' 2>/dev/null
import base64, json, sys
import boto3
from botocore.config import Config
want = int(sys.argv[1])
vault = '/home/xingzeng/文档/Obsidian/Second_Brain'
d = json.load(open(f'{vault}/.obsidian/plugins/remotely-save/data.json'))['d']
cfg = json.loads(base64.b64decode(d[::-1] + '=' * (-len(d[::-1]) % 4)))['s3']
s3 = boto3.client('s3', endpoint_url=cfg['s3Endpoint'], region_name=cfg['s3Region'],
                  aws_access_key_id=cfg['s3AccessKeyID'],
                  aws_secret_access_key=cfg['s3SecretAccessKey'],
                  config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'}))
r = s3.head_object(Bucket=cfg['s3BucketName'], Key='4Archive/world-historian/chronicle.sqlite')
sys.exit(0 if r['ContentLength'] == want else 1)
PY
  then
    say "DONE 快照已同步 git + COS（$NEW_SIZE B, sha=${NEW_SUM:0:12}）"; exit 0
  fi
  /usr/bin/sleep 25
done
say "WARN 已提交推送，但 COS 未在 150s 内确认到新尺寸（$NEW_SIZE B）——检查 Obsidian/Remotely Save"
exit 0