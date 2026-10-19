# 审计后续工作计划（2026-10）

本文承接 2026-10 平台深度审计。当轮已确认并修复的缺陷不在本文重复（见提交
`45f1c5a..HEAD` 的提交说明与各自回归测试）；这里登记**已确认但未修复**的剩余问题、
建议方案与验收标准，按优先级排列。每项标注：影响、建议最小修复、工作量（S/M/L）、风险。

维护规则：完成一项就把它移到文末「已完成」并链接提交；新审计发现按同样格式追加。

---

## P1（影响可靠性/合规，建议尽快）

### 2. librarian `visual_checks` 死代码与契约失实
- **影响**：`gateway_review.py` 恒返回空 `visual_checks`；`gateway_review_finalize.py`
  的 `visual_negative_no_marks` 分支不可达；`profile/SOUL.md` 却指导模型解释该字段，
  openclaw-plugin README（已修正一处）曾声称有视觉模型兜底。模型会向用户描述不存在
  的行为。
- **建议**：三选一并保持三处一致——(a) 从契约、finalize 分支、SOUL.md 中全部移除；
  (b) 用 BookScan report 中已有的检测数据真实填充；(c) 实现裁剪后的多模态复核。
  推荐 (a)（最小、诚实）。
- **工作量**：S。**风险**：低（需同步改 SKILL/SOUL 文案与契约 schema 说明）。
- **验收**：grep 全仓无残留死分支；相关测试更新。

### 3. librarian 桥接层失败无本地诊断日志
- **影响**：`gateway_errors.write_error` 把所有非契约异常脱敏为 `BRIDGE_FAILED`，
  原始 traceback 不落任何介质；插件侧 `child.stderr.resume()` 直接丢弃。生产排障
  （如本轮修复前的数字轨迹 KeyError）只能靠盲猜。
- **建议**：在 `write_error` 内把异常类型+净化 traceback（正则去除 `$HOME` 前缀与
  记录内容）写入 `<stateRoot>/logs/bridge-errors.jsonl`（0600），wire 契约保持脱敏不变。
- **工作量**：S。**风险**：低（新增旁路写入，不改变 stdout 协议）。
- **验收**：注入一个必崩桥接调用后日志文件有可读条目、且不含 vault 路径/记录内容；
  线格式响应与现状逐字节一致。

### 4. world-historian dashboard generations 无清理
- **影响**：每次内容变更生成一个 generation 目录（硬链接复用限制字节数，但目录项/
  inode 无限增长；容量目标 10 万事件时每代 15 万+ dentries）。
- **建议**：`publish()` 指针翻转成功后，按 generation 序号保留最近 N=3 代，其余
  `shutil.rmtree`；清理失败只记日志不影响发布。
- **工作量**：S。**风险**：中（删除逻辑必须永不触碰 CURRENT 指向与构建中的 staging；
  需要针对硬链接共享的测试）。
- **验收**：连续发布 5 次后磁盘上 ≤3+1 代；插件读取不受影响；测试覆盖。

### 5. world-historian projector 硬编码 vault 子目录
- **影响**：`dashboard_projector.py` 将笔记目录固定为 `<vault>/2Area/41 新闻及事件`
  （作者个人 PARA 布局）。其他 vault 布局下 `obsidian_path` 全部失效（「打开源笔记」
  报 Note missing）。
- **建议**：复用 `obsidian.py` 的 vault 目录解析（env `WORLD_HISTORIAN_VAULT_DIR` /
  `var/config/world-historian.yaml`）得到笔记目录；`--vault` 仅作为回退根，子目录名
  进配置（缺省值取通用名而非个人布局）。projector 与 sync_threads 必须解析出同一目录。
- **工作量**：M。**风险**：中（现有部署需在本地配置里补一行，否则链接退化——发布
  说明要写清楚）。
- **验收**：两种布局（根目录直放 / 自定义子目录）下 canonical_ref 往返测试通过；
  tracked 代码不再含个人布局字样。

### 6. 混合 embedding 模型共存（跨模型向量比较）
- **影响**：适配器解释器（系统 python3，无 sentence-transformers）与 CLI 解释器
  （.venv）会向同一 `evidence_embeddings` 写入不同 model_id/维度的向量；本轮已让
  cosine 对维度不匹配返回中性 0.0（不再产生伪相似度），但语义通道在混存期间仍然
  退化，且 `_ensure_embeddings` 只认 transformer model_id，会在哈希嵌入环境下每次
  build 重算全库。
- **建议**：为索引固定单一「当前嵌入模型」（记录在 meta 表）；`_embedding()` 只返回
  该模型的向量；模型切换时触发一次性重嵌入或标记降级。同时统一适配器解释器
  （`PAP_RUNTIME_PYTHON` 指向 .venv，或 `run.py` 在 venv 存在时优先 `sys.executable`）。
- **工作量**：M。**风险**：中（迁移语义要想清楚；先做解释器统一即可消除主要来源）。
- **验收**：交替用两种解释器 build 后，`evidence_embeddings` 只含单一 model_id；
  `_ensure_embeddings` 不再全库重算。

---

## P2（正确性/运维打磨）

### 7. cognition 反馈闭环在生产中是死的（契约先行）
- **现状**：适配器 complete 解析模型回复中的 `{"decisions":[...]}` 信封，但两个
  SKILL 的输出契约（恰好 `NO_REPLY` 或中文正文）从不产生该信封 → `complete_retrieval`
  永远空转；`delivered_connections` 只读不写；`prior_*_penalty` 恒 0；
  `record_rejection` 存原文 anchor 而查询用 digest，永不相遇。相关函数零测试。
- **契约草案（实现前先冻结本文）**：
  - 反馈**不再**走模型回复信封，改为显式 CLI：
    `pap cognition feedback --run-id <PAP_RUN_ID> --agent <id> --decisions <json>`，
    decisions 为数组：`{"evidence_id": "ev_…", "decision": "accepted"|"rejected",
    "anchor_term": "rejected 时必填，小写原词", "reason": "≤200 字，可选"}`。
  - anchor 键约定统一为**原词小写**；`cooldown` 查询侧的 `digest(term)` 与
    `record_rejection` 存储侧二者取一（推荐都存 digest，CLI 入口负责 digest）。
  - `delivered_connections` 写入点：调度器投递成功后（`_deliver` 返回 sent 时）按
    pack 元数据回写；这是跨模块改动，允许分期（阶段 1 只做 rejection/positive）。
  - SKILL 增补：模型在正文明确采用/否决某条连接后调用 feedback CLI；不调用不报错
    （feedback 是 best-effort 学习信号）。
- **工作量**：M（CLI+键约定+测试）；delivered 回写另计 M。**风险**：低（新增旁路）。
- **验收**：端到端测试——shadow_pack → feedback(accepted/rejected) → 下一次
  shadow_pack 的 rank/cooldown 可观测地变化。

### 8. paplog：schema 无强制、ULID 同毫秒不单调、每事件建连开销
- **建议**：
  1. `emit` 对 kind/phase/severity/content_mode 做枚举自检（非法值替换+记
     `paplog.invalid_event`），并新增一个用 `pap.event.v2.schema.json`（已是包数据）
     对采样事件跑 jsonschema 的测试；`observe._Scope.__enter__` 补 32/16-hex 校验。
  2. ULID：进程内单调工厂（同毫秒递增随机段）或在文档明确「排序一律用 seq」。
  3. Ledger 持久连接（进程级）或 schema-once 标记：cognition build 每文件 2 事件、
     双 agent 每天 ~10 次 build，按 2000 文件 vault 估算每天数千次重复 DDL 检查。
- **工作量**：各 S。**风险**：低。
- **验收**：schema 校验测试进 CI；单调性测试；build 事件写入吞吐对比数据。

### 9. bookscan CLI 与缓存键零测试覆盖
- **影响**：`bookscan/cli.py` 的 `read_config` 路径解析、`run` 编排、`_cached_json`
  视觉/OCR 缓存命中逻辑无任何测试；陈旧缓存 bug 会静默复用错误 OCR。
- **建议**：仿照 `tests/test_bookscan.py` 的 FakeOCR 模式，补 tmpdir 级测试：
  config 解析/相对路径锚定、缓存 hit-vs-miss（改图片字节/改代码版本各触发 miss）、
  `--limit/--scan-index` 边界。
- **工作量**：M。**风险**：无（纯增测试）。

### 10. 小型硬化项（各 S，低风险）
- `bitable_handwriting`：外部 Feishu 字段只写错误码/固定文案，内部详情进本地日志。
- `recover.mjs`：channel/account 参数化（env 或 CLI 参数），去 feishu/librarian 硬编码。
- 真实 journal 复制测试（`test_historian_event_cards.py::test_the_real_journal_*`）：
  加 `PAP_TESTS_USE_REAL_JOURNAL` opt-in，避免个人数据落 /tmp。
- `feeds` 与 `store_bundle` 的跨路径 source 去重依赖 published/content_hash 逐字节
  一致（通常不成立）：要么规范化 published 格式与 hash 输入，要么在
  chronicle-bundle.md 明示「同文两行是预期行为」。
- historian：ContextPack 幂等检查前移到 `store.commit(allocate(...))` 之前（每日 no-op
  prepare 不再累积 canonical 修订）；`NO_NEW_THREAD` 否决记忆（按候选集哈希存
  decline 标记）；默认时区 `Asia/Shanghai` 与中文提醒文案配置化。
- scheduler notify 签名读写在锁外（并发 tick 可重复通知一次）：并入 `_locked_state`。
- delivery-queue 损坏时重置为空会丢已批准消息（有 paplog 记录）：损坏文件旁存 `.corrupt`
  备份再重置。
- office-floor：tracked `apps/web/dist` 与 `src` 的漂移防护——CI 加 `npm ci && npm run
  build && git diff --exit-code dist`（或改为不 track dist，文档要求先 build）。
- `fb2080e-scan`：保留 `/usr/bin/scanimage` 钉死（防劫持，文档已解释），可选加
  `SANE_SCANIMAGE` 显式覆盖。
- 工具链统一：`uv.lock` 与 Makefile 的 pip 流程二选一（当前 lock 已随 [test] extra
  再生成，但 Makefile 不用 uv；建议 make setup 检测 uv 并优先 `uv sync --extra test`）。

---

## 不修（记录为设计取舍）

- **DST 边界**：cron 匹配在 DST 时区可能对「重复小时」双触发、「不存在时刻」跳过。
  部署时区无 DST；修复收益低于回归风险。已在 schedule.py 注释说明为宜。
- **RESERVATION_TTL=6h vs 运行超时 4h**：TTL 必须大于最长单次运行，维持现值。
- **append_jsonl 无锁**：单 write() 的 O_APPEND 行在本机文件系统上事实原子；读取侧
  已容忍截断行（本轮修复）。
- **`_ensure_entity` 首个拼写为规范名**：大小写变体归并到首见拼写，别名机制已存在。

---

## 已完成（2026-10 审计轮）

### P1#1. cognition 索引构建移出 runtime prepare/反馈路径

- **原影响**：`PAP_RUNTIME_TIMEOUT_SECONDS` 默认 120s；大 vault 的同步索引构建
  可能超时且事务回滚，导致 intelligence/serendipity 的 slot 反复失败。
- **已实现方案 1+2**：部署文档明确用 `PAP_VAULT` 和 `pap cognition index` 在 runtime
  之外预建/刷新索引（可用定时 command job）。两适配器的 prepare 与模型后反馈均移除
  `Index.build`；prepare 对索引缺失、零有效文档或零有效 evidence 返回 `not_ready`
  并提示 CLI 预建，不再按 vault 文档数设阈值；保留缺失 vault 的就绪提示。反馈直接
  调用 `complete_retrieval`，索引不可用时跳过反馈，保留模型回复与既有 JSON 契约。
- **有意不采用方案 3+4**：不改 `Index.build` 的事务分批方式，也不移动 transformer
  模型加载位置；runtime 不再构建索引，无需为本项修改核心索引逻辑。
- **回归验证**：`tests/test_cognition_runtime.py` 使用临时 vault/索引覆盖两适配器的
  缺失/空索引、已有索引、缺失 vault 与反馈失败；禁止 runtime 调用 `Index.build`。

见提交：`45f1c5a`（取消跟踪）、`5a87476`（core）、`c3d073f`（world-historian）、
`23b012b`（librarian）、`8e736b2`（cognition/paplog/historian）、`45b6704`（模板
去个人化）、`62c6a91`（docs）、`4911606`（CI）。回归测试：
`tests/test_audit_regressions.py`、`tests/test_world_historian_audit_regressions.py`、
`tests/test_librarian_audit_regressions.py`。
