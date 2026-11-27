# 中纪委“六大纪律”通报标准术语与窝案特征映射表

当摄入 `source_type = 'ccdi_sanction'`（党纪政务处分/双开通报）时，按本表将通报标准表述映射为 `claims_and_clues.violation_codes_json` 中的标准代码，用于窝案模式聚类与关联分析。

## 一、政治纪律（Political Discipline）

| 标准码 (`violation_code`) | 典型通报高频表述 | 窝案/传导特征 |
| --- | --- | --- |
| `political_clique` | 搞团团伙伙、拉帮结派、培植个人势力、结交政治骗子、搞政治攀附 | 强团伙/派系联动信号 |
| `disloyalty_two_faced` | 对党不忠诚不老实、做两面人、阳奉阴违、自行其是 | 政治路线或核心决策偏差 |
| `obstruct_investigation` | 对抗组织审查、串供、转移隐匿证据、与他人订立攻守同盟 | 往往伴随上下级或政商同案人 |
| `superstition` | 搞迷信活动、长期参加迷信活动 | 常规政治纪律附加项 |
| `failed_party_governance` | 履行全面从严治党主体责任不力、污染当地政治生态 | 辖区塌方式腐败信号 |

## 二、组织纪律（Organizational Discipline）

| 标准码 (`violation_code`) | 典型通报高频表述 | 窝案/传导特征 |
| --- | --- | --- |
| `buy_sell_post` | 在干部选拔任用工作中为他人谋取利益并收受财物、跑官要官、买官卖官 | 强人事提拔链/旧部窝案信号 |
| `conceal_personal_matters` | 隐瞒不报个人有关事项、在组织谈话函询时不如实说明问题 | 隐匿房产/经商/境外关系 |
| `violate_democratic_centralism` | 违反民主集中制原则、个人决定重大事项、搞“一言堂” | 主官独断专行特征 |

## 三、廉洁纪律与领域型腐败（Integrity & Sectoral Graft）

| 标准码 (`violation_code`) | 典型通报高频表述 | 窝案/传导特征 |
| --- | --- | --- |
| `urban_planning_graft` | 在工程承揽、土地出让、规划审批、房地产开发等方面谋利 | 城建/规划/国土/区县主官高发窝案 |
| `financial_graft` | 在贷款审批、融资借款、债券发行、监管执法、金融投资等方面谋利、“靠金融吃金融” | 金融系统/地方金控链条 |
| `soe_procurement_graft` | 在企业经营、项目承揽、物资采购、矿产开发等方面谋利、“靠企吃企” | 央企/国企/能源系统链条 |
| `judicial_intervention` | 违规干预和插手司法活动、执纪执法活动、以案谋私 | 政法/司法系统联动 |
| `family_business_conflict` | 纵容默许亲属利用本人职权谋利、家风不正、违规经商办企业、拥有非上市公司股份 | 家族式/影子股东腐败 |
| `gift_and_banquet` | 违规收受礼品礼金、接受可能影响公正执行公务的宴请和旅游安排 | 违反中央八项规定精神 |
| `revolving_door_graft` | 政商“旋转门”、“逃逸式辞职”、离职后违规任职取酬 | 退休/离职后倒查高发 |

## 四、工作与生活纪律（Work & Life Discipline）

| 标准码 (`violation_code`) | 典型通报高频表述 | 窝案/传导特征 |
| --- | --- | --- |
| `illegal_debt_vanity` | 盲目举债、大搞政绩工程/形象工程、统计造假 | 地方债与主政地遗留风险 |
| `negligence_malfeasance` | 失职失责、造成重大损失或严重不良影响、滥用职权 | 事故问责或重大决策失误 |
| `moral_corruption` | 搞权色交易、钱色交易、道德败坏 | 生活纪律违纪 |

## 五、特殊状态标记（写入 `payload`）

- `in_office_fallen: true` — 任上落马（通报职务不含“原”字）
- `retired_fallback_probe: true` — 卸任/退休倒查（通报职务含“原”字）
- `voluntary_surrender: true` — 主动投案（通报含“主动投案”）
