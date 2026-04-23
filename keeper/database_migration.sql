-- Database Migration for GoFile Keeper
-- This script adds necessary columns and indexes to support the keeper functionality

-- ============================================================================
-- STEP 1: Add tracking columns to gofile_uploads table
-- ============================================================================

-- Add last_kept column to track when a link was last kept alive
ALTER TABLE gofile_uploads 
ADD COLUMN IF NOT EXISTS last_kept TIMESTAMP;

-- Add keep_alive_count to track how many times a link has been kept alive
ALTER TABLE gofile_uploads 
ADD COLUMN IF NOT EXISTS keep_alive_count INTEGER DEFAULT 0;

-- Add status column to track link status (active, failed, deleted)
ALTER TABLE gofile_uploads 
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';

-- Add comment to explain the columns
COMMENT ON COLUMN gofile_uploads.last_kept IS 'Timestamp of last successful keep-alive operation';
COMMENT ON COLUMN gofile_uploads.keep_alive_count IS 'Number of times this link has been kept alive';
COMMENT ON COLUMN gofile_uploads.status IS 'Status of the link: active, failed, or deleted';

-- ============================================================================
-- STEP 2: Create indexes for better query performance
-- ============================================================================

-- Index on last_kept for efficient sorting and filtering
CREATE INDEX IF NOT EXISTS idx_gofile_uploads_last_kept 
ON gofile_uploads(last_kept);

-- Index on status for filtering active links
CREATE INDEX IF NOT EXISTS idx_gofile_uploads_status 
ON gofile_uploads(status);

-- Composite index for the keeper's main query
CREATE INDEX IF NOT EXISTS idx_gofile_uploads_keeper_query 
ON gofile_uploads(status, last_kept) 
WHERE status = 'active' OR status IS NULL;

-- Index on upload_date for date-based filtering
CREATE INDEX IF NOT EXISTS idx_gofile_uploads_upload_date 
ON gofile_uploads(upload_date);

-- ============================================================================
-- STEP 3: Update existing records
-- ============================================================================

-- Set status to 'active' for all existing records that don't have a status
UPDATE gofile_uploads 
SET status = 'active' 
WHERE status IS NULL;

-- Initialize keep_alive_count to 0 for existing records
UPDATE gofile_uploads 
SET keep_alive_count = 0 
WHERE keep_alive_count IS NULL;

-- ============================================================================
-- STEP 4: Create a view for the keeper (optional but recommended)
-- ============================================================================

-- Create a view that only exposes what the keeper needs
CREATE OR REPLACE VIEW gofile_keeper_view AS
SELECT 
    id,
    streamer_name,
    gofile_link,
    upload_date,
    last_kept,
    keep_alive_count,
    status
FROM gofile_uploads
WHERE status != 'deleted' OR status IS NULL;

-- Grant access to the view (adjust role as needed)
-- GRANT SELECT, UPDATE ON gofile_keeper_view TO anon;
-- GRANT SELECT, UPDATE ON gofile_keeper_view TO authenticated;

-- ============================================================================
-- STEP 5: Create Row Level Security (RLS) policies (optional but recommended)
-- ============================================================================

-- Enable RLS on the table (if not already enabled)
-- ALTER TABLE gofile_uploads ENABLE ROW LEVEL SECURITY;

-- Policy to allow keeper to read active uploads
-- CREATE POLICY "keeper_read_active_uploads" ON gofile_uploads
--     FOR SELECT
--     TO authenticated
--     USING (status = 'active' OR status IS NULL);

-- Policy to allow keeper to update keep status
-- CREATE POLICY "keeper_update_keep_status" ON gofile_uploads
--     FOR UPDATE
--     TO authenticated
--     USING (true)
--     WITH CHECK (true);

-- ============================================================================
-- STEP 6: Create helper functions (optional)
-- ============================================================================

-- Function to mark a link as kept alive
CREATE OR REPLACE FUNCTION mark_link_kept_alive(link_id INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE gofile_uploads
    SET 
        last_kept = NOW(),
        keep_alive_count = COALESCE(keep_alive_count, 0) + 1,
        status = 'active'
    WHERE id = link_id;
END;
$$ LANGUAGE plpgsql;

-- Function to mark a link as failed
CREATE OR REPLACE FUNCTION mark_link_failed(link_id INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE gofile_uploads
    SET status = 'failed'
    WHERE id = link_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get links that need keeping alive
CREATE OR REPLACE FUNCTION get_links_needing_keepalive(
    days_threshold INTEGER DEFAULT 5,
    batch_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
    id INTEGER,
    streamer_name TEXT,
    gofile_link TEXT,
    upload_date TIMESTAMP,
    last_kept TIMESTAMP,
    keep_alive_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gu.id,
        gu.streamer_name,
        gu.gofile_link,
        gu.upload_date,
        gu.last_kept,
        gu.keep_alive_count
    FROM gofile_uploads gu
    WHERE (gu.status = 'active' OR gu.status IS NULL)
      AND (gu.last_kept IS NULL OR gu.last_kept < NOW() - INTERVAL '1 day' * days_threshold)
    ORDER BY gu.last_kept ASC NULLS FIRST
    LIMIT batch_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STEP 7: Create statistics view (optional)
-- ============================================================================

-- View to monitor keeper statistics
CREATE OR REPLACE VIEW gofile_keeper_stats AS
SELECT 
    COUNT(*) as total_links,
    COUNT(*) FILTER (WHERE status = 'active') as active_links,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_links,
    COUNT(*) FILTER (WHERE status = 'deleted') as deleted_links,
    COUNT(*) FILTER (WHERE last_kept IS NOT NULL) as kept_at_least_once,
    COUNT(*) FILTER (WHERE last_kept IS NULL) as never_kept,
    COUNT(*) FILTER (WHERE last_kept > NOW() - INTERVAL '7 days') as kept_recently,
    AVG(keep_alive_count) as avg_keep_count,
    MAX(last_kept) as most_recent_keep,
    MIN(last_kept) as oldest_keep
FROM gofile_uploads;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check if columns were added successfully
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'gofile_uploads'
  AND column_name IN ('last_kept', 'keep_alive_count', 'status');

-- Check if indexes were created successfully
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'gofile_uploads'
  AND indexname LIKE 'idx_gofile_uploads_%';

-- View current statistics
SELECT * FROM gofile_keeper_stats;

-- Sample query: Get links that need keeping alive
SELECT 
    id,
    streamer_name,
    gofile_link,
    upload_date,
    last_kept,
    keep_alive_count,
    status
FROM gofile_uploads
WHERE (status = 'active' OR status IS NULL)
  AND (last_kept IS NULL OR last_kept < NOW() - INTERVAL '5 days')
ORDER BY last_kept ASC NULLS FIRST
LIMIT 10;

-- ============================================================================
-- ROLLBACK (if needed)
-- ============================================================================

-- Uncomment these lines if you need to rollback the changes

-- DROP VIEW IF EXISTS gofile_keeper_stats;
-- DROP FUNCTION IF EXISTS get_links_needing_keepalive(INTEGER, INTEGER);
-- DROP FUNCTION IF EXISTS mark_link_failed(INTEGER);
-- DROP FUNCTION IF EXISTS mark_link_kept_alive(INTEGER);
-- DROP VIEW IF EXISTS gofile_keeper_view;
-- DROP INDEX IF EXISTS idx_gofile_uploads_upload_date;
-- DROP INDEX IF EXISTS idx_gofile_uploads_keeper_query;
-- DROP INDEX IF EXISTS idx_gofile_uploads_status;
-- DROP INDEX IF EXISTS idx_gofile_uploads_last_kept;
-- ALTER TABLE gofile_uploads DROP COLUMN IF EXISTS status;
-- ALTER TABLE gofile_uploads DROP COLUMN IF EXISTS keep_alive_count;
-- ALTER TABLE gofile_uploads DROP COLUMN IF EXISTS last_kept;
