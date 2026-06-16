BEGIN;

ALTER TABLE generated_resources
    DROP COLUMN IF EXISTS personalization,
    ADD COLUMN IF NOT EXISTS teaching_plan JSONB,
    ADD COLUMN IF NOT EXISTS review_result JSONB,
    ADD COLUMN IF NOT EXISTS failed_agents JSONB,
    ADD COLUMN IF NOT EXISTS workflow_metadata JSONB;

ALTER TABLE generated_resource_items
    ADD COLUMN IF NOT EXISTS metrics JSONB,
    ADD COLUMN IF NOT EXISTS downstream_context JSONB;

CREATE INDEX IF NOT EXISTS ix_generated_resource_items_metrics
    ON generated_resource_items USING GIN (metrics);
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_downstream_context
    ON generated_resource_items USING GIN (downstream_context);

COMMIT;
