-- =============================================================================
--  001_auth_schema.sql
--  Authentication & User Management — PostgreSQL schema migration
--  Apply via Supabase SQL editor or migration tooling.
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
--  public.users  (extends auth.users managed by Supabase Auth)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE public.users (
    user_id               UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name          TEXT        NOT NULL
                                          CHECK (char_length(display_name) BETWEEN 1 AND 100),
    avatar_url            TEXT        CHECK (avatar_url IS NULL OR avatar_url ~* '^https?://'),
    preferred_language    TEXT        NOT NULL DEFAULT 'en'
                                          CHECK (preferred_language ~ '^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$'),
    preferred_date_format TEXT        NOT NULL DEFAULT 'YYYY-MM-DD'
                                          CHECK (preferred_date_format IN ('YYYY-MM-DD','DD/MM/YYYY','MM/DD/YYYY')),
    failed_login_attempts INTEGER     NOT NULL DEFAULT 0,
    locked_until          TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_created_at ON public.users(created_at);

-- Row-Level Security
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_select_own ON public.users
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY users_update_own ON public.users
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────────
--  public.workspaces
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE public.workspaces (
    workspace_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT        NOT NULL CHECK (char_length(name) BETWEEN 3 AND 80),
    owner_id     UUID        NOT NULL REFERENCES public.users(user_id),
    is_deleted   BOOLEAN     NOT NULL DEFAULT FALSE,
    deleted_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique workspace name per owner (soft-delete handled at app layer)
    CONSTRAINT uq_workspace_name_per_owner
        UNIQUE NULLS NOT DISTINCT (owner_id, name)
);

CREATE INDEX idx_workspaces_owner_id   ON public.workspaces(owner_id);
CREATE INDEX idx_workspaces_is_deleted ON public.workspaces(is_deleted) WHERE is_deleted = FALSE;

-- Row-Level Security
ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;

-- Members can see workspaces they belong to with an active membership
CREATE POLICY workspaces_select_member ON public.workspaces
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1
            FROM public.workspace_members wm
            WHERE wm.workspace_id = workspaces.workspace_id
              AND wm.user_id      = auth.uid()
              AND wm.membership_status = 'active'
        )
    );

-- Only the owning user may insert a workspace for themselves
CREATE POLICY workspaces_insert_owner ON public.workspaces
    FOR INSERT
    WITH CHECK (auth.uid() = owner_id);

-- UPDATE and DELETE are performed via the service role only (no user-level policy needed)

-- ─────────────────────────────────────────────────────────────────────────────
--  public.workspace_members
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE public.workspace_members (
    member_id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        REFERENCES public.users(user_id) ON DELETE SET NULL,
    workspace_id      UUID        NOT NULL REFERENCES public.workspaces(workspace_id) ON DELETE CASCADE,
    role              TEXT        NOT NULL CHECK (role IN ('Admin','Analyst','Viewer')),
    membership_status TEXT        NOT NULL DEFAULT 'pending'
                                      CHECK (membership_status IN ('active','pending','removed')),
    invited_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at      TIMESTAMPTZ,
    expires_at        TIMESTAMPTZ,     -- 72-hour window for pending invitations
    invited_email     TEXT,            -- email for not-yet-registered invitees
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One active record per user per workspace
    CONSTRAINT uq_active_member UNIQUE (workspace_id, user_id)
);

CREATE INDEX idx_wm_workspace_id ON public.workspace_members(workspace_id);
CREATE INDEX idx_wm_user_id      ON public.workspace_members(user_id);
CREATE INDEX idx_wm_status       ON public.workspace_members(membership_status);

-- Trigger function: enforce hard cap of 50 active members per workspace
CREATE OR REPLACE FUNCTION check_workspace_member_cap()
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF (
        SELECT COUNT(*)
        FROM public.workspace_members
        WHERE workspace_id      = NEW.workspace_id
          AND membership_status = 'active'
    ) >= 50 THEN
        RAISE EXCEPTION 'workspace_member_cap_exceeded';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_workspace_member_cap
    BEFORE INSERT ON public.workspace_members
    FOR EACH ROW
    EXECUTE FUNCTION check_workspace_member_cap();

-- Row-Level Security
ALTER TABLE public.workspace_members ENABLE ROW LEVEL SECURITY;

-- Users can read their own membership records
CREATE POLICY wm_select_own ON public.workspace_members
    FOR SELECT
    USING (user_id = auth.uid());

-- Admin-scoped reads for member management are handled via service role in the application layer

-- ─────────────────────────────────────────────────────────────────────────────
--  public.audit_log  (append-only)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE public.audit_log (
    entry_id     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type   TEXT        NOT NULL,
    user_id      UUID,       -- nullable: some events may not have a resolvable user
    workspace_id UUID,       -- nullable: some events are not workspace-scoped
    timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_ip    TEXT        NOT NULL,
    detail       TEXT        CHECK (char_length(detail) <= 2000),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_workspace_id ON public.audit_log(workspace_id);
CREATE INDEX idx_audit_timestamp    ON public.audit_log(timestamp DESC);
CREATE INDEX idx_audit_user_id      ON public.audit_log(user_id);
CREATE INDEX idx_audit_event_type   ON public.audit_log(event_type);

-- Row-Level Security
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

-- SELECT restricted to workspace Admins querying their own workspace's log entries
CREATE POLICY audit_select_admin ON public.audit_log
    FOR SELECT
    USING (
        workspace_id IS NOT NULL
        AND EXISTS (
            SELECT 1
            FROM public.workspace_members wm
            WHERE wm.workspace_id      = audit_log.workspace_id
              AND wm.user_id           = auth.uid()
              AND wm.role              = 'Admin'
              AND wm.membership_status = 'active'
        )
    );

-- Grant authenticated users the ability to append audit entries (via application layer).
-- UPDATE and DELETE are explicitly revoked to enforce append-only semantics.
GRANT INSERT, SELECT ON public.audit_log TO authenticated;
REVOKE UPDATE, DELETE ON public.audit_log FROM authenticated;
