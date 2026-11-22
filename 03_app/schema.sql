-- Concrete Evidence. Run with: npm run db:local (or db:remote online)

-- One row per checked photo
CREATE TABLE IF NOT EXISTS checks (
  id             TEXT PRIMARY KEY,           -- random id (crypto.randomUUID)
  created_at     TEXT NOT NULL,              -- ISO date and time, UTC
  element        TEXT,                       -- e.g. "Column C1", from the schedule
  face           TEXT,                       -- which face of the column, e.g. "A"
  zone           TEXT,                       -- "end" or "middle"
  file_name      TEXT,                       -- the uploaded file's name
  photo_key      TEXT NOT NULL,              -- R2: the checked photo (faces blurred, outlines drawn)
  result_key     TEXT NOT NULL,              -- R2: the full result JSON (every piece and outline)
  model          TEXT,                       -- which model weights answered
  pieces         INTEGER,                    -- how many pieces were found
  faults         INTEGER NOT NULL,           -- how many faults the check found
  scale_source   TEXT,                       -- how mm were found: "markers", "diameter" (bar size), or none
  schedule_json  TEXT NOT NULL,              -- the bar bending schedule used
  check_json     TEXT NOT NULL,              -- the check: faults, fixes, every rule and its status
  review_status  TEXT NOT NULL DEFAULT 'pending',  -- pending, then reviewed once every fault is decided
  signed_off_by  TEXT,                       -- who signed off after the review
  signed_off_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_checks_created_at ON checks (created_at);

-- One row per person's decision on one fault: the human review step
CREATE TABLE IF NOT EXISTS reviews (
  id           TEXT PRIMARY KEY,
  check_id     TEXT NOT NULL REFERENCES checks (id),
  fault_index  INTEGER NOT NULL,             -- the failed rule's position in check_json.checks
  decision     TEXT NOT NULL CHECK (decision IN ('confirm', 'reject')),
  note         TEXT,
  reviewer     TEXT,
  created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reviews_check ON reviews (check_id);

-- The checked photo and full result when R2 is not bound (lib/storage.js). Empty when R2 is used.
CREATE TABLE IF NOT EXISTS files (
  key           TEXT PRIMARY KEY,            -- same key as in R2, e.g. checks/<id>/checked.jpg
  content_type  TEXT NOT NULL,
  body          BLOB NOT NULL,
  created_at    TEXT NOT NULL
);
