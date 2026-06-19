CREATE TABLE IF NOT EXISTS sessions (
  participant_id TEXT PRIMARY KEY,
  started_at TEXT,
  ended_at TEXT,
  duration_sec INTEGER,
  turns INTEGER DEFAULT 0,
  max_stage INTEGER DEFAULT 0,
  ended INTEGER DEFAULT 0,
  transcript TEXT,
  created_at TEXT
);
