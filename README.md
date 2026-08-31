# personal-agent-platform

个人 Agent 平台：声明式 `pap/v1` agent spec、统一调度与 Run 审计、共享主动门控，以及按 Agent 隔离的长期状态。

## 分层

```text
agents/<name>/agent.yaml       Agent 能力、profile 与 job 声明
agents/<name>/profile/         SOUL.md、config、distribution、skills
agents/<name>/runtime/         可选的确定性领域代码（事务、去重、migration）
pap/                           平台原语：spec、scheduler、Run、gate、CLI
var/state/                     平台运行状态与 append-only 日志（不进 git）
var/<agent>/                   Agent 的真实长期状态（不进 git）
```

`pap` 不理解 Claim、Event 或 Thread；这些是 World Historian 的领域概念。新闻数据库位于 `var/world-historian/chronicle.sqlite`，不属于 profile，也不会进入 Git。

## Agents

| Agent | 职责 | 主动性 |
|---|---|---|
| `serendipity` | 跨时间、跨领域的罕见证据关联 | every 4h |
| `intelligence` | 只报告会更新世界模型的外部进展 | every 1h |
| `red-team` | 论证、设计和假设的对抗性审查 | 关闭 |
| `world-historian` | 把外部变化保存为来源、可修订 Claim、Event 与长期 Thread | follow / reflect / crosslink / report |

## 快速开始

```bash
make setup
make validate
make test

pap agents
pap jobs
pap status
```

安装器只复制 profile 与 skills，不创建 Hermes cron：

```bash
.venv/bin/python scripts/install_agents.py --list-only
.venv/bin/python scripts/install_agents.py --apply --hermes-profile <profile>
```

## 调用 Agent

```bash
pap invoke world-historian news-capture "Mojo 全部开源"
pap invoke world-historian news-follow --arg priority=high
pap runs --agent world-historian
pap runs <run_id>
```

`pap invoke` 从 repo profile 目录运行 Hermes：SOUL 由工作目录加载，指定 skill 的完整指令被作为可信 profile guidance 注入。每次调用在 `var/state/runs.jsonl` 写入 `run.started` 与 `run.completed`；输入仅记录哈希和长度，不把私人原文复制进全局 Run 日志。

## 平台调度

所有 schedule 留在 `agent.yaml`，唯一调度入口是：

```bash
pap tick
```

它会在 `var/state/scheduler-state.json` 原子预留到期槽位，再调用对应 profile + skill。重复执行同一分钟不会重复跑；失败 run 延迟 5 分钟后最多重试三次，超过 20 分钟的孤立 reservation 可被回收；停机恢复最多补最近 24 小时内每个 job 的最新一个到期槽位。

先预览当前到期任务：

```bash
pap tick --dry-run
```

调试要点：

- `pap tick --now '<ISO 时间>'` 可显式指定判定时刻，验证某个槽位是否会触发；
- `pap runs <run_id> --json` 查看单次 Run 的完整生命周期与错误信息；
- 在一个 Hermes 交互/定时会话里手工执行 `hermes --oneshot` 会被嵌套会话守卫
  直接吞掉（毫秒级返回 `[SILENT]`，并不调用模型）。调试真实调用链请用干净
  环境（如 `env -i HOME=... PATH=... pap invoke ...`）或直接依赖系统 cron。

系统只需一个每分钟入口。主动投递目标通过部署环境配置，不写进 repo：

```cron
PAP_HERMES_HOME=/home/xingzeng/.hermes/profiles/<profile>
PAP_DELIVERY_TARGET=weixin
* * * * * cd /home/xingzeng/personal-agent-platform && /home/xingzeng/personal-agent-platform/.venv/bin/pap tick
```

`PAP_HERMES_HOME` 选择调用模型、skills 和消息凭据所属的独立 Hermes profile；未设置时使用 Hermes 默认 home。`PAP_DELIVERY_TARGET` 使用 `hermes send --to` 的目标格式，例如 bare platform 或 `platform:chat_id`。返回 `[SILENT]` 的 run 永不投递；`delivery: local` 的 job 只更新本地状态。如果机器上已有旧的 Hermes agent cron，安装器不会擅自删除，迁移到 `pap tick` 后应人工确认并停用旧 job，避免双跑。

## Artifact

跨 Agent 共享的结构化产物写入一个 append-only JSONL（不做消息总线）：

```bash
pap artifact append news.thread.created world-historian \
  --payload '{"thread_id": "thr_abc", "title": "..."}' \
  --provenance '{"run_id": "run_..."}'
pap artifact list --type news.thread.created
```

World Historian 预留的 artifact 类型：`news.thread.created`、
`news.thread.updated`、`news.claim.corrected`、`news.relation.discovered`、
`news.report.generated`。文件位于 `var/state/artifacts.jsonl`（不进 git），
其他 Agent 目前只按类型/生产者扫描读取。

## World Historian

初始化或检查领域库：

```bash
.venv/bin/python agents/world-historian/runtime/cli.py init
.venv/bin/python agents/world-historian/runtime/cli.py stats
.venv/bin/python agents/world-historian/runtime/cli.py search Mojo
.venv/bin/python agents/world-historian/runtime/cli.py thread <thread_id>
```

领域写入使用一个经过验证的 JSON bundle，并在单个 SQLite transaction 中提交：

```bash
.venv/bin/python agents/world-historian/runtime/cli.py store-bundle --json /tmp/capture.json
```

Schema migration 从 `agents/world-historian/runtime/migrations/` 顺序执行。第一版包含 sources、claims、events、threads、entities、relations、interpretations、open questions、watch queries、discovery candidates、reports 和单向 `personal_links`。

PersonalLink 的隐私流向固定为：

```text
public Chronicle event -> local read-only personal lookup -> PersonalLink
```

私人日记、消息或观察默认禁止进入互联网 query、第三方 prompt 或公开日志。

## 共享主动门控

主动投递仍必须经过 gate；不过则输出 `[SILENT]`：

```bash
pap gate --agent world-historian --dedupe-key '<stable-key>' --priority 80 --message '...'
```

规则：白天优先级至少 70，22:00–08:00 至少 90；同一概念 key 七天去重；连续拒绝触发 4h → 8h → 16h → 32h 的退避。全部决策写入 `var/state/gate-log.jsonl`。
