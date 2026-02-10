CREATE TABLE IF NOT EXISTS protocols (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  year INTEGER NOT NULL,
  product TEXT NOT NULL,
  protocol_no TEXT NOT NULL,
  batch_no TEXT NOT NULL DEFAULT 'N/A',
  version INTEGER NOT NULL DEFAULT 1,
  storage_key TEXT NOT NULL,
  filename TEXT NOT NULL,
  size_bytes INTEGER,
  mime TEXT DEFAULT 'application/pdf',
  tg_file_id TEXT,
  is_active INTEGER DEFAULT 1,
  uploaded_by INTEGER,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_protocols_lookup ON protocols(year, product, protocol_no);
CREATE INDEX IF NOT EXISTS idx_protocols_active ON protocols(is_active);

CREATE TABLE IF NOT EXISTS moderators (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tg_user_id INTEGER NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_moderators_user ON moderators(tg_user_id);
