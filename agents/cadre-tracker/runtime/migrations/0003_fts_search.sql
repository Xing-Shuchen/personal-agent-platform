CREATE VIRTUAL TABLE IF NOT EXISTS cadre_fts USING fts5(
    person_id UNINDEXED,
    name,
    native_place,
    resume_blob,                                    -- 拼接所有机构名、职务、院校、专业的扁平文本，支持“清华 水利 东城”秒查人
    tokenize = 'unicode61'
);
