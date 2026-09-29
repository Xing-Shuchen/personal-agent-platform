# Librarian 修改与 specification 一致性审计

初审日期：2026-09-28；报告澄清更新：2026-09-29。初审结论（针对 `d111ace`）：**部分一致，不满足该版本对应 specification 的完整验收条件。建议暂不发布 release-v0.8。**

**数据结构、元数据、Schema、桥接模块均未获得“整体无问题”的审计结论。** 领域分层与部分持久化、修订、幂等和隔离检索路径有测试证据，但已确认的问题横跨元数据真实性、跨对象依赖、事务恢复和桥接授权；不能将问题仅归为 worker/OCR 的识别效果。Schema 校验通过不等于数据语义正确，也不等于端到端链路通过验收。

**版本适用说明**：第 1–7 节的原始发现、行号、测试数量和 AC 状态以 `d111ace` 为准；第 8 节记录后续整改与现场验证，其中已有原问题修复、入口补齐及测试数量增加。本次更新补充结论边界和模块复核要求，不是对最新 HEAD 或未提交改动的一次完整复审。不得将初审缺陷无条件套用到最新代码，也不得因后续单项成功记录而关闭整个模块的审计。

### 当前交付快照（2026-09-29；历史初审见下文）

| 范围 | 当前状态 | 可核对证据 |
|---|---|---|
| 首书纸书数据与笔记 | BookScan 重建了 27 张保留照片对应的 73 条活跃纸书 trace；Vault 按 EPUB 章节与正文顺序呈现，原图不进入 Vault | §§10、14、17；私有原图与派生数据恢复测试 |
| 手写复核工具 | 15 条手写裁片网页、版本化确认/校正/误检排除及 Vault 刷新已交付；本机 `127.0.0.1:8765` 在监听 | §§14、17；人工逐条判断留正式运行，生产库 0/15 条手写确认 |
| 本地约束与回归 | R1 修订事件回滚、R3 候选状态迁移及旧可选字段兼容、R4 入站失败查询已补；最近完整 Python 回归 522 passed，插件 18/18 | §§19–21；`ab27186`、`634a68e`、`cf2b4f7`；后者专项 6/6 |
| 用户明确延期 | 普通新图旁注/角括号发现和严格墨线与 EPUB 扩句边界本轮跳过；§38.1 四图与底稿暂缓 | §14–15、spec 末尾首书决策；不记为能力通过 |
| 正式运行核验 | 真人手写判断、真实飞书错误/附件重放/平台投送与客户端显示、数字上游变化和慢源恢复留待现场 | §§9、15、19；当前 Gateway active，插件上轮检查 loaded，无上述新现场结论 |

上表只标识已交付的功能与待运行证据，不把本地测试升级为 `release-v0.8` 全部 AC 通过。第 1–10 节出现的旧 RapidOCR 路径、旧 trace 数量和旧待审 run 均是历史记录；现行入口及数据以 §§10–21 的较新状态为准。

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

历史复现代码位于后续审计提交的 Git 历史中（`8a5494e:docs/audits/librarian_20260928_repro.py`）；旧图像处理模块已按用户要求从当前工作树移除，因此该脚本不再是现行可执行测试。历史结果：[librarian_20260928_repro.json](librarian_20260928_repro.json)。当时的断言确认被审计版本的缺陷行为，不能当成整改后的合格测试。

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

R2 历史引文与空间关系首轮只读清点：以正式 Library 的 `records.current=1` 且 trace `status=active, medium=physical` 为范围，共 83 条，关联 25 个 observation。70 条有印刷文字、13 条无印刷文字。按 trace 的 `detection_ids` 取到 146 个印刷文字区，逐个回读各 observation 的不可变 raw OCR 对应行；146 段文字均为各自 OCR 行去空白后的子串，没有发现当前活跃引文直接使用 OCR 范围外的 EPUB 扩文。70 条中有 1 条 trace 文字不等于 observation 的印刷区拼接，字段明确标记 `basis=user_statement`，是人工更正，不能当作 OCR 一致性错误。另检查 83 条 trace 的 305 个关联 detection：ID 均存在、页区一致，detection bbox 位于 trace bbox 与页区 bbox 内，未发现结构性空间越界。本项只证明文字来源和几何包含关系；**不证明墨线确实覆盖该文字、OCR 字词准确或所有历史 superseded 版本正确**。第 23、29、39 页待审扫描仍按 A 逐项核对，尤其第 39 页候选的过宽文字不得因本项计数而自动接受。

F06 当前调度路径复核：Gateway 定时恢复和新图片触发均以 `--physical-only` 启动纸书子进程，定时恢复另以 `--digital-only` 启动数字子进程；两者分别使用非阻塞 `physical-worker.lock`、`digital-worker.lock`。纸书批次循环逐项捕获异常并写 `batch-status`，已有“坏批次在前、好批次在后”隔离测试。另在临时 Library 中让数字同步替身持续占用数字锁，同时运行纸书模式，纸书空队列在约 0.001 秒内完成，数字任务随后释放；这证明现行进程模式和锁互不等待，但**未**验证有真实照片、SQLite 写入竞争或慢真实 WeRead 请求时的端到端延迟。正式 Gateway 服务此时为 active，最近数字同步状态两来源均 success；子进程标准输出仍被忽略，完整故障可观测性和重启恢复继续列在 D/R4。

R4 错误响应契约修复：七个 Gateway Python 桥接入口原来只返回 `error.code`（图片接收还原样返回异常文字），与 §27.4 的五字段 `ErrorResult` 不符。`3a47e89` 增加统一脱敏响应，包含 `code / stage / retryable / message / details`，保留待审、版本冲突和上游错误等实际错误码；未知异常统一为 `BRIDGE_FAILED`，不暴露异常原文或私有路径。Schema 的错误码枚举同步覆盖这些已用代码。七入口非法 JSON 子进程测试及敏感文本反例通过，Librarian Python 128 项、OpenClaw 插件 13 项、契约离线校验通过。该修复证明本地桥接失败形状；插件对超时、投送失败与 `queued`/客户端送达的端到端语义仍需 R4 现场复核。

R4 原图投送媒体寿命修复：`librarian_evidence` 原先等待 `ctx.delivery.send` 后立刻删除允许媒体目录中的裁片，却只向调用方报告 `queued`；若通道稍后读取 `mediaUrl`，文件可能已不存在。`55d61e7` 保留已入队的私有裁片最多一小时（定时删除，重启后由下一次取证清理过期文件），失败入队立即清理；桥接临时文件仍在调用结束后删除。插件测试证明 `send` 返回后路径仍可读取、失败时无遗留，14 项通过。13:11 重启 Gateway 后服务 active、插件 enabled；此为本地文件寿命与加载证据，尚不能替代飞书平台实际发送回执和用户端看见**当前扫描版本**的确认。工具继续只报告 `delivery_status=queued`，不宣称送达。

R1/F08 索引事务边界复核与修复：初次照片提取和重提取对账此前已把索引投影移至领域提交之后，但 `correct_trace`、`resolve_capture`、数字导出和 Koodo/WeRead native 创建/更新/删除及待审来源对账仍在领域事务内更新 `trace_index`。这会使索引插入或删除故障回滚用户更正、页码修订或来源同步。`48099cd` 将这些写入口改为先提交 trace revision、来源状态与事件，再由独立的最佳努力索引修复处理投影；重放同一来源也会修复滞后索引。隔离库注入索引异常后，纸书更正、页码修订、数字导出及两种 native 同步的领域结果保留，解除故障后可重建/重放检索。Librarian Python 133 项、插件 14 项、契约校验通过。正式库只读显示 205 个活跃 trace 对 205 条索引、缺失/旧 revision 为 0；这证明当前投影就绪，不替代所有故障点和旧迁移链的完整 R1/F08 验收。

R1 引用链写入边界增补：此前知识候选的公开创建路径会校验当前 trace，但 `Library._put` 对 TraceRelation、KnowledgeCandidate 的历史版本引用以及纸书 trace 的 capture→observation→resolution→detection 关联只执行单对象 Schema。`399c3f5` 在最终存储写入口增加同 owner、指定 revision 存在性及纸书页区/身份/bbox 一致性检查，保留历史 superseded trace 可作为 lineage 目标。伪造检测 ID、换用同 owner 其他 capture、缺失或空 trace revision、跨 owner 关系与知识候选均被拒绝且不写半条记录。正式库只读备份用新检查遍历 678 个纸书 trace 版本、70 条 TraceRelation 和 0 条 KnowledgeCandidate，全部兼容；Librarian Python 136 项、契约校验通过。这覆盖所列引用，不表示 §30 其余每条不变量或知识服务外部对象已完成复审。

R1 目录与会话上下文追加检查：`register`、`start_session` 等公开路径原已检查部分引用，但最终 `_put` 可写入形状合法而跨 owner 或互相矛盾的 Edition、BookInstance、ReadingSession、CaptureResolution。`0880d5c` 在写入边界核对 Edition→Work、Instance→Edition、Session 的完整目录链，以及 Resolution 的 Capture、Session 和目录身份；部分未知上下文仍可保持 `null`。跨 owner Work、缺失 Edition、Session 工作归属错误及 Resolution 缺失目录对象的反例均在事务内拒绝且无部分记录。正式库只读备份的 1 个 Edition、2 个 BookInstance、4 个 ReadingSession 与 137 个 CaptureResolution 历史版本均通过新检查；Python 138 项及契约校验通过。此项不证明书目信息真实、全部旧元数据正确或 §30 的附件幂等与事件恢复已全面复审。

R1/AC-01 并发摄取幂等修复：两个独立 Library 连接在首次查询后同时接受同一来源消息、附件字节和幂等键，旧代码让先提交者返回 `accepted`，后到者因 `source_items`/`idempotency` 唯一约束得到 `IDEMPOTENCY_CONFLICT`，违反同一命令重试返回同一凭据的要求。`d029cc1` 在唯一约束竞争回滚后重查已提交命令；仅当业务指纹完全相同且原图对象仍可读取时返回胜出者 receipt。并发隔离测试得到相同 `batch_id`，只生成一个 capture、一个幂等记录和一条接收事件；同一来源身份改用不同幂等键仍明确冲突。Python 139 项和契约校验通过。此为受控并发反例，不替代真实 Gateway 重复消息、附件变化和进程重启的全链路验收。

R1/§30 捕获链写入边界增补：`PageCapture`、`ProcessingRun`、`PageObservation` 此前经正常流程创建时关系一致，但最终 `_put` 未核对 capture 是否属于同 owner 的 batch、run 是否指向存在的 capture、observation 的 run/capture 是否一致。`686fb10` 增加这些写入校验；同 owner 下伪造未列入 batch 的 capture、悬空 run、跨 capture observation 和悬空 processing run 均在事务内拒绝，且不留下记录。正式库只读核对 23 个 CaptureBatch、27 个 PageCapture、241 个 ProcessingRun 版本、142 个 PageObservation 版本，无对应关系违例。Python Librarian 140 项及契约离线校验通过。该次未覆盖 observation 内检测 ID 与链接的最终写入校验；后续验证见下一段，R1 全项仍开放。

R1/§30 observation 内部约束增补：原 `_check_observation` 只由 `process_capture` 调用，直接走最终 `_put` 时可保存重复页区/检测 ID、失效文字链接或页区外 bbox。`4fb048c` 将该语义检查提为提取与存储共用的验证函数，保持提取失败归类为 `EXTRACTION_SCHEMA_INVALID`，存储边界拒绝为 `VALIDATION_FAILED`。同一 run 的伪造重复检测 ID、悬空文字链接在事务内被拒绝；正式库 142 个 PageObservation 历史版本只读校验为 0 违例。Python Librarian 140 项和契约离线校验通过。检查只证明几何包含与引用结构，不证明墨迹与引文的视觉真实性。

R1/§30 空间标签写入边界增补：normalizer 原会计算纸书 trace 的方位，但最终 `_put` 可接受页区外 bbox、与页区不一致的 side 或与坐标不一致的 vertical/horizontal。`498512e` 复用同一方位算法，在写入时核对页内非零面积、side 和五乘三方位；无 bbox 时仅允许没有 detection 和方位标签。伪造反例在事务内拒绝；正式库只读备份的 678 个纸书 trace 历史版本全部通过新增检查。Python Librarian 140 项及契约离线校验通过。此检查不替代照片墨迹与文字覆盖范围的人工真实性审核。

R3/§30 页区几何语义增补：`CaptureResolution.pages` 的单项 BBox 仅有坐标范围 Schema，原可接受重复 page ID 或零面积页区。`97998ee` 在共用 `validate` 中拒绝这两类合法 JSON、错误语义的记录；直接 `_put` 负例无部分提交。正式库 137 个 CaptureResolution 历史版本只读校验为 0 违例；Python Librarian 140 项及契约离线校验通过。页码数字及其依据是否来自本图可见印刷内容仍需 R2/A 证据核对。

R4 插件错误契约增补：七个 Python bridge 已返回脱敏的五字段 `ErrorResult`，但 OpenClaw 插件 `runPythonBridge` 原只保留 `code`，将错误消息统一变为 `bridge failed`，使 agent 看不到失败阶段及是否可重试。`07f99f3` 让异常携带 `code / stage / retryable / message / details`，并在异常显示文本中保留脱敏的状态；子进程启动、超时、输出过大或非法 JSON 归一为 `BRIDGE_FAILED`，不显示原始 stdout。15 项插件测试通过；本机真实 Python `gateway.search` 无库反例经插件返回 `OBJECT_STORE_UNAVAILABLE`、`gateway.search`、`retryable=true` 及固定脱敏消息。13:45 重启 Gateway 后服务 active、插件 enabled。此证据不证明飞书客户端展示了错误，也不证明入站 hook 失败持久可查询或平台媒体送达。

R1 数字 trace 目录归属增补：最终 `_put` 原只对纸书 trace 校验 capture/resolution 引用；数字 trace 即使 `work_id` 指向另一 owner 或不存在的 Work，只要单对象 Schema 合法就可写入。`aa39e57` 对 Koodo/WeRead trace 在最终写入核对 owner 范围的 Work→Edition→Instance 链及可选 ReadingSession 归属。同 owner 下伪造跨 owner Work 和悬空 Work 的反例均拒绝且无部分记录。正式库只读备份的 122 个数字 trace 历史版本全部兼容；Python Librarian 141 项及契约离线校验通过。数字上游 source→owner 凭证绑定和原始 payload 真实性仍属 R4/F05，不因目录引用修复而关闭。

R1 trace/event 事务复核：当前生产库只读对照 `records` 的全部 800 个 ReadingTrace 历史版本与 outbox 的 `reading.trace.created/corrected` 聚合引用，得到 466 条创建、334 条修订事件，版本匹配 800/800，缺失、孤儿及重复版本事件均为 0。静态逐入口检查了纸书初提取、重提取对账、文字/页码更正、数字导出及 Koodo/WeRead 的创建、更新、删除、待审来源对账；这些领域路径均在同一个 `Library.transaction` 内写 trace 与事件。`b3fa5df` 另以 SQLite outbox 插入故障验证初次纸书提取和数字导出：trace、run/observation 或 Work、来源导出记录均回滚；移除故障后同输入可成功重试。Python Librarian 143 项及契约离线校验通过。`_put` 是内部方法，本身不强制调用者写事件；这些证据不证明外部消费者已收到事件，也不覆盖每一种修订入口的故障注入。

R1 原始对象恢复性只读审计：`df93ce6` 新增 `librarian_object_integrity.py`，遍历正式库 `records` 及 extractor/数字待审 sidecar 的 ObjectRef，检查私有路径、文件可读性、字节长度和 SHA-256，并列出未引用对象。正式库本轮共有 2,891 处引用、290 个独立对象；290 个散列及长度均匹配，缺失路径、孤儿文件和无效 sidecar JSON 均为 0。临时 Library 中将已接收照片文件改坏后，脚本从 `ok` 变为 `corrupt`，证明该检查能检测散列错误。运行命令：`.venv/bin/python docs/audits/librarian_object_integrity.py --root var/librarian`。此结论只覆盖本机当前快照；没有执行备份还原、断电恢复或未来孤儿回收，不以零孤儿证明回收流程已经完善。

R2 历史文字范围只读审计：`156574a` 新增 `librarian_historical_text_scope.py`，逐个比较 OCR 来源的印刷区文字与同一 raw OCR 行及其 EPUB 对齐行（仅去除空白）。正式库扫描 677 个 OCR 印刷区，发现 11 个旧 v2/v3 印刷区的文字不在对应单行范围内，分布于 3 张 capture；22 个 ReadingTrace 历史版本引用这些印刷区，但当前活跃 trace 引用数为 0。其余 666 个印刷区通过此结构性范围检查。运行命令：`.venv/bin/python docs/audits/librarian_historical_text_scope.py --root var/librarian --details`，输出只含 ID 和字数，不含正文。这说明早期版本存在跨行扩文，不能据此断言这些旧照片原文正确；不可变 observation 与 revision 保持原样，若需更正应走版本化领域命令。本检查也不证明 OCR 准确、墨线覆盖或 EPUB 对齐正确。

A 阶段真实飞书取证：13:57 用户发送「查看《社会理论二十讲》待审核扫描」，受信 librarian trajectory 调用一次 `librarian_review`，成功列出最新 3 张 pending run：第 39 页 5 组、第 29 页 4 组、第 23 页 3 组。13:58 用户再发「都发我看看吧」，同一受信会话调用三次 `librarian_review(capture_id)` 和 12 次 `librarian_evidence(candidate_id)`，12 个工具结果均为 `delivery_status=queued`；agent 随后发出含差异摘要的飞书文字回复。用户随后确认客户端实际收到 12 张扫描局部；这为该次投送提供客户端证据，不等于未来每次排队都已送达。用户尚未作 accept/reject 决定；三张 capture 保持 `RECONCILIATION_REQUIRED`。第 39 页旧 trace 页码为 65/66、新候选标 39；第 23 页旧 41、新 23，这些差异须按照片可见页眉核对，不凭模型或 EPUB 自动接受。此次 agent 两轮用量分别为约 4.9 万、6.4 万输入 token（另有缓存读取约 4.8 万、9.8 万），一次索取 12 张裁片的成本偏高，D 阶段需记录并优化调用方式。

R2 元数据字段来源续审：正式库全部 678 个纸书 ReadingTrace 历史版本逐条回查其引用的指定 CaptureResolution revision，页码、页码置信度及 work/edition/instance/session 四项身份均与对应页区和身份值一致（字段不一致 0）；这是版本引用一致性，不是页码真实性。354 个版本页码 `vision/resolved`，324 个 `unknown/unresolved`；身份来源 636 个版本为 `edition_fingerprint`、42 个 unknown。83 条当前活跃纸书 trace 中，79 条页码为 `vision/resolved`，4 条 unknown，身份全部由 `edition_fingerprint` 绑定，`marked_at` 与 `mark_author` 全为 unknown。关联的 146 个印刷区去空白后全部是同一 raw `ocr_text` 行的子串（110 个也恰好匹配 EPUB 对齐行，36 个只匹配 OCR 行），未发现当前活跃印刷区仅凭 EPUB 扩文；这仍不能证明 OCR 字词或画线边界正确。历史中有 3 个逻辑 trace 的 6 个版本引用 confidence 0.7、`basis=vision` 的邻图推断旧页码，现均为 superseded，未作原位改写。`session_scope` 中两条自动会话已 `selected=0`、最后分配时间为 9 月 28 日；9 月 29 日用户明确启动的会话 `selected=1`，其进度依据为 `user_statement`。当前 83 条纸书痕迹关联旧自动会话，记录既有 capture 归属，不表示该会话仍被长期自动选中。

A/C 旁注审核入口修复：`7eb75fb` 发现正式 `librarian_review_finalize` 把所有接受的候选都强制按印刷 OCR/EPUB 句子核边界，导致第 23、29、39 页共 4 个纯 `margin_note` 候选即便被用户确认也无法提交；`reconcile_extraction` 还会把旁注更正误写到 `printed_text`。现对纯旁注要求非空的审核转录，跳过不适用的印刷句界检查，并将用户明确给出的更正写入 `content.annotation`，标记 `basis=user_statement`；画线继续执行原句界校验。隔离库端到端测试让同一扫描的画线与更正旁注均经决定和 finalize 入库，检查旁注的印刷文字保持空；相关 45 项 Python 测试通过。正式 3 张待审图无新增决议，未执行生产 finalize，Vault 与客户端结果仍待真人审核。

R1/R2 来源对象续审：正式库 678 个纸书 trace 历史版本各有 3 个 provenance 对象引用，逐项都与所指 PageCapture 原图、PageObservation 派生图和 raw_output_asset 完全相同，错链 0；先前对象完整性审计另证明这批底层文件可读且散列吻合。27 张 PageCapture 的 `captured_at` 均为 unknown，而 `received_at` 保留飞书接收时间；3 个当前 ReadingSession 的 `started_at`、`ended_at` 也均为 unknown。现行 normalizer 从 observation 的检测链接拼接印刷/旁注文字和最小置信度，以 ink 与关联文字区域的并集生成 bbox；因此 trace bbox 是取证范围，不是仅覆盖墨线的精确边界。`marked_at`、作者、书籍置信度保持 unknown/null，页码置信度直接取指定 resolution 页区。此字段来源表述已核对 `pipeline.normalize` 和生产数据；OCR 真值、可见笔迹及用户端图片显示仍需 A/R2 的照片复核。

用户于 9 月 29 日明确调整分工：暂停纸书识别，识别方法由用户另行确定；当前只实施框架和数据 Schema。`ec34679` 为插件增加 `physicalWorkerEnabled` 开关，本机私有 OpenClaw 配置已置为 `false`，配置校验与 Gateway 重启后确认服务存活且没有纸书 worker 进程。图片接收、原图私有对象和数字 worker 保留；既有三张待审扫描不自动识别、对账或入库。`e362654` 在纸书 trace 写入入口强制 provenance 与原图/派生图/raw 三个对象精确相符，并强制页码置信度等于所引用 resolution 版本的页区置信度；隔离反例拒绝且旧 revision 未变，2 项定向 Python 测试及 16 项插件测试通过。正式库 678 个历史纸书 trace 版本只读核对均符合这两条关系，因此该约束无需回填既有记录。运行文档新增 `process_capture` 的可替换识别输出契约；没有运行新的 OCR、模型识别或正式扫描 finalize。

R3 数据契约续审：`TextField`、`TimeField`、`IdentityField`、`PageField` 的 JSON Schema 现在要求 `basis=unknown` 时值与 confidence 都为 null；其他 basis 必须有值，但评分仍可为 null。此约束落实 §13 的未知值不得补猜原则，没有改变字段集合或 `schema_version=0.1.0`。只读复核正式库 1,450 条历史 records，新增约束下无 invalid；42 个正例、43 个反例及 18 个入口的离线契约检查通过。合成正例中 4 个「无时间值却标 exif」的来源错误已改成 unknown；4 组定向 schema 正反例和 `test_librarian_store.py` 13 项测试通过。此项只保证值和来源状态相容，不能证明照片正文、手写字形或页码真实性。

纸书图像处理方案已按用户提供的 `explore/segement-ocr-alignment` 分支接入现有 Librarian：仅移入 `bookscan/` 处理代码、必要配置/manifest/哈希及测试，不将探索分支的 22 张原图和 EPUB 合入主线。`worker.py` 使用 `bookscan_adapter.py` 调本地 PaddleOCR 分割、逐行识别和可选 EPUB 对齐，处理结果仍经 `process_capture` 的 `PageObservation` Schema、领域关系、review、revision、Vault 和通知链路；不调用旧 RapidOCR/全页模型作为内容提取 fallback。无 EPUB 可保留图片 OCR 结果并显示对齐待审。匹配样本精确哈希时使用其预标注手写/角括号区域；新照片目前不会自动找出这两类区域，不能把缺席当无笔记。EPUB 标点扩展仅保存在 raw 取证，不写成照片可见 `printed_text`。历史 trace 不自动替换，新输出进入对账。隔离环境用真实权重跑一张样本，生成 4 条划线与 2 条旁注并通过 Librarian Schema；173 项 Python 与 16 项插件测试通过。没有全页人工真值，不能宣称识别准确率；正式纸书 worker 仍关闭，未重跑生产扫描。详见 `agents/librarian/runtime/BOOKSCAN_INTEGRATION.md`。

| R2 纸书字段 | 当前写入来源与已核对证据 | 尚未由此证明 |
|---|---|---|
| 页码、页码置信度 | observation 页区进入指定 `CaptureResolution` revision，trace 拷贝同页区；678/678 版本字段一致 | 页眉是否被正确识别；旧邻图推断仅保留为历史 |
| Work/Edition/Copy/Session | `capture_context` 的 `edition_fingerprint` 或 unknown，经 resolution 版本进入 trace；678/678 版本字段一致 | 指纹是否对应照片实物及自动归属时限的所有反例 |
| 印刷文字、旁注、置信度 | normalizer 拼接关联 detection 的文字并取最小文本置信度；明确用户更正改为 `user_statement` | OCR 真值、手写辨认、墨线是否覆盖整句 |
| bbox、方位 | 墨迹和已链接印刷区 bbox 的并集、页区内五乘三方位；结构校验已过 | bbox 不等于精确墨线轮廓 |
| 时间、作者 | `captured_at`、`marked_at`、`started_at`、`ended_at`、`mark_author` 保持 unknown；接收时间单存 | 实际阅读或拍摄时间与执笔人 |
| 原始证据 | 每版 trace 关联原图、派生图、raw 对象；678/678 引用精确匹配，290 个独立对象的散列已另验 | 备份恢复、视觉真实性或飞书客户端送达 |

## 9. 现行实现计划（2026-09-29）

第 1–7 节仍是对 `d111ace` 的初审，不能用其中的旧行号和测试数量描述当前 HEAD。本节把整改转为可执行批次；每批结束时在第 8 节记录实际提交、测试、生产状态和未验项。除明确列出的真实用户审核外，调试与迁移均通过 Librarian 的 worker、领域命令或受信 Gateway 工具执行，不手改生产数据库或 Vault 生成块。

| 顺序 | 实现范围与当前状态 | 必须形成的证据 | 完成门槛 |
|---|---|---|---|
| A · 首书剩余扫描对账 | 第 23、29、39 页扫描现分别为 3、4、5 个待审核候选，OCR 缺口均为 0；第 39/40 页两条真人确认的画线已入库。用 `librarian_review`、`librarian_evidence` 给用户展示旧 trace、新候选及扫描裁片；用户决定由 `librarian_review_decision` 记录，`librarian_review_finalize` 对内容完整且无缺口的整图做版本化替换，worker 刷新数据库、索引、Vault 并通知。第 39 页「行动参照框架」候选多含未画线词，第 23 页弱线视觉判断不稳、首条手写边注字形未定，不得按 OCR 文本自动接受 | 每张图当前 run ID、候选稳定 ID、用户来源 message ID、接受/拒绝与更正文字、旧新 trace/revision/事件/索引对账、Vault 摘录和通知回执；用户端裁片及通知显示另行确认 | 3 张图不再 `RECONCILIATION_REQUIRED`，用户认可的画线和笔记在 Library 与微信读书式 Vault 笔记中一致；不确定内容保持待审，不以“处理成功”掩盖误识别 |
| B · 页码与历史元数据 | F02/F03 及模块复核。用同一照片可见页眉修订历史 unknown，限定单一未解页区、可靠 OCR、未人工修正/无知识依赖；以 `CaptureResolution` 新 revision 保留原 observation 和内容。继续只读清点旧版页码、bbox、文本 basis、自动会话归属；多页区或相邻照片推断不得自动补号 | 受影响 capture/trace 清单、每项原图页眉及 raw OCR、修订前后页码/置信度/basis、同一 trace 内容散列、事件与索引、Vault 及检索结果；打乱上传顺序和双页码反例 | 有直接可见证据的页码可检索；无证据者保留 unknown；历史错误通过新版本而非改写 observation 纠正 |
| C · 领域与桥接安全复审 | 对照 §30 和 §2.3 逐入口检查 `store.py`、`pipeline.py`、Schema、Gateway bridge、review/finalize、数字 adapter；特别复核 F05/F07/F08：source→owner 唯一归属、知识依赖与词表版本保护、领域提交与索引投影分离；补齐错误响应层级和 queued/实际送达语义 | 双 owner/account/chat、重复/变更附件、知识晋升/人工修正、索引插入/消费故障、重启恢复和旧版迁移的正反例；相关跨对象不变量与规范条款逐项映射 | 非法关系在所有写入口均拒绝且无部分提交；索引故障不重跑提取；现行 HEAD 的四类模块取得逐项复审证据，不能只凭 Schema 或套件全绿签发整体通过 |
| D · 运行与三来源验收 | F01/F04/F06、M2。验证无 EPUB/无 Vault/未知书页的普通图片仍进入观察；受限自动会话按 90 分钟/6 小时降级；物理 worker 不被坏批次或慢数字源阻塞；Koodo/WeRead 的真实周期增改删和网络恢复 | Gateway 真实入站、周期任务状态、故障注入、有限重试、实际三来源 SearchHit 与来源身份；记录模型调用数、耗时和冷/热启动成本。核显仅有隔离基准，安装稳定驱动与生产路由前不宣称已启用 | 不丢已接受照片；错误可定位并恢复；同 owner 三来源可检索且错误归属不能进入库；生产成本可量化 |
| E · 规格验收与交接 | 复跑 §5 的 AC-01–26 并区分本地、现场、未验；回填 `LIBRARIAN_V0_8_HANDOFF.md` 与本报告。§38.1 p159/166/171/184 四张标注照片及 `source-design.txt` 已按用户指示暂缓，不用同号 Vault 孤图代替 | 每条 AC 的当前证据链接、未完成原因、修复提交、真实运行与用户确认记录；延期样本单列 | 核心 P1 与真实闭环均经逐项验收后再考虑 `release-v0.8`；暂缓输入保留“延期/未验”，不得记“通过” |

执行顺序已按用户最新指示调整：Bookscan 方法已接入现有纸书图像处理入口，并经隔离样本验证。当前仍推进 C 中领域框架、Schema、R1/R3 跨字段和跨对象不变量；A 的三张生产扫描内容审核和替换继续等待真人判断，物理 worker 保持关闭。Bookscan 对新照片的旁注和角括号尚无自动区域发现，须作为验收缺口处理。E 仅在 A–D 的相应证据齐备后更新判定。

B 的后续清单：现有 11 张旧版多页区照片与笔记时间来源已按第 8 节修订并复核；纸书活跃页码未知尚有 4 条，均在第 29 页待审核扫描，不越过 A 的用户决议自动补号。继续对其余历史 trace 的 bbox、文本 basis、自动会话归属和通知状态做只读清点。不得把 EPUB 页码、边注数字或邻图顺序当作印刷页码；对仍无法从本图证明的页码保留 unknown。

### 9.1 本次审计澄清纳入的专项复核任务

§2.1–2.3 的更新要求分别复核数据结构、元数据、Schema 和桥接入口。以下任务属于上表 B/C/D 的明确工作包；“已有局部证据”只表示第 8 节记载的具体路径，不代表整类模块通过。每项以当前 HEAD 为基线建立条款→写入口→验证结果的清单，记录修复提交和历史数据处理结果。

| 任务 / 对应批次 | 实施步骤 | 验证与交付物 | 当前边界 |
|---|---|---|---|
| R1 · 领域引用与事务（C，F07/F08） | 按规范 §30 逐项列出 `store.py`、`pipeline.py`、知识晋升、review/finalize、数字 adapter 的写入口；检查 owner 链、引用存在性、revision/current 指针、detection/observation/resolution 关联、事件与 trace 同事务、原始 evidence 只增不改。用旧库迁移样本复核新约束 | 每条不变量对应执行位置和正反例；跨 owner、悬空引用、旧 revision、知识依赖及人工修正的失败均无部分提交；注入索引故障后从已存 trace 恢复，extractor 调用次数不增加 | `48099cd`、`399c3f5`、`0880d5c`、`d029cc1`、`686fb10`、`4fb048c`、`498512e`、`aa39e57`、`b3fa5df`、`df93ce6` 已测试索引边界、领域引用、捕获链、空间标签、数字归属、并发摄取、事件失败回滚及对象完整性；正式库 800/800 trace 版本有对应 outbox 事件、290/290 私有对象可读取且散列匹配。仍须完成其余修订入口故障注入、知识晋升、旧迁移链和备份恢复复核 |
| R2 · 历史元数据与证据边界（B，F02/F03/F04） | 只读枚举活跃及受影响历史 trace，将页码、身份、时间、作者、basis、confidence、locator、bbox、provenance、配置版本逐字段追溯到本图、原始返回、EPUB、用户决议或规则；重点核对早期 OCR/EPUB 扩文、自动会话及 bbox 对应的可见文字 | 受影响记录清单与字段来源表；照片局部、raw、EPUB 对齐和旧/新 revision 对照；无照片证据的文字不进入照片原文，未知字段保持 unknown；经确认的更正走领域修订并保持历史可读 | 11 张页码和笔记时间已版本化修订；83 条活跃纸书 trace 的 146 段印刷区、305 个 detection 引用有首轮只读核对。678 个纸书历史版本的页码/身份与其指定 resolution 一致，旧邻图页码的 3 个逻辑 trace 已退出活跃集。历史 677 个 OCR 印刷区中 11 个旧 v2/v3 跨行扩文，涉及 22 个历史 trace 版本、0 个当前活跃 trace。仍须查墨线覆盖、OCR 真值及其余字段；第 29 页 4 条 unknown 和三张待审扫描依赖 A |
| R3 · Schema 与语义校验（C） | 对规范正文 MUST 和 `schemas/` 的字段、枚举、null/unknown、状态组合逐项比对；把结构校验、跨对象事务校验、外部证据真实性分配到明确执行层；检查旧版对象读取和迁移 | 条款→字段→校验函数/事务→测试矩阵；合法 JSON 但错误 owner、虚假页码 basis、单行 bbox 对应整段文字、失效 revision 等反例由应用层拒绝或进入待审；无法程序验证的真实性标明人工证据 | 四类字段的 unknown/value/confidence 组合已入 Schema；正式库 1,450 条旧记录与 85 个契约样本兼容。其余状态、来源和跨对象矩阵尚无逐字段完整结论 |
| R4 · Gateway 与投送边界（C/D，F05/F06） | 清点图片、session、search、evidence、review/decision/finalize、digital sync 的每个入口；核对受信身份、account/chat→owner、source→owner、幂等键及 payload 冲突、`ErrorResult`、重启恢复；把“已排队”“平台发送成功”“用户端已显示”分成独立状态 | 插件替身和真实消息分别留证；双 owner/account/chat、重复消息与变更附件、坏批次、慢上游、投送失败重试均有正反例；错误可查询且不会伪报送达或阻塞其他照片 | `3a47e89` 补齐七个 Python bridge 的错误字段，`07f99f3` 将其传过插件，`55d61e7` 修复裁片排队后文件过早删除，`0fd6a2b` 补 hook 错误持久查询，物理/数字 worker 已分锁；只证明本地与指定真实入口。跨账户、真实重复/变更附件、平台投送及慢源恢复留正式运行核验 |

实施顺序：R2 的只读清单与 R1/R3/R4 的入口清单先行；发现违反不变量时先在隔离库复现并修复写入口，再经正式 worker 或受信工具形成版本化结果。A 的三张扫描继续等待用户逐项审核；不能用专项复核代替用户对画线和手写文字的判断。R1–R4 完成后，才在 E 中更新 AC-01–26、handoff 与模块结论。

下一轮执行点：先核对 Bookscan 接入的真实单图耗时、内存、失败恢复、预标注区域来源和候选审核界面，再决定是否开启正式纸书 worker；当前三张待审 run 保持原状，不自动替换。继续核对 R1 全写入口事件事务和 R3 字段/状态矩阵，R4 留附件幂等和投送层级的正式运行核验；hook 错误持久查询见 §19。每个任务结项时在第 8 节记录提交、测试、正式状态及剩余限制；当前不得把四类模块标为整体通过。

### 9.2 §30 不变量的当前写入层映射

本表以当前实现为准，列出对应的执行点和仍需验收的范围。指定反例通过不等于同类所有入口通过；生产记录的只读兼容也不能证明外部证据真实。

| §30 不变量 | 当前执行点与证据 | 尚需完成 |
|---|---|---|
| 全引用链同 owner | `Library._validate_record_links` 核对目录、会话、捕获链、纸书 trace、数字 trace 目录、知识候选和 trace relation；数字 source 另由 `bind_digital_source` 绑定 | 按 Gateway、worker、review、数字 adapter 的每个入口复核受信身份和 source→owner 传递，包含双 account/chat 的真实反例 |
| Edition→Work、Instance→Edition、resolved physical trace 完整上下文 | `_check_catalog_chain`、`_validate_record_links` 与 `ReadingTrace` 跨字段校验；正式库旧目录及 resolution 版本已只读兼容 | 旧迁移链、上下文修订及知识依赖在同一事务失败时的完整反例 |
| `(owner,id,revision)` 唯一、当前指针合法 | `records` 主键和 `records_current` 唯一索引；`Library._put` 校验相邻 revision 并切换 current | 迁移、崩溃恢复与绕过领域 API 的直接 SQL 路径单列边界；不得以 Schema 成功代替版本链复核 |
| 来源附件身份唯一 | `source_items` 复合主键；`Library.ingest` 校验来源身份、对象持久性与重试；`d029cc1` 覆盖两个连接同时摄取 | 真实 Gateway 重复消息、变更附件及重启重放 |
| 幂等键不能对应不同 payload | `idempotency` 与 `command_receipts` 持久化业务指纹；相同摄取竞争返回同一 receipt，冲突拒绝 | 每种 session/review/finalize 桥接命令逐项核对相同键的不同 payload 与重放结果 |
| trace 的 capture/observation/resolution/detection 一致 | `Library._validate_record_links` 在最终写入核对 owner、历史 revision、页区及 detection；`686fb10` 补捕获链 | 人工修正、待审替换及旧迁移样本的全路径故障注入；视觉覆盖仍属 R2/A |
| observation ID 唯一且 link 有效 | `validate_observation` 在提取和最终写入共用；正式库 142 个版本只读校验通过 | 检测语义和 OCR 真值只能由照片及用户审核确认，不能以结构校验宣称准确 |
| trace 与领域事件同事务 | 已逐入口静态核对 `process_capture`、`reconcile_extraction`、`correct_trace`、`resolve_capture`、数字导出及 Koodo/WeRead 创建/修订/删除/来源对账；正式库 800 个版本各有 1 条对应 outbox 事件。`b3fa5df` 注入初提取和数字导出事件失败，领域记录回滚后可重试；索引投影已移出领域事务 | 其余修订入口逐项故障注入、外部消费者投递与旧迁移链；`_put` 自身不强制事件 |
| bbox、方向和空间标签有效 | observation 共用语义检查；`498512e` 在纸书 trace 写入时验证 bbox/页区/side/方位，正式库 678 个纸书版本兼容；`97998ee` 拒绝 resolution 页区重复 ID 与零面积，137 个旧版本兼容 | 页码依据和照片中墨线是否对应引文仍需人工审阅；更多图像方向、跨页链接与旧迁移反例归 R2/R3 |
| 原始 evidence 无普通 UPDATE | `evidence_immutable` 和 `evidence_undeletable` 触发器保护 PageCapture/PageObservation 的 `records` 行；对象先写后引用。`df93ce6` 只读核对 2,891 处引用、290 个对象均可读取且散列匹配，无当前孤儿 | 对象文件丢失后的恢复、未来孤儿回收和备份还原演练，确认已接受回执仍可重新打开原图 |

## 10. 当前状态与未完成项（2026-09-29 晚间）

本节覆盖第 9 节写成时的运行状态，不追改第 1–8 节历史记录。用户随后要求清除旧图像处理流程和结果、用 Bookscan 重建。`8735afc` 移除旧 RapidOCR/整页视觉模块，正式库经专用开发重置清除旧纸书派生记录与 Vault 生成笔记；原始 27 张 PageCapture、目录、会话及 122 个数字 trace 版本保留。清理期间的旧结果备份在重建及完整性验证后按用户“完全清除”的要求删除。这是用户明确授权的开发期重建，不是规格要求的常规版本化纠错；先前 R2 历史记录统计不能再解释为当前库仍保存那些旧 observation/trace。

当前正式库只读检查：27 张 capture 对应 27 个 Bookscan ProcessingRun/Observation/Resolution，19 个 run 为 `success`、8 个为 `partial`、0 个为 `pending`；73 条活跃纸书 trace 为 56 条 underline、2 条 bracket、15 条 margin_note，其中 19 条页码未知。58 个画线/角括号组中，53 个可靠匹配使用 Bookscan 的 EPUB 标点扩展，`printed_text.basis=source_payload`；5 个弱匹配仍保留照片 OCR 转录，`basis=vision`。15 条旁注没有印刷正文。73 条 trace 的 `review.state` 均为 `none`，因此不能把“无 pending run”当成人工审核完成。Vault《社会理论二十讲》已按微信读书式版面重建，正文不再显示内部 trace/capture ID 或原图投送提示，仍有隐藏 trace 标记；原图不在 Vault。私有对象审计为 203/203 对象可读且散列/长度正确、0 缺失、0 孤儿。Gateway active，`physicalWorkerEnabled=true`；本次修正后由 Gateway 的正式物理 worker 自动重跑。上述是运行与结构证据，不是识别准确率或用户审阅结论。

| 未完成项 | 当前需要的证据或决定 |
|---|---|
| 首书内容与页码审核（A/R2） | 人工逐页核对 58 个画线/角括号组及 15 条旁注，尤其 5 个弱 EPUB 匹配、19 条 unknown 页码、2 个 Bookscan failure 记录；确认遗漏、误检、墨线覆盖范围和手写字形。旧版 23/29/39 页 pending run 已随开发期重建删除，原计划的 3 张旧新对账不再适用；须以当前 Bookscan run/trace 重新建立审核清单。 |
| EPUB 引文边界与规格决定（F03/R2/R3） | 当前 53 条匹配文字直接采用 EPUB 补至标点的句子并标注 `source_payload`，与初审规格“trace 只含可由对应照片区域验证的文字”的原要求存在边界差异。需对照照片和纸版逐项验证，明确是否修订规格以允许这种补全，或把超出画线的上下文移到独立字段；异文、跨页和仅半句画线须有反例。 |
| 通用新图识别（F01/D） | Bookscan 对精确哈希匹配的样本使用预标注旁注/角括号区域；普通新照片尚无这两类区域的自动发现证据。仍需无 EPUB、无 Vault、仅内页、未知书页、旋转/多页、普通新手写及高亮/符号的真实入口与质量验收。 |
| 领域、Schema 和桥接复审（C/R1–R4） | §9.1、§9.2 剩余的知识依赖、旧迁移与备份恢复、修订入口故障注入、跨 owner/account/chat、幂等附件变更、入站 hook 错误查询及“queued→平台成功→客户端显示”逐层证据尚未齐备；现有单项测试与一次成功运行不能给四类模块整体签发通过。 |
| 数字来源与运行验收（D/M2） | 当前 `digital-sync-status.json` 仅证明最近一次 Koodo 118 条、WeRead 4 条均为 unchanged/success；仍需真实增改删、断网恢复、慢源隔离、重复 timer/重启进程上界与成本/耗时记录，并验证三来源同一检索契约。 |
| 规格 AC 与交接（E） | 以当前 HEAD 重跑 AC-01–26，分别标注本地/真实/未验，回填 handoff、修复提交和客户端证据。§38.1 p159/166/171/184 四张标注图及 `source-design.txt` 依用户指示暂缓，保留延期/未验，不用当前 27 图代替。`release-v0.8` 仍未达到审计放行条件。 |

## 11. ISBN 元数据、审核入口与重复 run 修复（2026-09-29）

`f698060` 从 agent 数据目录的 ISBN 来源记录填充 Vault 纸书笔记元数据；`a9134d9` 将同一来源记录显示在 Bookscan `review.html`。书目记录对应 `9787208171411`，包含作者、译者、出版社、出版日期、原作名和来源链接。27 个原始审核页已重新生成；Vault 仍只含文字，不存原图。元数据来源记录保存在 `var/librarian/source-books/9787208171411.metadata.json`，不是 Bookscan 的 OCR 输出。

检查时发现旧 `processor_fingerprint()` 把审核页代码也计入图像处理版本。仅修改 `review.py` 后，后台 worker 对 27 张原图各产生一个待对账 run；调试指纹修复期间又产生 27 个。两批新 observation 与对应已入库 observation 的 `image_space`、页码、印刷区、标记、批注、符号、链接和警告字段逐项相同。`cf0cf76` 将审核展示代码排除于处理器指纹，新增领域操作将这 54 个重复待对账 run 版本化标记为 `duplicate`，保留原始 run/observation 与 73 条活跃纸书 trace，不执行 trace 替换。正式 worker 连续运行后，当前 81 个 run 为 27 原始 `success/partial`、54 `duplicate`、0 `pending`；Vault 仍有 73 个隐藏 trace 锚点。相关 104 项测试通过。

私有审核总览已生成在 `var/librarian/review/index.html`，按当前已入库的 27 张 capture 各列一条，连接原始 Bookscan 审核页。**审核页目前仍只在浏览器 localStorage 保存草稿或导出 JSON；尚未把逐页判断、校正、漏检框接入 Librarian 的版本化写入和 Vault 刷新。** 所以 A/R2 的人工内容审核仍未开始结项，不能把新总览或 `duplicate` 状态当作人工确认。下一步先实现审核提交的身份/快照校验与领域写入，再由用户在网页逐页复核；其余 R1–R4/AC 边界沿用 §10。

后续入口检查又发现 Bookscan 的 `bookscan_N_mark`/`bookscan_note_N` 不在旧 `candidate_id()` 的标记前缀集合中，同一 capture 的多个候选会得到相同 ID。现已补入这两类检测 ID 并覆盖唯一性测试。审核页也补了批注的接受/误收/无法判定判断和完成审核包导出校验；该导出仍只是离线文件，尚无提交端，不能称为入库。

## 12. Bookscan 网页复核写入路径（2026-09-29）

新增 `bookscan_review_apply.py` 和仅绑定 `127.0.0.1` 的 `bookscan_review_server.py`。审核包须与 owner 下唯一的已入库 Bookscan run 对应，逐页、逐行、逐标记组和逐批注给出确定判断；漏检框必须落在原图内并有人工转录，人工页码必须为正整数。网页从本地服务取得当前 trace 引用和最新人工审核 run 快照，提交时再核对版本；旧审核包不能覆盖后来的人工作业。对同一页可再次复核，新的提交建立新 run、observation、resolution 和 trace 版本，前一版保持可读。用户认可的引文/手写字记为 `user_statement`，trace 的 review 状态记为 `resolved`；误检旧 trace 退出活跃集，漏检框形成新的有原图坐标的标记。审核包和来源 run ID 存于新 observation 的私有 raw 对象，原图仍只在 Librarian 对象库。提交后物理 worker 刷新 Vault 笔记，网页分别显示入库与 Vault 状态。

验证边界：新测试覆盖完整审核、修订、误检、漏检、页码、幂等、过期快照、残缺审核拒绝、localhost cookie/同源限制和路径越界拒绝。27/27 份正式 Bookscan 报告仅做内存中的审核包预校验，均通过；另在**正式库和对象的隔离副本**中以一条测试文字完成 `apply_review`→worker→副本 Vault 笔记更新，正式库及正式 Vault 未写入测试内容。客户端真实人工审阅仍为 0/27，因此内容正确性、漏检率和首书 A/R2 不能签收。§9.1 的 R1–R4、数字来源 D 与 AC-01–26 仍保留未验项。服务是本机私有审核入口，不是公开 Gateway 路由。

## 13. 用户调整范围与快速验收（2026-09-29）

用户明确要求跳过两个项目：普通新照片对旁注/角括号等区域的自动发现质量，以及 EPUB 扩句与照片画线边界的规格处理。此决定只缩小本轮验收范围，**不构成这两项已经实现或符合原规格的证据**。§10 中这两行及早期 AC/F01/F03 判断保留为历史记录；本轮不再为其开发或等待验证。其余首书网页复核、现有数据入库、Gateway、数字来源和领域不变量继续验收。

本机私有审核服务已启动并以 HTTP 实际读取：登录跳转后的总览返回 200，列出 27 个原始 Bookscan 审核页；第 23 页审核页返回 200，包含提交按钮、ISBN 元数据和当前版本上下文接口；`/api/review-context` 对该 run 返回 200、2 条当前 trace 引用。此项证明网页与只读接口可用；没有以测试判断提交正式数据。§11 所说“仅能本地保存/导出、尚无提交端”已由 §12 实现覆盖，不再是当前状态。

本轮复跑完整 Python 套件 **511 passed**（4 条弃用警告），离线契约 77 定义、18 入口、42 正例、43 反例通过；OpenClaw 插件 **16/16** 测试通过。正式首书仍为 **0/27 页人工确认**；因此候选文字、漏检和手写正确性仍待用户在审核页判断，不能以自动测试代签。

运行态只读检查：`openclaw-gateway.service` 为 active/running，`pap-librarian-intake` 为 loaded/enabled、1 个 typed hook、7 个工具、0 diagnostics；正式 owner 下《社会理论二十讲》p.39 的现有检索返回 6 个 hit。数字同步状态文件最近一次完成时间为 2026-09-29 12:50 UTC，Koodo 118 条、WeRead 4 条均为 unchanged/success。检索命中和同步状态不能代替真实飞书入站问答、上游真实增改删或客户端投送验收。

正式数据只读完整性检查：27 张当前 PageCapture、81 个当前 PageObservation/ProcessingRun（含 54 个重复 run）、73 条活跃纸书 trace，0 条纸书 trace 标记为人工复核完成；Vault 笔记有 73 个隐藏 trace 锚点。对象审计检查 814 处引用、257 个唯一私有对象，257/257 文件大小与 SHA-256 一致，0 缺失、0 孤儿、0 无效 JSON。该检查证明存储结构完整，不能证明画线识别正确。

复核站点逐页 HTTP 冒烟检查：27/27 个审核页返回成功；页面引用的 246/246 张图片均返回 200、`image/*` 类型和非空内容；27/27 个 `/api/review-context` 请求成功，共返回 73 条当前 trace 引用，0 错误。此检查覆盖浏览器取资源的路径与身份会话，但未代替真人视觉判读或最终提交动作。

正式 SQLite 只读 `PRAGMA integrity_check` 返回 `ok`，`foreign_key_check` 返回 0 条违规；这只证明数据库物理完整性和已声明的外键，不代替 §9.1 所列跨记录语义不变量。

R1 故障注入补证：在隔离库对 Bookscan 网页复核对账的 `reading.trace.corrected` outbox 写入注入失败，旧 trace/current 指针与事件保持原状；恢复后重试同一审核包，完成新版本及每条旧 trace 的修订事件。在知识晋升的 `reading.knowledge.promoted` 事件写入注入失败，candidate 保持 `approved` 且无成功事件；恢复后用同一知识服务幂等键重试并只产生一条成功事件。`test_librarian_bookscan_review_apply.py` 与 `test_librarian_knowledge.py` 合计 9/9 通过。此项补齐两条指定入口的事务反例；不表示所有 R1 修订入口或实际知识服务已验收。

R1 隔离恢复演练：对正式 SQLite 做在线 backup，复制私有 `objects/` 与 `source-books/` 到临时目录并从副本重新打开 Library。副本 257/257 个唯一对象通过大小和散列检查，27/27 张已接受原图可经领域 API 读取，p.39 检索仍返回 6 条；临时目录退出后清理，正式库未改。此演练覆盖库、对象、目录和索引的基础恢复；未包含 2.1 GB 的 Bookscan 审核产物、Vault 或真实 Gateway 切换，故不宣称完整生产灾备通过。

## 14. 首书手写复核与章节投影（2026-09-29）

用户进一步确认：现有 EPUB 标点扩展画线文字基本可用，不再逐条要求画线文本人工核验；本轮仅提供手写笔记复核工具。实际逐条核验属于正式运行，网页与版本化提交路径可用即可视为本轮工具交付，不把 0/15 手写笔记用户确认作为本轮开发完成阻塞。原书四图和普通新图自动发现仍依用户先前决定暂缓。此决定已同步记入 `docs/SPEC_v0.8_Librarian.md` 末尾；不把未验证能力转写为“通过”。

`review/handwriting.html` 从当前纸书 trace 的 `bookscan_note_N` 证据引用生成 15 张手写裁片卡片，只显示 OCR 初稿、可编辑文本和确认/误检排除按钮。提交由同源私有 `/api/handwriting-review` 进入 `review_handwriting`：核对 owner、trace revision 与笔记来源，在同一事务写入新的 ReadingTrace revision 与 `reading.trace.corrected` outbox 事件；确认文本 basis 为 `user_statement`，误检退出活跃集，重复提交幂等，后续再改字或恢复误排除项仍形成新 revision。服务随后运行物理 worker 刷新 Vault。隔离库单元测试与 HTTP POST 均通过；正式库没有代用户提交任何手写判断。正式站点 GET 15/15 张裁片返回 200 与非空图片。

Vault 渲染新增 EPUB 章节投影：用 `EpubIndex` 将印刷引文映射到 spine 与正文偏移，按该顺序排序；无印刷文字的手写笔记借同页/邻近引文定位，保留页码作行内来源信息。当前 58/58 条活跃印刷引文均找到 EPUB 候选，其中 53 条相似度 1.0，其余 5 条为弱匹配，均定位到第二讲。正式物理 worker 已更新《社会理论二十讲》Vault 笔记：章节标题 1 个（「第二讲 帕森斯与他尝试集各家大成的理论」），页码分组标题 0 个，73 个隐藏 trace 锚点、15 条手写笔记、0 个原图嵌入。旧版生成块仍须精确匹配才可自动替换；有人为编辑时保留冲突，不覆盖用户内容。手写笔记的章内位置是基于相邻引文的估计，不是 EPUB 对手写字的直接对齐。

本轮后续验收边界：本机网页和提交路径交付不等于用户已完成 15 条手写内容确认；R1–R4 中未覆盖的真实 Gateway、外部知识服务、数字源变更与全链路故障证据以及 AC-01–26 的逐项现场判定仍单列，不用网页可访问性代替这些要求。

变更后完整回归：Python **516 passed**（4 条弃用警告），OpenClaw 插件 **16/16**，离线契约 77 定义、18 入口、42 正例、43 反例通过。手写复核服务以当前代码重启，浏览器会话 GET `/review/handwriting.html` 返回 200、15 张卡片和新的提交接口；旧启动 token 已失效。

第二次正式物理 worker 运行返回 0 错误，Vault 笔记散列不变；当前 73/73 条活跃纸书 trace 均得到第二讲 EPUB 位置。此处仅验证现有首书与当前 EPUB 的排序稳定性，不能推广为所有图书的匹配准确率。

## 15. AC-01–26 当前证据快照（2026-09-29）

以下更新 §5 的历史判断。“本地”表示已执行隔离测试，“正式数据”表示当前生产 Library 的只读或 worker 证据，“历史入站”表示用户真实飞书消息在 Bookscan 重建前的轨迹；三者不互相替代。用户明确跳过的能力标“本轮延期”，不写“通过”。

| AC | 当前证据 | 尚未满足的范围 |
|---|---|---|
| 01 | 本地同键重试/并发测试；历史五图重放保持 capture ID | 当前 Bookscan 入站无新重复消息现场反例 |
| 02 | 本地同键异 payload 冲突测试 | 当前真实附件变更重放未验 |
| 03 | 本地同字节新消息分别建 capture 测试 | 当前真实重复照片未验 |
| 04 | 本地同名多版本/副本冲突测试 | 现场双副本未验 |
| 05 | 本地显式 session/可见书名冲突测试 | 真实新图现场延期 |
| 06 | 本地 90 分钟/6 小时 affinity 测试 | 真实长间隔未验 |
| 07 | 本地未知页保留 trace；正式首书仍有 19 个未知页码 trace | 137/139 标注图延期 |
| 08 | 本地照片页码不自动推进进度测试 | 真实新照片与进度联动未验 |
| 09 | 历史真实飞书「读到第39页」→`librarian_session.progress`→同一会话 `user_statement` 修订 | p.184 样本延期 |
| 10 | 本地 EXIF/crop/跨页测试；当前 27 个 Bookscan 页面与 246 张审核图片可读 | §38.1 标注图延期 |
| 11 | 本地普通划线不强制 content review；用户接受当前 EPUB 标点扩展文字 | 普通新图的识别质量本轮延期 |
| 12 | 本地启用符号词表与重要内容 queue 测试 | 真实独立符号识别本轮延期 |
| 13 | 本地正文/边注符号误触发反例 | 真实符号样本延期 |
| 14 | 本地 correction 与新手写网页提交形成版本；隔离 HTTP POST 证实 `user_statement` | 本轮不要求用户实际逐条提交 |
| 15 | 本地旧模型/旧事件保护、索引修复测试 | 当前真实迟到事件未验 |
| 16 | 本地重提取分组冲突保留旧 trace、待对账测试 | 复杂真实冲突现场裁定未验 |
| 17 | 本地对象写失败不确认、原键重试成功测试 | 实际磁盘故障未验 |
| 18 | 本地提取超时/非法输出保存错误并不造 trace 测试 | 真实供应商故障未验 |
| 19 | 本地 outbox 重放、消费者去重及网页/知识事件失败回滚测试 | 外部发布者真实崩溃未验 |
| 20 | 本地索引故障后用已存 trace 重建且不重识别；当前正式检索索引 ready | 真实 Gateway 故障恢复未验 |
| 21 | 本地跨 owner 引用、搜索、取证拒绝测试 | 双真实账户/会话现场未验 |
| 22 | 本地纸书 `mark_author=unknown` 默认值测试 | 无需假定首书字迹作者 |
| 23 | 当前正式 Library 三来源 SearchResponse：physical 5、WeRead 4、Koodo 5 个命中，`index_state=ready` | 真实三来源混合问答未验 |
| 24 | 历史真实飞书问书/按页查询调用 `librarian_search` 并回复；当前正式 p.39 直接检索 6 条 | Bookscan 重建后真实入站问答未验 |
| 25 | 本地知识服务失败、事件失败与同幂等键重试测试 | 实际知识 writer 未接入，M1 不宣称该阶段现场通过 |
| 26 | 本地普通划线不晋升测试；当前正式库 0 个 KnowledgeCandidate | 当前纸书 58 条印刷摘录不构成积压错误 |

此表不关闭 R1–R4 全部专项核验或 `release-v0.8` 放行门槛。§38.1 四图与底稿继续按用户指示延期；用户已允许手写内容真人核验在正式运行阶段完成。其余未验项保持显式状态，后续取得真实入口或故障证据时逐条更新。

## 16. 当前正式库跨记录结构复核（2026-09-29）

在现有正式 Library 上逐条对 498 个 `records` 版本执行当前 `validate` 与 `_validate_record_links` 只读校验，0 失败；覆盖 CaptureBatch 23、PageCapture 27、Work 3、Edition 1、BookInstance 2、ReadingSession 4、ReadingTrace 195、ProcessingRun 135、PageObservation 81、CaptureResolution 27 个版本。442 个 `(owner, model, id)` 逻辑对象的 revision 均从 1 连续到最新，恰有一个 current 且指向最新版本，`supersedes_revision` 与前一版一致，0 异常。195/195 个 ReadingTrace 版本各有 1 条同 owner、trace ID 和 revision 的 `reading.trace.created/corrected` outbox 事件；195 条当前活跃 trace 对 195 条索引投影，revision 一致，0 缺失或滞后。

这补充了 R1/R3 对**当前保留数据**的兼容与一致性证据；开发期清除的旧纸书派生记录不在本次样本内，现有库没有 KnowledgeCandidate/TraceRelation 实例。上述检查不证明图片内容准确、所有未来写入口的原子性或跨账户真实授权，也不能代替 R3 的完整条款→执行层矩阵及负例。

手写审核链接改为受限 `view=handwriting` 登录后直达该页，避免用户再从 27 页总览寻找入口；同源 cookie、Host/Origin 检查维持原约束。Chrome 无头浏览器从新 token 链接完成跳转并渲染首张手写裁片、OCR 初稿、文本框与确认/排除按钮；临时截图及浏览器 profile 已清理。此为客户端页面呈现证据，不等于用户已确认内容。

新手写提交入口的 R4 反例：隔离库使用他人 owner 访问当前笔记返回 `UNAUTHORIZED`，尝试把普通印刷 trace 当作手写笔记提交返回 `VALIDATION_FAILED`；浏览器无同源 Origin 的 POST 返回 403。`test_librarian_bookscan_review_apply.py` 7/7 通过。这证明此新增本机入口的受信范围，未扩展到飞书跨账户整链路。

## 17. 完整私有数据恢复复核（2026-09-29）

在临时目录将正式 SQLite 以在线 backup 复制，并复制 `objects/`、`source-books/`、2.1 GB 的 `bookscan-runs/` 和运行状态文件。首次恢复发现实际缺陷：Bookscan raw 报告中的 `config.output_dir` 是旧主机绝对路径，`review_index` 因安全路径校验把所有恢复后的报告跳过，出现 0 张审核页、0 条手写卡片。已让审核入口优先使用当前私有根目录下的路径，迁移时仅以受限 run ID 在当前 `bookscan-runs` 内寻找唯一产物；含路径分隔符的 ID 和多重匹配均拒绝，不回退访问旧主机路径。隔离测试覆盖迁移、歧义和目录逃逸。

修复后再次完整临时恢复并从副本启动 localhost 服务：27/27 个审核页、15/15 张手写卡片及其裁片可经 HTTP 读取，257/257 个唯一私有对象大小/散列一致。在另一份完整副本连同 Vault 笔记运行正式物理 worker，0 错误，仍生成 1 个第二讲章节标题和 73 个隐藏 trace 标记。临时目录随后清理，生产数据未改。此项证明数据目录迁移后当前 Bookscan 网页与 worker 的基础恢复；尚未演练 Gateway 的真实服务切换、密钥迁移和飞书平台重连，故完整灾备放行仍保留该边界。

再对完整迁移副本执行一条**合成**手写决定的真实 HTTP POST：本地服务返回 `status=applied`、`vault_status=updated`；复核页显示已确认，副本 Vault 出现合成文字。临时目录退出后删除，正式库及正式 Vault 均无该文字。由此复核页在迁移后的 GET、版本化提交、索引重建和 worker 投影链路均可用；这仍不代表用户在生产数据中确认了手写内容。

## 18. R3 结构/语义/外部真实性分层（2026-09-29）

| 约束 | 执行层 | 已有反例/正式证据 | 边界 |
|---|---|---|---|
| 字段、枚举、null/unknown、ObjectRef 形状 | JSON Schema；`store.validate` | 77 定义、18 入口、42 正例、43 反例；当前 498 个记录版本通过 | Schema 不判来源真实 |
| `(owner,model,id,revision)`、current 与 supersedes 链 | `records` 主键/唯一索引、`Library._put` 事务 | 并发/旧 revision 本地反例；当前 442 个对象、498 个版本 0 链错误 | 开发期已删除的旧纸书派生记录不在当前样本 |
| 书目、会话、捕获、trace、知识来源同 owner | `Library._validate_record_links` 与 `_check_catalog_chain` | 跨 owner、悬空/异捕获链接本地拒绝；当前 498 个版本 0 引用错误 | Gateway 双真实账户入口仍属 R4 |
| observation 检测 ID、页区、bbox、trace provenance | `validate_observation`、`_validate_record_links` | 越页/缺检测/错 bbox 本地反例；当前纸书版本全量回读通过 | 墨线是否对应文字属照片证据，不由几何包含证明 |
| resolution 页码/身份的 status 与 value | `_validate_semantics`、`resolve_capture` 受限 `_basis` 与版本事务 | unknown/resolved 状态反例、页区重复/零面积拒绝；当前 27 个 resolution 版本通过 | `basis=user_confirmation` 的外部人类依据须由受信入口/用户决定证明 |
| 引文/手写 basis 与审阅状态 | Schema、`correct_trace`、`review_handwriting` | 仅手写确认写 `user_statement`，误检退出活跃；隔离 HTTP 及跨 owner 反例通过 | 用户接受当前 EPUB 扩句；实际手写字形真值在正式运行核验 |
| KnowledgeCandidate 状态、来源 revision、成功知识 ID | `_validate_semantics`、`knowledge.py` | 失败 writer/事件、过期来源、跨 owner 本地反例；候选不提前 promoted | 无当前正式候选与实际知识 writer |
| trace 修订与 outbox 事件原子性 | 写入口事务、Event 语义校验 | 当前 195/195 版本各有 1 条事件；网页对账及知识晋升事件失败回滚测试 | 外部 publisher/Gateway 崩溃现场未演练 |

完整回归在本次恢复修复后为 **518 passed**（4 条弃用警告），插件 **16/16**。此表将已可程序检查的不变量分配到 Schema、应用事务与证据层；R3 仍保留历史迁移样本与未枚举的每个状态组合逐项反例，R2/R4 的外部真实性不被计入 R3 通过。

## 19. R4 图片入站 hook 失败可查询（2026-09-29）

`message_received` 原先在图片接收桥接失败时只写 Gateway 警告日志，agent 无法按 owner 查询失败消息。现以受信 channel/account/sender 映射和源消息 ID 为键，在私有 `intake-status/` 中原子写入最新 `accepted/failed` 状态；成功重试覆盖同一消息的旧失败。文件权限为 0600、目录为 0700，查询只经现有 owner 受限的 `librarian_review` 无 capture 汇总返回最近十条失败。公开字段只有消息/通道/账户标识、脱敏错误码、阶段、可重试标志和时间；原异常文字、附件内容、私有路径不写入。无可信映射或消息 ID 时不造状态。

插件测试分别覆盖私有权限、脱敏、同消息失败后成功覆盖、未映射 sender，以及真实 hook 调用合成桥接错误后留存失败；Python 测试覆盖双 owner 隔离。完整回归 **519 passed**（4 条弃用警告），插件 **18/18**。该状态仅说明 hook 图片接收结果，不把后台 worker 完成或 `queued` 媒体当作送达。测试使用隔离目录和合成故障；真实飞书故障、变更附件重放、平台投送和客户端显示仍留在 R4 现场验收。

Gateway 已重启，`systemctl --user` 返回 active；运行时插件检查为 `loaded`、`enabled`，包含 `message_received` hook 和 `librarian_review` 工具，diagnostics 为空。没有以重启状态替代一条真实飞书故障或客户端送达证据。

## 20. R1 修订入口事件故障注入（2026-09-29）

对 `correct_trace` 和 `resolve_capture` 两个仍缺逐入口故障证据的路径注入 outbox 写失败。前者在已有 pending 知识候选的来源 trace 上修正文句，失败后 trace 保持 revision 1、候选保持 pending、无 `reading.trace.corrected` 事件；恢复事件写入后用同一 expected revision 重试，trace 到 revision 2、候选转为 superseded。后者在同张多 trace 照片上修改用户确认的页码，失败后 CaptureResolution 和所有 trace 均保持旧 revision、无 corrected 事件；恢复事件写入后原 expected revision 可重试，resolution 与所有 trace 一起前进。这两项复核了关联候选、解析和 trace 修订不能部分提交。

证据为隔离库的应用入口故障注入；完整 Python 回归 **521 passed**（4 条弃用警告）。这不代表 SQLite 进程崩溃、实际磁盘故障或所有其余入口。正式库未注入故障，也未替用户更改内容。

## 21. R3 候选状态迁移写入边界（2026-09-29）

审视 `KnowledgeCandidate` 时发现 Schema 已限制状态值与 `promoted`/`knowledge_id` 组合，但 `Library._put` 原可接受结构合法的初版 `promoted` 或 `pending→promoted`，绕过 `decide_candidate` 的批准步骤。最终写入层现只允许初版 `pending`，后续 `pending→approved/rejected/superseded`、`approved→promoted`；来源 trace 引用、候选类型、内容和触发依据在修订中保持不变。非法跳级和改写解释的隔离库反例均拒绝且当前版本不变；现有正常知识流程与回滚测试 52/52 通过。

本约束保证状态链和解释不被普通内部写入绕过；完整 Python 回归 **522 passed**（4 条弃用警告）。`KnowledgeObject` 是否已由外部知识服务持久化，仍由 `promote_candidate` 的 writer 回执和幂等键保证，不能由 SQLite 状态本身证明。当前正式库无 `KnowledgeCandidate`，因此没有可复核的旧候选迁移样本。

兼容性补查发现 `trigger` 在当前 Schema 为可选字段；旧候选可能缺失。状态迁移校验已对比可选值而不索引必有键，隔离库中模拟缺失 `trigger` 的初版 candidate 可正常 `pending→approved`；知识模块 6/6 测试通过。此模拟只覆盖该字段的旧形状，不替代真实旧库迁移样本。
