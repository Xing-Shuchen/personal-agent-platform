# Librarian 修改与 specification 一致性审计

审计日期：2026-09-28。审计结论：**部分一致，不满足当前 specification 的完整验收条件。建议暂不发布 release-v0.8。**

领域模型、原图持久化、修订、幂等、统一 ReadingTrace 和隔离检索已具备可验证基础；最近的首本书 worker/OCR 集成引入了规范明确禁止的页码推定、证据范围扩张和会话归属行为。测试通过不能证明这条实际调用链符合规范。

## 1. 审计边界与方法

- 按用户要求，通过 `git log / git show / git diff / git blame` 确定修改范围，而非仅检查工作区差异。
- 基线：`264db03a9b01d23a0b4a95904499c3ac5630e8f4`；首个实现提交：`9000dc0`；被审计 HEAD：`d111acece7870fe7a3fb6d4031e37b82370793a1`。
- 范围 `264db03..d111ace` 共 **40 个提交、71 个文件、15,522 行新增、2 行删除**。审计开始时工作区干净。
- 主要基准：该 HEAD 的 `docs/SPEC_v0.8_Librarian.md`，正文版本为 **Implementation Specification 0.1.0 / Implementation Draft**。文件名中的 v0.8 与契约版本不是同一概念。本报告判断相对该稿的一致性，不推定所有“实现提案”已另行获得批准。
- 核查源代码、调用链、Schema、测试及交接文档；重跑现有 Librarian 专项测试，并用临时目录、合成图片和替身执行故障复现。
- 未调用真实模型、上游 API 或消息发送；未修改生产数据库、Vault 或运行配置。交接文档记载的线上导入数量和现场试验属于既有记录，本次未独立复验。
- `source-design.txt` 和 §38.1 四张标注照片未取得；不能审计缺失底稿的忠实度，也不能给出真实 OCR 准确率结论。

### Git 修改脉络

| 提交 | 变化 | 审计判断 |
|---|---|---|
| `9000dc0` | 引入规格、契约与持久化 pipeline | 方向一致；索引与 trace 提交耦合，见 F08 |
| `9f6f062`、`2a83682`、`09645f8` | affinity、命令、可修订归属、事件 | 单元路径有基础；后续 worker 绕过部分边界 |
| `823b0dc`、`aa9b27e`、`8b7e203` | 原图空间、失败留存、标题冲突 | 有针对性测试 |
| `3abc4f7`、`b606dac`、`bd5da10`、`81d9eb7` | 契约验证、结构搜索、三来源 fixtures | 可证明结构与合成行为；不证明现场验收 |
| `47a87c7`、`b7f54cc` | Gateway 图片接收、映射用户搜索 | 图片入库和检索已连接；会话写命令及证据打开入口待补 |
| `e7a098e`、`70c6e65`、`678cb9a` | 重提取、知识候选与来源修订 | 初期有保护；`4ec1471` 的自动对账未保留全部约束，见 F07 |
| `37732a0` 至 `5d04cfa` 的视觉相关提交 | 可替换视觉端口、超时、裁剪、OpenClaw 路由 | 有底层能力，但当前 worker 不为普通输入选择该通用路径 |
| `da4574e`、`f71abc5`、`87b5c7b`、`8b5b262` | native 数字导入、隔离及搜索验证 | adapter 层有测试；调度配置引入新的隔离风险，见 F05 |
| `41f5332` | 首本书 OCR/EPUB/worker/通知 | F01、F03、F04、F06 主要来源 |
| `4ec1471` | 多页分段、自动对账、数字源调度、Vault 标记 | F02、F05、F07 主要来源；也扩大 F06 影响 |
| `d111ace` | 捕获数字源错误并继续其他来源 | 异常捕获有效；并未消除串行同步对照片处理的等待，见 F06 |

规范本身在 `9000dc0 / 8b7e203 / 3abc4f7 / b606dac / bd5da10` 中有修改。最近三个 worker 提交没有同步修改相关规范边界，不能视为已记录的规格例外。

## 2. 本次验证结果

| 验证 | 结果 | 能证明的范围 |
|---|---|---|
| `.venv/bin/python -m pytest tests/test_librarian*.py -q` | **68 passed**，4 条 RefResolver 弃用警告 | 现有合成测试 |
| `node --test agents/librarian/openclaw-plugin/test.mjs` | **3 passed** | staged media、sender mapping、search tool 授权 |
| `.venv/bin/python agents/librarian/runtime/tests/validate_contracts.py` | **77 定义、18 入口、42 正例、43 反例通过** | 离线契约及选定跨实体约束 |
| `.venv/bin/python docs/audits/librarian_20260928_repro.py` | **6 项缺陷复现成功** | F01/F03/F04/F06/F07/F08 的指定条件 |

复现代码：[librarian_20260928_repro.py](librarian_20260928_repro.py)。结果：[librarian_20260928_repro.json](librarian_20260928_repro.json)。脚本中的断言确认被审计版本的缺陷行为，不能当成整改后的合格测试；修复时应改为下文的期望行为。

## 3. 发现与整改指导

优先级：P1 为影响核心闭环、证据真实性或授权边界，应在对应功能发布前修复；P2 为阶段性功能缺陷，应在启用该功能前修复。以下共 **7 项 P1、1 项 P2**；F05 是多 owner 配置下的条件性风险，不代表本机已发生泄露。

### F01 · P1：普通照片无法进入实际识别闭环

**规范**：§1、§7–9、§26.2、§37；缺书名/页码不得阻止独立视觉观察，应保存 unresolved trace。

**代码与提交**：`41f5332` 引入；当前 `runtime/worker.py:355–360, 380–400`、`openclaw-plugin/index.js:58`。

worker 总是把批次第一张照片交给 `_book_for_cover`，只有它识别出本地 `source-books/<ISBN>.epub` 的 ISBN 才继续。无匹配直接 `continue`，即便已有明确会话，也不调用通用视觉 extractor。没有 Vault 配置时插件甚至不启动 worker。已识别但页码未知的 trace 又在导出前触发整次运行异常。

**复现**：返回“封面无匹配”后，已接受 batch 仍为 `received`，ProcessingRun 数为 0。这不只是准确率待测，而是确定的入口控制流缺口。当前 OCR 路径也未产生 highlight/symbol 检测，不能用它替代 §37 的通用划线、高亮、基础手写闭环。

**整改**：先使用可信提交上下文和受限会话 resolver；每张已接受图片都进入通用提取。EPUB 对齐作为可选增强。未知书籍/页码持久化 partial 及异常队列；将 Vault 导出设为下游可选步骤，不能控制摄取是否执行。

**验收**：分别测试“只有内页”“ISBN 在第二张”“无 EPUB”“已有显式 session”“无 Vault”“未知页码”，均能保存 observation，存在痕迹时生成 trace；无可确认归属时保持 unresolved，且后续批次继续处理。

### F02 · P1：通过相邻照片补页码，并标记为视觉事实

**规范**：§5.5、§13、§26.2 C 明确要求未知页码保持未知，禁止用相邻照片补号；AC-07/10。

**代码与提交**：`4ec1471`；`runtime/ocr.py:309–324`、`runtime/worker.py:380–397`。

worker 把上一 capture 的最后页码传入 `preceding_page`。当前照片首个可见页码之前的区域，若满足 `preceding_page == visible_number - 1`，即写入上一页码、固定 confidence 0.7、`basis=vision`、`status=resolved`。这依赖上传顺序推定当前页区，没有当前区域的独立页码依据；随机顺序、漏拍及非连续页面均可能产生错误个人阅读位置。

**证据级别**：Git diff/blame 与确定分支审查；本次未执行真实 OCR 复现。

**整改**：移除该自动落值。跨照片线索最多作为待确认候选；确认时新增 resolution revision，明确用户依据，保留原 observation。已有受影响结果通过新版本纠正，禁止改写历史。

**验收**：用打乱顺序、前图 39/本图仅可见 40、漏页及重复照片做回归；当前未显示页码的区段必须仍为 null/unresolved，不能因上一图而改变。

### F03 · P1：EPUB 补全文本越过照片证据边界

**规范**：§4、§13、§14.2、§22、§39；trace 引文应对应直接关联的原文区域，推断不能伪装成证据。

**代码与提交**：`41f5332` 引入补句，`4ec1471` 调整分段；`runtime/ocr.py:113–132, 369–402`，`runtime/pipeline.py:454–467`。

`EpubGroundTruth.sentence` 向前后句界扩展，结果直接替换 `printed_regions[].text`，bbox 仍是原行位置；后续还删除延续行的 printed regions。normalizer 又统一把 `printed_text.basis` 写成 `vision`。因此检索出的“画线”可能含照片未拍到或用户未画线的文字，打开 bbox 无法核对整段。raw 仅记录 EPUB hash，trace provenance 未包含对应 EPUB 的可读取、版本固定对象。

**复现**：给补句函数仅传“照片里面恰好拍到了中间这一部分文字”，输出包含合成 EPUB 的“照片之外的前半句”和“照片之外的后半句”。这证明算法会扩大引文，不意味着已判定每条线上 trace 都有错误。

**整改**：trace 只保存有可见区域支持的转录文本及独立区域坐标。EPUB 可辅助纠错，但补充上下文必须单独展示、单独标注来源与 locator，不占用照片引文字段。保留各行 detection；若扩展契约，按 Appendix C 显式升级版本并补迁移 fixture。

**验收**：半句、跨页、EPUB/纸版异文场景中，trace 不能含无法在对应区域验证的补充文本；EPUB 上下文可独立打开；更换 EPUB 文件不得静默复用旧配置身份。

### F04 · P1：自动归属会话被提升为长期显式会话

**规范**：§9–10；自动 affinity 必须遵守 90 分钟/6 小时限制，不能借 active session 绕过过期。

**代码与提交**：`41f5332`，后经 `4ec1471` 修改；`runtime/worker.py:128–132`、`runtime/store.py:252–258, 398–426`。

无用户明确选书时，worker `_catalog` 调用 `start_session(..., scope=scope)`；后者将 `session_scope.selected=1`。`_choose_session` 对 selected active session 无条件继承，不检查时间。原本的自动识别被转换成用户长期选中的上下文。

**复现**：由 `_catalog` 自动建会话后，将 `last_assigned_at` 设为 2000 年；选择器仍返回该会话与 `active_session`。现有 affinity 测试没有覆盖 worker 自动建会话的路径。

**整改**：明确区分“用户选择”与“自动识别”；自动归属只能写非 selected affinity，并记录 capture 的可靠接收时间。仅经可信会话命令允许设置 selected。ISBN 查询也不能无记录地标成已注册 edition fingerprint。

**验收**：从 worker 入口分别推进到 89/91 分钟和 6 小时以上，自动上下文按规范降级；显式选择可持续；不同 owner/account/chat 不继承。

### F05 · P1（条件性）：同一数字书库被导入每个映射 owner

**规范**：§5.1、§10、§27.2、§33；owner 是授权边界，不能先错误归属再依靠查询过滤保证隐私。

**代码与提交**：`4ec1471`；`openclaw-plugin/index.js:57–67, 137–144`、`runtime/worker.py:298–332`。

恢复服务枚举全部 `ownerMappings.ownerId`，但给每个 worker 传入同一份全局 `digitalSources`：相同 Koodo DB、WeRead 凭证与书目列表。同步函数再将数据记到传入 owner 下。配置第二个 owner 后，第一份私人书库会在第二个 owner 名下重新导入，owner-scoped search 将合法地返回错误归属的数据。`source-books` 与 Vault 也共用配置，不能据现有数据库隔离测试宣称整个调度链已支持多用户。

**证据级别**：静态调用链确认；没有创建真实第二用户或进行生产泄露测试。

**整改**：数字 source 必须显式绑定唯一 owner，并在调度和导入边界验证；按 owner 配置 source-books、输出目录与通知路由。若当前产品仅支持单用户，先在配置校验阶段拒绝多 owner，避免对外承诺多用户隔离。

**验收**：插件级双 owner 集成测试：A 的上游记录不能在 B 命名空间生成；B 的检索不命中 A 数据；重新映射来源必须是显式可审计操作。

### F06 · P1：批次错误和数字同步仍会阻塞后续照片处理

**规范**：§7、§26.1–3、§27.4、§37 M1 异常不打断。

**代码与提交**：`41f5332` 的 worker、`4ec1471` 的同步与周期调度、`d111ace` 的异常捕获；`runtime/worker.py:338–411`、`openclaw-plugin/index.js:69–76, 137–145`。

整个 worker 持全局阻塞 flock，先执行所有数字同步，再遍历物理 batch；批次循环没有隔离 catalog/未知页码/Vault 冲突等异常。任意一个 batch 失败会退出并使后续批次饥饿，下一轮仍可能先遇到同一坏 batch。子进程标准输出与错误被忽略，缺少任务级可查询失败状态。每条图片消息和周期 timer 仍可新增等待锁的进程。

`d111ace` 确实使数字来源抛异常后可以继续，但不解决慢调用：WeRead 请求和分页仍串行运行在照片之前。**图片接收桥仍可接受原图；这里的阻塞指后续识别处理，不能混为“入口不能保存”。**

**复现**：临时库接受两个 batch，向第一个注入 catalog conflict；worker 退出，只访问一个 batch。

**整改**：按 capture/batch 记录任务结果，隔离故障并继续下一任务；partial 不抛整批致命错误。将数字同步与物理处理分开调度，使用有限并发、去重任务和退避；记录脱敏错误及下次重试时间。批次状态应随处理推进，不长期停在 `received`。

**验收**：坏 batch 在前、好 batch 在后时后者可完成；慢数字源不延迟物理任务；多次 timer/消息触发不产生无限等待进程；故障在重启后可定位、可恢复。

### F07 · P2：自动重提取对账未保护知识依赖及完整配置

**规范**：§14.3、§18、§26.3；已有知识晋升依赖或不可确定拆分/合并须待对账。

**代码与提交**：`4ec1471`；`runtime/pipeline.py:499–588`、`runtime/worker.py:382–389`。

`reconcile_extraction` 只检查旧 trace revision 和 user_statement，没有查询已晋升知识依赖，随后整批 supersede 旧 trace。它也没有更新旧 pending candidate，调用 normalize 时不传原 vocabulary 配置。早期 `e7a098e` 保留待对账 observation 的保护因此在新增自动执行路径中不完整。

**复现**：从 trace 创建并通过替身 writer 晋升 candidate，随后 v2 重提取并对账成功；旧 trace 变为 superseded，而 candidate 仍为 promoted。历史未丢失，但规范要求的人工对账保护未触发。

**整改**：在原子提交前检查用户修正、知识依赖和可确定替换关系，任一不满足则保留 pending；显式保存配置身份与 lineage；同步废止失效候选，重算时使用原有或明确升级的 vocabulary。

**验收**：已晋升知识、pending candidate、符号配置、拆分/合并分别测试；受保护的当前 trace 不被自动替换，旧事件不能回滚索引。知识 writer 尚未正式接通，故该项按 P2 管理，但不能把端口测试称为完整晋升验收。

### F08 · P1：索引故障回滚 trace 与 observation，恢复需重新提取

**规范**：§26.2 F/G、§26.3、§28.3、AC-20；trace/outbox 先持久化，索引可重建，恢复应复用已提取证据。

**代码与提交**：`9000dc0` 引入且仍存在；`runtime/pipeline.py:341–367`。

`_index_trace` 在同一事务中、trace.created/capture.processed 事件之前执行。索引写失败会同时回滚 ProcessingRun、PageObservation、ReadingTrace 和事件；raw blob 虽可能留在对象目录，失败任务没有对应已提交检查点。现有 rebuild 测试只验证“成功提交后删除索引”，没有验证初次索引写失败。

**复现**：向 `_index_trace` 注入异常后，三类对象计数均为 0；重试 extractor 累计调用两次。不能把这种状态视为“已保存、索引滞后”。

**整改**：先原子提交 run/observation/trace/outbox，再通过已有事件消费者维护索引；失败保留消费游标，检索报告 lagging。恢复从已保存 observation 或 trace 继续，禁止因索引故障重跑模型。

**验收**：在索引 insert、提交后投递、消费阶段分别注入故障；trace 和原 observation 留存，重启重建后可查；extractor 调用次数不增加，事件 ID 与 revision 保持正确。

## 4. 尚未完成的集成与验收

这些项目与上述已确认缺陷分开计数。

| 项目 | 当前证据与缺口 | 完成条件 |
|---|---|---|
| `/lib read` 与会话操作 | `commands.py` 有领域命令；仓库插件仅注册图片 hook 和 search tool，没有会话命令适配，SOUL 也未连接写入端口 | 通过可信 Gateway 操作选择书籍、报告进度、结束/恢复会话；真实消息验证，不能靠手工数据库调用代替 |
| 可打开原图 | Library 有授权读取和 crop 函数；search 返回 ObjectRef；Vault 输出 capture ID。专用插件未暴露打开/发送原图的路径 | 提供授权的按 trace 取证入口或等价受控打开动作，用户可从结果打开原图/bbox；保持“不把图片写入 Vault”的既有选择 |
| 真实视觉主闭环 | handoff 记载首本书 5 图、10 条当前 trace，待用户 review；§38.1 四图、12 组、Weber/Parsons 闭环未完成 | 取得约定样本并核验分组、原文、页区、进度报告和检索；替换验收样本须有明确等价标准与规格决策记录 |
| M2 实际周期同步 | handoff 记载一次导入和隔离重放；周期触发、真实 app 增改删及预期 WeRead 范围未独立验收 | 观察实际调度、断网恢复和 create/edit/delete，同一查询返回三来源共同契约 |
| 实际知识服务 | 有端口及替身测试，无已配置 writer 的证据 | 仅在宣称此阶段完成时接通 writer；它不是 M1 前置条件 |
| 其他契约差距 | worker 用 ISBN 直接构造 Work/Edition/Copy ID，与 §5.1 不透明 ID 约定不符；bridge error 未返回完整 ErrorResult；OCR 手写替身分数及模型原始失败返回的留存需进一步收敛 | ID 改用不透明标识并独立维护 ISBN 映射；错误响应契约一致；字段分数保留实际来源，原始失败响应可追溯 |

Vault 不保存图片和首本书 review 在 handoff 中记有用户要求，本报告不将这两项本身判为违规，也不建议恢复用户已要求去掉的图片。需要补齐的是等价的授权取证能力。

## 5. AC-01–26 证据矩阵

“本地通过”只代表现有指定合成测试通过，不表示生产端到端通过。测试文件位于 `tests/`。

| AC | 当前判定 | 证据 / 限制 |
|---|---|---|
| 01 | 本地通过 | store/bridge 同键重试；handoff 记载五图重放 |
| 02 | 本地通过 | store/commands 同键不同 payload 拒绝 |
| 03 | 本地通过 | 相同字节新消息保存不同 capture |
| 04 | 局部通过 | pipeline/worker 多副本冲突；worker 的冲突处理阻断其他批次，F06 |
| 05 | 局部通过 | 通用 pipeline 强标题冲突保留观察；生产 OCR 不输出 visible_title，worker 提前冲突未形成同等诊断 |
| 06 | 不满足集成要求 | 底层 affinity 测试通过；自动会话路径绕过时限，F04 |
| 07 | 不满足集成要求 | pipeline 支持 unknown；实际 OCR 补页码、worker 因未知页码退出，F01/F02 |
| 08 | 本地通过 | 未用照片最高页更新进度 |
| 09 | 本地通过，真实验收待补 | 显式 progress 更新；Gateway 报告进度入口待接 |
| 10 | 局部通过 | EXIF、裁剪、跨页链接有测试；新增 OCR 的页区和文本范围仍有 F02/F03 |
| 11 | 局部通过 | 普通不确定划线不进内容 review；实际文本可能被 EPUB 扩张，F03 |
| 12 | 本地通过 | opt-in symbol 与重要内容 review 测试；当前 OCR worker 不检测独立 symbol |
| 13 | 本地通过，真实分类待验 | 测试正确分型的印刷/边注标点；不能证明模型分类准确率 |
| 14 | 本地通过 | correction 新 revision，原证据不改 |
| 15 | 局部通过 | correction 与旧事件保护通过；新自动对账需补知识与配置保护，F07 |
| 16 | 覆盖不足 | 初始重提取会 pending；自动 reconcile 缺少完整依赖检查与映射证明，F07 |
| 17 | 本地通过 | 对象保存失败不确认，原键重试成功 |
| 18 | 局部通过 | 通用 extractor 超时/非法 JSON 留存有测试；OCR 子调用错误捕获及 worker 隔离不等价 |
| 19 | 本地通过 | outbox 恢复后重投同 event，consumer 去重 |
| 20 | 不完整 | 删除索引重建通过；初次索引失败需重跑提取，F08 |
| 21 | 局部通过 | foreign IDs、映射搜索拒绝通过；全局数字源跨 owner 导入风险，F05 |
| 22 | 本地通过 | physical mark_author 默认为 unknown |
| 23 | 本地通过，live 范围待验 | 三来源 SearchHit；现场导入据 handoff，周期/变更待验证 |
| 24 | 待端到端验收 | SOUL 限制与搜索端口已在；真实入站问题→查询→来源回复未独立验证 |
| 25 | 本地替身通过 | writer 失败不发布成功，来源写入期间改变会拒绝；实际服务待接 |
| 26 | 本地通过 | 普通划线不会默认晋升 |

## 6. 整改实施顺序与放行标准

| 顺序 | 建议独立改动 | 对应发现 | 必须附带的验收证据 |
|---|---|---|---|
| 1 | 修复页码及引文证据边界，修复自动会话类型 | F02/F03/F04 | 相邻图/乱序图、半句/异文、超时矩阵；不覆写历史的修订结果 |
| 2 | 将首本书专用流程改为可选增强，接通会话命令与取证动作 | F01、集成缺口 | 无封面/无 EPUB/无 Vault/unknown 场景，真实消息完整链路 |
| 3 | 绑定上游 source 与 owner，隔离任务与调度 | F05/F06 | 双 owner 禁止误导入、坏批次不中断、慢上游不中断、有限重试 |
| 4 | 分离索引投影和持久化，完善重提取保护 | F08/F07 | 索引故障恢复不重提取；知识依赖与 vocabulary 对账测试 |
| 5 | 复验现有受影响数据，补真实验收、更新 handoff | 全部 | 可审计的新版本修订、用户确认项、AC 矩阵与运行证据 |

受影响数据排查应定位 `rapidocr-epub-notes-v3:*` 及早期 OCR extractor 的 observation、相关 capture 和自动建立的 session。先只读生成清单；按 F02/F03 核验后通过正常修订/对账接口处理，保留原图、原始返回及历史版本。不得为了使测试通过直接重写原 observation 或删除不利证据。

M0：基础已具备，F08 修复并经故障恢复验证后再称验收完成。M1：须修复核心路径偏差，补会话/证据入口和真实图像闭环。M2：已有 adapter 与初次导入记录，仍需来源归属、周期调度及实际 app 变更验收。Knowledge 阶段单独放行，不阻塞 M1。

最终放行至少要求：核心 P1 清零；68 项既有 Python 测试、3 项插件测试和契约校验无回归；新增缺陷场景转为正向验收；§38.1 或明确修订后的等价样本通过；真实受信入站查询能返回 trace、edition/page 和可打开证据。用户暂缓提供的验收输入应标为“延期/未验”，不能替换成“通过”。

## 7. 审计交付说明

本次新增本报告、合成复现脚本及输出 JSON。未整改实现、未提交 Git commit、未创建 release 分支。后续开发应针对每项整改提供独立证据，再更新 `LIBRARIAN_V0_8_HANDOFF.md` 中的状态；不宜仅把现有测试全绿或一次首本书成功导出作为完整 specification 已实现的依据。

## 8. 当晚追加执行记录（2026-09-29 凌晨）

此节记录审计完成后的修复进度，不修改上述审计结论。飞书新发的 22 张内页照片已由受信媒体 hook 全部接收；旧版 worker 把每张单独处理且对倒置页使用错误方向。新 worker 按会话和接收间隔成组，使用本地 RapidOCR 和 EPUB 多行匹配识别书籍，并对页眉位于底部的扫描件旋转分析、将坐标映回原图。模型仅用于手写裁剪。Vault 的旧生成块经历史 trace revision 精确校验后合并为一份微信读书式笔记；原图仍只在私有对象库。

当前 27 张照片共对应 86 个活跃纸书 trace；笔记中 68 条高亮摘录、13 条笔记、5 条文字未辨认标记。新 22 张所属组有 47 个 trace 的页码待核对、1 张与旧提取的分组冲突；旧 5 张仍有 3 个页码未解。因而首本书“接收→识别→数据库/Vault→人工 review 通知”已发生，准确性与全部页码并未验收。旧 worker 在修复前曾发出重复通知；新增 60 秒接收防抖和 45 秒安静窗口只对后续批次生效，需下一批真实消息验证。

新增受信 `librarian_session` 工具及域命令桥，包含 source message 幂等回执；插件能力变更须执行 `openclaw plugins enable pap-librarian-intake --accept-capabilities`，否则会出现“没有可调用工具”并阻断所有消息。当晚已完成能力登记、配置校验及 Gateway 重启，后续一条真实飞书消息未再触发该错误。真实入站 `/lib read`、检索工具调用、授权原图读取尚待独立验证，M1 与发布门槛仍未满足。相关代码检查结果为 83 项 Python Librarian 测试、6 项 Node 插件测试及契约校验通过。

F06 后续增量：worker 现将模型不可用、提取格式错误及未分类 worker 失败写为脱敏批次状态，持久化 `retry_attempts`、`next_retry_at` 和 `retry_exhausted`。同一批最多自动尝试三次，间隔先后为 5 分钟和 30 分钟；Gateway 重启后仍遵守状态，成功后清零。坏批次与其他批次隔离、物理与数字 worker 分锁已有本地测试；新增退避和成功复位测试通过。未验项目仍有真实慢源/重启恢复及反复 timer 触发下的进程数量上界，故 F06 暂不关闭。

授权原图取证入口后续增量：新增 `librarian_evidence`，只在受信发送者、账户、频道和当前路由匹配且 Gateway 提供绑定投送能力时暴露。桥接按 owner 读取 physical trace 的不可变原图证据，在私有目录生成短期局部 JPEG；投送后删除，Vault 不存图。插件能力已重新登记、工具白名单已更新、Gateway 重启后 active。本地插件投送替身及真实对象库的只读取图成功；**飞书真实消息投送尚未验收**，所以该集成缺口仍为局部完成。

F08 后续验证：索引 insert 故障后，PageObservation、ProcessingRun、ReadingTrace 和稳定 outbox event 已提交；重开数据库显示 `index_state=lagging`，复用已有 run 补建索引时 extractor 不再调用且 event ID 不变。真实 trace 事件消费者写索引失败时 dedup 游标不前进，重启后用同一事件恢复。worker 启动恢复现在也检查并补建缺失索引，即使没有新照片也能修复数字 trace 投影。上述为本地故障注入与恢复证据；真实 Gateway 重启和外部事件投递仍需观察，F08 的本地缺陷已修，整体放行仍未完成。

F07 后续验证：已晋升和待审知识候选引用旧 trace 时，自动对账均保留原活跃 trace 并返回待人工对账；带个人符号词表的 normalizer 版本不会在未恢复配置的情况下自动替换；旧标记分组发生合并时也不自动接受。本地测试覆盖了这些保护。词表快照的持久化身份、明确 lineage 和可审核的人工对账入口仍未实现，因此 F07 继续开放。

F01 与成本控制后续增量：没有匹配 EPUB 的纸书内页现在先用本地 RapidOCR 定位正文和下划线；只在本地未找到标记时调用整页视觉模型。图片有画线但书籍或页码未知时仍持久化 unresolved trace，不以 EPUB 或 Vault 为接收前提。定位 OCR 和 worker 分支测试证明一张有本地可识别画线的图不触发整页模型。高亮颜色、独立符号及同图混合标记的真实覆盖率尚未验收，不能据此关闭 F01。

§5.1 目录 ID 后续增量：新入库纸书的 Work、Edition、BookInstance 改用不透明随机 ID；ISBN 只作为 Edition 字段和查询键。按 owner 与 ISBN 唯一匹配已有版本时复用旧 ID，因此首本书已存在的 ISBN 派生 ID 不被强行重写。新建及旧版复用均有测试；历史 ID 的迁移政策仍需单独制定。

M2 周期运行观察：Gateway 重启后的 `digital-sync-status.json` 于 2026-09-28 16:20:08 UTC 记录 Koodo 与 WeRead 均成功；Koodo 118 条、WeRead 4 条来源记录在这次运行中均为 unchanged。当前 owner 的 208 条活跃 trace 与 208 条索引投影一致。此证据确认周期调度至少执行了一轮并能读取两个真实来源；实际来源增改删及断网恢复仍未验收。

真实入站工具审计：Librarian 本机 `trajectory_runtime_events` 截至本轮检查有 32 条历史 tool.call（`exec` 25、`memory_search` 4、`read` 3），没有 `librarian_search`、`librarian_session` 或 `librarian_evidence` 调用。插件已加载和工具已获许可只证明可供调用，不证明模型在真实飞书消息中使用过。受信入站问答及取证验收继续待实际消息。

F02 真实照片复核发现双页码版式歧义：一张原图顶部印有「23」，中段边栏有「41」，旧 v6 将上段留为 unknown 并把下段误标为 41；另一张无顶部页码的原图在边栏印「39」「40」，确实对应上下两段。v7 在 OCR 识别出与短页眉同行的唯一顶部页码时，以该号码覆盖整张正文页；否则保留边栏分段。两张既有原图只读重跑分别得到 `[23]` 和 `[unknown,39,40]`，并增加合成回归测试。生产 trace 尚待 v7 正常重提取与对账更新，不能以只读重跑声称数据库及 Vault 已纠正。

v7 正式 worker 已重处理两组照片：旧 5 图组仍为 10 条 trace、3 条页码未解；新 22 图组为 76 条 trace、47 条页码未解及 1 张分组冲突。抽查上述误标原图的活跃 trace 已从 41 修订为 23，旧 trace 为 superseded。该结果证明正常对账路径已生效，但整本书的页码准确性仍需人工 review。修订通知原先共用固定 marker，后续修订会静默跳过；现改为按当前 trace 状态摘要去重，每一版只发送一次，待真实飞书投送验证。

按摘要去重的 worker 再运行后，为两组各生成一条 2026-09-28 16:35 UTC 的修订通知回执；`openclaw message send` 返回成功并写入 marker。两组在这次修订分别投送了一条，用户端展示和点击审阅尚未核验。后续同一摘要不会重复投送。
