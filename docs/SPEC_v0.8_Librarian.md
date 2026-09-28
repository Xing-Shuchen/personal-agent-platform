# PAP Librarian — Physical Reading Ingestion
# Implementation Specification v0.1.0

> **Digitize the traces, not the book.**<br>
> 数字化阅读痕迹，而不是数字化整本书。

## 0. Status

| 项目 | 内容 |
|---|---|
| 文档版本 | 0.1.0 |
| 文档状态 | **Implementation Draft / 待评审实现稿** |
| 日期 | 2026-09-28 |
| 系统 | Personal Agent Platform / Librarian |
| 范围 | Physical Reading Ingestion + Unified Reading Trace Layer |
| 主要读者 | PAP 维护者、Librarian 实现者、Codex 等编码智能体 |
| 规范性数据契约 | `schemas/contracts.schema.json` 及其 18 个模型入口 |
| 基础材料 | 用户提供的《PAP Librarian — Physical Reading Ingestion Specification v0.1》 |

> PAP 仓库落地状态与现有组件映射见 [`LIBRARIAN_REPO_MAPPING.md`](LIBRARIAN_REPO_MAPPING.md)。本文件描述目标契约和验收条件，不代表这些条件已经通过。当前 Schema、合成 examples 和离线验证报告位于 `agents/librarian/runtime/`；原稿的 `references/source-design.txt` 未随此文件提供。

### 0.1 本文与底稿的关系

本文沿用底稿第 0–41 节的组织、术语和设计方向，把描述性设计展开为数据约束、应用命令、处理步骤、事件语义和验收条件。原稿所称 `references/source-design.txt` 未随独立规格文件提供；本文中的「底稿 §N」均指该原稿对应章节。

来源与决策性质必须区分：

- **[继承]**：底稿已经明确的范围、原则或行为约束。
- **[实现提案]**：为使接口可编码而补充的实现选择；本稿采用，但不表示用户已批准，也不表示 PAP 当前仓库已经如此实现。
- **[待核实]**：附件没有提供的信息，必须通过仓库检查或真实样本验证确定。不能用猜测代替。

本稿没有读取 PAP repository，没有验证现有数据库、事件总线、对象存储、Agent Gateway 接口，也没有获得真实页面照片。本稿不据此指定新的全局架构、云供应商、视觉模型或微信读书/Koodo 的外部 API。

### 0.2 规范用语与优先级

**MUST / 必须**表示接受本实现稿后不可省略的约束；**MUST NOT / 禁止**表示不可采用的实现；**SHOULD / 应当**表示允许有记录的替代方案；**MAY / 可以**表示可选功能。

优先级：底稿的明确边界 → 本文的业务不变量 → 机器 Schema 的字段约束 → 示例。Schema 与正文如有冲突，不能静默任选其一，必须同时修订并提升契约版本。示例是合成测试数据，不是真实阅读记录或真实书目资料。

机器 Schema 负责单对象结构；跨对象归属、授权、事务、时间真实性及状态迁移由应用服务负责。通过 Schema 不等于满足所有业务规则。

### 0.3 本次交付

`IMPLEMENTATION_SPEC.md` 是实现规格正文；`schemas/` 给出正式 JSON Schema；`examples/` 给出三种来源、修订、命令和事件的合成示例；`tests/` 给出离线契约校验及验证报告。

**JSON Schema 是本次唯一规范性模型定义。** Pydantic 或其他语言模型应从其映射或生成，不应成为第二份独立维护、可能漂移的契约。本稿不假设 PAP 使用 Python，也不把示例目录当成实际项目目录。

---

## 1. Goals

**[继承：底稿 §§1、38、41]** 系统必须记住的是「用户读了什么、在哪里留下了痕迹、这些痕迹后来如何被重新使用」，而不是建立纸书全文库。

v0.1 必须完成以下闭环：注册 `Work / Edition / BookInstance`；建立或归集 `ReadingSession`；接收有痕迹的页面照片；持久化原图；解析书籍、会话和页码；识别划线、高亮与基础边注；生成 `ReadingTrace`；按原文或边注检索；返回能够打开原始证据的结果。

实现完成的核心判据是：一个月后询问「我之前在哪里把 Weber 和 Parsons 联系起来过？」，系统可以返回某条实际 trace、它所在的 edition / page，以及原图位置；不能仅生成一段无法追溯的 AI 回答。

**[实现提案]** 对证据不足的输入，正确输出可以是「已保存，但书籍或页码仍未确定」。成功保存不等于成功识别；成功识别不等于知识晋升。

## 2. Non-goals

**[继承：底稿 §§2、37、41]** v0.1 不扫描整本书，不构建电子版全文，不要求百分之百手写识别，不自动把所有划线转为知识卡片，不大规模生成摘要，不解释所有符号，不做复杂知识图谱 UI，也不让用户逐条审核普通 OCR 结果。

QR workflow、自动跨书关联、复杂概念本体、自动荐书与反荐书决策、高级空间 UI 均不属于本次 MVP 的实现验收范围。相应接口可以预留，不能反过来阻塞纸书摄取闭环。

**[实现提案]** 本次不交付可运行的摄取服务、真实平台同步连接器或模型准确率报告；交付的是可用于实现和测试的规范与契约包。

## 3. Core Architecture

**[继承：底稿 §§3、27–30、40]** 三种来源必须在 `ReadingTrace` 汇合；Librarian 上层不能直接理解 `WeReadHighlight`、`KoodoNote` 或 `PhysicalCapture`。

```text
Agent Gateway / explicit session              WeRead / Koodo source events
              │                                           │
              ▼                                           ▼
       Capture acceptance                           Source adapters
       ├─ immutable original asset                        │
       └─ durable capture manifest                        │
              │                                           │
              ▼                                           │
   Physical ingestion orchestrator                        │
   resolve context → resolve pages                        │
   → observe → normalize                                  │
              │                                           │
              └───────────────┬───────────────────────────┘
                              ▼
             ReadingTrace persistence + durable events
                              │
                  ┌───────────┴────────────┐
                  ▼                        ▼
             Search index           Candidate generation
                  │                        │
                  ▼                        ▼
          Provenance-first answer    Explicit promotion policy
```

**[实现提案]** 将入口接受与耗时处理分开：入口只在原始证据和 manifest 持久化后返回 `accepted`；视觉识别和索引可以随后执行。这里规定系统的处理契约，不要求独立微服务、特定队列或 HTTP server。

PAP 已有的 blob/object/event infrastructure 必须优先复用。不存在时，只补足当前闭环所需能力，不另造第二套 PAP。

## 4. Fundamental Data Separation

**[继承：底稿 §§4、22、39、末尾设计决策]**

| 层级 | 权威对象 | 可以表达什么 | 不能表达什么 |
|---|---|---|---|
| Layer 0 — Source | `Work`、`Edition`、`BookInstance` | 作品、版本、用户实际持有的副本 | 不凭 Work 推定纸书页码 |
| Layer 1 — Evidence | 原图、raw adapter payload、`PageCapture`、原始视觉输出 | 收到了什么、照片上出现了什么 | 不直接表达用户立场或知识结论 |
| Layer 2 — Reading Trace | `ReadingTrace` 的版本化记录 | 哪段文字被标记、有什么边注、证据在哪里 | 不把模型解释伪装成用户原话 |
| Layer 3 — Knowledge | `KnowledgeCandidate`、已有知识服务中的 `KnowledgeObject` | 有来源的概念、问题、联系和结论 | 不默认吸收所有普通划线 |

**[实现提案]** `CaptureResolution` 和 `ProcessingRun` 是可修订的解释/运行记录，不是原图事实。`PageObservation` 是「某次模型输出的不可变记录」，不意味着模型识别内容绝对正确。

任何用户修正都必须形成新版本或显式 correction；不能改写 `PageCapture`、原图或历史 `PageObservation`。界面可展示当前修正结果，但必须仍可打开初始证据及其历史。

---

## 5. Domain Model

### 5.1 共同约定

**[实现提案]** 规范文件使用 JSON Schema Draft 2020-12。当前仓库主文件有 77 个定义，默认根对象为 `ReadingTrace`；其中复用定义从原先内嵌的结构提取，缺少原始底稿包，无法逐名比较。其他类型通过 `schemas/<Model>.schema.json` 入口校验，或选择主文件中的对应 `$defs`。

所有持久领域记录包含 `object_type`、`schema_version`、`id`、`owner_id`、`created_at`。`schema_version` 在本稿固定为 `0.1.0`。业务对象 ID 是带前缀的不透明字符串；调用方不能从 ID 推断题名、页码、时序或所有者。

所有对象默认 `additionalProperties: false`。Schema 中声明为必填但可为 `null` 的字段，表示「这个字段已被考虑，但目前未知」；不能用空字符串、`0`、`1.0` 或虚构 ID 代替未知值。

时间使用包含时区的字符串；`created_at` 表示该记录版本的持久化时间，不保证等于阅读时间、拍照时间或落笔时间。`owner_id` 是访问隔离边界；它必须由可信身份上下文验证，不能信任模型或用户提交的任意 owner 字符串。

版本化对象的第一版为 `revision: 1, supersedes_revision: null`。后续版本必须满足 `revision = previous + 1` 且 `supersedes_revision = previous`。当前视图指向某个版本，历史版本不被覆盖。

### 5.2 Work

**[继承：底稿 §5.1]** `Work` 表示抽象作品。

| 字段 | 类型 / 约束 |
|---|---|
| `id` | `work_` 前缀 ID |
| `title` | 非空标题 |
| `original_title` | 字符串或 `null` |
| `authors` | `{name, entity_id}` 数组；未知时可为空，不虚构实体 ID |
| `identifiers` | `{scheme, value}` 数组；保存实际取得的外部标识 |
| `revision / supersedes_revision` | 目录修订版本 |

**[实现提案]** `authors` 从底稿的简单 ID 示例展开为姓名与可选 entity reference，避免依赖尚未验证存在的人物实体库。

### 5.3 Edition

**[继承：底稿 §5.2]** 纸书页码只能在 edition 上下文中解释，不能直接挂到 Work。

`Edition` 必须引用同一 owner 下存在的 `Work`。其字段为 `work_id`、`edition_label`、`publisher`、`publication_year`、`isbn.isbn13`、`isbn.isbn10`、`language`、`page_count`、`volume_label`。除 `work_id` 外的书目细节允许未知。

ISBN 格式长度由 Schema 校验；校验位、书目真实性和外部查询不是 Schema 能证明的。系统禁止把底稿中的出版年份、出版社或示例页数当成用户实际版本的已核实信息。

**[实现提案]** `volume_label` 预留卷册范围。同一 Work 存在多卷且页码重复时，必须明确定位所用的版本/卷册上下文；无法确认时不跨卷合并。PAP 对多卷 edition 的现有建模方式属于待核实事项。

### 5.4 BookInstance

**[继承：底稿 §5.3]** `BookInstance` 是用户持有、借阅或曾经持有的那一本，不能被 ISBN 或 Edition 替代。

本版本 `BookInstance.medium` 固定为 `physical`。其核心字段为 `edition_id`、`acquired_at`、`ownership_status`、`physical.qr_id`、`physical.shelf`、`reading_status`。

`reading_status` 包含 `state`、`current_page` 和 `progress_evidence_ref`。状态取值为 `unknown / unread / reading / paused / abandoned / finished / rereading`。这是显式状态或有来源的记录，不从照片数量推断。

同一 edition 的自有本、借阅本、重购本和二手本必须允许使用不同 `BookInstance.id`。二手本上的痕迹不能因为用户拍摄了照片就自动归为用户本人所写。

### 5.5 支撑类型

**[实现提案]**

| 类型 | 关键语义 |
|---|---|
| `TextField` | `{text, confidence, basis}`；文本未知可为 `null` |
| `TimeField` | `{value, confidence, basis}`；保留 EXIF、源系统或用户陈述的来源差异 |
| `PageLabel` | `{label, number, scheme}`；支持普通数字、罗马页码或其他标签 |
| `IdentityField` | `{value, confidence, basis, status}`；身份识别可为 unresolved 或 conflict |
| `ObjectRef` | `{object_key, sha256, mime_type, byte_size}`；对象引用不是公开访问授权 |
| `TraceRevisionRef` | `{trace_id, revision}`；知识和事件引用确切版本 |
| `BBox` | `[x_min, y_min, x_max, y_max]`；坐标规则见 §23 |

`PageLabel.number` 仅在确实解析出普通整数页码时填写。页码未知时整个 `PageField.value` 为 `null`，不能借照片顺序补号。

## 6. Reading Session

**[继承：底稿 §§6、25、34]** Session 是第一等对象。备注可来自短文字、语音转录或不填写；它不是强制步骤。

`ReadingSession` 的正式字段为：四类上下文引用 `work_id / edition_id / book_instance_id / medium`，`status`，`started_at`，`ended_at`，`progress` 和 `session_note`。

**[实现提案]** 明确选择书籍的 `/lib read` 创建或恢复确定会话；无命令图片可以建立归属待定的会话。后者允许上下文 ID 为空，不能因此虚构某本书或某个版本。数字来源没有真实会话信息时，trace 的 `session_id` 可以为空，不需要伪造 Session。

开始和结束时间只记录实际获得的报告。创建会话的系统时间、收到照片的时间和用户实际开始/结束阅读的时间必须区分。没有时间报告时，`started_at.value` 或 `ended_at.value` 可以为空；不得据此计算精确阅读时长。

`progress` 是 `ProgressReport` 或 `null`；它包含 `start_page / end_page / basis / reported_at / evidence_ref`。仅接受用户报告或可靠 source payload，不接受「最大照片页码」作为阅读终点。

## 7. Physical Capture Protocol

**[继承：底稿 §§7、35、39]** 默认交互是：用户阅读时不操作 PAP；阅读后拍下有痕迹的页面。上传不要求逐图命名、打标签或手动框出所有划线。

**[实现提案]** 正常处理过程中最多给出一次聚合反馈。书籍歧义应尽量按 batch 或共同冲突询问，而不是逐条 trace 询问。页码不清可以保存为 unresolved，不必强制补拍。

系统不可用时不能要求用户重新读书或重做批注；已经成功接受的图片必须能从持久化原图恢复处理。

## 8. Capture Entry Points

**[继承并显式裁定：底稿 §§8、37]**

| 入口 | v0.1 行为 |
|---|---|
| Agent Gateway | 必须支持；图片消息进入统一摄取命令，不强制用户写命令 |
| Explicit session | 必须支持；`/lib read <书名>` 是用户交互意图，适配为会话应用命令 |
| QR | 仅保留设计；本次 MVP 不实现扫码 workflow |

底稿 §8 将 QR 列入三个入口，§37 又将 QR 排除在 MVP 之外。**本稿采用 §37 的 MVP 边界**。这是一项显式范围裁定，不是认定底稿已经无歧义。

Gateway 必须传入稳定的 `source_event_id`、每个附件的 `source_item_id`，以及可信上传引用 `upload_ref`。没有稳定源 ID 时，Gateway 应在首次接受时生成并持久化重试标识，不能退化为仅按图片哈希认定“同一次上传”。

用户可见的 `/lib read` 命令不是服务接口本身；实际 slash command 或自然语言解析应复用 PAP 当前 Gateway。

## 9. Book Resolution

**[继承：底稿 §9]** 解析优先级保持为：explicit session → active session → recent-session affinity → visible title/running header → edition fingerprint → user confirmation。禁止直接依赖 LLM 猜书。

**[实现提案]** Resolver 输出版本化 `CaptureResolution`，而不是修改 `PageCapture`。它分别记录 `session`、`work`、`edition`、`book_instance` 的 `IdentityField`，以及页区结果和证据指针。

`status=resolved` 时必须有 `value`；`unresolved / conflict` 时不得在有效值中保留一个未经确认的“最佳猜测”。候选可以留在诊断日志或独立解析记录中，但不能伪装为选中事实。

解析决策必须遵守：

1. 优先级只决定证据检查顺序，不能让弱线索覆盖强冲突。明确 session 与可见标题冲突时，应记录 conflict，而不是擅自换书或忽略标题。
2. 标题只确定 Work 时，不得顺手确定 Edition 或 BookInstance。多个同名作品、同作品多版本及同版本多副本都需要保留歧义。
3. 只有经过可信映射的上下文、已注册且可审计的 fingerprint，或明确用户确认，才能形成可采用的身份链。模型自行给出的高分不是事实依据。
4. 缺失书名或页码不阻止原图保存和独立视觉观察；生成的 trace 必须携带 unresolved 状态，禁止偷偷挂到最近一本书。

v0.1 的自动归属至少实现 explicit session、唯一适用 active session 和受约束的 affinity。没有 fingerprint 数据或验证方法时，不能宣称已实现版式指纹识别；对应策略只作为扩展接口存在。

## 10. Session Affinity

**[继承：底稿 §§10、25]** 默认值保留 `soft_timeout_minutes: 90` 与 `hard_timeout_hours: 6`。90 分钟不等于阅读结束。

**[实现提案]** Affinity 必须限定在相同 `owner_id + transport + account_id + conversation_id` 的上下文内，不建立跨聊天或跨用户的“最近一本书”全局变量。

计时使用同一捕获流中最后一次可靠归属的接收时间。0–90 分钟内，可以在无冲突且上下文唯一时继承；90 分钟至 6 小时之间，近期关联只能作为辅助线索，不得单独决定；超过 6 小时，不再依赖 recent-session affinity。

显式提供的 session 不因上述时限失效；但 CLOSED session 不应静默重新打开。用户明确选中的长期 active session 与“因为最近上传而推测活跃”必须区别处理，避免以 active-session 名义绕过 affinity 的过期规则。

即使超过 hard timeout，也不能据此推断用户已读完、已停止或已弃读。

## 11. Capture Batch

**[继承：底稿 §11]** `CaptureBatch` 表示一次摄取批次，包含源上下文、接收时间、capture 列表和处理状态。

**[实现提案]** 默认以一次 Gateway 请求或平台明确提供的同一相册/媒体组作为 batch 边界。不同消息的连续照片仍可归入同一 Session，但不能在无边界依据时无限合并为同一 batch。跨消息的 debounce 聚合属于 Gateway 侧可选能力，不是当前 domain contract 的前置依赖。

`capture_ids` 非空且唯一。`status` 为 `received / processing / processed / partial / failed`；该状态属于版本化 manifest，不属于原始图片。

入口采用 **all-or-retry acceptance**：一个请求中的附件全部通过入口校验并完成原始对象持久化后，才提交该 batch 的接受结果。识别阶段可以部分成功；入口阶段不能返回“全部已保存”而实际只保存部分附件。入口失败后的对象临时写入由存储回收策略处理，不作为已接受的阅读记录展示。

## 12. Page Capture

**[继承：底稿 §§12、22、末尾设计决策]** 每张照片必须保存为 immutable source artifact；`PageCapture` 永远属于 Evidence，不是 note。

### 12.1 不可变字段

| 字段 | 说明 |
|---|---|
| `batch_id` | 首次接受时所属 batch |
| `received_at` | 服务确认收到附件的时间 |
| `captured_at` | 获得的拍照时间与来源；可以未知 |
| `asset` | 原始字节的对象引用、SHA-256、MIME、字节数 |
| `origin` | transport、account、conversation、源事件与附件 ID |
| `submitted_context` | 首次接收时用户或 Gateway 提供的上下文提示，不代表最终解析结果 |

### 12.2 从底稿示例中分离可变字段

**[实现提案]** 底稿 §12 的示例把原图、页码解析、book/session 和 processing status 放在同一个对象中。本稿为落实“证据不可覆盖”，拆分为：

```text
PageCapture          immutable receipt + original ObjectRef
CaptureResolution    append-only context/page resolution revisions
PageObservation      immutable extraction record + raw output reference
ProcessingRun        versioned execution state / attempts / issues
ReadingTrace         normalized, revisioned reading record
```

UI 可以提供组合后的 `CaptureView`，但它是投影，不是新的证据权威。更正书籍归属不会改写 `submitted_context`。

### 12.3 原图与去重

原图哈希针对接收到的原始文件字节计算。旋转、纠偏、压缩、裁剪或去阴影结果都只能作为 derivative，不替换原始对象。

同一 SHA-256 可以复用存储字节，但不等于同一次摄取行为。不同消息中再次发送同一照片，可以有新的 `PageCapture`。照片字节去重、上传重试去重和阅读行为判断是三个独立问题；重复照片不能证明用户重读了该页。

## 13. Vision Extraction Output

**[继承：底稿 §13]** 视觉模型输出 observation，不直接输出 knowledge，也不决定用户相信什么。

**[实现提案]** 正式 `PageObservation` 包含 `capture_id`、`processing_run_id`、`extractor`、`raw_output_asset`、`image_space`，以及 `pages / printed_regions / marks / annotations / symbols / links / warnings`。

可选的 `visible_title` 是视觉识别到的书名线索，带字段级 confidence；它不直接决定归属。只有当高置信线索唯一匹配已登记的另一部 Work 时，才将当前会话归属标为冲突并等待用户确认。低置信线索或仅仅与当前标题不完全一致，不足以自动换书。

每个检测元素必须有稳定的本次 observation 内 ID、所属 `page_region_id`、bbox 和字段级识别信息。页码、印刷文字、手写文字、符号与连接关系分别给分；整个 observation 不能用一个总分代表。

关键输出规则如下。

- 不知道页码、手写内容或作者时输出 `null / unknown`，不能补齐一个“合理答案”。没有痕迹的纯印刷区域不能自行产生 trace。
- `marks` 只描述可见标记；`linked_text_region_ids` 指向确实关联的印刷区域，`link_confidence` 与标记存在的 confidence 分开。箭头端点可以未知。
- `annotations` 保存读出的边注或行内注。单词内部的标点不自动成为独立的用户符号命令。
- 一张跨页照片必须按 page region 区分页区。所有 region 坐标最终回到同一个原图坐标系。无法可靠分开时保留局部观察和异常，不能把左右页文字混成一句。

`printed_regions` 的数组顺序由 extractor 尽力提供页内阅读顺序；normalizer 不通过简单的 x/y 排序假装解决多栏、竖排或复杂版式。无法确定连续性的片段在展示时分段，不作为连续引文。

模型的原始返回字节先保存到 `raw_output_asset`，解析后的对象再做 Schema 校验。输出不合法时保留原始返回并标记错误；不得把自作主张“修好”的 JSON 当成原始模型输出。修复尝试须形成新的处理记录。

页面中的指令性文字、书名、批注和二维码内容全部是输入数据。Extractor 和 normalizer 禁止据此执行系统命令、调用外部工具或修改用户配置。

## 14. Reading Trace

**[继承：底稿 §§14–16]** `ReadingTrace` 是三个来源共享的规范化阅读事件对象。

### 14.1 正式结构

`ReadingTrace` 包含版本和状态、`context_state`、四类归属 ID、`medium`、`location`、`trace_types`、`content`、`source`、`provenance`、字段 confidence、`marked_at`、`attribution`、`intent_signals` 和 `review`。

| 部分 | 必须满足的约束 |
|---|---|
| 上下文 | physical 且 `context_state=resolved` 时，Work / Edition / BookInstance / Session 必须齐全并构成同一条有效身份链 |
| 位置 | physical 使用 `PhysicalLocation`；数字来源使用 `DigitalLocation`；不能将 EPUB/平台 locator 冒充纸书页码 |
| 内容 | 印刷文本、边注和符号分开；未知文本可为空，但不能用摘要补写原文 |
| 来源 | physical 指向 capture、observation、resolution 的确切版本和检测 ID；数字来源指向原始 payload 与源记录 ID |
| 修订 | 稳定 trace ID 加连续 revision；旧文本、旧归属和旧 provenance 均可追溯 |
| 作者归属 | `mark_author=user / other / unknown`；上传者身份不足以证明批注作者身份 |
| 意图信号 | 用户启用的符号语义或明确指令的结构化信号；不是视觉检测类型 |

未解析 trace 可以保存；正常书名归属检索默认不把它混入已确认书籍结果。用户明确检索 unresolved 内容时，必须显示「书籍未确定」等警告，不能用命中的文本反向假造书名。

### 14.2 Deterministic normalization

**[实现提案]** 同一 `PageObservation + CaptureResolution revision + normalizer version + configuration` 必须产生相同的归一化 write plan。

以 mark、annotation、symbol 为痕迹节点。明确的 `annotates / continues` 等观察连接，在满足配置的链接采纳阈值且位于同一页区时，可以形成一组 trace。两个标记仅因为邻近或指向同一段文字，不应无条件合并。跨页连接使用独立 trace 和关系表示。

每组 trace 汇集其直接关联的印刷区域、边注和符号；bbox 为相关证据区域的包络。没有可靠文本关联的划线仍可保存为空文本 trace，不能绑定到“最像的一句话”。没有可见痕迹的印刷文字不生成独立 trace。

合并后的 `printed_text` 是检索字段；非连续区域应分段展示并能分别回到原文区域，不能把字符串串接结果冒充原书的连续引文。跨多个同一 extractor 字段合并 confidence 时，仅在全部评分已知且量纲一致时取最小值；否则为 `null`。原始各区域评分始终留在 observation 中。

### 14.3 Trace 身份与重新提取

同一 observation 内，trace 的业务键由 `owner + source identity + observation_id + sorted detection_ids` 确定。处理重试不能创建第二份相同业务 trace。

用户纠正文案或确认归属时，沿用 trace ID 并新增 revision。重新运行视觉模型可能改变区域分组，不能假定 `mark_01` 在不同 observation 中仍是同一痕迹。

**[实现提案]** 跨 observation 的重新提取先生成待对账结果。无用户修正依赖且可确定替换范围时，原子切换新一代有效结果，并把旧 trace 标为 superseded，保留 lineage。存在用户修正、已晋升知识或无法可靠映射的拆分/合并时，不自动覆盖当前有效版本；记录 `RECONCILIATION_REQUIRED`。v0.1 不要求实现任意复杂的自动对账算法，但必须避免重复和修正丢失。

## 15. Unified Reading Trace

**[继承：底稿 §§15、27]** `medium` 保留 `physical / weread / koodo`，上层只消费 `ReadingTrace[]`。

**[实现提案]** 三类差异仅存在于 source/locator 与各 adapter 中：

| 项目 | physical | weread / koodo |
|---|---|---|
| 原始证据 | 图片 + raw observation | raw adapter payload |
| 位置 | edition 范围内的页标签和图像区域 | chapter / paragraph / source-native locator / EPUB CFI 等 |
| 会话 | 优先建立真实或待归属 session | 源系统未提供时允许为空 |
| 纸书副本 | resolved 时必须有 | 不强制创建虚构 BookInstance |
| 文本来源 | 视觉提取或用户更正 | 源字段导入或用户更正 |

底稿中的数字来源 `confidence: 1.0` 是示例，不要求 adapter 虚构一个绝对可靠分数。源文本可精确复制时记录 `basis=source_payload`；源系统未提供评分则 `confidence=null`，这不表示数据不可用。

目前附件没有提供微信读书或 Koodo 的真实 payload，因此本稿只固定 adapter 输出契约及合成测试，不声称已验证任何私有 API、导出格式或同步权限。

## 16. Trace Types

**[继承：底稿 §16]** 合法值仅为：

```text
highlight  underline  circle  bracket  margin_note  inline_note
symbol  arrow  page_mark  unknown_mark
```

一个 trace 可以有多个 type；集合非空且无重复。

**[显式裁定]** 底稿验收示例中的 `question` 与 `reread_target` 不是新增的视觉 trace type。原始痕迹应记录为 `symbol` 或相应批注；问题与重读意图进入 `intent_signals`，必要时进入 `KnowledgeCandidate`。这一处理保留了“观察”与“解释”的边界。

## 17. Personal Annotation Vocabulary

**[继承：底稿 §17]** 预设模板保持：`!! → promote_candidate`、`? → unresolved_question`、`× → disagreement`、`↔ → connection_candidate`、`R → reread_target`。语义属于用户级配置，普通感叹号不能自动获得 `!!` 的含义。

**[实现提案]** 模板默认不启用。用户选择启用后，规则必须有 `vocabulary_version`；trace 记录使用了哪个版本。修改词汇表不静默改变历史 trace 的原始符号或过去解释。

语义匹配必须作用于独立、可见且可靠识别的纸面符号，不能把正文里的 R、引用中的问号或边注单词里的标点当成操作指令。符号可触发 candidate，不等于知识已经晋升，也不等于确定用户立场。

## 18. Knowledge Candidate

**[继承：底稿 §18]** `knowledge_candidate != knowledge_object`。

`KnowledgeCandidate` 必须记录 `source_trace_refs`，包括 trace ID 和 revision。`candidate_type` 为 `concept / claim / question / disagreement / connection / reread_target`；内容和 entity/concept 解释分别保存自己的来源与 confidence。

**[实现提案]** Candidate 状态为 `pending → approved → promoted`，或 `pending → rejected`。来源发生相关修订时可进入 `superseded`；不能把旧版解释默默迁移为对新版来源的断言。`promoted` 必须引用已由知识服务成功持久化的 `knowledge_id`。

模型写出的候选内容须标记为 `basis=model_inference`，不能装入 trace 的 `printed_text` 或用户 `annotation` 字段。仅凭 `Parsons?`，候选只能表达可能存在的联想，不能断言赞同 Parsons、反对 Weber 或已经形成特定理论观点。

## 19. Promotion Policy

**[继承：底稿 §19]** 默认路径为 `trace → stay trace`。候选触发源限于明确符号/指令、强语义信号、跨来源重复出现、或 Librarian 的显式整理任务。

**[实现提案]** 普通 underline/highlight 不触发自动晋升。`!!` 在启用词汇表时默认只创建 candidate。明确要求“记下来”的用户指令可以作为批准依据，但仍必须经过同一 knowledge service 的来源保留和幂等写入流程。

知识服务成功写入之后，才允许 candidate 标为 promoted 并发送 `reading.knowledge.promoted`。失败或重试不能产生多张重复知识卡，也不能提前发布成功事件。

MVP 的基础摄取不得依赖 Candidate/Knowledge 功能可用。自动 recurrence、跨书 connection、recommendation 均属于后续阶段，不由本次 Schema 的存在暗示已经实现。

## 20. Confidence Policy

**[继承：底稿 §20]** Confidence 属于具体字段，不能用一个全局分数代表整个对象。

**[实现提案]** 分数取 `[0,1]` 或 `null`；`null` 表示未提供或不能合理给分，不能强行替换为 `0`。身份选择、页码、印刷文本、手写文本、符号检测、文字关联、关系解释必须分别处理。

模型分数在本契约中只是局部评分，不被当成已校准的客观正确率。用户更正记录 `basis=user_statement`，不需要伪装为模型 confidence 1.0。

`ReadingTrace.confidence.book_resolution/page_number` 是对应解析字段的快照；文本评分在各自 `TextField` 中。快照必须与引用的解析版本一致。`TraceRelation.confidence` 只描述该条关系判断，不代表其全部源文本的正确率。

阈值是策略配置；本稿提供的初始值是实现提案，不是基于真实照片测得的性能结论，参见附录 D。

## 21. Review Policy

**[继承：底稿 §21]** 内容 review queue 只处理 `important AND low-confidence` 的例外，不要求用户审核每条 trace。

**[实现提案]** 必须区分两类队列：

- **归属异常**：无法确定书籍、副本或会话时的 resolution queue。可以按 batch 询问一次，也可以先保留 unresolved。这不是逐条 OCR 审核。
- **重要内容复核**：可靠识别出启用的 `!!` 等重要信号，但对应手写或正文读不清时，进入 content review queue。

重要内容的必要字段评分未知，也可以视为需要复核；普通划线评分低则保留原图与不确定性，不主动打断用户。`review.state=pending` 必须同时 `required=true`。

单个独立 `?` 表示待解决问题，不自动等于需要人工校正 OCR。问题跟踪与识别复核不能合并成一条无限积压的“待处理”队列。

## 22. Evidence Immutability

**[继承：底稿 §22]** 原图、raw payload、原始时间来源、原始 OCR/vision output 不得被 inference 覆盖。

**[实现提案]** 用户将 `Parsons?` 改为 `Parsons!` 时：PageCapture 不变；原 observation 不变；ReadingTrace 新增 revision；该版本标记 `user_correction`；事件 `reading.trace.corrected` 指向新旧版本。

自动重新识别不得覆盖人工 correction。没有确定映射时停留在待对账状态，而不是以新模型分数更高为由抹掉人工输入。

“不可变”不等于“永远不能由用户删除”。用户要求的数据删除与存储保留策略是独立生命周期能力；若执行删除，必须覆盖原图、衍生图、索引和关联导出，且不能声称删除后仍可查看原始证据。具体删除接口与保留周期依赖 PAP 当前能力，列为待核实，不在本稿伪造既有实现。

## 23. Spatial Memory

**[继承：底稿 §23]** 必须保留纸书的空间线索，例如「右页上方」与具体 bbox。

**[实现提案]** 统一坐标系为 `exif_oriented_original`：原图字节不改动，但解码显示时应用原图 EXIF 方向。所有观察、trace 和 crop 坐标都必须映射到这一显示坐标系。缩放、纠偏或局部裁剪推理后的坐标必须反变换；无法映射时不能作为最终 trace bbox 提交。

`BBox = [x_min, y_min, x_max, y_max]`，满足 `0 ≤ x_min < x_max ≤ 1` 及 `0 ≤ y_min < y_max ≤ 1`。原点为左上角。`image_space.width/height` 为上述显示坐标系的尺寸，不是某个模型缩略图的尺寸。

`PhysicalLocation` 同时携带 `page_bbox` 与 trace `bbox`，两者都位于原图坐标系。文字“上/中/下”和“左/中/右”在 **页区局部坐标** 中计算，不能以整张跨页照片的位置替代页内位置。

初始区域规则：纵向等分五段 `upper / upper_middle / middle / lower_middle / lower`；横向等分三段 `left / center / right`，用 trace 包络框中心所在区段决定。`side=left/right` 指书页位置，不能仅根据页码奇偶推断；缺少可见或明确依据则为 `unknown`。

## 24. Derived Page Crop

**[继承：底稿 §24]** Crop 是非权威 derivative；source of truth 仍为原始页面图像和 bbox。

**[实现提案]** Crop 缓存键至少包含原图 hash、规范化 bbox、renderer version 和裁剪参数。它可以删除重建；旧 crop 不能使当前修订后的文字或归属看起来仍来自旧位置。

像素框从规范化 bbox 计算，起点向下取整、终点向上取整并限制在图像边界。上下文边距可以配置，必须保持原图链接始终可用。没有实现 crop UI 时，MVP 至少可以打开原图并指出 bbox；高级空间 UI 不作为首期前置依赖。

## 25. State Machine — Reading Session

**[继承：底稿 §25；状态细化为实现提案]** `IDLE` 是没有 active session 的用户/上下文状态，不创建一个 `status=idle` 的伪会话。

| 当前状态 | 动作 | 新状态 | 限制 |
|---|---|---|---|
| 无 session | 明确启动或建立待归属会话 | active | 缺失时间保持未知 |
| active | pause | paused | 不代表读完 |
| paused | resume | active | 仍是同一 session |
| active / paused | close | closed | 终点页码和实际结束时间可为空 |
| closed | 重复同一 close 请求 | closed | 幂等返回原结果 |
| closed | 新一轮阅读 | 新 session | 不静默把旧 session 重新打开 |

允许 inactivity 使交互上下文变弱或进入 paused，但不得在 90 分钟时自动 close，不得捏造阅读结束时间。pause/resume 可以不新增底稿之外的公开领域事件，但必须持久化状态修订。

## 26. Capture Processing State and Pipeline Contract

### 26.1 状态与异常

**[继承：底稿 §26]** 无异常的参考路径为：

```text
RECEIVED → STORED → SESSION_RESOLVED → PAGE_RESOLVED
         → EXTRACTED → NORMALIZED → INDEXED
```

**[实现提案]** `ProcessingRun` 使用 `checkpoint + outcome + issues`，避免将“页码未知”和“系统崩溃”混成同一个失败状态。

`outcome` 为 `pending / success / partial / failed`；`issues` 保留底稿的 `NEEDS_BOOK_RESOLUTION / NEEDS_PAGE_RESOLUTION / PARTIAL_EXTRACTION / FAILED`，并新增防止修订丢失的 `RECONCILIATION_REQUIRED`。

`checkpoint` 表示已经完成的最高处理阶段，不意味着前面的所有业务值都已解析成功。存在 unresolved 结果时仍可完成提取和 normalization；业务归属以 `CaptureResolution` 状态为准，不能仅凭 `PAGE_RESOLVED` 等名字推定页码已知。

### 26.2 每一步的输入、输出和写入边界

| 阶段 | 输入 | 输出 | 允许的持久化副作用 | 异常 / 重试语义 |
|---|---|---|---|---|
| A. Accept / Store | `reading.capture.ingest` + 可信上传字节 | `CaptureBatch`、`PageCapture[]`、receipt | 原图对象、manifest、接受事件 | 原图未持久化不得接受；相同幂等键返回同一结果 |
| B. Resolve session/book | `PageCapture`、用户上下文、catalog、现有 session | `CaptureResolution` 上下文 revision | 解析记录，必要时新建待归属 session | 冲突保留，不自动覆盖 explicit context |
| C. Resolve pages | 原图、已知 edition 范围、页区检测结果 | `CaptureResolution.pages` revision | 页区、页码和依据 | 不确定可继续提取；禁止用相邻照片补页码 |
| D. Visual extraction | 原图/可追溯 derivative、提取配置 | `PageObservation` + raw output | 原始返回对象、通过校验的 observation | 失败可重试；每次实际新模型调用留新记录 |
| E. Normalize | `PageObservation`、确定版本的 `CaptureResolution`、符号词汇表 | `TraceWritePlan` | 纯规划阶段不改源证据 | 相同输入必须可重复；不调用知识晋升 |
| F. Persist | `TraceWritePlan`、expected revisions | `ReadingTrace` 新记录/修订、outbox rows | 同一事务提交 trace、lineage/引用、领域事件、处理检查点 | 乐观锁冲突重新读取；不能只写 trace 不写事件 |
| G. Index | trace created/corrected events | 可重建搜索索引、消费游标 | 索引、消费去重记录、可选处理投影 | 至少一次消费；旧 revision 不覆盖新索引 |

`TraceWritePlan` 是应用服务内的结构，不是另一个用户可编辑领域对象。它应包含待创建 trace、待新增 revision、明确的 supersession 关系和 expected revisions；提交前必须通过 Schema 与业务不变量校验。

页码解析和主要视觉提取可以复用一次模型调用，避免为了流程图重复识别整张图片；逻辑输出仍分别存放在 resolution 与 observation 中。页码阶段必要的早期视觉输出也必须保留原始返回，不能只有最终结论。

### 26.3 可重复执行

每个阶段以 `owner + capture/source identity + input revision(s) + component version + config identity` 确定执行键。已经保存的有效 observation 在同一次重试中优先复用；不得把“重试持久化”变成再次随机抽取模型输出。

失败后的恢复从最后一个持久检查点开始。不同 pipeline/extractor/config 版本属于有意 reprocessing，不等于原请求重试。reprocessing 必须遵守 §14.3 的对账规则。

索引失败不能抹掉已提交 trace。`reading.capture.processed` 表示 trace 已持久化而非所有索引已追上；UI 必须区分“已保存”和“已可检索”。

## 27. Unified Ingestion Interface and Application Commands

### 27.1 Adapter boundary

**[继承：底稿 §27]** 完成态的 adapter 协议保持：

```text
ReadingSourceAdapter.ingest(source_event) → ReadingTrace[]
ReadingSourceAdapter.resolve_work(source_event) → WorkRef / unresolved result
ReadingSourceAdapter.provenance(source_event) → Provenance
```

**[实现提案]** 以上描述处理完成后的领域结果，不要求 Gateway 在一次同步请求中等到模型和索引结束。Physical 入口先返回 `CommandReceipt`，orchestrator 再执行各阶段。每个 adapter 负责自己的来源身份、位置映射、raw payload 和幂等键；上层检索与知识服务不得分支调用平台私有对象。

### 27.2 Command envelope

所有写入命令使用 `Command`，包含 `command / version / command_id / owner_id / issued_at / idempotency_key / actor / payload`。可信应用服务必须验证 owner 与 actor 权限。

客户端不能借命令中的 owner 字段访问其他用户；即使请求可通过 JSON Schema，也必须执行授权检查。重复同一业务请求的幂等比较以 `owner + command + payload` 为准，忽略仅用于追踪的 command ID 与发送时间；同键不同业务内容返回 `IDEMPOTENCY_CONFLICT`，禁止覆盖原结果。

### 27.3 命令目录

| 命令 | 主要输入 | 结果 / 关键约束 | 阶段 |
|---|---|---|---|
| `catalog.register_work` | Work 初版 record | Work 引用；owner 一致、版本为初版 | MVP |
| `catalog.register_edition` | Edition 初版 record | Edition 引用；Work 必须存在 | MVP |
| `catalog.register_book_instance` | BookInstance 初版 record | 副本引用；Edition 必须存在 | MVP |
| `reading.session.start` | book instance、可选开始时间和起始页 | session 引用；未知值不补写 | MVP |
| `reading.session.pause` | session、expected revision | 新 session revision | MVP |
| `reading.session.resume` | session、expected revision | 新 session revision；closed 不可直接恢复 | MVP |
| `reading.session.report_progress` | session、expected revision、ProgressReport | 有来源的进度修订 | MVP |
| `reading.session.close` | session、expected revision、可空终点/备注 | closed session；不要求补全未提供信息 | MVP |
| `reading.capture.ingest` | source、context hint、attachments | accepted receipt + batch/capture 引用 | MVP |
| `reading.capture.resolve` | capture、expected resolution revision、书/会话及页码 | 新解析版本和受影响 trace revision | MVP |
| `reading.trace.correct` | trace、expected revision、correction | 新 trace revision；原 observation 不动 | MVP |
| `reading.knowledge_candidate.approve` | candidate、expected revision | approved，再委托知识服务；不等于自动成功晋升 | 后续 |
| `reading.knowledge_candidate.reject` | candidate、expected revision、reason | rejected candidate | 后续 |

当前 payload 见运行时 Schema 与 `examples/positive.json` 中的命令案例。`correction` 中省略的字段保持不变，显式 `null` 表示改为未知；不能用省略/空值混淆覆盖语义。

本稿不强制 HTTP 路径。底稿中的 `POST /librarian/sessions/start` 可以由现有 API 映射到相应应用命令；没有检查当前路由前，不新增一套与现有 Gateway 重复的 API。

### 27.4 错误契约

使用 `ErrorResult`：`code / stage / retryable / message / details`。错误详情必须脱敏，不能包含完整页面内容、访问令牌或未经授权的其他用户 ID。

业务冲突使用 `IDEMPOTENCY_CONFLICT / REVISION_CONFLICT / CONTEXT_CONFLICT / INVALID_STATE_TRANSITION`；资源错误使用 `OBJECT_STORE_UNAVAILABLE / EXTRACTOR_UNAVAILABLE / INDEX_UNAVAILABLE`；模型输出结构不合法使用 `EXTRACTION_SCHEMA_INVALID`。

书籍或页码未知通常是已接受处理中的 partial 状态，不是必须把整批丢弃的 HTTP 错误。可重试错误仍需要应用重试策略；`retryable=true` 不表示可以无限重试。

## 28. Event Model

**[继承：底稿 §28]** ingestion 通过领域事件解耦下游 embedding、索引、entity extraction 和后续整理任务。

### 28.1 Envelope

**[实现提案]** 保留底稿的 `event / version / occurred_at / payload`，补充 `event_id / owner_id / producer / correlation_id / causation_id / aggregate`。

```json
{
  "event": "reading.trace.created",
  "version": 1,
  "event_id": "evt_example_1",
  "owner_id": "owner_example",
  "occurred_at": "2026-09-28T15:01:15+08:00",
  "producer": "librarian",
  "correlation_id": "cmd_example_ingest",
  "causation_id": null,
  "aggregate": {"type": "reading_trace", "id": "rt_example", "revision": 1},
  "payload": {
    "trace_id": "rt_example",
    "revision": 1,
    "medium": "physical",
    "book_instance_id": "bookinst_example"
  }
}
```

`version` 是该事件类型的 payload 契约版本，不是 trace revision，也不是 extractor version。`occurred_at` 是领域变化时间，不是阅读行为时间。

### 28.2 九个事件的发布语义

| 事件 | 何时发布 | 必须引用的 payload | 业务去重键 |
|---|---|---|---|
| `reading.capture.received` | 原图与 capture manifest 已持久化、批次正式接受 | batch ID、capture IDs | event type + batch ID + initial revision |
| `reading.capture.processed` | 本次 run 的 trace 结果已提交；可有 partial | capture ID、processing run ID、outcome、trace refs、issues | event type + processing run ID + 完成代次 |
| `reading.session.started` | 新 session 首次提交 | session ID/revision、medium、副本引用 | type + session ID + revision |
| `reading.session.progressed` | 新的有来源进度已提交 | session ID/revision、ProgressReport | type + session ID + revision |
| `reading.session.closed` | session 进入 closed | session ID/revision、可空进度 | type + session ID + revision |
| `reading.trace.created` | trace 首版提交 | trace ID、revision=1、medium、副本引用 | type + trace ID + revision |
| `reading.trace.corrected` | trace 新 revision 提交 | trace ID、previous/new revision、reason | type + trace ID + revision |
| `reading.knowledge_candidate.created` | candidate 首版提交 | candidate ID/revision、source trace refs | type + candidate ID + revision |
| `reading.knowledge.promoted` | 知识对象已成功持久化且 candidate 更新完成 | candidate ID/revision、knowledge ID、source trace refs | type + candidate ID + promotion result |

`capture.received` 的名字保留底稿，但语义是进入可重放的持久域，不是在网络包刚到达时提前宣布成功。`capture.processed` 不承诺索引已经完成，也不承诺归属全部 resolved。

### 28.3 投递、事务与顺序

**[实现提案]** 以至少一次投递设计：消费者按 `event_id` 去重，并按实际业务键实现幂等。禁止依赖“事件只来一次”。同一 trace 的晚到旧 revision 不得覆盖新索引。

trace/domain 写入与待发布事件必须原子提交；优先使用 PAP 已有 transactional event 能力，否则采用同一事务中的 outbox 或等价恢复机制。Publisher 重试只改变投递状态，不生成新 event ID。

不承诺全局事件顺序。引用可修订实体时通过 aggregate revision 判断新旧；immutable PageCapture 的 revision 始终为 1，多次处理以 `processing_run_id` 区分，不能拿 capture revision 当作处理代次。

capture 处理彻底失败时，不发布一个假的 processed-success。使用失败的 ProcessingRun 和 Gateway 状态反馈；是否增加新的失败公开事件需另行扩展契约，不能擅自改变九种事件的含义。

## 29. Proposed Storage Layout

**[继承：底稿 §29]** Librarian 拥有自己的 domain data，但对象存储、事件与基础设施优先复用 PAP。

**[实现提案]** 以下是逻辑责任分区，不是必须在仓库创建的目录：

```text
catalog/       works, editions, book_instances and revisions
reading/       sessions, trace revisions, candidates, relations
captures/      capture manifests, resolution revisions, processing runs
observations/  immutable parsed observations + raw output references
objects/       original images and raw source payloads
indexes/       rebuildable retrieval projections
state/         active-session and delivery projections
```

`active_sessions`、全文索引、vector index、crop 均是可重建投影，不是原始阅读事实的唯一保存位置。

对象存储与元数据通常不能在同一数据库事务里原子写入。入口必须先确认原始对象持久化，再提交引用它的 manifest；写入失败留下的临时/孤儿对象由可审计回收流程处理。绝不能存在已向用户宣称接受、但原图引用不可恢复的记录。

## 30. Recommended Database Entities and Invariants

**[继承：底稿 §30；新增支撑实体为实现提案]** 逻辑实体保留 works、editions、book_instances、reading_sessions、capture_batches、page_captures、reading_traces、knowledge_candidates、knowledge_objects、trace_relations；新增或映射 `capture_resolutions / page_observations / processing_runs / idempotency_records / event_outbox / consumer_cursors`。

`knowledge_objects` 应接入已有知识层，而不是在 Librarian 下另造一套不兼容的知识系统。

必须落实的约束至少包括：

| 不变量 | 执行位置 |
|---|---|
| `owner_id` 在所有引用链上一致 | 应用授权 + 数据访问层 |
| Edition→Work、Instance→Edition、resolved physical trace→完整上下文链 | 外键/应用事务校验 |
| 同一逻辑对象 `(owner, id, revision)` 唯一；当前指针只向合法版本 | 数据库/存储层 |
| 同一源附件身份 `(owner, transport, account, source_event_id, source_item_id)` 唯一 | 唯一约束/幂等记录 |
| 同一命令幂等键不能对应两种业务 payload | 应用服务 + 持久幂等记录 |
| trace 引用的 capture、observation、resolution 和 detection IDs 一致 | normalization 提交校验 |
| observation 内 ID 不重复，link 指向存在的对象 | Schema 之外的语义校验 |
| trace 写入和领域事件同时提交 | 事务/outbox |
| bbox 非零面积、方向合法，空间标签与页内位置一致 | 语义校验 |
| 原始 evidence 无普通 UPDATE 路径 | 存储权限/API 设计 |

如果暂用 JSON 文件存储，也必须提供等价的幂等、原子提交与恢复保障；不能因为“单用户”就省略这些数据安全约束。本稿不要求将整个 PAP 改成 event-sourced architecture。

## 31. Trace Relations

**[继承：底稿 §31]** 关系独立建模，不直接把一张知识图塞进 trace。

`TraceRelation` 包含 `source_trace_ref`、`relation`、`target`、`provenance` 和关系级 confidence。`target.type` 保留 `trace / concept / entity / knowledge_object / question`。

**[实现提案]** 初始 relation 词表采用 `reminds_of / supports / contradicts / related_to / supersedes`。非确定性语义关系须标记由 user、model 或 rule 创建；`supersedes` 是修订 lineage，不与概念上的“相关”混为一谈。

关系引用 trace 时应包含 revision。源文本修订后，旧关系不得自动成为对新文本成立的关系。v0.1 只要求原始痕迹可追溯，自动跨书语义关系不在 MVP 范围。

## 32. Search Model

**[继承：底稿 §32]** 长期模型保留 lexical、embedding、entity、structural 四个 retrieval channel，最终返回原始 trace 而不是只有 AI summary。

**[显式裁定]** MVP 先实现 lexical + structural；embedding 和 entity 保留扩展接口，不作为纸书闭环的前置条件。底稿同时提出四路检索与 basic retrieval，本稿按分阶段交付解释这一差异。

### 32.1 读接口

`SearchRequest` 包含 `owner_id / query / filters / limit / cursor`。filters 支持 Work、Edition、BookInstance、medium、Session、trace types 和 `include_unresolved`。权限必须在召回前生效，不能先跨用户检索再靠模型隐藏结果。

纯结构检索可以让 `query` 为空，但必须指定至少一个身份、媒介或 trace type 过滤器；这使没有可靠识别文字的符号痕迹仍可按结构找回。空文字且无结构过滤器的请求无效。

`SearchResponse` 返回 `hits / next_cursor / index_state`。每个 hit 包含 trace ID/revision、medium、上下文状态、题名、location、原始提取内容、命中 channel、rank score、证据引用和警告。

`rank_score` 是排序值，不是证据置信度。默认只搜索 active 的当前 trace revision；历史/superseded 结果应走显式历史查询，不同时作为多条当前事实展示。

### 32.2 检索与来源

印刷文本和用户边注应分别索引并可联合查询。未知文本、空文本或低置信文字不能通过模型摘要补入“原文索引”。数字来源返回 raw payload 定位；physical 返回原图引用和 bbox。

索引未追上时 `index_state=lagging`；来源记录仍可按 ID 读取。索引丢失必须能从有效 trace 重建，不要求重新调用视觉模型。

## 33. Provenance-first Answering

**[继承：底稿 §33]** Librarian 关于用户阅读史的断言必须能沿 trace 回到 source evidence。

physical 的最小路径为：`Work → Edition → BookInstance → Session → Trace revision → Capture → Observation/Resolution → bbox`。实际未知的节点必须明确未知，不得为了让链路完整而虚构。

**[实现提案]** 输出必须区分三种表述：原文摘录、识别出的用户/未知作者批注、模型解释。比如 `Parsons?` 可以支持“页边出现了这个词”，在作者归属可靠时支持“你写过这个词”；不能独立支持“你赞同 Parsons 的 system integration 理论”。

原图不可访问时，应显示证据暂不可打开，不生成伪 crop 或假链接。没有找到可支持用户提问的 trace 时，回答未检索到，而不是靠常识补写个人阅读记忆。

## 34. Reading Progress

**[继承：底稿 §34]** 有痕迹的照片页集合不等于阅读范围。拍到 p.137 只能证明这张照片的相关位置，不证明用户只读到 p.137。

**[实现提案]** 分开保存两种值：

```text
observed_pages = 已解析的捕获页集合，属于证据统计
reported_progress = 用户或可靠来源报告的起止位置，属于阅读进度
```

只有第二种可更新 `BookInstance.reading_status.current_page`。回到较早页重读是合法行为；不应把进度简单实现成所有页码的最大值。finished/abandoned 等状态需要明确报告或既有可靠来源，不能由图片位置推断。

未报告终点时保持上一次有依据的 progress；反馈“本批照片含 p.159、p.166……”而不是“你已读到 p.166”。

## 35. Session Closing Interaction

**[继承：底稿 §35]** 正常流程最多一个低摩擦聚合 interaction，不逐项要求确认。

**[实现提案]** 已有独立进度报告时，可以反馈：

```text
已保存《经济与社会》本次的 4 张页面照片，整理出 12 条阅读痕迹。
你报告的阅读终点是 p.184，进度已记录。
其中 1 条重要边注暂未读清，原图已保留。
```

只有照片、没有进度报告时，应反馈：

```text
已保存 4 张页面照片，整理出 12 条阅读痕迹。
照片中识别到 p.159、p.166、p.171、p.184。
本次未报告阅读终点，阅读进度保持原记录。
```

以上数量为说明交互的合成示例，不代表本次真的进行了页面识别。是否关闭会话与是否已处理完照片也要分开；上传完成本身不是实际阅读结束时间的证明。

## 36. Anti-Recommendation Integration

**[继承：底稿 §36]** 后续 Anti-Recommendation 可以使用拥有状态、已开始/部分阅读/弃读/读完/重读状态及痕迹分布，而不是只看书单。

**[实现提案]** `heavily_annotated / lightly_processed` 属于带定义的派生指标，不是用户主观状态；阈值和时间窗口需要另行明确。“待解决问题”“低质量识别”“尚未晋升的普通划线”也不是同一种 unresolved。

禁止把“普通划线尚未变成 knowledge”视为欠账，再据此劝用户停止新阅读。绝大多数 trace 永远停留在 Layer 2 是设计预期，不是 backlog。

本阶段只提供可追溯事实和指标基础，不实现自动荐书/反荐书策略。

## 37. MVP Delivery Boundary

**[继承：底稿 §37]** 必须实现：book registration、ReadingSession、physical capture、image persistence、book/session resolution、page-number extraction、underline/highlight detection、基础手写提取、ReadingTrace 持久化、原图 provenance、统一 trace interface 和 basic retrieval。

**[实现提案]** 将交付分为三个检查点：

| 检查点 | 必须完成 | 不作为前置依赖 |
|---|---|---|
| M0 — Contract / Persistence | Schema、语义约束、原图存储、修订、幂等与事件持久化 | 特定视觉模型、向量数据库 |
| M1 — Physical closed loop | Gateway/explicit session、页面提取、normalize、来源检索、异常不打断 | WeRead/Koodo live sync、Knowledge 晋升 |
| M2 — Unified adapters | 两个数字 adapter 的真实 payload 映射与统一检索 | 自动知识图谱、推荐 |

本契约包中的数字来源 fixture 只证明共享 schema 能容纳其基本信息，不能替代 M2 的真实数据接入验收。Candidate 与关系 schema 也不意味着后续功能已经完成。

## 38. v0.1 Acceptance Test

### 38.1 主闭环

**[继承并形式化：底稿 §38]**

**Given**：已注册测试 Work、Edition、BookInstance；用户明确开始本次 session；起点 p.151 来自明确报告或既有记录，并标明其来源。

**When**：用户实际提供 p.159、p.166、p.171、p.184 四张有痕迹的页面照片，并独立报告本次读到 p.184；Gateway 将它们接受为同一会话的 batch。

**Then**：原图、模型原始输出和 observation 持久化；正式 trace 能回到每个来源检测区域；合成的标注测试集应得到 12 个 trace group。其中 8 个 underline、2 个 underline+margin_note、1 个带问号的 symbol、1 个带 R 的 symbol。后两个仅在已启用词汇表时具有 question/reread 意图，不把这些意图加入 trace_types。

**And**：close 后进度 p.184 的 evidence 指向用户报告，而非最大照片页码。一个月后的 Weber/Parsons 查询能够检索到 p.171 的 trace，并呈现原文、`Parsons?` 和可打开的原图区域。

实际视觉验收必须使用真实标注照片，而不能让实现硬编码生成上述数量。当前包没有这些照片，不能宣称已通过主闭环的真实图像验收。

### 38.2 异常与工程验收

| ID | 测试输入 / 故障 | 必须出现的结果 |
|---|---|---|
| AC-01 | 同一摄取命令按原幂等键重试 | 同一 batch/capture 引用，不新增 trace/event |
| AC-02 | 同一幂等键对应不同附件或 payload | 明确冲突，不覆盖历史 |
| AC-03 | 不同消息再次发送相同字节图片 | 可复用 blob；不伪装成同一次消息，也不据此推定重读 |
| AC-04 | 两个版本或两个同版本副本同名 | unresolved/conflict，不随机选中 |
| AC-05 | explicit session 与可见书名强冲突 | 保存原图并标记冲突；不静默换书 |
| AC-06 | 间隔超过 90 分钟或 6 小时 | 按 affinity 降级；不自动宣告阅读结束 |
| AC-07 | 页面无页码或 137/139 不清 | 页码未知且保留原图；可保存局部 trace |
| AC-08 | 只拍到 p.137，没有终点报告 | 阅读进度不自动改为 p.137 |
| AC-09 | 读到 p.184，但最高拍摄页为 p.171 | 以用户报告更新 p.184，不以照片限制进度 |
| AC-10 | 跨页照片、旋转照片或缩略图推理 | 坐标回到原图，页区不混并，crop 对应正确 |
| AC-11 | 普通划线文字有轻微识别错误 | 保存并标不确定，不要求逐条确认 |
| AC-12 | 已启用 `!!`，符号可靠但手写分数低/未知 | 进入重要内容 review queue |
| AC-13 | 正文中的 R、普通感叹号或边注词内问号 | 不当作个人符号协议命令 |
| AC-14 | 用户将 Parsons? 更正为 Parsons! | 新 trace revision；原图和原 observation 不变 |
| AC-15 | 更正后重跑旧模型/旧事件晚到 | 人工修订不丢失，索引不回滚 |
| AC-16 | 新提取分组与旧 trace 不可确定映射 | 待对账，不覆盖已有人工修正 |
| AC-17 | 对象存储在接受前失败 | 不返回已保存；按原幂等键可安全重试 |
| AC-18 | 模型超时或返回不合法 JSON | 原图和原始返回保留，错误可定位，不生成虚构 trace |
| AC-19 | trace 事务提交后 publisher 崩溃 | 恢复后仍能发同一 event，消费者去重 |
| AC-20 | 索引失败或被删除 | 已存 trace 不丢；从 trace 重建，不重新识别图片 |
| AC-21 | 跨 owner 的 capture/trace/对象引用 | 授权拒绝，检索不泄露内容 |
| AC-22 | 二手本旧批注，作者不明确 | `mark_author=unknown`；不声称用户本人写过 |
| AC-23 | 同一查询分别命中三种来源 | 返回共同 SearchHit 契约，不暴露上游私有对象 |
| AC-24 | 没有支持某个用户阅读史结论的证据 | 回答未找到，不用通识补造记忆 |
| AC-25 | Knowledge 服务失败 | candidate 不标 promoted，不发布成功事件 |
| AC-26 | 多普通划线从未晋升 | 不被视为数据异常或必须清空的任务积压 |

### 38.3 契约包已完成的检查

当前离线校验检查 77 个 Schema 定义、18 个模型入口、42 个正向合成 fixture，拒绝 43 个负向案例，并执行选定的跨实体一致性检查。具体结果见 `agents/librarian/runtime/tests/validation-report.json`；数字相符不等于已与缺失的原始底稿包逐项核对。

这些检查覆盖结构、部分字段/版本/坐标/引用不变量，**没有运行生产 pipeline，没有真实图片，没有测试真实模型准确率、消息平台、存储耐久性、事务恢复或真实跨来源同步**。AC 表是未来实现必须通过的验收清单，不是当前已完成列表。

## 39. Design Rules

**[继承：底稿 §39]** 以下十条不可被任何“优化”破坏：

1. **Digitize traces, not books.**
2. **Capture must not interrupt reading.**
3. **Original evidence is immutable.**
4. **Inference never overwrites evidence.**
5. **Physical, WeRead and Koodo converge at ReadingTrace.**
6. **Most traces never become knowledge objects.**
7. **Confidence belongs to individual fields.**
8. **Ambiguity is stored, not hallucinated away.**
9. **Every Librarian inference should remain traceable to evidence.**
10. **The user should review exceptions, not ingestion.**

**[实现提案]** 评审、代码生成提示和测试名称应直接引用这些边界。任何可疑捷径，例如把页面照片变成自由文本 note、把 `Parsons?` 改写成一个确定知识结论、用上传时间计算阅读时长，都应在合并前阻止。

## 40. Suggested Implementation Boundary

**[继承：底稿 §40]** 应先读取 PAP repository architecture，再决定具体目录，避免强行建立第二套 architecture。

**[实现提案]** 无论目录如何映射，模块职责必须保持如下分离：

| 逻辑组件 | 唯一主要责任 |
|---|---|
| Catalog service | Work/Edition/BookInstance 及归属约束 |
| Session manager | 会话状态、明确进度、受作用域限制的 active context |
| Capture service | 原始文件接受、哈希、manifest、来源身份 |
| Resolver | 身份与页码的有证据解析，不改原图 |
| Extractor | 视觉 observation + raw output，不产生知识结论 |
| Normalizer | 由 observation 和 resolution 生成确定的 trace write plan |
| Trace store | revision、幂等、引用一致性、事务提交 |
| Event port | durable publish、outbox 或已有等价机制 |
| Retrieval | current-trace 索引、权限过滤、来源返回 |
| Knowledge port | 后续候选晋升；复用已有知识模型 |

编码智能体开始前必须完成仓库侦察：现有领域 ID 与 owner 约定、配置与密钥管理、存储路径、迁移框架、上传机制、事件接口、搜索能力、测试工具，以及 WeRead/Koodo 是否已经存在 adapter。侦察结果应映射到这些逻辑组件，不应依据本文示例路径直接创建全新顶层框架。

## 41. Implementation Order

**[继承：底稿 §41]** 保持依赖顺序：

```text
01 domain schemas → 02 storage → 03 session manager
→ 04 physical capture → 05 vision extraction contract
→ 06 normalization → 07 reading_trace persistence
→ 08 retrieval → 09 WeRead adapter → 10 Koodo adapter
→ 11 knowledge promotion → 12 Librarian reasoning
```

**[实现提案]** 每阶段交付应能单独验证：

| 步骤 | 本阶段完成定义 |
|---|---|
| 01 | 正式模型与失败案例一致；语言模型不偏离 JSON Schema |
| 02 | 原图/原始输出可保存、读取、校验；元数据事务和修订可恢复 |
| 03 | 会话迁移和进度证据不变量通过测试；90 分钟不自动结束阅读 |
| 04 | 同消息重试不重复；无命令上传可接受并保留 unresolved |
| 05 | 可替换 extractor；输出严格校验，原始返回不丢 |
| 06 | 合成 observation → 确定 trace；符号协议与原文分离 |
| 07 | trace 与事件原子提交；人工 correction 不被重试覆盖 |
| 08 | 原文/边注/结构查询能返回可打开证据；完成 M1 主闭环 |
| 09–10 | 取得真实平台 payload 后完成 adapter contract tests；不得靠猜测接口 |
| 11 | 候选与知识对象区分；晋升幂等，来源版本保留 |
| 12 | 解释只基于可追溯 trace；推荐仍需独立策略评审 |

第一阶段不要做 recommendation。先让系统可靠记住：**我读了什么，以及我当时在哪里停下来想了一下。**

---

# Appendix A — Explicit Decision Log

下表列明本稿的新增与裁定，便于评审时逐项接受或修改；它们不冒充附件中已经确定的事实。

| ID | 决策 | 性质 / 原因 | 来源边界 |
|---|---|---|---|
| D-01 | JSON Schema 为唯一规范模型；Pydantic 等做映射 | 实现提案；避免双份契约漂移 | 底稿末尾要求正式模型，但未指定语言 |
| D-02 | QR 不进入 MVP | 范围裁定；优先采用明确 MVP 排除项 | 底稿 §§8、37 有表述张力 |
| D-03 | PageCapture 与 resolution / observation / run 拆分 | 实现提案；同时满足不可变证据和可修订识别 | 底稿 §§12、22 |
| D-04 | question/reread 作为语义，不加入 trace_types | 术语裁定；避免检测类型与解释混用 | 底稿 §§16–19、38 |
| D-05 | 接受事件仅在证据持久化后发布；索引晚于 processed 允许滞后 | 实现提案；明确成功反馈与耐久性 | 底稿 §§26、28 |
| D-06 | MVP lexical + structural；其他 channel 后续 | 分期裁定 | 底稿 §§32、37 |
| D-07 | 未知评分为 null，数字源不默认 confidence 1.0 | 实现提案；不把示例值当成事实保证 | 底稿 §§15、20 |
| D-08 | origin、capture time、reading time、mark time 分离 | 实现提案；禁止以上传时间填个人历史 | 底稿 §§6、12、22、34 |
| D-09 | owner 作用域、命令幂等、outbox、optimistic revision | 实现提案；落实隔离、重试与证据保存 | 底稿 §§22、26、28–30 |
| D-10 | EXIF 显示坐标、页区局部空间标签 | 实现提案；支撑跨页与 crop 一致性 | 底稿 §§13、23–24 |
| D-11 | 词汇表默认 opt-in，启用后版本化 | 实现提案；不强迫改变用户习惯 | 底稿 §17 |
| D-12 | mark authorship 默认为 unknown，除非有来源证明 | 实现提案；二手/借阅照片不等于用户原笔迹 | 底稿 §§5.3、13 |
| D-13 | 原图 hash 去重不等于摄取事件去重 | 实现提案；不混淆存储和阅读行为 | 底稿 §§11–12、26 |
| D-14 | 对人工修正有依赖的 re-extraction 先对账 | 实现提案；防止不可逆的 correction 丢失 | 底稿 §§22、26 |
| D-15 | 部分知识服务契约仅预留，不能阻塞 M1 | 分期落实 | 底稿 §§37、41 |

# Appendix B — Schema Inventory

入口文件只提供类型选择，完整定义集中在 `schemas/contracts.schema.json`。离线验证器注册主 schema 的 URN 后即可解析，示例测试不访问网络。

| 入口 | 用途 | 是否版本化领域记录 |
|---|---|---|
| Work | 抽象作品 | 是 |
| Edition | 具体版本/定位范围 | 是 |
| BookInstance | 纸书副本 | 是 |
| ReadingSession | 阅读会话 | 是 |
| CaptureBatch | 接受批次与处理投影 | 是 |
| PageCapture | 原始照片接受事实 | 否，不可变 |
| CaptureResolution | 身份与页码解析 | 是，append-only |
| ProcessingRun | 执行状态、检查点、重试 | 是 |
| PageObservation | 某次视觉输出 | 否，不可变 |
| ReadingTrace | 规范化阅读痕迹 | 是，append-only |
| KnowledgeCandidate | 待晋升解释 | 是 |
| TraceRelation | 显式或推断的独立关系 | 是 |
| Event | 九类领域事件 envelope/payload | 不可变消息 |
| Command | 十三类写入命令 envelope/payload | 请求契约 |
| CommandReceipt | 接受/完成结果 | 响应契约 |
| ErrorResult | 统一错误结果 | 响应契约 |
| SearchRequest | 查询及过滤器 | 请求契约 |
| SearchResponse | trace + provenance 结果 | 响应契约 |

Schema 入口不是已经实现的 API，也不承诺某个服务运行在特定语言上。正文中 `TraceWritePlan` 等内部概念属于行为契约，不是新增公开 API 类型。

# Appendix C — Compatibility and Migration

**[实现提案]** schema_version、事件 version、领域 revision、extractor_version、normalizer_version 和 vocabulary_version 必须分开。它们分别表达结构、事件契约、同一对象修订、提取器、规范化规则和用户符号语义的变化。

本稿使用封闭 Schema；新增字段也可能使旧验证器拒绝消息，因此不能把“只加字段”视为天然兼容。升级必须携带显式版本、迁移/适配规则和回归 fixture。

迁移的边界是派生数据：可以把旧 trace 投影到新结构，但不能重写旧 raw payload 或原始视觉输出。当前版本指针更新前必须确保新版本的引用链可用。

如果 PAP 已有类似类型，应做字段映射和版本兼容，而不是重命名全部现有实体来匹配本稿。需要改变两个锁定边界——ReadingTrace 统一接口、PageCapture evidence 身份——的提议必须另行评审，不能归入普通字段迁移。

# Appendix D — Initial Configuration Proposal

下面配置仅体现本稿采用的初始策略。只有 affinity 的 90 分钟与 6 小时直接来自底稿；其他开关和阈值是待真实样本验证的实现提案。

```yaml
physical_capture:
  session_affinity:
    soft_timeout_minutes: 90
    hard_timeout_hours: 6
    scope: [owner_id, transport, account_id, conversation_id]

  resolution:
    allow_llm_only_book_binding: false
    allow_photo_max_page_as_progress: false
    permit_unresolved_traces: true

  normalization:
    observation_link_min_confidence: 0.90

  review:
    important_only: true
    handwriting_low_confidence_below: 0.70
    printed_text_low_confidence_below: 0.85
    important_required_field_unknown_requires_review: true

  personal_annotation_vocabulary:
    enabled: false
    version: personal-v1
    symbol_min_confidence: 0.90
    mappings:
      "!!": promote_candidate
      "?": unresolved_question
      "×": disagreement
      "↔": connection_candidate
      "R": reread_target

retrieval:
  enabled_channels: [lexical, structural]
  include_unresolved_by_default: false

knowledge:
  automatic_promotion_enabled: false
```

这些分数不能被宣传为模型正确率。confidence 缺失时，不能通过阈值比较得到“安全自动执行”的结论；只允许有其他明确来源的确定性行为。

输入图片字节上限、并发数、模型调用超时、重试次数/退避、blob 保留周期、crop 边距和视觉成本预算，附件均未确定，应依据现有 PAP 配置和真实样本设定，不在本稿填入无依据的性能承诺。

# Appendix E — Open Integration Questions

这些问题不是要求用户现在逐项回答；编码前优先从 repository 和已有配置查明。查不到时再形成具体决策记录。

| ID | 待核实事项 | 影响 | 当前不依赖的处理方式 |
|---|---|---|---|
| Q-01 | PAP 现有目录、语言、领域 ID 和 owner 模型 | 文件位置、类型映射、权限 | 逻辑边界与 JSON Schema 独立于语言 |
| Q-02 | 是否已有 blob/object store 与读取授权 | 原图存储、去重、crop | 使用 ObjectRef 端口，不指定供应商 |
| Q-03 | 是否已有 durable events/outbox | 事务、发布、消费重试 | 保留原子提交语义，不另造消息平台 |
| Q-04 | Gateway 的上传、相册、消息/附件稳定 ID | batch 边界、幂等、上下文作用域 | 定义可信 source/upload_ref 契约 |
| Q-05 | Catalog 的 edition/卷册/多副本现有约定 | 页码定位与迁移 | 不从标题或 ISBN 猜副本 |
| Q-06 | 视觉模型、输入限制、输出坐标能力和实际评分 | 提取效果、阈值、成本 | 只固定 observation contract 与拒绝策略 |
| Q-07 | 用户是否愿意启用个人符号词汇表 | candidate 触发 | 默认不启用，不妨碍普通痕迹保存 |
| Q-08 | WeRead/Koodo 现有同步路径与真实 payload | M2 adapter 映射 | 只有合成输出 fixture，不伪造接口 |
| Q-09 | 现有搜索和知识服务接口 | M1 retrieval / 后续 promotion | trace/provenance 接口固定，下游可替换 |
| Q-10 | 数据删除、备份、恢复和保留策略 | 隐私与长期可靠性 | 不将 immutable 解释为不可删除 |
| Q-11 | 实际语言、字迹、页面版式和标注测试集 | 识别准确率与误分组 | 不承诺未测得的准确率或时延 |

# Appendix F — Contract Validation

在具备 `jsonschema` 及其依赖的 Python 环境中，于 `agents/librarian/runtime/` 目录运行：

```bash
python3 tests/validate_contracts.py
```

测试依赖来自仓库的 Python 环境。测试使用离线 resolver 加载本地 schema，不抓取页面、不调用 OCR、不访问真实书库。

验证范围分三层：单对象 Schema；选定的语义规则（版本链、bbox、事件 aggregate、符号类型、作者来源等）；一个合成领域集合的上下文与 evidence 引用一致性。它不取代存储和应用服务的全部业务校验。

`examples/positive.json` 中的出版社、ISBN 等未知字段没有被填成底稿中的示例书目；原文字段明确标注为合成文本。fixture 里的 asset 引用是契约占位，不对应可下载真实页面。事件和命令案例是各类独立契约例子，不是完整的按时序执行日志。

# Appendix G — Implementation Handoff Checklist

在实现首个 PR 前，应形成一份简短的 repo mapping，说明：哪些现有组件对应 §40 的职责；哪些端口确实缺失；哪些 Schema 字段需要映射；哪些 [实现提案] 被采纳或变更。不能把“需要检查架构”当成重写 PAP 的理由。

首个可合并实现应优先提供 domain 校验、测试 fixture、原图/manifest 持久化和幂等接受；随后接入替身 extractor 完成 normalize/retrieval 的确定性闭环，最后用真实 extractor 和标注图片替换替身做 M1 端到端验收。

任何交付声称“已完成”时，必须同时指出完成的是契约校验、替身 pipeline、真实图像验收还是 live adapter 接入。不同层级不能互相替代。

---

**最终锁定边界：`ReadingTrace` 是 Physical / WeRead / Koodo 的统一下游接口；`PageCapture` 永远是 evidence，不是 note。**
