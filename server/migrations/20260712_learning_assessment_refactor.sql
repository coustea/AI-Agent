-- Migration: learning_assessment_refactor
-- Date: 2026-07-12

-- 1. Drop weekly_learning_digests
DROP TABLE IF EXISTS weekly_learning_digests CASCADE;

-- 2. Create learning_assessment_reports
CREATE TABLE IF NOT EXISTS learning_assessment_reports (
    id                 SERIAL PRIMARY KEY,
    user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    range_days         SMALLINT NOT NULL CHECK (range_days IN (7, 14, 30)),
    window_start       TIMESTAMPTZ NOT NULL,
    window_end         TIMESTAMPTZ NOT NULL,
    status             VARCHAR(16) NOT NULL CHECK (status IN ('generating', 'ready', 'failed')),
    facts_snapshot     JSONB,
    report_markdown    TEXT,
    generated_at       TIMESTAMPTZ,
    failure_code       VARCHAR(64),
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    updated_at         TIMESTAMPTZ DEFAULT NOW(),
    CHECK (window_end > window_start),
    CHECK (
        (status = 'ready' AND facts_snapshot IS NOT NULL AND report_markdown IS NOT NULL) OR
        (status = 'failed' AND failure_code IS NOT NULL) OR
        (status = 'generating')
    )
);

CREATE INDEX IF NOT EXISTS ix_reports_user_created ON learning_assessment_reports (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_reports_user_status ON learning_assessment_reports (user_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS uq_reports_user_generating ON learning_assessment_reports (user_id) WHERE status = 'generating';

-- 3. Modify user_profiles
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS guidance_strategy JSONB NOT NULL DEFAULT '{}';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS guidance_updated_at TIMESTAMPTZ;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS last_assessment_report_id INTEGER;

-- Foreign Key constraint
ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS fk_user_profiles_last_report;
ALTER TABLE user_profiles ADD CONSTRAINT fk_user_profiles_last_report FOREIGN KEY (last_assessment_report_id) REFERENCES learning_assessment_reports(id) ON DELETE SET NULL;

-- 4. Modify learning_events
ALTER TABLE learning_events ADD COLUMN IF NOT EXISTS client_event_id VARCHAR(64);
ALTER TABLE learning_events ADD COLUMN IF NOT EXISTS occurred_at TIMESTAMPTZ;

-- Backfill occurred_at
UPDATE learning_events SET occurred_at = created_at WHERE occurred_at IS NULL;
ALTER TABLE learning_events ALTER COLUMN occurred_at SET NOT NULL;
ALTER TABLE learning_events ALTER COLUMN occurred_at SET DEFAULT NOW();

CREATE UNIQUE INDEX IF NOT EXISTS uq_events_user_client_event
    ON learning_events (user_id, client_event_id)
    WHERE client_event_id IS NOT NULL;

-- 5. Modify learning_sessions
ALTER TABLE learning_sessions ADD COLUMN IF NOT EXISTS client_session_id VARCHAR(64);

CREATE UNIQUE INDEX IF NOT EXISTS uq_sessions_user_client_session
    ON learning_sessions (user_id, client_session_id)
    WHERE client_session_id IS NOT NULL;
