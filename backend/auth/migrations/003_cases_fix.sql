-- =============================================================================
--  003_cases_fix.sql
--  Run this in Supabase SQL Editor to fix the cases table.
--
--  The cases table was created without the status, description columns
--  and without RLS policies or indexes. This migration adds everything
--  that 002_cases_schema.sql assumed but couldn't create (IF NOT EXISTS
--  skipped the CREATE TABLE so the ALTER TABLE is needed instead).
-- =============================================================================


-- ─────────────────────────────────────────────────────────────────────────────
--  STEP 1: Add missing columns to existing cases table
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE public.cases
    ADD COLUMN IF NOT EXISTS description TEXT        NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS status      TEXT        NOT NULL DEFAULT 'processing'
                                             CHECK (status IN ('processing', 'completed', 'failed')),
    ADD COLUMN IF NOT EXISTS updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW();


-- ─────────────────────────────────────────────────────────────────────────────
--  STEP 2: Add missing indexes
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_cases_user_id    ON public.cases(user_id);
CREATE INDEX IF NOT EXISTS idx_cases_created_at ON public.cases(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cases_status     ON public.cases(status);


-- ─────────────────────────────────────────────────────────────────────────────
--  STEP 3: auto-update updated_at trigger
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_cases_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_cases_updated_at ON public.cases;
CREATE TRIGGER trg_cases_updated_at
    BEFORE UPDATE ON public.cases
    FOR EACH ROW
    EXECUTE FUNCTION update_cases_updated_at();


-- ─────────────────────────────────────────────────────────────────────────────
--  STEP 4: Enable RLS and add policies
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE public.cases ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS cases_select_own ON public.cases;
CREATE POLICY cases_select_own ON public.cases
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS cases_insert_own ON public.cases;
CREATE POLICY cases_insert_own ON public.cases
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS cases_update_own ON public.cases;
CREATE POLICY cases_update_own ON public.cases
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS cases_delete_own ON public.cases;
CREATE POLICY cases_delete_own ON public.cases
    FOR DELETE USING (auth.uid() = user_id);


-- ─────────────────────────────────────────────────────────────────────────────
--  STEP 5: Backfill status on any rows that have NULL (edge case)
-- ─────────────────────────────────────────────────────────────────────────────

UPDATE public.cases SET status = 'processing' WHERE status IS NULL;


-- ─────────────────────────────────────────────────────────────────────────────
--  VERIFY — run this SELECT to confirm the fix worked
-- ─────────────────────────────────────────────────────────────────────────────
-- SELECT column_name, data_type, column_default, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'public' AND table_name = 'cases'
-- ORDER BY ordinal_position;
