-- Migration: Adopt existing unique index as constraint-backed index
-- Date: 2026-06-19
-- One-time, non-idempotent migration
--
-- This migration:
-- 1. Verifies no duplicate (resource_id, agent_type) pairs exist
-- 2. Verifies the existing uq_generated_resource_items_resource_agent is a unique index
-- 3. Adopts it as a constraint-backed index using UNIQUE USING INDEX
-- 4. Drops the redundant composite index
--
-- Deployment order:
-- 1. Back up generated_resource_items
-- 2. Run this migration
-- 3. Resolve any reported duplicates manually outside this change
-- 4. Deploy application source
-- 5. Verify constraint through PostgreSQL catalog inspection

BEGIN;

-- Step 1: Preflight - check for duplicate (resource_id, agent_type) pairs
DO $$
DECLARE
    dup_count INTEGER;
    dup_details TEXT;
BEGIN
    SELECT COUNT(*) INTO dup_count
    FROM (
        SELECT resource_id, agent_type, COUNT(*) as cnt
        FROM generated_resource_items
        GROUP BY resource_id, agent_type
        HAVING COUNT(*) > 1
        LIMIT 11
    ) duplicates;

    IF dup_count > 0 THEN
        SELECT string_agg(
            format('resource_id=%s agent_type=%s count=%s', resource_id, agent_type, cnt),
            E'\n' ORDER BY resource_id, agent_type
        ) INTO dup_details
        FROM (
            SELECT resource_id, agent_type, COUNT(*) as cnt
            FROM generated_resource_items
            GROUP BY resource_id, agent_type
            HAVING COUNT(*) > 1
            LIMIT 10
        ) duplicates;

        RAISE EXCEPTION 'Duplicate (resource_id, agent_type) pairs found. Manual cleanup required before migration.%s',
            CASE WHEN dup_details IS NOT NULL THEN E'\n' || dup_details ELSE '' END;
    END IF;
END $$;

-- Step 2: Verify preconditions and adopt the existing unique index
DO $$
DECLARE
    idx_oid OID;
    is_unique BOOLEAN;
    is_owned BOOLEAN;
    indexed_columns TEXT[];
    redundant_idx_oid OID;
    redundant_is_unique BOOLEAN;
    redundant_columns TEXT[];
BEGIN
    -- A pre-existing constraint on this table means the migration baseline is wrong.
    SELECT con.oid INTO idx_oid
    FROM pg_constraint con
    JOIN pg_class tbl ON tbl.oid = con.conrelid
    JOIN pg_namespace ns ON ns.oid = tbl.relnamespace
    WHERE con.conname = 'uq_generated_resource_items_resource_agent'
      AND con.contype = 'u'
      AND ns.nspname = 'public'
      AND tbl.relname = 'generated_resource_items';

    IF idx_oid IS NOT NULL THEN
        RAISE EXCEPTION 'Constraint uq_generated_resource_items_resource_agent already exists. Migration already applied or fresh bootstrap.';
    END IF;

    -- Verify the exact table, schema, uniqueness and ordered columns of the old index.
    SELECT c.oid, i.indisunique, EXISTS (
        SELECT 1 FROM pg_constraint owned WHERE owned.conindid = c.oid
    ), array_agg(att.attname ORDER BY key.ordinality)
    INTO idx_oid, is_unique, is_owned, indexed_columns
    FROM pg_class c
    JOIN pg_namespace ns ON ns.oid = c.relnamespace
    JOIN pg_index i ON i.indexrelid = c.oid
    JOIN pg_class tbl ON tbl.oid = i.indrelid
    JOIN LATERAL unnest(i.indkey::smallint[]) WITH ORDINALITY AS key(attnum, ordinality) ON TRUE
    JOIN pg_attribute att ON att.attrelid = tbl.oid AND att.attnum = key.attnum
    WHERE c.relname = 'uq_generated_resource_items_resource_agent'
      AND c.relkind = 'i'
      AND ns.nspname = 'public'
      AND tbl.relname = 'generated_resource_items'
    GROUP BY c.oid, i.indisunique;

    IF idx_oid IS NULL THEN
        RAISE EXCEPTION 'Index uq_generated_resource_items_resource_agent not found. Unexpected database state.';
    END IF;

    IF NOT is_unique THEN
        RAISE EXCEPTION 'Index uq_generated_resource_items_resource_agent is not unique.';
    END IF;

    IF is_owned THEN
        RAISE EXCEPTION 'Index uq_generated_resource_items_resource_agent is already owned by a constraint.';
    END IF;

    IF indexed_columns IS DISTINCT FROM ARRAY['resource_id', 'agent_type']::TEXT[] THEN
        RAISE EXCEPTION 'Index uq_generated_resource_items_resource_agent has unexpected columns: %', indexed_columns;
    END IF;

    -- The redundant ordinary index must also match the exact expected baseline.
    SELECT c.oid, i.indisunique, array_agg(att.attname ORDER BY key.ordinality)
    INTO redundant_idx_oid, redundant_is_unique, redundant_columns
    FROM pg_class c
    JOIN pg_namespace ns ON ns.oid = c.relnamespace
    JOIN pg_index i ON i.indexrelid = c.oid
    JOIN pg_class tbl ON tbl.oid = i.indrelid
    JOIN LATERAL unnest(i.indkey::smallint[]) WITH ORDINALITY AS key(attnum, ordinality) ON TRUE
    JOIN pg_attribute att ON att.attrelid = tbl.oid AND att.attnum = key.attnum
    WHERE c.relname = 'ix_generated_resource_items_resource_agent'
      AND c.relkind = 'i'
      AND ns.nspname = 'public'
      AND tbl.relname = 'generated_resource_items'
    GROUP BY c.oid, i.indisunique;

    IF redundant_idx_oid IS NULL THEN
        RAISE EXCEPTION 'Index ix_generated_resource_items_resource_agent not found. Unexpected database state.';
    END IF;

    IF redundant_is_unique OR redundant_columns IS DISTINCT FROM ARRAY['resource_id', 'agent_type']::TEXT[] THEN
        RAISE EXCEPTION 'Index ix_generated_resource_items_resource_agent has unexpected definition: unique=% columns=%', redundant_is_unique, redundant_columns;
    END IF;
END $$;

-- Step 3: Adopt the existing unique index as a constraint-backed index
-- This avoids creating a second index with the same columns
ALTER TABLE generated_resource_items
ADD CONSTRAINT uq_generated_resource_items_resource_agent
UNIQUE USING INDEX uq_generated_resource_items_resource_agent;

-- Step 4: Drop the redundant composite index (same columns as the constraint)
DROP INDEX ix_generated_resource_items_resource_agent;

COMMIT;
