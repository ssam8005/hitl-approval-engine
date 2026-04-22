-- 001_initial.sql — Initial schema for hitl-approval-engine
-- Applied automatically via SQLAlchemy on first run.
-- Kept here for documentation and manual PostgreSQL migration.

CREATE TABLE IF NOT EXISTS approval_requests (
    id                   TEXT PRIMARY KEY,
    lead_id              TEXT NOT NULL,
    lead_name            TEXT NOT NULL,
    company              TEXT,
    title                TEXT,
    email                TEXT,
    linkedin_url         TEXT,
    ai_score             REAL NOT NULL,
    ai_rationale         TEXT,
    source_system        TEXT DEFAULT 'unknown',
    status               TEXT DEFAULT 'pending',
    decision_by          TEXT,
    decision_at          DATETIME,
    decision_note        TEXT,
    telegram_message_id  INTEGER,
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at           DATETIME NOT NULL,
    webhook_fired        BOOLEAN DEFAULT 0,
    webhook_fired_at     DATETIME,
    webhook_response_code INTEGER
);

CREATE INDEX IF NOT EXISTS idx_approval_requests_lead_id ON approval_requests(lead_id);
CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id  TEXT NOT NULL REFERENCES approval_requests(id),
    event_type  TEXT NOT NULL,
    actor       TEXT,
    detail      TEXT,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_log_request_id ON audit_log(request_id);
