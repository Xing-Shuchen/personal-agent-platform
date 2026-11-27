PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- 1. 官员实体主表
CREATE TABLE IF NOT EXISTS persons (
    person_id TEXT PRIMARY KEY,                     -- 格式: p_<slug>_<birth_ym_or_shorthash>
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
    credibility_lock INTEGER NOT NULL DEFAULT 4,    -- 写入当前 status 的最高信源等级(1最高)，防止低等级信源降级覆写
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
    source_id TEXT REFERENCES raw_sources(source_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_edu_unique
    ON education_records(person_id, school_org_id, COALESCE(degree, ''), COALESCE(start_ym, ''));
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
