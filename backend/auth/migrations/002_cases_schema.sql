-- =============================================================================
--  002_cases_schema.sql
--  Cases table for the Compliance Intelligence Platform
--  Apply via Supabase SQL editor after 001_auth_schema.sql
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
--  public.cases
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.cases (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title       TEXT        NOT NULL CHECK (char_length(title) BETWEEN 1 AND 200),
    description TEXT        NOT NULL DEFAULT '',
    status      TEXT        NOT NULL DEFAULT 'processing'
                                CHECK (status IN ('processing', 'completed', 'failed')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cases_user_id    ON public.cases(user_id);
CREATE INDEX IF NOT EXISTS idx_cases_created_at ON public.cases(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cases_status     ON public.cases(status);

-- Auto-update updated_at on row change
CREATE OR REPLACE FUNCTION update_cases_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_cases_updated_at
    BEFORE UPDATE ON public.cases
    FOR EACH ROW
    EXECUTE FUNCTION update_cases_updated_at();

-- Row-Level Security — users can only see and manage their own cases
ALTER TABLE public.cases ENABLE ROW LEVEL SECURITY;

CREATE POLICY cases_select_own ON public.cases
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY cases_insert_own ON public.cases
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY cases_update_own ON public.cases
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY cases_delete_own ON public.cases
    FOR DELETE USING (auth.uid() = user_id);
