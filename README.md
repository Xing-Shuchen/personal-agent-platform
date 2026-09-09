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

## 2026-09-09:调度统一回归 PAP

所有平台 job 只由 `pap tick` 调度，系统 crontab 每分钟调用一次；
`agents/*/agent.yaml` 是唯一 job 声明源。此前对应的 OpenClaw automation
镜像已删除，禁止重新创建，否则会产生双跑。

OpenClaw 仍可保留与 PAP 无关的独立 automation。技能的单一源仍是本仓库
`agents/*/profile/skills`；运行时使用绝对路径
`/home/xingzeng/personal-agent-platform`。

当前运行链路：

```text
system crontab (每分钟)
  -> pap tick
    -> agents/*/agent.yaml（到期判定、幂等、重试、Run 审计）
      -> OpenClaw Gateway: openclaw agent --agent <agent>
        -> DeepSeek-V4.1 Flash（thinking=low）执行 skill
      -> 最终输出严格等于 NO_REPLY：不投递
      -> 其他输出：OpenClaw Gateway -> Feishu4
```

也就是说，系统 cron 是 PAP job 唯一的触发器；OpenClaw Gateway 只负责
agent 执行和消息投递，不负责 PAP job 的调度。

### PAP job 管理规则

所有 PAP job 的新增、修改、启用、停用和移除，必须在本仓库完成：修改对应
`agents/<agent>/agent.yaml`，再由 `pap tick` 生效。不得为 PAP job 创建、编辑或
恢复 OpenClaw automation；这样可保证 manifest 是唯一真相源，且不会出现双跑。

OpenClaw automation 仅可用于 PAP 范围之外的独立任务。

## 快速开始

```bash
make setup
make validate
make test

pap agents
pap jobs
pap status
```

安装器只将 skills 合并到既有 OpenClaw agent workspace；不创建 OpenClaw automation
或 cron，调度继续由 `pap tick` / `agent.yaml` 负责：

```bash
.venv/bin/python scripts/install_agents.py --list-only
.venv/bin/python scripts/install_agents.py --apply --openclaw-home <path>
```

## 调用 Agent

```bash
pap invoke world-historian news-capture "Mojo 全部开源"
pap invoke world-historian news-follow --arg priority=high
pap runs --agent world-historian
pap runs <run_id>
```

`pap invoke` 从 repo profile 目录运行一个 OpenClaw Gateway turn：SOUL 由工作目录加载，指定 skill 的完整指令被作为可信 profile guidance 注入。每次调用在 `var/state/runs.jsonl` 写入 `run.started` 与 `run.completed`；输入仅记录哈希和长度，不把私人原文复制进全局 Run 日志。

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
- `pap tick --dry-run` 只预览到期任务；它不会调用 OpenClaw 或投递消息。

系统只需一个每分钟入口。主动投递目标通过部署环境配置，不写进 repo：

```cron
PAP_OPENCLAW_BIN=/home/xingzeng/.local/bin/openclaw
PAP_OPENCLAW_CHANNEL=feishu
PAP_OPENCLAW_ACCOUNT=feishu4
PAP_OPENCLAW_DELIVERY_TARGET=<feishu_user_id>
PAP_OPENCLAW_THINKING=low
* * * * * cd /home/xingzeng/personal-agent-platform && /home/xingzeng/personal-agent-platform/.venv/bin/pap tick
```

PAP 通过 OpenClaw Gateway 执行每次 job，并以 `PAP_OPENCLAW_THINKING` 控制思考档位。`delivery: user-home` 也通过同一 Gateway 投递，分别由 `PAP_OPENCLAW_CHANNEL`、`PAP_OPENCLAW_ACCOUNT` 和 `PAP_OPENCLAW_DELIVERY_TARGET` 指定渠道、账号和收件人。最终响应严格等于 `NO_REPLY` 的 run 永不投递；`delivery: local` 的 job 只更新本地状态。

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

### Obsidian 同步（2Area/41 新闻及事件）

每个 Thread 对应 vault 中 `2Area/41 新闻及事件/` 下的一个 Markdown 文件，作为
数据库的投影**覆盖式**再生成——数据库是唯一事实源：

- **触发规则**：只有 bundle 新建或修改了 Thread（thread 本体、挂接事件、
  主张变化、开放问题/监视查询、thread 端点 relation）才写文件；纯
  discovery candidate 等不触及 Thread 的提交不产生任何文件写入。
- `store-bundle` 在事务**提交成功后**自动同步被触及的 Thread（回滚则不写）；
  `--no-sync` 可跳过。
- `runtime/cli.py sync` 可从数据库全量重建（`--thread <id>` 限定单个）。
- 文件 frontmatter 带 `thread_id`，重命名 Thread 时文件自动迁移；目标名
  被无关文件占用时换用带 ID 后缀的名字，绝不删除非本 Thread 的文件。
- 文末「手工批注」一节供人工批注，重新同步时原样保留；其余机器生成部分
  请勿手工编辑。
- 同步索引位于 `var/world-historian/obsidian-index.json`（不进 git）。
- 目标目录可用 `WORLD_HISTORIAN_VAULT_DIR` 覆盖，设为空字符串则完全关闭同步。

PersonalLink 的隐私流向固定为：

```text
public Chronicle event -> local read-only personal lookup -> PersonalLink
```

私人日记、消息或观察默认禁止进入互联网 query、第三方 prompt 或公开日志。

## 共享主动门控

主动投递仍必须经过 gate；不过则输出 `NO_REPLY`：

```bash
pap gate --agent world-historian --dedupe-key '<stable-key>' --priority 80 --message '...'
```

规则：白天优先级至少 70，22:00–08:00 至少 90；同一概念 key 七天去重；连续拒绝触发 4h → 8h → 16h → 32h 的退避。全部决策写入 `var/state/gate-log.jsonl`。
