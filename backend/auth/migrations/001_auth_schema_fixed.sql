-- =============================================================================
--  001_auth_schema_fixed.sql
--  Run this in Supabase SQL Editor:
--  https://supabase.com/dashboard/project/ohqkjizvfrmfdxghkurp/sql/new
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
--  public.users  (profile table — extends auth.users)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.users (
    user_id               UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name          TEXT        NOT NULL DEFAULT 'User'
                                          CHECK (char_length(display_name) BETWEEN 1 AND 100),
    avatar_url            TEXT        CHECK (avatar_url IS NULL OR avatar_url ~* '^https?://'),
    preferred_language    TEXT        NOT NULL DEFAULT 'en',
    preferred_date_format TEXT        NOT NULL DEFAULT 'YYYY-MM-DD',
    failed_login_attempts INTEGER     NOT NULL DEFAULT 0,
    locked_until          TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_select_own ON public.users;
CREATE POLICY users_select_own ON public.users
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS users_update_own ON public.users;
CREATE POLICY users_update_own ON public.users
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────────
--  Auto-create public.users row on signup
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    INSERT INTO public.users (user_id, display_name)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1))
    )
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Backfill existing auth users that don't have a public.users row yet
INSERT INTO public.users (user_id, display_name)
SELECT id, COALESCE(raw_user_meta_data->>'display_name', split_part(email, '@', 1))
FROM auth.users
ON CONFLICT (user_id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
--  public.workspaces
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.workspaces (
    workspace_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT        NOT NULL CHECK (char_length(name) BETWEEN 3 AND 80),
    owner_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    is_deleted   BOOLEAN     NOT NULL DEFAULT FALSE,
    deleted_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_workspace_name_per_owner UNIQUE NULLS NOT DISTINCT (owner_id, name)
);

CREATE INDEX IF NOT EXISTS idx_workspaces_owner_id   ON public.workspaces(owner_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_is_deleted ON public.workspaces(is_deleted) WHERE is_deleted = FALSE;

ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS workspaces_insert_owner ON public.workspaces;
CREATE POLICY workspaces_insert_owner ON public.workspaces
    FOR INSERT WITH CHECK (auth.uid() = owner_id);

-- ─────────────────────────────────────────────────────────────────────────────
--  public.workspace_members
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.workspace_members (
    member_id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    workspace_id      UUID        NOT NULL REFERENCES public.workspaces(workspace_id) ON DELETE CASCADE,
    role              TEXT        NOT NULL CHECK (role IN ('Admin','Analyst','Viewer')),
    membership_status TEXT        NOT NULL DEFAULT 'pending'
                                      CHECK (membership_status IN ('active','pending','removed')),
    invited_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at      TIMESTAMPTZ,
    expires_at        TIMESTAMPTZ,
    invited_email     TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_active_member UNIQUE (workspace_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_wm_workspace_id ON public.workspace_members(workspace_id);
CREATE INDEX IF NOT EXISTS idx_wm_user_id      ON public.workspace_members(user_id);
CREATE INDEX IF NOT EXISTS idx_wm_status       ON public.workspace_members(membership_status);

ALTER TABLE public.workspace_members ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS wm_select_own ON public.workspace_members;
CREATE POLICY wm_select_own ON public.workspace_members
    FOR SELECT USING (user_id = auth.uid());

-- ─────────────────────────────────────────────────────────────────────────────
--  public.audit_log
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.audit_log (
    entry_id     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type   TEXT        NOT NULL,
    user_id      UUID,
    workspace_id UUID,
    timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_ip    TEXT        NOT NULL DEFAULT 'system',
    detail       TEXT        CHECK (char_length(detail) <= 2000),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_workspace_id ON public.audit_log(workspace_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp    ON public.audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user_id      ON public.audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_event_type   ON public.audit_log(event_type);

ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS audit_select_admin ON public.audit_log;
CREATE POLICY audit_select_admin ON public.audit_log
    FOR SELECT USING (
        workspace_id IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM public.workspace_members wm
            WHERE wm.workspace_id      = audit_log.workspace_id
              AND wm.user_id           = auth.uid()
              AND wm.role              = 'Admin'
              AND wm.membership_status = 'active'
        )
    );

GRANT INSERT, SELECT ON public.audit_log TO authenticated;
REVOKE UPDATE, DELETE ON public.audit_log FROM authenticated;
