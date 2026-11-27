# `cadre-bundle` JSON Schema 契约（v1.0）

所有 `cadre-tracker` 技能在读取 `raw_sources` 后，严禁直接拼接 SQL，必须生成符合本规范的 JSON 文件并通过下述命令校验入库：

```bash
"$PAP_ROOT/.venv/bin/python" "$PAP_ROOT/agents/cadre-tracker/runtime/cli.py" ingest-bundle --file <bundle.json>
```

## 顶层字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `schema_version` | string | 是 | 固定 `"1.0"` |
| `source_id` | string | 是 | 对应 `raw_sources.source_id`（必须先落盘 `raw_sources`，或在测试/手工导入时附带 `source` 对象） |
| `source` | object | 否 | 可选内联信源对象（当 `source_id` 尚未在 `raw_sources` 中存在时自动注册） |
| `persons` | array | 否 | 官员主体及学缘教育记录列表 |
| `tenures` | array | 否 | 时态任职履历切片列表 |
| `claims` | array | 否 | 异动事件、纪律处分、传闻线索列表 |

## `persons[]` 对象

- `name` (string, 必填): 官员姓名。
- `gender` (`"男"` | `"女"` | null)
- `ethnicity` (string | null): 如 `"汉族"`
- `birth_ym` (string | null): 7 字符 `YYYY-MM`
- `native_place` (string | null): 标准化至省+市县，如 `"江苏建湖"`
- `birth_place` (string | null)
- `party_join_ym` (string | null): `YYYY-MM`
- `work_start_ym` (string | null): `YYYY-MM`
- `current_rank` (string): `正国级` / `副国级` / `正省部级` / `副省部级` / `正厅局级` / `其他`
- `cc_membership` (array[string]): 如 `["二十届中央候补委员"]`
- `status` (string): `active` | `anomaly_watch` | `retired` | `demoted` | `under_investigation` | `expelled` | `sentenced` | `deceased`
- `status_updated_at` (string | null): UTC ISO-8601 `YYYY-MM-DDTHH:MM:SSZ`
- `is_tracked_target` (int): `1` 核心副部级以上监控对象，`0` 被动关联入库
- `wikidata_qid` (string | null): 如 `"Q9095615"`
- `summary_note` (string | null)
- `educations` (array):
  - `school_name` (string, 必填)
  - `department` (string | null)
  - `degree` (string | null): `学士` / `硕士` / `博士` / `在职研究生` / `党校培训`
  - `major` (string | null)
  - `is_full_time` (bool | int | null)
  - `start_ym` (string | null): `YYYY-MM`
  - `end_ym` (string | null): `YYYY-MM`

## `tenures[]` 对象

- `person_name` (string, 必填)
- `person_birth_ym` (string | null): 辅助消歧
- `person_native_place` (string | null): 辅助消歧
- `person_wikidata_qid` (string | null): 辅助消歧
- `action` (string): `"UPSERT_SPAN"`（默认）或 `"CLOSE_SPAN"`（免职/调离闭合当前在任切片）
- `org_canonical_name` (string, 必填): 机构规范全称
- `org_short_name` (string | null): 常用简称
- `org_kind` (string): `party_central` | `gov_central` | `party_local` | `gov_local` | `npc` | `cppcc` | `judicial` | `commission_ccdi` | `soe_financial` | `soe_industrial` | `university` | `party_school` | `military` | `other`
- `admin_level` (string | null)
- `province_name` (string | null)
- `parent_org_canonical_name` (string | null)
- `role_title` (string, 必填): 标准化纯职务名（如 `"书记"` / `"市长"` / `"常务副市长"` / `"常委"`）
- `raw_role_text` (string | null): 原文完整职务串
- `role_tier` (string): `chief` (4.0) | `gov_head` (3.5) | `deputy_chief` (3.0) | `member` (2.0) | `subordinate` (1.0)
- `rank_at_time` (string | null)
- `start_ym` (string, 必填 for `UPSERT_SPAN`): `YYYY-MM`
- `end_ym` (string | null): `YYYY-MM`；`null` 唯一代表仍在任
- `date_precision` (string): `"MONTH"`（默认）或 `"YEAR"`
- `is_concurrent` (int): `0` 主职 / `1` 兼职或脱产培训
- `is_acting` (int): `0` / `1`
- `predecessor_name` (string | null)
- `successor_name` (string | null)
- `certainty` (string): `"FACT"` | `"INFERRED"`

## `claims[]` 对象

- `claim_type` (string, 必填): `appointment` | `removal` | `investigation` | `voluntary_surrender` | `expulsion_sanction` | `dom_removal_anomaly` | `co_worker_mention` | `patronage_speculation` | `disambiguation_conflict`
- `event_date` (string | null): `YYYY-MM-DD`
- `subject_raw_name` (string, 必填)
- `subject_birth_ym` (string | null): 辅助消歧
- `related_raw_name` (string | null)
- `related_birth_ym` (string | null): 辅助消歧
- `certainty` (string, 必填): `FACT` | `INFERRED` | `SPECULATION` | `RUMOR`
- `violation_codes` (array[string]): 双开通报违纪标准码
- `payload` (object, 必填): 结构化上下文
- `evidence_quote` (string, 必填): 原文逐字证据句
- `confidence` (float): 默认 `1.0`

## 信源权威等级锁规则

- **Tier 4 信源**：严禁写入 `persons` 与 `tenures`，所有 `claims` 强制锁定为 `SPECULATION` 或 `RUMOR`。
- **Tier 1 保护锁**：当 `persons.status` 或 `tenures` 已被 Tier 1 信源锁定（`credibility_lock = 1`），后续 Tier 2/3/4 信源不得覆盖其状态或起止年月。
