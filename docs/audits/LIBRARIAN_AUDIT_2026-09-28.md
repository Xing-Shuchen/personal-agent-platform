# Librarian 修改与 specification 一致性审计

初审日期：2026-09-28；报告澄清更新：2026-09-29。初审结论（针对 `d111ace`）：**部分一致，不满足该版本对应 specification 的完整验收条件。建议暂不发布 release-v0.8。**

**数据结构、元数据、Schema、桥接模块均未获得“整体无问题”的审计结论。** 领域分层与部分持久化、修订、幂等和隔离检索路径有测试证据，但已确认的问题横跨元数据真实性、跨对象依赖、事务恢复和桥接授权；不能将问题仅归为 worker/OCR 的识别效果。Schema 校验通过不等于数据语义正确，也不等于端到端链路通过验收。

**版本适用说明**：第 1–7 节的原始发现、行号、测试数量和 AC 状态以 `d111ace` 为准；第 8 节记录后续整改与现场验证，其中已有原问题修复、入口补齐及测试数量增加。本次更新补充结论边界和模块复核要求，不是对最新 HEAD 或未提交改动的一次完整复审。不得将初审缺陷无条件套用到最新代码，也不得因后续单项成功记录而关闭整个模块的审计。

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

### 2.1 模块级审计结论

下表将原始发现与模块责任对应起来。“有测试证据”仅指已执行的具体路径，**不表示该模块所有字段、状态迁移、引用关系和入口均已验证**。后续进度引用第 8 节，尚未在本次澄清中逐项重新执行。

| 模块 / 责任 | 初审已验证的范围 | 已发现的问题或缺口 | 后续记录与结论边界 |
|---|---|---|---|
| 数据结构与领域关系：`store.py`、`pipeline.py`、`knowledge.py`、migrations | Work→Edition→BookInstance 基本引用、trace 修订、不可变 evidence 分层及部分跨 owner 拒绝 | 重提取未完整保护知识依赖和配置（F07）；索引失败回滚领域对象及运行记录（F08）；目录 ID 违反不透明约定（§4） | 第 8 节记载 F08 本地修复、F07 增补保护和新目录 ID 改进；未形成所有引用与迁移不变量的完整复审结论 |
| 元数据：页码、basis、confidence、session、provenance | 部分 unknown 保留、时间区分、人工 correction 及 mark_author=unknown | 相邻照片页码推定被标为 vision/resolved（F02）；EPUB 扩文与 bbox、basis 不一致（F03）；自动会话被标为长期选中（F04）；来源配置可能造成错误 owner 归属（F05） | 后续 OCR、页码与审核修订有逐次记录；仍需区分旧错误数据、新候选、已审核 trace，不能以新算法通过样例证明全部历史元数据正确 |
| Schema 与运行时校验：`schemas/`、`validate`、契约 fixtures | 77 定义、18 入口、42 正例、43 反例及选定语义检查通过 | 此结果不是逐字段业务语义审计。错误页码、虚假 basis 或合法格式但错误的 owner 可通过结构校验；跨对象存在性、真实授权、版本迁移和来源真实性不能由单对象 Schema 证明 | 未确认 Schema 全部无缺陷，也不把未覆盖项直接判成 Schema 缺陷；必须检查正文→字段→语义校验→写入口的对应关系 |
| 桥接与应用入口：plugin、gateway bridges、commands、worker 调度 | staged 图片接收、稳定来源 ID、映射搜索和指定 owner 拒绝路径 | 初审时会话写命令与授权原图入口未接齐、ErrorResult 不完整（§4）；调度给不同 owner 传同一数字源（F05）；批次隔离及恢复不足（F06） | 第 8 节已记载 session/evidence/review 等入口及部分真实调用，不能再笼统称“全部缺失”；仍需按每个入口复核授权、幂等、失败响应和投送语义，已有一次 queued/送达混淆的现场问题记录 |

### 2.2 Schema 通过与业务正确的区别

| 示例 | 结构上可能合法 | 必须由应用或证据验证的事实 |
|---|---|---|
| `page=39, basis=vision, status=resolved` | 类型、枚举、必填字段均正确 | 39 是否来自当前页区可见页码，而非相邻照片推定 |
| `printed_text` 含完整句，bbox 指向一行 | 字符串与坐标格式均正确 | 整段是否确实对应所标区域，EPUB 补充是否被冒充照片转录 |
| owner B 下存储来源 A 的数字记录 | owner 字符串和对象形状均合法 | 上游凭证、书库和 source 是否确实授权给 B；查询加 owner 过滤无法纠正错误入库归属 |
| candidate 引用 `{trace_id, revision}` | 引用结构正确 | 被引用版本是否存在、是否有知识依赖、重提取是否应阻断、历史来源能否继续打开 |

因此，整改应落实在产生事实、验证引用与决定权限的写入边界；不能仅通过放宽 Schema、增加默认值或修改 fixture 消除报错。未覆盖的语义检查应标为“待验证”，而非“已通过”。

### 2.3 模块专项复核清单与通过条件

此清单是下一轮复核要求，不增加本次已确认缺陷的数量，也不表示以下场景都已发现漏洞。

| 复核对象 | 需要补齐的检查 | 通过条件 |
|---|---|---|
| 数据结构 / 引用 | 逐条核对 §30 不变量；覆盖命令、adapter、worker、审核对账等全部写入口，检查同 owner、引用存在性、版本链、当前指针和 lineage；检查迁移兼容 | 非法关系通过任一入口均被拒绝且无部分提交；旧版本证据可读；知识依赖与人工修正受到保护；迁移有回归样本 |
| 元数据 | 建立字段来源表：页码、身份、时间、作者、basis、confidence、locator、bbox、provenance、配置版本分别由谁生成、何时可修订；列出受影响历史记录 | 未知保持未知；来源与证据相符；更正形成新版本；新候选与已确认事实不混用；历史错误修复有可追溯记录 |
| Schema | 逐字段核对正文与 `$defs`；区分 Schema 约束、运行时语义校验和外部事实验证；补 unknown/null、非法状态组合、版本迁移及跨实体反例 | 每条 MUST 有明确执行位置和证据；结构上合法但业务非法的输入在应用层被拒绝；不能检查的真实性限制被明确记录 |
| 桥接 | 列举图片、session、search、evidence、review、finalize、digital sync 等入口；检查可信身份、source→owner 绑定、稳定幂等键、ErrorResult、进程/任务失败和 queued/送达状态 | 覆盖跨 owner、跨 account/chat、重复消息、附件变化、重启与投送失败；工具声明成功对应实际完成层级；本地 bridge、插件替身和真实消息证据分开记录 |

复审关闭项目时应同时记录：修复 commit、对应规范条款、回归测试、必要的现场证据、历史数据处理结果和剩余限制。仅凭某次全套测试通过，不足以给上述四类模块签发整体通过结论。

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

2026-09-28 初审交付新增本报告、合成复现脚本及输出 JSON；该次审计未整改实现、未提交 Git commit、未创建 release 分支。后续开发应针对每项整改提供独立证据，再更新 `LIBRARIAN_V0_8_HANDOFF.md` 中的状态；不宜仅把现有测试全绿或一次首本书成功导出作为完整 specification 已实现的依据。

2026-09-29 澄清更新：修正开篇可能被理解为“基础模块均无问题”的表述，新增 §2.1–2.3 的模块结论、Schema 能力边界与专项复核条件，并区分初审版本与后续执行记录。本次仅更新报告；未重新执行测试或对最新实现作完整复审，原测试数字不能作为本次最新代码验证结果。

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

F06 恢复补充：批次重试状态现包含配置指纹（视觉模型及 `source-books` 内 EPUB 内容摘要）。失败批次耗尽三次自动尝试后保持停止；模型变更或 EPUB 增补会自动重置该批重试计数。故障注入测试覆盖耗尽、相同配置不重跑及两类配置变更恢复，避免要求生产环境手工删除状态文件。

F01/F04 迟到书籍绑定补充：只读检查发现 86 条纸书活跃 trace 中有 12 条 Work 未绑定，分布在 3 张照片；其中 2 张已有 v7 成功提取和 `edition_fingerprint` capture_context，早期全 unknown 的 CaptureResolution 仍挡住书籍身份。新增 `bind_fingerprint_context` 仅在既有 resolution 未含任何确认值、trace 未经用户修订、没有活跃知识候选依赖，且指纹 session 仍开放时，复用原 observation 与 trace 作带来源标记的修订；不调用 OCR 或模型。合成测试证明新版本绑定、原观察数量不变、重复调用幂等及用户修订保护。生产三张照片的实际回填结果需继续核对。

迟到绑定正式 worker 运行后，86 条活跃纸书 trace 的 Work 未绑定数从 12 降为 0，索引仍为 208/208。随后真实数据库搜索暴露一个 P1：`SearchHit` 的 revision >1 被错误套用存储对象的 `supersedes_revision` 语义校验，导致查询直接报错。现将该语义约束限于实际带 `supersedes_revision` 的记录，增加修订 trace 搜索回归；生产库「帕森斯」检索返回 20 条、`index_state=ready`，包含 revision 2。真实飞书 agent 入站仍待验。

AC-24 按书页检索补充：`librarian_search` 现接受 `book` 和 `page`，允许不带关键词查某本书的印刷页；按 owner 解析唯一 Work，并在索引查询中按 trace 当前 location 的页码过滤。生产库只读查询《社会理论二十讲》39 页命中 1 条、23 页命中 2 条，索引均 ready；本地测试涵盖书名、页码、未知书、无权 owner。模型是否在真实飞书提问中正确调用该工具仍需入站验收。

F07 配置身份与 lineage 补充：新 ProcessingRun 将 `normalizer_version`、`vocabulary_version` 与词表映射快照的私有 ObjectRef 分开保存；同名版本但映射不同不再被当作幂等重试。重提取只在旧新快照内容摘要一致时自动对账，旧版没有快照的个人词表 trace 保守停在待人工对账。可确定的一对一标记组替换同时写入 `TraceRelation(supersedes)`，指向旧 trace 及精确 revision。测试覆盖相同快照幂等、同名异配置阻断、同配置换提取器成功和关系写入。无法确定映射的分拆/合并及旧数据人工对账入口仍未关闭。

首本书剩余分组冲突只读诊断：`capture_92f01023e12541aeb64c135ec543a6ba` 的旧视觉 observation 当前有 5 个活跃空文本下划线 trace；v7 待对账 observation 检出 8 个定位下划线，其中较上方两段旧版未覆盖。两代 mark ID 与数量均不同，且旧 trace 已有上下文绑定修订；自动替换会破坏可追溯性，继续保持 `RECONCILIATION_REQUIRED`。下一步需要可展示候选与明确人工裁定的操作入口，不能靠调低自动对账门槛消除该冲突。

2026-09-29 调试补充：新增只读 `librarian_review` 工具与 owner 范围桥。无参数时仅列每张照片最新 ProcessingRun 仍待对账的项目，避免旧 v4/v5/v6 pending 记录误报；带 capture ID 时对比当前 trace 与待入库 normalize 候选，不修改数据库。生产库结果仅余上述一张照片：5 条当前 trace 对应 v7 的 3 个划线组（8 个检测点），候选印刷页 39、39、40，候选文字有缺行，仍需人工对照原图和 EPUB。插件能力已重新登记、配置校验通过，Gateway 启动并建立飞书长连接；真实飞书调用与明确裁定仍未验收。

同张照片的 OCR 原始行复核：第二组中间 y≈0.577 的正文行有明显划线（局部得分 0.1722），但本地 OCR 文本无法匹配 EPUB，故 normalize 候选遗漏该行。审核预览现在返回 `ocr_gaps`，定位这类有划线却无可靠印刷文字的行，防止候选以表面完整的句号掩盖中间缺失。该结果仍需原图确认，不能自动从 EPUB 补字。

v8 本地 OCR 局部重试：强划线而整页 OCR 无法匹配 EPUB 的正文行，最多逐张重试 8 个小裁片；只接受裁片中位置对应且 EPUB 匹配度 ≥0.85 的行，不调用大模型。上述 y≈0.577 行从原始乱码恢复为「从社会学自成立以来发展得相当杂乱的理论给整合起来，以及将涂尔干和韦伯的」，只读完整提取生成第 9 个划线检测点。103 项 Python Librarian 测试通过。正常 worker 重跑后，目标照片仍按分组变化保留 `RECONCILIATION_REQUIRED`；另有 4 张照片进入待对账，其中一张原本 0 条活跃 trace 新检出 1 条划线，另有旧 margin note 与新观察不一致。当前仍为 208 条活跃 trace（纸书 86 条）及 208 条索引，未自动覆盖旧证据。v8 批次整体重跑与模型/视觉观察波动会扩大待审核队列，后续需要区分真实新增标记与不稳定检测，不能以该次重跑宣称首书验收完成。

五张待对账照片只读分诊：`…14d58569` 与 `…f4dcd3df` 均为旧、新各 4/4 和 3/3 组；抽查旧 trace 的 revision 1→2 仅改变书籍、版本、会话和来源绑定，不涉及印刷文字或笔记内容，因此当前 `revision != 1` 门槛对这两张偏保守，但仍需精确 lineage 核验后才能自动通过。`…9f96e4a5` 原来 0 条、新版 1 条，原图局部可见手写括号而对应印刷行没有明显划线，局部 OCR 找到正文不等于找到了画线，倾向误检，不能入库。`…c543a6ba` 为原 5 条空文本与新版 3 组（9 个检测点）的真实分组冲突；`…b95eae21` 为原 4 组与新版 5 组，新增候选及另一处低置信墨迹仍需原图审阅。当前 Gateway 活跃，尚无新的真实 librarian 飞书入站，故工具使用验收仍未完成。

2026-09-29 07:30 首次真实「查看待审核提取」入站揭示另一配置缺陷：飞书消息成功路由并回复，但 agent trajectory 的当前工具列表只有 `session_status`，没有 `librarian_review` 或其他 `librarian_*`，模型未调用工具，还复述了旧会话中的失效白名单故障。插件自身已加载、factory 的 sender/route 校验为真；根因是全局 `coding` 工具 profile 先过滤插件工具，agent 的 `tools.allow` 无法扩大 profile。将 librarian 单独改为 `tools.profile: minimal` 加四个 `tools.alsoAllow`（该 scope 不允许同时设 `allow` 和 `alsoAllow`），配置校验通过并重启 Gateway。最小 profile 仅提供 `session_status`，插件工具仅在受信 sender/route 下由 factory 暴露。实际第二次入站工具调用仍待核验，不能以配置校验和插件 inspect 代替。

07:40 真实重试验证：同一受信飞书 sender 的「查看待审核提取」进入 librarian 会话；trajectory `context.compiled.tools` 含 `librarian_review`、`librarian_search`、`librarian_evidence`、`session_status`，随后出现一次 `tool.call librarian_review`（空参数）与成功 `tool.result`，返回 5 个 v8 待对账 capture。agent 回复也列出这 5 个 ID，未声称已入库。故只读审核工具的真实入站调用已验证；但回复只给不透明 ID，缺少页码和差异摘要，人工审阅体验不足。`librarian_session` 未出现在这次工具列表，尽管配置授权，具体原因与真实 `/lib read` 仍未验证。证据取自本机 OpenClaw trajectory SQLite 和 Gateway 日志，不能据此宣称所有 agent 工具闭环完成。

审核列表后续改为单次只读桥调用就返回书名、印刷页、现有/候选组数与 OCR 缺口数；生产库当前五项摘要为页 65/66/unknown 4→5（1 处缺口）、unknown 4→4、45 页 0→1、41 页 3→3、39/40 页 5→3。agent 指令改为用这些信息直接向人说明，避免要求用户从不透明 ID 中选一项。该展示改动已用生产库只读调用检查；真实飞书第二轮展示尚待验证。

`librarian_session` 缺席的下一步诊断：OpenClaw 的 `message_received` hook 契约把 `conversationId` 定义为可选，却保证规范 `sessionKey` 与 agent run 一致；现有临时入站绑定错误地要求前者。插件改用受信 `sessionKey` 作会话 scope，同时继续要求真实 inbound message ID、映射 sender/account/channel 和 10 分钟时限。8 项 Node 插件测试通过，其中包含 hook 无 `conversationId` 的情形；增加仅记录布尔值的运行时诊断。此项尚未经过真实 `/lib read` 消息验证，且进程内 hook/tool registry 是否共享临时映射仍待运行时观察。

07:47 首次真实 `/lib read 社会理论二十讲` 验证失败：飞书入站成功，hook 见到 sender、message ID、sessionKey、conversationId，但 tool factory 报 `recent=false available=false`；trajectory 的工具列表仍不含 `librarian_session`，模型明确回复未执行 start，数据库会话未因此改变。这排除了缺少 `conversationId` 是本次唯一原因。插件把 10 分钟临时入站映射放到同一 Node realm 的 `globalThis`，覆盖 hook 和 tool 的独立插件注册实例，并增加 binding 是否写入、映射条数的非敏感日志。新增跨注册实例回归，Node 插件测试 9/9 通过。尚待 Gateway 重启及下一条真实入站证明此修复有效；不能把本地回归算作生产会话成功。

07:53 第二次真实 `/lib read`：Gateway 日志显示 `owner=true saved=true entries=1`、`recent=true available=true`；运行轨迹 `session.started.toolCount=5`，会话存储的工具快照明确包含 `librarian_session`。因此共享映射修复已在真实入站生效。但模型仍沿用上一轮失败答复，错误声称工具不存在，没有任何 `tool.call`，也没有会话回执。用 Gateway 的 `sessions archive --dry-run` 核对目标后，归档了这一个 Librarian 飞书会话；归档保留历史，下一次入站应以新上下文运行。下一次真实调用与状态写入尚待验证，不能把工具注册成功当作会话闭环。

归档语义更正：检查 OpenClaw 当前运行版的 `restoreArchivedDispatchSession` 后确认，已归档会话在下一条受信真人消息到来时会恢复原上下文，故上段“下一次入站应以新上下文运行”的判断错误。先通过 `sessions.patch` 对同一 `expectedSessionId` 解除归档，再用 Gateway 原生 `sessions.reset` 定点重置；两次 RPC 均成功。随后 `chat.history` 仅返回 Reset 系统标记，证明当前对话上下文已清空；旧 transcript 由运行时保留，未直接改写 SQLite。真正的下一条飞书入站调用仍待验证。

08:00 周期 worker 只读核验：Gateway 自 07:49 重启后，两个当前可处理纸书批次的状态在 08:00 更新为 `partial`，分别保留 10/76 条活跃 trace；后者明确列出 5 张 `RECONCILIATION_REQUIRED`，重试次数为 0。`digital-sync-status.json` 同时记录 Koodo、WeRead 均成功。状态目录另有 7 个旧 `error` 文件，但对应批次不在当前 `_processing_batches` 集合，文件时间停在 09-28 23:30–23:35，不能误报为这轮 worker 的失败。当前没有滞留的 Librarian worker 进程。此证据证明本次周期调度和两类任务各自完成，尚不能代替慢源、网络中断及多次 timer 进程上界的专门验收。

08:05 再观察一个完整周期：同两张当前批次状态分别在 08:05:12、08:05:20 更新，仍为 `partial` 及 10/76 条 trace，5 个待对账 capture 未变；数字同步在 08:05:09 更新，Koodo 与 WeRead 均成功。08:05:31 无残留 worker 进程。两次正常周期未见进程堆积，但不能推断故障或慢源场景的上界。

09:15 用户第三次从飞书发送 `/lib read 社会理论二十讲`。Gateway 入站身份绑定为 `owner=true saved=true`，会话工具 factory 为 `recent=true available=true`；agent trajectory 出现 `tool.call librarian_session`，参数为 `{"action":"start","book":"社会理论二十讲"}`，随后 `tool.result` 返回 `status=active`、revision 1、会话 `session_1094c8d65911414c9d3893a54328eccf`。agent 的飞书回复引用该回执。生产 Library 中同一 owner 的 ReadingSession 为 active、对应《社会理论二十讲》的 Work/Edition/Copy、进度为空；`gateway_session_receipts` 有唯一匹配回执。因此 `/lib read` 的受信入站→agent 工具调用→领域命令→数据库回执→飞书回复已按真实链路验证。页码 progress、暂停/恢复/结束、检索及原图取证尚未因这一条成功而视为通过；首书的 5 张待对账照片也仍需人工裁定。

09:17 用户从飞书明确报告「我读到第39页了」。真实轨迹出现 `tool.call librarian_session`，参数 `{"action":"progress","page":39}`，工具返回成功；同一 ReadingSession 升为 revision 2、保持 active，`progress.end_page.number=39`、`basis=user_statement`，`evidence_ref` 与本次飞书入站 message ID 相同。agent 回复引用相同会话及第 39 页。显式进度报告链路通过；照片自身页码不因此自动成为阅读进度。

09:21 用户实际从飞书问「我在《社会理论二十讲》里画了什么」（未限定第 39 页）。真实轨迹出现 `tool.call librarian_search`，参数 `{"book":"社会理论二十讲","limit":20}`；工具成功返回 20 条同书 trace、`next_cursor=20`、`index_state=ready`。agent 飞书回复注明 20 条为本次上限、可能还有更多，并列出 trace ID、已解析页码或页码未知及正文片段。这证明受信入站→按书 owner 范围检索→来源化答复的真实链路；第 39 页条件过滤、结果翻页和授权原图投送仍未通过该问题验证。首书待对账照片不因搜索成功而视为已审核。

09:23 用户从飞书问第 39 页并要求原图局部。真实 agent 先调用 `librarian_search`（book+page=39）命中 1 条 `rt_7fc74a2b140edf941ecea6ef689bc19e`，再调用 `librarian_evidence`。平台日志明确报 `Local media path is not under an allowed directory`，因为裁片仍位于仓库私有 `var/librarian/delivery-evidence`；插件的 `ctx.delivery.send` 却正常 resolve，工具回报 `delivered:true`，agent 因此错误说“原图局部已发送”。按页检索真实链路通过，原图投送失败且成功判断不可信。修正插件为先复制裁片到显式配置的 OpenClaw media allowlist 子目录（0700 目录、0600 文件），等待当前路由投送调用后清除两份临时文件；工具只返回 `delivery_status: queued`，SOUL 不把排队等同平台送达。Node 回归与配置校验通过，真实投送尚待重启和下一条消息复验。

10:04 用户在 Gateway 重启后重发同一句第 39 页原图请求。真实 agent 先调用 `librarian_search`（book+page=39），返回同一条 trace，再调用 `librarian_evidence`，工具成功回报 `delivery_status: queued`。本次 Gateway 日志无 `sendMediaFeishu failed`，飞书文字回复完成，agent 明确说平台尚未确认送达。私有裁片目录与 OpenClaw 媒体目录均无残留文件。OpenClaw 投递 API 的工具回执仍未提供图片消息 ID；是否实际显示在飞书客户端，已请用户确认，确认前不能记为图片送达验收通过。

用户确认图片已收到，但指出它仍是旧拍照版，之后发送过扫描版。核查发现旧 active trace `rt_7fc74a2b140edf941ecea6ef689bc19e` 的源 capture 时间为 13:34，而扫描件 `capture_92f01023e12541aeb64c135ec543a6ba` 于 15:25 入站；扫描件 v8 因 5→3 分组冲突停在待审核，故旧 trace 原图工具按其不可变来源正确裁了旧图，却不符合用户对最新扫描证据的期望。扫描版只读候选含第 39 页两组，其中 candidate 1 的原图裁片目视确认为「正是帕森斯……」画线；candidate 0 仍未确认，不自动入库。按书页检索现附带同 owner、同书、同页的 pending 扫描候选；原图工具可用 capture ID 与候选编号只读取其裁片，并明确标注待审核，不伪称它是旧 trace 的来源。Python 定向测试 6 项、Node 插件测试 10 项通过，生产库只读检索返回旧 trace 1 条和扫描候选 2 组，裁片生成通过目视核对。Gateway 已重启并建立 librarian 飞书连接；扫描候选的真实 agent 投送仍待用户下一条消息验证。

用户反馈 OCR 结果不足，询问直接多模态识图。针对同一扫描件做只读定向实验：将第 39 页 Parsons 画线区域的原图局部交给 OpenClaw 已配置的 `zai/glm-5.3-flash`，模型返回 1 组、4 行完整画线文字，与目视裁片一致；将本地 OCR 误报的另一候选局部交给同一模型，返回 `has_underline=false`。两个局部调用分别约 8 秒、5 秒，未写入 Library 或 Vault。这说明定向高分辨率视觉复核在本例有价值，但两例不足以证明整批准确率；既有整页多模态 v1 曾产生空文本和错误分组。下一方案应以整页找标记、局部多模态辨认、EPUB 校对印刷字、跨方法冲突待审的分阶段流程评估，不能把该次实验直接当成首书入库通过。

10:16–10:18 真实飞书复验：用户再次按页询问原图，agent 搜索返回旧拍照 trace 与扫描件第 39 页两处待审核候选，随后分别调用 `librarian_evidence` 发送两个扫描局部；用户明确说「只要候选1，第二个明显无画线」，agent 再调用候选 1 原图工具。轨迹中的当时编号对应候选 0（齐美尔/滕尼斯区域）与候选 1（帕森斯段），用户认可的是帕森斯区域。候选序号会随重提取变化，后续以 capture+标记检测组生成稳定候选 ID，并让工具优先使用该 ID；这条反馈不能误套到重跑后的新序号。

10:25–10:27 正式 worker 对 5 张已有 v8 对账冲突的照片运行 v9 局部多模态复核。模型在扫描件第 39 页的齐美尔/滕尼斯区域判无画线，且局部墨迹分数低，新候选由 3 组减为 2 组（第 39 页帕森斯、第 40 页另一处）；另有原 0→1 的第 45 页误检降为 0→0。5 张照片仍保留 `RECONCILIATION_REQUIRED`，没有自动覆盖旧 trace；生产活跃 trace 总数仍 208、纸书 86。模型对帕森斯划线起点和结尾在多次局部调用中不稳定，故 v9 只用明确负例排除弱墨迹误报，将模型转录与 EPUB 匹配度作为私有审核证据，不把模型文本直接替换入库。`librarian_review` 现返回 `visual_checks`；新版 scan 候选使用稳定 ID。Librarian Python 套件 99 项、Node 插件 10 项通过。用户的候选反馈尚未通过受信 agent 审核写入领域记录，首书入库闭环仍未完成。

10:45–11:00 本地 OCR 与核显实验：依据 PaddleOCR 官方 GitHub/安装说明，在隔离的 `/tmp/librarian-paddle-venv` 安装 PaddleOCR 3.5 与 PaddlePaddle 3.2 CPU 版，未改生产依赖。官方 PP-OCRv5 server 检测/识别模型对原尺寸 2480×3507 扫描件默认阈值漏掉正文；缩至 1414×2000、检测阈值 0.2/框阈值 0.3 后，第 39 页得到 30 行（9.56 秒），正文 27/27 行与 EPUB 匹配度至少 0.85；现有 RapidOCR 同样 27/27，约 3.5 秒。另一张倒置扫描件先旋转再缩放，PaddleOCR 得 75 行、29 个长正文行中 28 个匹配 EPUB（11.59 秒）；RapidOCR 得 74 行、28 个长正文行中 27 个匹配。新增的一行是普通印刷正文，未证明待审核的墨迹/OCR 缺口已解决。两个样本不足以替换生产识别器。

同机硬件为 Intel Meteor Lake-P Arc 核显，用户可访问 `/dev/dri/renderD128`；系统未安装 OpenCL ICD。将 Intel 官方发行包仅解压在 `/tmp/librarian-intel-opencl` 后，隔离的 OpenVINO 2026.2 能列出 GPU 并在 GPU 上编译现有 RapidOCR PP-OCRv6 ONNX 检测/识别模型。临时 GPU 适配器对同一第 39 页扫描件输出 30 行，已有模型编译缓存时初始化 0.83 秒，连续推理 1.91/0.97/0.85 秒；同进程 CPU ONNX 路径为 3.38/2.81/2.80 秒、同为 30 行。首次无缓存的 GPU 推理曾达 22.4 秒，故只将热身后的加速视为有条件的性能结果。RapidOCR 当前 OpenVINO 后端将设备固定为 CPU；实验使用临时适配器，生产 Gateway/worker 未启用核显，也未将临时驱动包视为已部署依赖。

11:00 后新增 `librarian_review_decision` 受信入口，仅接受同一真实入站飞书消息绑定的 owner/actor/source，要求当前 pending run ID 与稳定候选 ID 匹配，并以来源消息幂等记录 accept/reject 及用户明确提供的完整更正文本。`librarian_review` 可读该 run 的最新决定。该入口只写私有审核账本，不修改 ReadingTrace、索引或 Vault；后续还需有明确的整图对账命令和文本边界核实才可完成入库。Python Librarian 套件 100 项、Node 插件 11 项通过；OpenClaw 配置校验通过、插件能力已登记、Gateway 重启且飞书长连接启动。生产第 39 页 scan 的最新 run 有两个稳定候选，目前审核账本为空；新工具尚未有真实飞书调用，不宣称真人审核已被系统记录。

11:10–11:18 修正局部 OCR 边界：第 39 页 scan 的第一条被画线正文行，在前一句句号之后的检测画线起点相差仅约 0.0014 个行宽；旧规则错误地把「社会学家帕森斯……的名字。」并入候选。调小该边界误差后，只读原图重跑从「正是帕森斯」开始。正式 worker 以 v10 版本跑完 5 张冲突图，仍全部保持待对账；第 39 页候选现为「正是帕森斯，在20世纪……著作树立为社会学思想的核心构成部分。」及第 40 页另一组，稳定候选 ID 未变，活跃 trace 仍 208。该行修复并不证明第 40 页候选完整，也不代表第 39 页已入库。

增加 `librarian_review_finalize`：只有当前 run 的每个候选都有来源绑定的接受/拒绝决定，且用户明确要求替换整张扫描件的旧组、旧 trace ID+revision 与最新快照完全一致时才通过正式版本化对账；旧 trace 变 superseded，接受候选按原 observation 建新 trace，更正文本标记 `user_statement`，索引和事件沿用 pipeline，随后触发 worker 导出 Vault。知识依赖和用户已更正旧 trace 继续阻断。合成端到端测试覆盖一条接受、一条拒绝、提前提交拒绝与同源幂等；Python 102 项、Node 12 项通过，Gateway 重启、飞书长连接启动。生产 5 张图尚无审核账本决定，新工具无真实飞书调用，故不能把本地测试视为首书入库完成。

回归时发现审核列表用秒级 `created_at` 加随机 run ID 选“最新”；同一秒内创建旧成功 run 与新 pending run 时可能反选旧版，表现为待审核图消失。改为按 records 插入 rowid 选当前最新 run；同秒合成对账测试稳定通过，生产第 39 页仍指向 v10 pending run。此修复只影响审核定位，不自动提升内容。

11:22–11:23 用户按新提示发来真实飞书审核消息。agent 先调用 `librarian_review` 列出 5 张当前待对账图，再查第 39/40 页扫描件的两个候选；随后调用 `librarian_review_decision`，以 v10 run `run_f673f47233794ead9b97480326ca0bce` 和稳定候选 `candidate_0dd1e286dac983485c6c8fc8` 记录第 39 页「接受」，工具回报 recorded，生产审核账本有同一决定。agent 还分别调用 `librarian_evidence` 投送第 39、40 页扫描局部，工具回报 queued；客户端是否显示仍需用户确认。第 40 页未决定，`librarian_review_finalize` 未调用，活跃 trace 与 Vault 未替换。这个真实调用证明审核决定入口可用，但不等于整图入库验收。

用生产 Library 的隔离副本和单独的临时 Vault 演练另一阶段：模拟接受第 39 页、拒绝第 40 页后，正式对账将原扫描 5 条旧 trace 版本化 supersede、新建 1 条第 39 页 trace；活跃总数在副本中 208→204。基于现有生成笔记的历史 trace 锚点，`_consolidate_generated_note` 校验旧内容后在临时 Vault 渲染了新 trace 与「正是帕森斯」文字，不嵌入原图。此为结构和刷新路径验证，模拟决定未写入生产，也不能代替用户对第 40 页的判断。

第 40 页局部目视确有连续多行手划线，但 v10 候选漏掉第二行句号前「多花时间思考他们究竟是如何获得大师地位的。」；原因是逐行按单条最连续墨迹截句，忽略其与上下行同属一组。增加可选 `recover_span` 路径：内部行保留完整 OCR 文字，并在已确认有强墨迹的行内合并横跨不同高度的波浪线片段，以估计首尾边界；只读原图重跑可恢复第二行，并将首行未画线的「个学科的‘老手’」排除。阈值不由合并结果提高，避免单靠密集印刷笔画新增标记；合成测试覆盖该边界。该选项默认关闭，生产 v10 observation/候选未重跑，用户刚记录的第 39 页决定仍绑定原 run，绝不能把这次只读重跑当成已更新的审核候选或 Vault 文本。

11:30–11:33 用户在真实飞书确认两张局部已收到，指出第 40 页候选不应含「个学科的老手」，应从「涂尔干或韦伯的古典大师地位……」开始；随后明确「接受。这块你可以和 epub 文件对齐」。agent 在第二条入站调用 `librarian_review_decision`，将第 40 页稳定候选记为 accept，并提交从用户指定起点至照片可见终点的完整更正文字。账本现有第 39、40 页两条 accept；第 40 页文字经服务端对原图关联 OCR 起止锚点和该 EPUB 匹配度 1.0 校验。agent 未调用整图 finalize。独立副本使用这两条生产审核决定正式对账得 2 条新 trace、总活跃 205，并在临时 Vault 验证两条文字均可渲染。

11:38 正式 worker 基于两条受信审核决定自动对账第 39/40 页扫描件：只在旧 trace 全为空文本、旧版本更正事件仅为 `capture resolution`、所有新候选均有决定、照片 OCR 起止与 EPUB 一致时自动执行。生产旧 5 条空文本 trace 已 superseded，新建 2 条活跃 trace（第 39 页 printed_text basis=vision；第 40 页更正 basis=user_statement），活跃总数 208→205，待对账 capture 5→4。Obsidian《社会理论二十讲》生成笔记包含两条新 trace 与用户批准的第 40 页全文，未嵌原图；`batch_528...-revision-8dc44caebfca13f8.json` 于 11:38 记录修订通知已投送。客户端是否显示通知仍需用户确认。另 4 张扫描图与大批 unknown 页码继续待核对，不能称整本书验收完成。

11:43 后续周期 worker 对第 45 页扫描件的 0→0 冲突完成无标记对账：局部视觉复核明确 `has_underline=false`、无 OCR 缺口，故以 `visual_negative_no_marks` 清除该待对账状态，没有新建 trace。生产批次状态现列 3 张待对账扫描件，活跃总数仍为 205。其一是倒置的第 65/66 页附近扫描，原图局部可见「行动参照框架（action frame of reference）」连续画线，但该候选页码为 unknown，尚未审核入库；另两张分别有边注转写差异和第 41 页画线判断冲突。不能因第 45 页无标记对账而推断余下扫描可自动处理。

剩余第 41 页扫描的原图局部再次目视核验：v10 两个候选均为手写边注，第二条「1893. Harvard 开设社会学课程；1930. 索罗金整合，成立社会学系」大体可辨；第一条原图可辨「何谓资本主义与社会主义」，现有两版机器转写各自包含明显错字或缺字。旧版另有一条「森斯在那儿非常用功……」印刷文字 trace，当前局部视觉复核判无画线。由于旧 trace 含文字、手写边注转写不稳，自动对账保护正确保留此 capture 待审核；这次目视检查没有直接修改生产记录。

11:54–11:58 页码与取证方向修复：倒置扫描 `capture_e005...` 的照片顶部留有大块背景，真实页眉「39」出现在整图 y≈0.181；旧页眉阈值 y≤0.12 将其漏掉，误取正文旁「65」「66」为页码。改为要求页眉位于首条正文之上且与短页眉同行。对原图只读重跑后页码从 `[unknown,65,66]` 变为 `[39]`，页眉来源 `header_ocr`。第 23 页扫描同类，原先误用边栏「41」；v11 正式 worker 已将这 3 张仍待审核扫描分别更新为第 23、29、39 页候选，3 张均继续 `RECONCILIATION_REQUIRED`，活跃 trace 保持 205，第 39/40 页已审核 trace ID、页码与文字未变。旧 v8 pending run 不能再次触发对已对账扫描的提取，worker 现在只看每张图最新 run，并跳过已由较新版成功处理的 capture。取证裁片根据对应 observation 的倒置分析标记在投送前转正；真实第 23 页候选裁片目视朝向正确。Python Librarian 107 项、Node 插件 12 项通过。第 39 页扫描视觉模型将第一处画线辨为「行动参照框架（action frame of reference）」且 EPUB 匹配 1.0，但 OCR 候选仍包含未画线前后词；因此只供审核，不自动入库。此前“第 65/66 页附近”以及“第 41 页扫描”的表述是对错误机器页码的沿用，现以可见页眉 39、23 为准。

12:00 后补全审核证据：手写候选裁片增加边缘上下文，第 23 页第一条边注的真实裁片现能显示整条手写内容；只读局部多模态复读得到「《近期德国文献中的资本主义与社会主义」，与原图若干字形仍有歧义，不替用户裁定。第 39 页 v11 所报唯一 OCR 缺口先修正倒置原图坐标，再取证，裁片实际为书中行动要素图；局部多模态明确 `has_underline=false`。v12 worker 在疑似 OCR 缺口上补做最多四处局部复核，raw 保留结果；该图 line 45 正式返回无画线，审核列表缺口数 1→0。另两图缺口数仍 0，三图均保持待审核，活跃 trace 205，先前第 39/40 页两条已确认 trace 不变。服务端整图对账现在会拒绝仍有 OCR 缺口的 run；飞书原图工具新增当前 run 绑定的缺口裁片入口，避免模型将未复核缺口当成完整候选。v12 第 23 页弱墨迹的视觉结论变为 `uncertain=true`，该候选重新出现，说明弱边界仍不稳定，需用户审核。第 39 页「行动参照框架」候选文字仍过宽，不能自动对账。

v12 改动经 Librarian Python 111 项、OpenClaw 插件 13 项测试及配置校验通过；12:11 已同步 Librarian SOUL 并重启 Gateway，服务状态 active、插件列表显示 enabled。新增 OCR 缺口飞书工具调用尚未有真实入站验证，不能把插件单元测试等同平台投送成功。用户对三张待审核图的候选与旧 trace 尚未给出决议，故没有进行版本化替换。

12:16–12:20 历史 unknown 页码修订：从各自已保存的同一张照片 raw OCR 中识别短页眉旁的唯一印刷数字，兼容奇数页右侧和偶数页左侧布局；只处理单一未解页区、最新成功提取、活跃 trace 全部页码未知、无人工修正/知识候选依赖的 capture。六张照片的页眉分别为 31、32、34、38、40、42，涉及 25 条 trace。前五张由 Gateway 周期 worker 使用新增规则自动修订，34 页因 OCR 框轻微重叠暂未命中；允许同一行 OCR 框最多 0.01 的重叠后，正式物理 worker 修订最后三条。所有 25 条沿用原 trace ID，revision 1→2，正文和手写内容未变，原 observation 未改；当前 Library、索引和 Vault 笔记均可见这些页码，纸书批次 unknown 从 42 降至 17。隔离 Library 副本对剩余 34 页修订验证了幂等与内容不变；Python Librarian 115 项、插件 13 项通过。两次修订通知 marker 分别记录 12:16、12:20 的 sent_at，用户客户端展示仍待确认。其余多页区或页眉证据不足的 unknown 仍保留，不根据相邻照片补号。

时间来源修复的隔离验证：规范 §5.1 已说明 `ReadingTrace.created_at` 是记录版本时间；旧版纸书笔记把它无标签地写为每条 `⏱`，页码修订会使显示时间随 revision 改变。新渲染从对应 `PageCapture.received_at` 取值并标为「收图」，缺失时明确写「未知」；历史 v1–v5 生成块仍可精确识别，带人工修改的笔记仍由冲突保护阻止覆盖。周期物理 worker 增加生成笔记维护入口，批次即使等待审核也会检查现有生成笔记；每本笔记的审核冲突单独报告，不阻断其他批次。对生产 Library 的只读 SQLite 快照和 Vault 笔记副本运行该入口，83 条时间标签全部转换、无未标来源的旧标签；再次运行字节不变，追加人工文字后返回 `REVIEW_EDIT_CONFLICT` 且保留原文。没有在隔离验证中写生产 Vault。Librarian Python 115 项通过。正式 worker 落地后的笔记与投送仍待核验。

12:31 周期 Gateway worker 自行刷新正式 Vault 笔记；只读复核显示「收图」时间标签 83 条、trace 隐藏标记 83 条、旧版无来源时间标签 0 条、Vault 原图嵌入 0 条。最新 `RECONCILIATION_REQUIRED` capture 仍为 3 张，笔记维护没有替用户裁定待审核候选。此项不涉及新 trace 入库；未发修订通知，用户端笔记显示尚未单独确认。

多页区旧元数据复核：逐一目视 11 张原图，均只有一个清楚的印刷页眉；同图正文旁的 42–71 等数字是段落编号，旧提取器误当作页面边界。持久 raw OCR 对应页眉为 24、25、27、28、33、35、36、41、43，旧页区水平范围一致且只覆盖主纸页；相邻纸页窄边未进入痕迹区域。worker 增加多页区的严格页眉判据：页区 ID/坐标须与 observation 一致、旧编号须对应 raw margin marker、唯一页眉须与 marker 不同，人工文字或知识依赖继续由领域命令阻断。周期 worker 在隔离重放期间自行读取工作区新规则，已对正式库 11 张照片做 `CaptureResolution` 新版本，36 条活跃 trace 均 revision 1→2。生产只读复核：36 条原文字、bbox、observation 引用不变，索引 revision 全部一致，目标页码未知 16→0；纸书活跃 unknown 总数 20→4（余下 4 条属于待审核第 29 页扫描），Vault 仍为 83 个 trace 标记、无原图嵌入。隔离快照在运行中途取得，对当时尚未修订的 9 张照片重放成功，二次调用幂等；Librarian Python 116 项通过。这次也发现运行中的定时 worker 会加载尚未提交的工作区 Python 文件，今后此类规则须先在独立检出中隔离验证。相关批次没有新的发送回执，不把笔记落地等同用户端通知送达。

F05 领域边界增量复核：现行 OpenClaw 插件只允许配置一个 owner，双 owner 配置下 `workerArgs` 不生成任务参数、入站及检索工具关闭；正式配置只有一个映射 owner，Koodo/WeRead native 记录也各只有该 owner。adapter 原先可把同一 `source_id` 传给另一个 owner 再次导入，故新增 `digital_source_owners(kind, source_id)→owner_id` 绑定，并从历史 native 记录回填唯一归属；两个 adapter 在写入事务内拒绝跨 owner 重用。双 owner 正反例、旧库重开迁移及正式库只读快照验证通过：现有两来源都回填到原 owner，另一 owner 得到 `UNAUTHORIZED`，无新记录写入。Librarian Python 118 项、OpenClaw 插件 13 项通过。当前仍是单用户产品边界：如果用不同 `source_id` 别名指向同一个上游书库，native 层不能单凭 ID 识别同源；多 owner 正式支持仍需绑定上游账户/路径身份并做配置、凭证隔离，不能据此将 F05 宣称全面关闭。

12:46 定时 Gateway worker 在正式库自行执行新迁移；只读确认 `digital_source_owners` 中 Koodo 的 `local_koodo`、WeRead 的 `personal_weread` 均绑定到现有唯一 owner。随后 `digital-sync-status.json` 本轮 Koodo 与 WeRead 均为 success，Gateway 状态 active；本次未创建第二 owner 或接入第二套真实上游，现场证据不能替代未来的多用户验收。

F06 状态文件清点：目录中 7 个 `error` 文件来自旧版逐张照片批次，当前 `_processing_batches` 已将 23 个接收 batch 归入 2 个实际处理组；这 7 个文件不再是调度输入，不能当作 7 个正在失败的任务。现行两组状态均为 `partial`、`retry_attempts=0`，其中 22 图组的最新 run 有 3 张 `RECONCILIATION_REQUIRED`。但 5 图组状态仍显示 3 条页码未知，当前 trace 已修订，说明 `unchanged` 快速返回未刷新状态；快速返回也未明确排除更新的待审或失败 run。修复在独立检出中增加最新 run/待审判据，并在 `unchanged` 时按活跃 trace 更新状态文件，不触发重复提取或通知。测试覆盖较新待审/失败 run 和陈旧 `partial` 状态；正式 worker 运行后的状态仍须只读核验。

12:51 定时 worker 运行后只读核验：5 图组状态从旧的 `partial / unresolved_pages=3` 更新为 `processed / unresolved_pages=0`；22 图组仍为 `partial / unresolved_pages=4`，保留 3 项 `RECONCILIATION_REQUIRED`，没有把待审扫描误报为完成。两组状态时间均刷新到本轮，旧逐张错误文件仍作为历史记录存在；读取现行状态须以 `_processing_batches` 的组 ID 为准。本次修复的 Librarian Python 120 项通过，真实 Gateway 用户端未单独查询状态。

F07 当前 HEAD 复核更正：第 8 节早先“词表快照的持久化身份、明确 lineage 尚未实现”描述已过时。`process_capture` 现在把启用词表的完整配置保存为不可变对象，并在 `ProcessingRun.vocabulary_config_ref` 记录引用与版本；重试按配置摘要区分，`reconcile_extraction` 从该引用恢复词表且拒绝新旧摘要不同的自动替换。可确定的一对一重提取会在同一领域事务写入 `TraceRelation(relation=supersedes)`，测试覆盖词表同名异内容拒绝、同快照换 extractor 后 lineage 和知识依赖保护。此为当前代码及本地测试证据，尚未对所有旧版本关系和 3 张待审核扫描的实际对账做端到端复审；F07 的验收门槛仍须按 §2.3 核对，不能以这项更正宣称全面关闭。

A 阶段审核入口现场只读复核：`pending_extractions` 当前列出第 23、29、39 页三张扫描，旧 trace 数分别为 3、4、4，新候选数分别为 3、4、5；三者 OCR 缺口均为 0、候选 ID 各自唯一、审核决议均为 0。调用现有原图取证裁片函数检查全部 12 个候选，均得到非空图片；三张扫描都记录 180° 分析方向，正式 `prepare_evidence` 会按此方向转正再交给投送工具。此为本地只读证据，尚未有本轮 Feishu 入站 `librarian_review` 或用户决议；工具返回 `delivery_status=queued` 也不能替代客户端显示确认。

D 阶段三来源当前态只读验证：最近一轮数字同步 Koodo 的 118 条与 WeRead 的 4 条均为 unchanged/success；另有 83 条活跃纸书 trace。分别以每种来源的一条现有 trace 正文前 12 字作词面查询，`search` 均命中该 trace，来源 kind 分别为 physical、koodo、weread。生产 `trace_index` 205 条对 205 条活跃 trace，缺失或版本落后的投影为 0。这证明当前单 owner 的三来源可检索与索引就绪，不证明真实上游增改删周期、断网恢复或多 owner 隔离已端到端通过。

## 9. 现行实现计划（2026-09-29）

第 1–7 节仍是对 `d111ace` 的初审，不能用其中的旧行号和测试数量描述当前 HEAD。本节把整改转为可执行批次；每批结束时在第 8 节记录实际提交、测试、生产状态和未验项。除明确列出的真实用户审核外，调试与迁移均通过 Librarian 的 worker、领域命令或受信 Gateway 工具执行，不手改生产数据库或 Vault 生成块。

| 顺序 | 实现范围与当前状态 | 必须形成的证据 | 完成门槛 |
|---|---|---|---|
| A · 首书剩余扫描对账 | 第 23、29、39 页扫描现分别为 3、4、5 个待审核候选，OCR 缺口均为 0；第 39/40 页两条真人确认的画线已入库。用 `librarian_review`、`librarian_evidence` 给用户展示旧 trace、新候选及扫描裁片；用户决定由 `librarian_review_decision` 记录，`librarian_review_finalize` 对内容完整且无缺口的整图做版本化替换，worker 刷新数据库、索引、Vault 并通知。第 39 页「行动参照框架」候选多含未画线词，第 23 页弱线视觉判断不稳、首条手写边注字形未定，不得按 OCR 文本自动接受 | 每张图当前 run ID、候选稳定 ID、用户来源 message ID、接受/拒绝与更正文字、旧新 trace/revision/事件/索引对账、Vault 摘录和通知回执；用户端裁片及通知显示另行确认 | 3 张图不再 `RECONCILIATION_REQUIRED`，用户认可的画线和笔记在 Library 与微信读书式 Vault 笔记中一致；不确定内容保持待审，不以“处理成功”掩盖误识别 |
| B · 页码与历史元数据 | F02/F03 及模块复核。用同一照片可见页眉修订历史 unknown，限定单一未解页区、可靠 OCR、未人工修正/无知识依赖；以 `CaptureResolution` 新 revision 保留原 observation 和内容。继续只读清点旧版页码、bbox、文本 basis、自动会话归属；多页区或相邻照片推断不得自动补号 | 受影响 capture/trace 清单、每项原图页眉及 raw OCR、修订前后页码/置信度/basis、同一 trace 内容散列、事件与索引、Vault 及检索结果；打乱上传顺序和双页码反例 | 有直接可见证据的页码可检索；无证据者保留 unknown；历史错误通过新版本而非改写 observation 纠正 |
| C · 领域与桥接安全复审 | 对照 §30 和 §2.3 逐入口检查 `store.py`、`pipeline.py`、Schema、Gateway bridge、review/finalize、数字 adapter；特别复核 F05/F07/F08：source→owner 唯一归属、知识依赖与词表版本保护、领域提交与索引投影分离；补齐错误响应层级和 queued/实际送达语义 | 双 owner/account/chat、重复/变更附件、知识晋升/人工修正、索引插入/消费故障、重启恢复和旧版迁移的正反例；相关跨对象不变量与规范条款逐项映射 | 非法关系在所有写入口均拒绝且无部分提交；索引故障不重跑提取；现行 HEAD 的四类模块取得逐项复审证据，不能只凭 Schema 或套件全绿签发整体通过 |
| D · 运行与三来源验收 | F01/F04/F06、M2。验证无 EPUB/无 Vault/未知书页的普通图片仍进入观察；受限自动会话按 90 分钟/6 小时降级；物理 worker 不被坏批次或慢数字源阻塞；Koodo/WeRead 的真实周期增改删和网络恢复 | Gateway 真实入站、周期任务状态、故障注入、有限重试、实际三来源 SearchHit 与来源身份；记录模型调用数、耗时和冷/热启动成本。核显仅有隔离基准，安装稳定驱动与生产路由前不宣称已启用 | 不丢已接受照片；错误可定位并恢复；同 owner 三来源可检索且错误归属不能进入库；生产成本可量化 |
| E · 规格验收与交接 | 复跑 §5 的 AC-01–26 并区分本地、现场、未验；回填 `LIBRARIAN_V0_8_HANDOFF.md` 与本报告。§38.1 p159/166/171/184 四张标注照片及 `source-design.txt` 已按用户指示暂缓，不用同号 Vault 孤图代替 | 每条 AC 的当前证据链接、未完成原因、修复提交、真实运行与用户确认记录；延期样本单列 | 核心 P1 与真实闭环均经逐项验收后再考虑 `release-v0.8`；暂缓输入保留“延期/未验”，不得记“通过” |

执行顺序：先完成 B 中不依赖用户的直接页眉修订，再等待 A 的飞书逐图审核；其间可并行推进 C/D 的只读清单与隔离测试。A 的生产替换只由受信用户决定触发。每批在生产落地前先用隔离 Library/Vault 验证字段、索引和事件，再由正式 worker 执行；若新旧分组或文字改变且证据不充分，保留待审核状态。E 仅在 A–D 的相应证据齐备后更新判定。

B 的后续清单：现有 11 张旧版多页区照片与笔记时间来源已按第 8 节修订并复核；纸书活跃页码未知尚有 4 条，均在第 29 页待审核扫描，不越过 A 的用户决议自动补号。继续对其余历史 trace 的 bbox、文本 basis、自动会话归属和通知状态做只读清点。不得把 EPUB 页码、边注数字或邻图顺序当作印刷页码；对仍无法从本图证明的页码保留 unknown。

### 9.1 本次审计澄清纳入的专项复核任务

§2.1–2.3 的更新要求分别复核数据结构、元数据、Schema 和桥接入口。以下任务属于上表 B/C/D 的明确工作包；“已有局部证据”只表示第 8 节记载的具体路径，不代表整类模块通过。每项以当前 HEAD 为基线建立条款→写入口→验证结果的清单，记录修复提交和历史数据处理结果。

| 任务 / 对应批次 | 实施步骤 | 验证与交付物 | 当前边界 |
|---|---|---|---|
| R1 · 领域引用与事务（C，F07/F08） | 按规范 §30 逐项列出 `store.py`、`pipeline.py`、知识晋升、review/finalize、数字 adapter 的写入口；检查 owner 链、引用存在性、revision/current 指针、detection/observation/resolution 关联、事件与 trace 同事务、原始 evidence 只增不改。用旧库迁移样本复核新约束 | 每条不变量对应执行位置和正反例；跨 owner、悬空引用、旧 revision、知识依赖及人工修正的失败均无部分提交；注入索引故障后从已存 trace 恢复，extractor 调用次数不增加 | F08 和 F07 已有指定路径的修复与测试记录；尚未覆盖全部写入口及旧版本链 |
| R2 · 历史元数据与证据边界（B，F02/F03/F04） | 只读枚举活跃及受影响历史 trace，将页码、身份、时间、作者、basis、confidence、locator、bbox、provenance、配置版本逐字段追溯到本图、原始返回、EPUB、用户决议或规则；重点核对早期 OCR/EPUB 扩文、自动会话及 bbox 对应的可见文字 | 受影响记录清单与字段来源表；照片局部、raw、EPUB 对齐和旧/新 revision 对照；无照片证据的文字不进入照片原文，未知字段保持 unknown；经确认的更正走领域修订并保持历史可读 | 11 张页码和笔记时间已有局部修订；第 29 页 4 条 unknown 与三张待审扫描依赖 A，不能自动决议 |
| R3 · Schema 与语义校验（C） | 对规范正文 MUST 和 `schemas/` 的字段、枚举、null/unknown、状态组合逐项比对；把结构校验、跨对象事务校验、外部证据真实性分配到明确执行层；检查旧版对象读取和迁移 | 条款→字段→校验函数/事务→测试矩阵；合法 JSON 但错误 owner、虚假页码 basis、单行 bbox 对应整段文字、失效 revision 等反例由应用层拒绝或进入待审；无法程序验证的真实性标明人工证据 | 契约测试只证明覆盖的结构和语义样本；尚无逐字段完整结论 |
| R4 · Gateway 与投送边界（C/D，F05/F06） | 清点图片、session、search、evidence、review/decision/finalize、digital sync 的每个入口；核对受信身份、account/chat→owner、source→owner、幂等键及 payload 冲突、`ErrorResult`、重启恢复；把“已排队”“平台发送成功”“用户端已显示”分成独立状态 | 插件替身和真实消息分别留证；双 owner/account/chat、重复消息与变更附件、坏批次、慢上游、投送失败重试均有正反例；错误可查询且不会伪报送达或阻塞其他照片 | 现有单 owner 绑定、三来源检索与部分飞书入口有证据；跨账户、实际投送和故障恢复尚未完整验收 |

实施顺序：R2 的只读清单与 R1/R3/R4 的入口清单先行；发现违反不变量时先在隔离库复现并修复写入口，再经正式 worker 或受信工具形成版本化结果。A 的三张扫描继续等待用户逐项审核；不能用专项复核代替用户对画线和手写文字的判断。R1–R4 完成后，才在 E 中更新 AC-01–26、handoff 与模块结论。
