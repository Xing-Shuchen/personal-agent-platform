政经人事时态图谱与关联震荡波追踪规范文档状态：Draft v1.0（Ready for Implementation）所属平台：personal-agent-platform (pap)   目标模块：agents/cadre-tracker/（主模块） + agents/world-historian/（跨库只读联邦扩展）   存储与运行时基线：Python 3.12 + SQLite 3（WAL + Foreign Keys + Recursive CTE + FTS5），零外部数据库容器依赖关联平台规范：docs/specification_v0.6.md、docs/cognition/EVIDENCE_SCHEMA.md、docs/cognition/PROVENANCE.md、paplog/pap.event.v2.schema.json   1. 背景、定位与核心非目标（Scope & Non-Goals）1.1 核心痛点与系统定位在中国高层政经新闻（副省部级/中管干部及以上，在任规模约 2,500–3,200 人）分析中，单一的人事任免或落马通报本身信息密度极低（通常仅一句话），真正的深度洞察隐藏在跨时间尺度的三维耦合中：组织上下级共事轨迹：同班子搭档（如市委书记与市委常委）、跨层级直接辖属（如市长与下辖区委书记/委办局主任，典型如 2017–2022 年北京期间陈吉宁与夏林茂的辖属及共事交集）。岗位前腐后继链：同一机构关键岗位（穿透 2018/2023 机构改革更名，如“市规划委”→“市规自委”）历任主官的执政交接链。同源背景耦合：高校学缘（同校/同院系，如清华城建规划系）、中央党校中青班同班培训、秘书/办公厅服务经历及籍贯交集。cadre-tracker 是挂载于 pap 平台下的专职政经人事时态知识图谱 Agent。它负责以低打扰、零空转 Token 的方式 7×24 小时监控五类公开信源，将非结构化/半结构化文本转化为精确到月份（YYYY-MM）的时态履历切片（Temporal Tenure Slices）与证据溯源账本（Provenance Ledger），并在重磅人事异动发生时自动推理“落马震荡波”与历史关联路径。1.2 架构边界与非目标（Non-Goals）不污染 world-historian 宏观主库：约 3,000 名中管干部的数万条静默历史履历切片严禁直接写入 world-historian 的 entities 或 events 表，防止冲垮宏观叙事看板 world-path.json 的信噪比。两者通过只读 SQLite URI（cadre_lookup.py）按需联邦查询。   不引入重型外部图数据库容器：严禁引入 Neo4j、Memgraph 或 PostgreSQL 容器。所有机构改名等价簇、省市区上下级树遍历与时间区间重叠度计算，100% 由 SQLite WITH RECURSIVE 在本地毫秒级完成。不追踪现役基层厅处级全量池：监控靶标严格收敛于“现职或曾任副省部级及以上官员（含中管央企、中管金融、中管高校）”。但已入库官员的早期厅局级、县处级、科级历史履历必须全量完整录入，从而在不监控全国数万厅官的前提下，精准还原高官早年的上下级与发迹交集。严禁传闻污染事实层：自媒体、外媒评论或深度报道中的推测性关联（如“据传受某某案牵连”），必须严格标记为 SPECULATION 或 RUMOR 存入线索表，绝不允许直接修改官员主状态或覆写官方履历切片。2. 系统总体架构与目录契约2.1 数据流与认知闭环Plaintext[五类公开信源: 中纪委 / 人社部&新华社 / 维基&Wikidata / 财新&澎湃RSS / 31省官网领导窗DOM]
       │
       ▼ (1) 确定性探针轮询 (零 Token 消耗)
[runtime/gate_precheck.py] ──(无新增哈希 & 无DOM异动)──► pap/gate.py 静默短路结束
       │ (捕获新通报 / 简历撤下 / Wiki修订)
       ▼ (2) 落盘 raw_sources 并唤醒 Agent Session
[pap/run.py + cadre-intake SKILL]
       │ LLM 读取原文 + 机构改革字典 → 组装严格 JSON (cadre-bundle)
       ▼ (3) 确定性入库与实体对齐
[runtime/cli.py ingest-bundle] ──► [runtime/resolver.py]
       ├── 高置信度匹配 ──► 自动幂等写入 persons / tenures / claims_and_clues
       └── 同名冲突/低置信 ──► 挂起至 review_status='needs_review' 等待人工拍板
       │
       ▼ (4) 异动触发图谱推理 (若事件为 落马被查 / 双开 / 官网异常撤下 / 核心主官换帅)
[cadre-shockwave-brief SKILL]
       ├── 调用 cli.py shockwave 扫描 Top-20 高重叠现役官员与已爆雷旧部
       ├── 调用 cli.py project-obsidian 按需刷新涉事人物 Obsidian Markdown 档案(含 Mermaid 图)
       └── 经 distribution.yaml 推送【政经人事异动与关联快报】并向 paplog 发射 v2 事件
2.2 仓库文件树契约Plaintextagents/
├── cadre-tracker/
│   ├── agent.yaml                                  # PAP 声明式注册清单（对齐 pap/spec.py）
│   ├── profile/
│   │   ├── SOUL.md                                 # 认识论准则：克制、重证据链、严分事实与推测
│   │   ├── config.yaml                             # 巡检源配置、DOM 监控目标清单、评分权重参数
│   │   ├── distribution.yaml                       # 异动快报分发通道路由配置
│   │   ├── references/
│   │   │   ├── cadre-bundle.md                     # ingest-bundle 输入 JSON Schema 契约文档
│   │   │   ├── org-reform-lineage.md               # 2018/2023 党政机构改革历史更名标准对照表
│   │   │   └── ccdi-violation-lexicon.md           # 中纪委“六大纪律”通报标准术语与窝案特征映射表
│   │   └── skills/
│   │       ├── cadre-intake/SKILL.md               # 日常增量通报、深度报道与 DOM 异动结构化抽取
│   │       ├── cadre-cv-backfill/SKILL.md          # 冷启动与全量履历回填（中经网/人民网/Wiki 源码双源互校）
│   │       ├── cadre-shockwave-brief/SKILL.md      # 落马震荡波扫描、上下级穿透与深度快报合成
│   │       └── cadre-review-resolve/SKILL.md       # 交互式消歧队列清理（处理同名干部与存疑时间线）
│   └── runtime/
│       ├── __init__.py
│       ├── migrations/
│       │   ├── 0001_initial_core_graph.sql         # 人物、机构、沿革、信源、履历、学缘、线索审核表
│       │   ├── 0002_gov_dom_sentinel.sql           # 官网“领导之窗”快照与异常撤下检测表
│       │   └── 0003_fts_search.sql                 # FTS5 全文检索虚拟表（支持按履历关键词反查官员）
│       ├── db.py                                   # SQLite 连接器、自动迁移器、递归 CTE 图查询集
│       ├── collectors.py                           # 五类信源抓取器与 MediaWiki / HTML 解析器
│       ├── gate_precheck.py                        # 对接 pap/gate.py 的轻量级前置检查入口
│       ├── resolver.py                             # 官员重名消歧评分器 + 机构全称规范化引擎
│       ├── obsidian.py                             # Obsidian 按需物化投射器（Frontmatter + Mermaid）
│       └── cli.py                                  # 面向 SKILL 与人工调试暴露的统一命令行入口
│
└── world-historian/
    ├── profile/skills/cadre-crosslink/SKILL.md     # 为宏观叙事线程补充官员仕途交集背景
    └── runtime/cadre_lookup.py                     # 只读连接 cadre-tracker.sqlite3 的联邦查询器
3. 本体论与时间编码规范（Ontology & Temporal Rules）为保证 SQLite 字符串比较与算术运算 100% 确定且无时区歧义，全库强制执行以下数据标准化法则：3.1 定长年月编码（YYYY-MM）与未知日降级所有履历起止时间（start_ym, end_ym）、出生年月（birth_ym）、机构改名时间（change_ym）统一采用 7 字符 ISO 年月格式 YYYY-MM（如 "2018-12"）。若早期简历仅记载年份（如 "1992年毕业"），标准化为 "1992-07"（毕业季）或 "1992-01"，并将字段 date_precision 设为 'YEAR'（默认 'MONTH'）。在任状态表达：end_ym IS NULL 唯一代表“至今仍在任”。任何通报免职、调离、退休或落马留置，必须闭合当前活跃切片的 end_ym。精确事件时间戳：落马通报发布时间、官网撤简历检测时间统一使用 UTC ISO-8601 格式 YYYY-MM-DDTHH:MM:SSZ。3.2 官员政治生命状态机（persons.status）状态枚举值中文释义状态跃迁触发条件联动副作用active在任现役默认初始态；或新任命通报参与“震荡波现役观察名单”评分计算anomaly_watch异常观察未到退龄但官网“领导之窗”撤下简历，或重要会议无故缺席触发高优预警，但不闭合 tenures.end_ymretired正常退二线/退休免去现职且未转任一线实职（或转任全国/省人大政协专委会闲职后满龄退休）闭合原实职 end_ymdemoted断崖降级/问责免职官方通报因事故问责免职，或贬任非领导职务闭合原职务，记录问责事件under_investigation接受审查调查（落马）中纪委国家监委“审查调查”通报发布立即触发 shockwave 震荡波计算；标记其被查时点expelled开除党籍/双开中纪委“党纪政务处分”通报发布提取“六大纪律”违纪特征标签入库sentenced司法宣判法院一审/二审宣判通报补充受贿金额、罪名与刑期标签deceased逝世官方讣告或权威报道确认冻结所有在任切片3.3 机构角色权重分级（tenures.role_tier）用于在无人工干预时，由 SQL 自动推导两人在同一机构或上下级机构中的权力支配/领导关系：chief（一把手，权重 4）：党委书记（省委书记/市委书记/区委书记/部委党组书记/高校党委书记/央企董事长）。gov_head（行政正职，权重 3.5）：省长、市长、区长、部长、校长、央企总经理（在党政同责下仅次于同级党委书记，高于其他党委副书记和副职）。deputy_chief（专职副书记/常务副职，权重 3）：省委专职副书记、常务副省长、常务副部长、纪委书记、组织部长。member（班子成员/副职，权重 2）：普通省委常委、副省长、副部长、党组成员、人大/政协副职。subordinate（内设司局/下属处室，权重 1）：办公厅主任、秘书、内设司局长、处长。自动上下级判定公理：同机构内（hop = 0）：当 A.role_tier_weight > B.role_tier_weight 且 A.role_tier IN ('chief', 'gov_head', 'deputy_chief') 时，判定 A 为 B 的同班子领导；权重相等则为平级同僚。父子辖属机构（hop = 1..2，父机构 → 子机构）：当 A 在父机构担任 chief / gov_head / deputy_chief（如北京市市长），且 B 在同一时间窗口担任直属子机构（如东城区委、市规自委）的 chief / gov_head 时，判定 A 为 B 的直接上级辖属领导。3.4 认识论与信源可信度分级（对齐 PROVENANCE.md & EVIDENCE_SCHEMA.md）等级 (credibility_tier)信源范畴允许写入的确定性级别 (certainty)冲突覆写权限Tier 1（最高法定权威）中央纪委国家监委网站、新华社人事任免通稿、人社部国务院任免、各级人大任免公报FACT可覆写 Tier 2/3/4 的任何起止月份与状态Tier 2（官方准权威与一线严肃调查）人民网/中经网地方领导资料库、各省政府/部委官网简历页、财新网实名政经深度报道FACT（履历事实） / SPECULATION（引述知情人士分析）可补全 Tier 1 未载明的早期履历，不可逆向推翻 Tier 1 状态Tier 3（开源协作百科）中文维基百科、Wikidata（P39 职务属性与前后任框）FACT（有来源引注的履历） / INFERRED（前后任推导）仅做空白字段填补（如前任/继任者姓名），与 Tier 1/2 冲突时自动退让并记日志Tier 4（外围解读与自媒体/视频评论）时政分析视频转写稿、海外媒体传闻、社交网络爆料强制锁定为 SPECULATION 或 RUMOR零主表写权限：严禁修改 persons 和 tenures，仅写入 claims_and_clues 供检索交叉印证4. SQLite 数据库完整表结构（Migrations 规范）默认数据库文件路径遵循 pap 数据目录惯例：${PAP_DATA_DIR}/cadre-tracker/cadre.sqlite3（支持通过 profile/config.yaml 覆盖）。4.1 0001_initial_core_graph.sqlSQLPRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- 1. 官员实体主表
CREATE TABLE IF NOT EXISTS persons (
    person_id TEXT PRIMARY KEY,                     -- 格式: p_<pinyin>_<birth_ym_or_shorthash>
    name TEXT NOT NULL,
    gender TEXT CHECK (gender IN ('男', '女') OR gender IS NULL),
    ethnicity TEXT,                                 -- 民族，如 '汉族'
    birth_ym TEXT CHECK (birth_ym IS NULL OR length(birth_ym) = 7),
    native_place TEXT,                              -- 籍贯（标准化到省+市县，如 '江苏建湖'）
    birth_place TEXT,                               -- 出生地
    party_join_ym TEXT,                             -- 入党年月
    work_start_ym TEXT,                             -- 参加工作年月
    current_rank TEXT NOT NULL DEFAULT '副省部级',   -- 正国级/副国级/正省部级/副省部级/正厅局级/其他
    cc_membership TEXT,                             -- JSON 数组: '["二十届中央委员"]' 或 '["二十届中央候补委员"]'
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','anomaly_watch','retired','demoted','under_investigation','expelled','sentenced','deceased')),
    status_updated_at TEXT,
    is_tracked_target INTEGER NOT NULL DEFAULT 1,   -- 1=核心副部级以上监控对象, 0=因关联提及被动入库的下属/关联人
    wikidata_qid TEXT UNIQUE,                       -- 如 'Q9095615'，用于幂等对齐 Wiki
    summary_note TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_persons_name ON persons(name);
CREATE INDEX IF NOT EXISTS idx_persons_status_rank ON persons(status, current_rank);

-- 2. 组织机构字典与层级树
CREATE TABLE IF NOT EXISTS organizations (
    org_id TEXT PRIMARY KEY,                        -- 格式: org_<hash12>
    canonical_name TEXT NOT NULL UNIQUE,            -- 标准全称: '中共北京市东城区委员会'
    short_name TEXT NOT NULL,                       -- 常用简称: '北京东城区委'
    org_kind TEXT NOT NULL CHECK (org_kind IN (
        'party_central', 'gov_central', 'party_local', 'gov_local',
        'npc', 'cppcc', 'judicial', 'commission_ccdi',
        'soe_financial', 'soe_industrial', 'university', 'party_school', 'military', 'other'
    )),
    admin_level TEXT,                               -- 国级 / 正部级 / 副部级 / 正厅局级 / 副厅局级 / 县处级
    province_name TEXT,                             -- 归属省份（中央部委填 '中央'，便于按地域聚类）
    region_code TEXT,                               -- 6位行政区划代码
    parent_org_id TEXT REFERENCES organizations(org_id), -- 直接上级管辖机构 ID
    is_defunct INTEGER NOT NULL DEFAULT 0           -- 已撤销或已改名历史机构标为 1
);
CREATE INDEX IF NOT EXISTS idx_orgs_parent ON organizations(parent_org_id);
CREATE INDEX IF NOT EXISTS idx_orgs_short ON organizations(short_name);

-- 3. 机构别名映射表（用于吸收通稿简写，如“北京市规自委” -> “北京市规划和自然资源委员会”）
CREATE TABLE IF NOT EXISTS org_aliases (
    alias_name TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE
);

-- 4. 机构历史沿革更名图（有向无环或双向等价改革边）
CREATE TABLE IF NOT EXISTS org_lineage (
    predecessor_org_id TEXT NOT NULL REFERENCES organizations(org_id),
    successor_org_id TEXT NOT NULL REFERENCES organizations(org_id),
    change_ym TEXT NOT NULL CHECK (length(change_ym) = 7),
    reform_batch TEXT,                              -- 如 '2018机构改革' / '2023机构改革' / '撤县设区'
    note TEXT,
    PRIMARY KEY (predecessor_org_id, successor_org_id)
);

-- 5. 原始公开信源存证账本
CREATE TABLE IF NOT EXISTS raw_sources (
    source_id TEXT PRIMARY KEY,                     -- 格式: src_<sha256_prefix16>
    source_type TEXT NOT NULL CHECK (source_type IN (
        'ccdi_investigation', 'ccdi_sanction', 'hrss_appoint', 'xinhua_appoint',
        'official_cv', 'wikipedia_wikitext', 'wikidata_sparql', 'deep_media', 'gov_dom_diff', 'manual_note'
    )),
    source_name TEXT NOT NULL,                      -- 如 '中央纪委国家监委网站', '财新网'
    credibility_tier INTEGER NOT NULL CHECK (credibility_tier BETWEEN 1 AND 4),
    url TEXT,
    title TEXT,
    published_at TEXT NOT NULL,                     -- ISO-8601
    fetched_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    content_hash TEXT NOT NULL,
    raw_content TEXT NOT NULL,
    ingest_status TEXT NOT NULL DEFAULT 'pending' CHECK (ingest_status IN ('pending', 'ingested', 'skipped', 'failed'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_url_hash ON raw_sources(url, content_hash);

-- 6. 核心：时态任职履历切片表
CREATE TABLE IF NOT EXISTS tenures (
    tenure_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES persons(person_id) ON DELETE CASCADE,
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    role_title TEXT NOT NULL,                       -- 标准化纯职务名: '书记' / '市长' / '常务副市长' / '常委'
    raw_role_text TEXT,                             -- 原文完整职务串，如 '北京市委常委、教育工委书记'
    role_tier TEXT NOT NULL DEFAULT 'member'
        CHECK (role_tier IN ('chief', 'gov_head', 'deputy_chief', 'member', 'subordinate')),
    role_tier_weight REAL NOT NULL DEFAULT 2.0,     -- 4.0 / 3.5 / 3.0 / 2.0 / 1.0
    rank_at_time TEXT,                              -- 担任该职时的个人级别（如 '正厅局级'）
    start_ym TEXT NOT NULL CHECK (length(start_ym) = 7),
    end_ym TEXT CHECK (end_ym IS NULL OR length(end_ym) = 7),
    date_precision TEXT NOT NULL DEFAULT 'MONTH' CHECK (date_precision IN ('MONTH', 'YEAR')),
    is_concurrent INTEGER NOT NULL DEFAULT 0,       -- 1=兼职 / 挂职 / 党校脱产培训班
    is_acting INTEGER NOT NULL DEFAULT 0,           -- 1=代理（如代省长、代市长）
    predecessor_name TEXT,                          -- 前任姓名（冗余存储加速窝案链扫描，消歧后同步填 ID）
    successor_name TEXT,                            -- 继任姓名
    certainty TEXT NOT NULL DEFAULT 'FACT' CHECK (certainty IN ('FACT', 'INFERRED')),
    source_id TEXT REFERENCES raw_sources(source_id),
    credibility_lock INTEGER NOT NULL DEFAULT 2,    -- 写入该记录的最高信源等级(1最高)，防止低等级信源覆盖
    UNIQUE (person_id, org_id, role_title, start_ym)
);
CREATE INDEX IF NOT EXISTS idx_tenures_person_span ON tenures(person_id, start_ym, end_ym);
CREATE INDEX IF NOT EXISTS idx_tenures_org_span ON tenures(org_id, start_ym, end_ym);

-- 7. 学缘与党校培训经历表
CREATE TABLE IF NOT EXISTS education_records (
    edu_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES persons(person_id) ON DELETE CASCADE,
    school_org_id TEXT NOT NULL REFERENCES organizations(org_id),
    department TEXT,                                -- 院系，如 '水利工程系' / '建筑学院' / '中青年干部培训一班'
    degree TEXT,                                    -- 学士 / 硕士 / 博士 / 在职研究生 / 党校培训
    major TEXT,                                     -- 专业，如 '城市规划与设计'
    is_full_time INTEGER,                           -- 1=全日制, 0=在职
    start_ym TEXT,
    end_ym TEXT,
    source_id TEXT REFERENCES raw_sources(source_id),
    UNIQUE (person_id, school_org_id, degree, COALESCE(start_ym, ''))
);
CREATE INDEX IF NOT EXISTS idx_edu_school ON education_records(school_org_id);

-- 8. 异动事件、纪律审查标签、外围关系线索与人工消歧队列表
CREATE TABLE IF NOT EXISTS claims_and_clues (
    claim_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES raw_sources(source_id),
    claim_type TEXT NOT NULL CHECK (claim_type IN (
        'appointment', 'removal', 'investigation', 'voluntary_surrender',
        'expulsion_sanction', 'dom_removal_anomaly', 'co_worker_mention',
        'patronage_speculation', 'disambiguation_conflict'
    )),
    event_date TEXT,                                -- YYYY-MM-DD
    subject_person_id TEXT REFERENCES persons(person_id),
    subject_raw_name TEXT NOT NULL,
    related_person_id TEXT REFERENCES persons(person_id),
    related_raw_name TEXT,
    certainty TEXT NOT NULL CHECK (certainty IN ('FACT', 'INFERRED', 'SPECULATION', 'RUMOR')),
    violation_codes_json TEXT,                      -- 双开通报违纪标准码 JSON 数组，如 '["buy_sell_post", "urban_planning_graft"]'
    payload_json TEXT NOT NULL,                     -- 完整结构化上下文或候选重名 ID 列表
    evidence_quote TEXT NOT NULL,                   -- 强制保留原文逐字证据句
    confidence REAL NOT NULL DEFAULT 1.0,
    review_status TEXT NOT NULL DEFAULT 'auto_merged'
        CHECK (review_status IN ('auto_merged', 'needs_review', 'approved', 'rejected')),
    reviewed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_claims_review ON claims_and_clues(review_status, created_at);
CREATE INDEX IF NOT EXISTS idx_claims_subject ON claims_and_clues(subject_person_id, claim_type);
4.2 0002_gov_dom_sentinel.sql（官网“领导之窗”哨兵表）SQLCREATE TABLE IF NOT EXISTS gov_roster_targets (
    target_id TEXT PRIMARY KEY,                     -- 如 'beijing_gov_leaders'
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    page_url TEXT NOT NULL,
    css_selector TEXT NOT NULL,                     -- 提取姓名与职务列表的精确选择器
    enabled INTEGER NOT NULL DEFAULT 1,
    last_checked_at TEXT
);

CREATE TABLE IF NOT EXISTS gov_roster_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL REFERENCES gov_roster_targets(target_id),
    captured_date TEXT NOT NULL,                    -- 'YYYY-MM-DD'
    roster_json TEXT NOT NULL,                      -- '[{"rank_order":1,"name":"殷勇","title":"市长"}, ...]'
    roster_hash TEXT NOT NULL,
    UNIQUE (target_id, captured_date)
);
4.3 0003_fts_search.sql（全文检索虚拟表）SQLCREATE VIRTUAL TABLE IF NOT EXISTS cadre_fts USING fts5(
    person_id UNINDEXED,
    name,
    native_place,
    resume_blob,                                    -- 拼接所有机构名、职务、院校、专业的扁平文本，支持“清华 水利 东城”秒查人
    tokenize = 'unicode61'
);
5. 五大信源采集器与 Gate 门控预检规范5.1 门控预检契约（runtime/gate_precheck.py）为严格适配 pap/gate.py 与 pap/scheduler.py 的低打扰调度原则，每次定时任务触发时先且仅运行 gate_precheck.py（纯 Python 标准网络请求与正则/AST 比对，耗时 < 15 秒，LLM Token = 0）：   返回契约（stdout JSON）：JSON{
  "gate_open": true,
  "priority": "urgent",
  "trigger_reasons": [
    "ccdi_investigation: 1 new central-managed cadre notice detected",
    "gov_dom_diff: [北京市人民政府] 领导列表移除 '夏林茂'"
  ],
  "pending_source_ids": ["src_8f92a1c04b12e3d4", "src_31b8e7f92a01c4b2"]
}
短路条件：当 pending_source_ids 为空时，输出 {"gate_open": false, "reason": "no_new_sources"} 并以状态码 0 退出，pap 调度器立即终止本次运行，不启动大模型会话。紧急抢占级别（priority = "urgent"）：只要命中 ccdi_investigation（中管干部被查）、ccdi_sanction（中管干部双开）或 gov_dom_diff（名字异常消失且无近期跨省履新记录），立即无视免打扰静默窗口触发研判流水线。5.2 各信源专属采集与预解析规则（runtime/collectors.py）中纪委国家监委监控器（CCDICollector）：盯防栏目：审查调查 -> 中管干部、党纪政务处分 -> 中管干部（每 30 分钟轮询）。确定性预提取：用正则先行切出核心句 ^(?P<prefix>.+?)(?P<name>[\u4e00-\u9fa5·]{2,5})涉嫌严重违纪违法，识别是否包含 “原” 字（区分任上落马 vs 卸任/退休倒查）以及是否包含 “主动投案”。人社部与新华网任免监控器（AppointCollector）：盯防栏目：人社部官网“国务院任免国家工作人员”、新华网/人民网“中央批准地方省委常委调整”通稿（每 2 小时轮询）。确定性预切分：国务院任免按句号与分号 ； 拆分为原子任免单句，再成批打包送入 cadre-intake。维基百科与 Wikidata 同步器（WikiCollector）：冷启动种子拉取：通过 Wikidata Query Service 执行 SPARQL，拉取所有带有 P39（担任职务：中央委员、候补委员、各省省长/书记/副省长、国务院正副部长）的人物 QID、出生日期、母校（P69）及前后任（P1365/P1366）。增量修订监听：每日调用中文维基 MediaWiki API action=query&list=recentchanges，过滤绑定了关注分类（如 Category:中国共产党第二十届中央委员会委员、Category:受处分的中国共产党党员）的词条源码变更；用 mwparserfromhell 直接解析 Wikitext 中的 {{Infobox officeholder}} 与 {{S-start}}...{{Succession box}} 模板。政经深度报道采集器（DeepMediaCollector）：通过自建或本地 RSS 订阅源拉取财新网（反腐记 / 人事观察）、澎湃新闻（人事风向）、新京报（政事儿）、上观新闻。仅当文章标题或导语命中库内已注册官员姓名或关键词（履新|落马|被查|双开|免职|投案|常委|副省长|副部长）时才入库 raw_sources，过滤无关民生社会新闻。省级与部委官网“领导之窗”哨兵（GovDomSentinel）：每日 06:00 与 18:00 两次拉取 gov_roster_targets 配置的 31 省区市政府及核心部委领导列表页，抽取纯文本结构 [(order, name, title)] 计算 SHA-256。Diff 判定：新增姓名 → 触发 cadre-intake 抓取其新挂出的官方标准简历全文。姓名消失 → 查询该官员 birth_ym（是否已满退龄）及近 14 天内是否已有跨省/跨部委新任命记录；若未满退龄且无去向通报，自动生成 claim_type = 'dom_removal_anomaly' 高优警报。6. LLM 知识抽取契约（cadre-bundle JSON Schema）所有 SKILL.md 在阅读 raw_sources 后，严禁直接拼接 SQL，必须生成符合 profile/references/cadre-bundle.md 规范的 JSON 文件，交由 python -m agents.cadre_tracker.runtime.cli ingest-bundle --file <bundle.json> 校验入库。6.1 cadre-bundle.json 完整契约结构JSON{
  "schema_version": "1.0",
  "source_id": "src_8f92a1c04b12e3d4",
  "persons": [
    {
      "name": "夏林茂",
      "gender": "男",
      "ethnicity": "汉族",
      "birth_ym": "1970-05",
      "native_place": "江苏建湖",
      "party_join_ym": "1997-05",
      "work_start_ym": "1993-07",
      "current_rank": "副省部级",
      "cc_membership": ["二十届中央候补委员"],
      "status": "under_investigation",
      "educations": [
        {
          "school_name": "清华大学",
          "department": "水利水电工程系",
          "degree": "学士",
          "major": "水工建筑",
          "is_full_time": true,
          "start_ym": "1988-09",
          "end_ym": "1993-07"
        },
        {
          "school_name": "清华大学",
          "department": "建筑学院",
          "degree": "博士",
          "major": "城市规划与设计",
          "is_full_time": false,
          "start_ym": "2005-09",
          "end_ym": "2011-01"
        }
      ]
    }
  ],
  "tenures": [
    {
      "person_name": "夏林茂",
      "person_birth_ym": "1970-05",
      "action": "UPSERT_SPAN",
      "org_canonical_name": "中共北京市东城区委员会",
      "org_short_name": "北京东城区委",
      "org_kind": "party_local",
      "parent_org_canonical_name": "中共北京市委员会",
      "role_title": "书记",
      "raw_role_text": "北京市东城区委书记",
      "role_tier": "chief",
      "rank_at_time": "正厅局级",
      "start_ym": "2018-12",
      "end_ym": "2021-02",
      "is_concurrent": 0,
      "predecessor_name": "张家明",
      "successor_name": "孙新军",
      "certainty": "FACT"
    }
  ],
  "claims": [
    {
      "claim_type": "investigation",
      "event_date": "2026-10-22",
      "subject_raw_name": "夏林茂",
      "related_raw_name": null,
      "certainty": "FACT",
      "violation_codes": [],
      "payload": {"in_office_fallen": true, "voluntary_surrender": false},
      "evidence_quote": "北京市委常委、常务副市长夏林茂涉嫌严重违纪违法，目前正接受中央纪委国家监委纪律审查和监察调查。"
    },
    {
      "claim_type": "patronage_speculation",
      "event_date": "2026-11-26",
      "subject_raw_name": "陈吉宁",
      "related_raw_name": "夏林茂",
      "certainty": "SPECULATION",
      "violation_codes": [],
      "payload": {"overlap_context": "2017-2022北京城建与区委上下级及清华校友背景"},
      "evidence_quote": "分析人士指出，陈吉宁主政北京市政府期间，清华建筑学院出身的夏林茂先后主政密云、东城并跻身市委常委。"
    }
  ]
}
6.2 抽取强制拆解规则（写入 cadre-intake/SKILL.md 与 cadre-cv-backfill/SKILL.md）一揽子兼职原子化拆分：遇到 2021.02—2023.01 北京市委常委、教育工委书记，严禁合并为一条记录！必须拆成两条 tenures：一条挂载 中共北京市委员会（role_title="常委", role_tier="member", is_concurrent=0），另一条挂载 中共北京市委教育工作委员会（role_title="书记", role_tier="chief", is_concurrent=1）。“其间”嵌套经历不断裂原则：简历中出现 2011.02—2017.05 北京市石景山区委副书记、区长（其间：2014.03—2014.07中央党校中青年干部培训一班学习），主职务 区长 保持 2011-02 至 2017-05 完整连续区间不变；括号内的中央党校经历单独生成一条 education_records（同时在 tenures 生成一条 is_concurrent=1 的培训班记录，以便图查询能搜出“同期党校同班同学”）。党政序列严格剥离：凡带“省委/市委/区委”且职务为“书记/副书记/常委/委员”，org_canonical_name 归入 中共XX委员会（party_local）；凡职务为“省长/市长/副市长/区长/厅长/局长”，归入 XX人民政府 或对应委办局（gov_local）。7. 知识融合：重名消歧与机构对齐算法（runtime/resolver.py）7.1 同名官员实体消歧评分器（Entity Disambiguation）中国官场同名现象普遍（如多位“王勇”、“李强”、“刘伟”、“陈刚”）。当 ingest-bundle 收到姓名 X 时，resolver.py 按以下四级流水线计算候选人匹配得分 $S \in [0, 1]$：硬特征精确命中（$S = 1.0$）：Bundle 中包含 birth_ym + native_place（或 wikidata_qid），且与库内某 person_id 完全一致 → 直接绑定合并。硬特征互斥否决（$S = 0.0$）：若双方均有非空 birth_ym 或 gender 且不相等 → 立即排除该候选人。仕途连续性与职级跃迁合理性打分（针对一句话任免通报无出生年月场景）：
遍历库内所有名为 X 的在任候选人 $C_i$，根据其最近一条未闭合（或刚闭合）履历 $T_{\text{last}}$ 计算：$$S(C_i) = 0.45 \cdot \mathbb{I}(\text{RankStepValid}) + 0.35 \cdot \mathbb{I}(\text{OrgOrRegionContinuity}) + 0.20 \cdot \mathbb{I}(\text{StatusActive})$$RankStepValid：新职务行政级别与 $T_{\text{last}}$ 级别相差不超过 1 级（例如正厅级升副部级、副部级平调副部级、副部级升正部级为合法；若某同名候选人 5 年前仍是某县副县长或已 retired/expelled，得分为 0）。OrgOrRegionContinuity：免职通报的机构与 $T_{\text{last}}$ 完全吻合（直接给满分 $S=0.98$），或同属一个垂直业务系统（如财政系统、规划城建系统）。分流阈值决策：最高分候选人 $S \ge 0.85$ 且领先第二名 $\Delta S \ge 0.30$ → 自动绑定（auto_merged）。库内无任何同名记录，且当前通报职务级别 $\ge$ 副省部级 → 自动新建 Person 实体。存在多个候选人且 $0.40 \le S < 0.85$ → 严禁盲目合并！将该声明写入 claims_and_clues（claim_type = 'disambiguation_conflict', review_status = 'needs_review'），并在下次交互时提醒用户调用 cadre-review-resolve 拍板。7.2 机构标准化与历史沿革自动挂载入库时先查 organizations.canonical_name，未命中则查 org_aliases.alias_name。内置预置种子文件 org-reform-lineage.md，初始化时批量导入 2018 年与 2023 年两轮机构改革核心映射（例如：北京市规划委员会 $\xrightarrow{2016-07}$ 北京市规划和国土资源管理委员会 $\xrightarrow{2018-11}$ 北京市规划和自然资源委员会；原环保部 $\xrightarrow{2018-03}$ 生态环境部；银保监会 $\xrightarrow{2023-05}$ 国家金融监督管理总局）。当新创建区县级机构（如 中共北京市密云区委员会）且 parent_org_id 为空时，根据行政区划前缀自动将其 parent_org_id 挂载到对应的省/直辖市党委或政府节点下。8. 图推理引擎算法规范（runtime/db.py）8.1 双人全维度关联探查（query_overlap(person_a, person_b)）一次调用同时返回四类结构化证据簇：work_overlaps（同班子与上下级辖属共事）：使用 WITH RECURSIVE 双向展开 org_lineage（最多 4 跳改名等价类），再沿 parent_org_id 展开 $0 \sim 2$ 跳上下级辖属树。时间窗口重叠条件：$\max(\text{start}_A, \text{start}_B) \le \min(\text{end}_A, \text{end}_B)$（其中 NULL 代入当前年月 strftime('%Y-%m', 'now')）。重叠月数公式：$$M_{\text{overlap}} = (Y_{\text{min\_end}} \times 12 + m_{\text{min\_end}}) - (Y_{\text{max\_start}} \times 12 + m_{\text{max\_start}}) + 1$$succession_links（同岗位前后任交接）：在同一等价机构簇的同一 role_title 下，$A.\text{end\_ym}$ 与 $B.\text{start\_ym}$ 相差在 $\pm 2$ 个月以内（或命中 predecessor_name / successor_name），识别为“直接前任/继任者”。edu_links（学缘与党校同窗）：连接同一 school_org_id。若起止年份存在交集标为 同期同校校友；若同属 department 标为 同院系校友；若学校为 中共中央党校 且时间完全重合标为 中青班同期同窗。external_clues（媒体点名与传闻线索）：联表检索 claims_and_clues 中同时涉及 A 与 B 的所有记录（附带 certainty 与 evidence_quote）。8.2 落马震荡波紧密度指数算法（query_shockwave(person_id, top_k=20)）当目标官员 $F$ 状态变更为 under_investigation 或 anomaly_watch 时，遍历所有与 $F$ 存在历史履历或学缘交集的官员 $P$，按以下公式计算震荡波紧密度指数（Closeness Index, $CI$）：$$CI(F, P) = \sum_{k \in \text{Overlaps}(F, P)} \left( M_k \times W_{\text{topology}}(k) \times W_{\text{recency}}(k) \right) + B_{\text{alumni}}(F, P) + B_{\text{succession}}(F, P)$$各项权重精确定义如下：$M_k$：第 $k$ 段重叠经历的持续月数（单段上限截断为 60 个月，防止早期挂名虚高）。$W_{\text{topology}}(k)$（组织拓扑权重）：同机构同班子，且其中一方为 chief / gov_head：$3.0$同机构普通副职搭档：$2.0$1 跳父子机构，且上级为 chief / gov_head / deputy_chief、下级为 chief / gov_head（如市长对区委书记/局长）：$2.2$2 跳上下级辖属：$1.0$$W_{\text{recency}}(k)$（时间衰减因子）：距离 2026 年 5 年内的交集取 $1.2$；5–12 年前取 $1.0$；12 年以上早期交集取 $0.6$。$B_{\text{alumni}}$：同校且同院系加 $15.0$ 分；中央党校同期培训班同窗加 $20.0$ 分；仅同校不同期加 $6.0$ 分。$B_{\text{succession}}$：在同一一把手岗位互为直接前任/继任者，加 $25.0$ 分。输出结果自动分两栏：already_fallen_associates（历史已爆雷关联人）：status IN ('under_investigation', 'expelled', 'sentenced') 的高分关联人——用于反向溯源此人为何落马（例如陈吉宁被查时，系统自动把 1 个月前刚被查的夏林茂置顶弹出，直接印证传导链）。active_watch_list（现役高危观察名单）：status = 'active' 的 Top-K 在任官员——用于前瞻性预警接下来谁可能受牵连或调整。9. pap 平台集成、CLI、Obsidian 投射与跨库联邦规范9.1 agents/cadre-tracker/agent.yaml 声明规范（实现时需与 pap/spec.py 的字段校验器做最终键名核对）：   YAMLid: cadre-tracker
name: Cadre Tracker (政经人事图谱追踪员)
version: "1.0.0"
description: 追踪副省部级及以上中管干部职务升迁调任轨迹、组织上下级共事图谱与反腐震荡波预警
workspace: agents/cadre-tracker

appearance:
  role_badge: "人事图谱"
  accent_color: "#B91C1C"

gate:
  precheck_command: "python3 -m agents.cadre_tracker.runtime.gate_precheck"
  timeout_seconds: 25

schedules:
  - id: ccdi-and-appoint-watch
    cron: "*/30 7-23 * * *"
    skill: cadre-intake
    gate_required: true
    description: "每30分钟巡检中纪委审查处分、人社部及新华社任免通报"

  - id: gov-dom-and-media-daily
    cron: "15 6,18 * * *"
    skill: cadre-intake
    gate_required: true
    description: "早晚两次执行31省与部委官网领导窗DOM Diff及财新/澎湃/Wiki增量同步"

skills:
  - cadre-intake
  - cadre-cv-backfill
  - cadre-shockwave-brief
  - cadre-review-resolve
9.2 统一 CLI 接口契约（runtime/cli.py）所有命令默认输出结构化 JSON（带 --pretty 时格式化输出），同时向 paplog 发射工具调用轨迹事件：   Bash# 1. 初始化与执行 SQL 迁移
python3 -m agents.cadre_tracker.runtime.cli migrate

# 2. 执行采集探针（供 gate_precheck 或手动调试调用）
python3 -m agents.cadre_tracker.runtime.cli poll [--source ccdi|appoint|wiki|media|dom|all]

# 3. 读取待解析的原始信源全文
python3 -m agents.cadre_tracker.runtime.cli fetch-pending

# 4. 幂等摄入 LLM 提取的 cadre-bundle.json（内部自动触发 resolver 消歧与状态机跃迁）
python3 -m agents.cadre_tracker.runtime.cli ingest-bundle --file /tmp/bundle.json

# 5. 图谱推理三剑客
python3 -m agents.cadre_tracker.runtime.cli overlap --a "陈吉宁" --b "夏林茂"
python3 -m agents.cadre_tracker.runtime.cli shockwave --person "陈吉宁" --top 20
python3 -m agents.cadre_tracker.runtime.cli succession --org "北京市东城区委" --role "书记"

# 6. 全文检索官员（支持组合条件，如查所有在清华读过书且在规划系统干过的在任副部级）
python3 -m agents.cadre_tracker.runtime.cli search --query "清华大学 规划" --status active

# 7. 待审核同名消歧队列管理
python3 -m agents.cadre_tracker.runtime.cli review-list
python3 -m agents.cadre_tracker.runtime.cli review-decide --claim-id <id> --action bind --person-id <pid>

# 8. 按需刷新 Obsidian 人物档案与震荡波报告
python3 -m agents.cadre_tracker.runtime.cli project-obsidian --person "夏林茂"

9.3 Obsidian 按需物化规范（runtime/obsidian.py）遵循 world-historian/runtime/obsidian.py 的幂等区块替换风格：   写入路径：${OBSIDIAN_VAULT}/Cadre-Graph/People/<姓名>.md 与 ${OBSIDIAN_VAULT}/Cadre-Graph/Briefs/YYYY-MM-DD-<事件简题>.md。触发阈值：仅对满足以下任一条件的人物生成 .md 文件：(1) 发生新任免或落马异动；(2) 出现在任意落马官员震荡波 Top-15 名单中；(3) 用户手动标记关注。自动生成 Mermaid 关系图：在人物 Markdown 的 <!-- PAP:CADRE_GRAPH:START --> 锚点区间内，自动渲染该官员的核心上下级与已爆雷关联节点（红色高亮落马节点 #ef4444，橙色高亮异常观察节点 #f59e0b），同时保留锚点外的个人手写研判笔记永不被覆盖。9.4 与 world-historian 的跨库联邦契约（cadre_lookup.py）模仿 agents/world-historian/runtime/personal_lookup.py：   使用只读模式打开库：sqlite3.connect(f"file:{cadre_db_path}?mode=ro", uri=True)，超时 3 秒；若 cadre.sqlite3 尚未初始化则优雅返回空列表，绝不阻塞 world-historian 原有流程。暴露函数：lookup_cadre_context(entity_names: list[str]) -> dict。当 world-historian 的 news-capture、news-follow 或 news-morning-brief 识别到国内政经人物实体时，自动附带该官员的现职级别、近 10 年关键主政地、以及与近期异动官员的 CI 紧密度交集摘要，辅助 world-historian 写出有纵深感的历史编年卡片。10. 冷启动回填方案与测试验收标准（Verification Plan）10.1 三批次冷启动数据建库（Seed Bootstrapping）不需要人工录入任何一条简历，按以下三步在 2 小时内建立完整全国底库：Batch 0（机构骨架初始化）：导入 31 省区市党委/政府/人大/政协四套班子根节点、国务院组成部门与直属机构节点，以及 org-reform-lineage.md 中的 80+ 组机构改革更名对。Batch 1（顶层 ~500 人核心池）：运行 WikiCollector 拉取二十届中央委员（205人）+ 中央候补委员（171人）+ 中央纪委委员（133人）的维基 Wikitext 与人民网/中经网简历，批处理跑完 cadre-cv-backfill。Batch 2（省部级全量 ~2,600 人扩展池）：遍历中经网“地方党政领导人物库”（31 省四套班子 + 法检两长）及人社部近 3 年国务院任免存档（补齐各部委副部长、副部级央企与中管高校正副职），完成全量闭环。10.2 契约单元测试矩阵（tests/test_cadre_tracker.py）所有代码合入前必须通过以下 6 项自动化 pytest 验收用例，确保不破坏现有 CI（.github/workflows/ci.yml）：   测试套件编号验证场景与黄金测试夹具（Golden Fixture）预期断言结果T1: 嵌套简历拆解与幂等入库输入包含 市委常委、常务副市长 及 （其间：中央党校中青班学习） 的复杂简历 Bundle 重复执行两次 ingest-bundle拆分为 2 条独立职务 + 1 条 is_concurrent=1 培训记录；二次摄入行数为 0 新增、无主键冲突T2: 机构改名跨期穿透构造官员 A（2015–2017 任北京市规划委副主任）与官员 B（2016–2019 任北京市规自委主任），中间通过 org_lineage 连接query_overlap(A, B) 准确识别出 2016–2017 共事重叠，且 query_succession 拉出完整连续历任链T3: 黄金案例（陈吉宁—夏林茂多维耦合）灌入陈吉宁（清华校长 → 环保部长 → 北京市长 → 上海市委书记）与夏林茂（清华本硕博 → 石景山区长 → 密云/东城区委书记 → 北京市委常委/常务副市长 → 2026.10 落马）真实履历切片overlap 同时命中 北京上下级辖属共事（2017.05–2022.10，66个月） 与 清华大学学缘；当陈吉宁状态设为 under_investigation 时，shockwave 的 already_fallen_associates 栏自动将夏林茂排在首位T4: 重名官员消歧拦截库内已有两位同名“王勇”（一位副国级/国务委员，一位海南省政协原副主席）；新输入一条未标出生年月的早年地方处级线索resolver.py 计算得分落入模糊区间，自动拦截写入 review_status='needs_review'，不污染任一主档案T5: 信源权威等级锁保护先以 Tier 1（中纪委通报）写入某官员 status='under_investigation'；随后摄入一篇滞后的 Tier 3/4 文章称其仍在任或仅为传闻credibility_lock=1 生效，拒绝降级回退 persons.status，仅将 Tier 4 内容记入 claims_and_cluesT6: Gate 静默短路与 DOM 撤下告警模拟连续两次拉取相同的中纪委列表 HTML；第三次模拟某省政府“领导介绍”页移除了54岁副省长姓名前两次 gate_precheck 中第二次必须输出 gate_open=false；第三次必须输出 gate_open=true, priority="urgent"

