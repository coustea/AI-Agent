-- Migration: Add generated_resource_agent_runs table and resource run snapshot fields
-- Date: 2026-06-20
-- Purpose: Support durable agent lifecycle tracking and task recovery

-- Add run snapshot fields to generated_resources
ALTER TABLE generated_resources
    ADD COLUMN IF NOT EXISTS run_id VARCHAR(96),
    ADD COLUMN IF NOT EXISTS request_snapshot JSONB,
    ADD COLUMN IF NOT EXISTS profile_snapshot JSONB,
    ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ;

-- Create agent runs table
CREATE TABLE IF NOT EXISTS generated_resource_agent_runs (
    id BIGSERIAL PRIMARY KEY,
    resource_id BIGINT NOT NULL REFERENCES generated_resources(id) ON DELETE CASCADE,
    run_id VARCHAR(96) NOT NULL,
    agent_id VARCHAR(32) NOT NULL,
    stage VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    error_type VARCHAR(128),
    error_message TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    elapsed_ms INTEGER,
    metrics JSONB,
    CONSTRAINT uq_resource_agent_run UNIQUE (resource_id, agent_id),
    CONSTRAINT ck_resource_agent_run_status
        CHECK (status IN ('pending','running','completed','failed','interrupted'))
);

-- Add source_item_ids to generated_resource_items
ALTER TABLE generated_resource_items
    ADD COLUMN IF NOT EXISTS source_item_ids JSONB;

-- Update legacy status values
UPDATE generated_resource_items
SET status = 'completed'
WHERE status = 'finished';

-- Validate no duplicate items exist before adding constraint
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM generated_resource_items
        GROUP BY resource_id, agent_type
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'duplicate generated resource items must be resolved before migration';
    END IF;
END $$;

-- Add unique constraint for (resource_id, agent_type) if not exists
CREATE UNIQUE INDEX IF NOT EXISTS uq_generated_resource_item_agent
    ON generated_resource_items(resource_id, agent_type);

-- Create indexes for agent runs table
CREATE INDEX IF NOT EXISTS ix_generated_resource_agent_runs_resource_id
    ON generated_resource_agent_runs (resource_id);
CREATE INDEX IF NOT EXISTS ix_generated_resource_agent_runs_run_id
    ON generated_resource_agent_runs (run_id);
