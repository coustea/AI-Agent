BEGIN;

ALTER TABLE generated_resources
DROP COLUMN review_result;

COMMIT;
