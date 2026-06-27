-- 事後アンケート(誰でも・ID不要)の回答テーブル。研究モード(?pid=)時はparticipant_idも併記。
-- 書き込み経路はWorkerの /survey のみ。CHECK/NOT NULLは将来の別経路・手入力に対する保険。
CREATE TABLE IF NOT EXISTS survey_responses (
  id TEXT PRIMARY KEY NOT NULL,
  created_at TEXT NOT NULL,
  participant_id TEXT,            -- 研究モード(?pid=)時のみ。通常は NULL
  -- 属性
  gender TEXT,                    -- female / male / other / na
  age_band TEXT,                  -- 10s / 20s / 30s / 40s / 50s_plus / na
  rp_experience TEXT,             -- none / yes
  trpg_experience TEXT,           -- none / yes
  watch_freq TEXT,                -- daily / weekly / monthly / less / NULL(任意)
  -- 再参加意向(5件法 1〜5)
  again INTEGER CHECK (again IS NULL OR (again BETWEEN 1 AND 5)),
  recommend INTEGER CHECK (recommend IS NULL OR (recommend BETWEEN 1 AND 5)),
  join_table INTEGER CHECK (join_table IS NULL OR (join_table BETWEEN 1 AND 5)),
  -- 理解の自己評価(5件法 1〜5)
  understand_flow INTEGER CHECK (understand_flow IS NULL OR (understand_flow BETWEEN 1 AND 5)),
  understand_next INTEGER CHECK (understand_next IS NULL OR (understand_next BETWEEN 1 AND 5)),
  -- 理解チェック小問(任意・選択肢インデックス文字列)。各問とも正答は選択肢"2"。
  quiz1 TEXT,
  quiz2 TEXT,
  quiz3 TEXT,
  -- 自由記述
  felt TEXT NOT NULL,             -- 体験中の気持ち(必須)
  hard TEXT,                      -- 難しかった/不安だった点(任意)
  wish TEXT,                      -- もう一度やるなら(任意)
  -- 体験メタ(クライアント申告・参考値)
  client_stage INTEGER,
  client_turns INTEGER
);
