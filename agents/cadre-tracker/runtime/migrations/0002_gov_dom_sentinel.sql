CREATE TABLE IF NOT EXISTS gov_roster_targets (
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
