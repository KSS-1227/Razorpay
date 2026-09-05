"""
smoke_test_constraints.py
--------------------------
Smoke tests for PostgreSQL DB constraints defined in 001_auth_schema.sql.

Tests:
  - test_audit_log_no_update_delete_grants  (Requirement 6.5)
  - test_workspace_member_cap_trigger       (Requirements 7.5, 7.11)

Run standalone (from repo root):
    pytest backend/auth/migrations/smoke_test_constraints.py -v --rootdir=backend/auth/migrations

Or from within this directory:
    cd backend/auth/migrations && pytest smoke_test_constraints.py -v

The tests will be skipped automatically if:
  - Required environment variables are not set, OR
  - The database is not reachable (connection refused / timeout)
"""

import os
import uuid

import pytest

# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def _get_connection_params() -> dict:
    """
    Build psycopg2 connection kwargs from environment variables.

    Supports two modes:
    1. SUPABASE_DB_URL  — a full libpq connection string / DSN
    2. Individual vars  — DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    """
    db_url = os.environ.get("SUPABASE_DB_URL")
    if db_url:
        return {"dsn": db_url}

    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT", "5432")
    dbname = os.environ.get("DB_NAME")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")

    if not all([host, dbname, user, password]):
        return {}

    return {
        "host": host,
        "port": int(port),
        "dbname": dbname,
        "user": user,
        "password": password,
    }


def _connect():
    """
    Attempt to create and return a psycopg2 connection.
    Returns None if psycopg2 is not installed, env vars are missing,
    or the database is unreachable.
    """
    try:
        import psycopg2
    except ImportError:
        return None

    params = _get_connection_params()
    if not params:
        return None

    try:
        conn = psycopg2.connect(**params, connect_timeout=5)
        return conn
    except Exception:  # OperationalError, timeout, auth failure, etc.
        return None


# ---------------------------------------------------------------------------
# Session-scoped fixture: one connection for the whole test module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db_conn():
    """
    Provide a live psycopg2 connection for the module.
    Skip the entire module gracefully if no connection can be established.
    """
    conn = _connect()
    if conn is None:
        pytest.skip(
            "Database not reachable or env vars not set "
            "(SUPABASE_DB_URL or DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD). "
            "Skipping DB constraint smoke tests."
        )
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Test 1 — audit_log append-only (Requirement 6.5)
# ---------------------------------------------------------------------------

def test_audit_log_no_update_delete_grants(db_conn):
    """
    Verify the `authenticated` role has NO UPDATE or DELETE privilege
    on public.audit_log.

    Queries information_schema.role_table_grants which captures explicit
    GRANT statements. A missing row means the privilege was either never
    granted or was explicitly REVOKEd — both are acceptable proof that
    the append-only constraint is in place.

    Validates: Requirement 6.5
    """
    query = """
        SELECT privilege_type
        FROM   information_schema.role_table_grants
        WHERE  table_schema = 'public'
          AND  table_name   = 'audit_log'
          AND  grantee      = 'authenticated'
          AND  privilege_type IN ('UPDATE', 'DELETE');
    """
    with db_conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    found = [row[0] for row in rows]

    assert "UPDATE" not in found, (
        "FAIL: `authenticated` role has UPDATE privilege on public.audit_log. "
        "The audit log must be append-only. "
        "Expected: REVOKE UPDATE ON public.audit_log FROM authenticated;"
    )
    assert "DELETE" not in found, (
        "FAIL: `authenticated` role has DELETE privilege on public.audit_log. "
        "The audit log must be append-only. "
        "Expected: REVOKE DELETE ON public.audit_log FROM authenticated;"
    )


# ---------------------------------------------------------------------------
# Test 2 — workspace_members 50-member cap trigger (Requirements 7.5, 7.11)
# ---------------------------------------------------------------------------

def test_workspace_member_cap_trigger_exists(db_conn):
    """
    Verify that the trigger `trg_workspace_member_cap` exists on
    public.workspace_members and that its backing function contains
    the >= 50 cap logic.

    This structural check works without needing to insert real rows and
    is safe to run against a shared / production-adjacent DB.

    Validates: Requirements 7.5, 7.11
    """
    # --- 2a. Confirm the trigger is registered on the table ---------------
    trigger_query = """
        SELECT t.tgname
        FROM   pg_trigger     t
        JOIN   pg_class       c ON c.oid = t.tgrelid
        JOIN   pg_namespace   n ON n.oid = c.relnamespace
        WHERE  n.nspname  = 'public'
          AND  c.relname  = 'workspace_members'
          AND  t.tgname   = 'trg_workspace_member_cap'
          AND  NOT t.tgisinternal;
    """
    with db_conn.cursor() as cur:
        cur.execute(trigger_query)
        trigger_row = cur.fetchone()

    assert trigger_row is not None, (
        "FAIL: Trigger `trg_workspace_member_cap` not found on "
        "public.workspace_members. "
        "The 50-member hard cap requires this trigger to be present."
    )

    # --- 2b. Confirm the trigger function body contains the cap logic -----
    func_body_query = """
        SELECT p.prosrc
        FROM   pg_proc p
        WHERE  p.proname = 'check_workspace_member_cap';
    """
    with db_conn.cursor() as cur:
        cur.execute(func_body_query)
        func_row = cur.fetchone()

    assert func_row is not None, (
        "FAIL: Function `check_workspace_member_cap` not found in pg_proc. "
        "The trigger must reference this function."
    )

    func_body: str = func_row[0]
    # Accept '>= 50' or '> 49' as equivalent cap expressions
    cap_present = ">= 50" in func_body or "> 49" in func_body
    assert cap_present, (
        f"FAIL: Trigger function `check_workspace_member_cap` does not appear "
        f"to enforce a 50-member cap. "
        f"Expected '>= 50' or '> 49' in function body. "
        f"Actual body:\n{func_body}"
    )


def test_workspace_member_cap_functional(db_conn):
    """
    Functional test: insert a workspace + 50 active members, then assert
    that a 51st INSERT raises an exception containing
    'workspace_member_cap_exceeded'.

    Everything runs inside a single transaction that is rolled back at the
    end, so no data is persisted.

    This test requires the DB user to have INSERT privileges on
    public.workspaces, public.users (or auth.users), and
    public.workspace_members, and the ability to create UUIDs.

    The test is skipped gracefully if the INSERT fails due to permission
    issues (e.g., FK to auth.users that cannot be satisfied without a real
    Supabase Auth user), so it never blocks CI environments.

    Validates: Requirements 7.5, 7.11
    """
    import psycopg2

    conn = _connect()
    if conn is None:
        pytest.skip("No DB connection available.")

    try:
        conn.autocommit = False
        workspace_id = str(uuid.uuid4())

        with conn.cursor() as cur:
            # Attempt to insert a workspace without an owner FK constraint
            # by using a direct INSERT that may be blocked by FK to public.users.
            # We wrap the whole body in a savepoint so partial failures don't
            # abort the outer transaction.
            cur.execute("SAVEPOINT functional_cap_test;")

            try:
                # Insert 50 active workspace_member rows with NULL user_id
                # (allowed by the schema: user_id REFERENCES … ON DELETE SET NULL)
                # and a synthetic workspace_id (no FK check if schema allows it).
                # We bypass the workspaces FK by inserting into workspace_members
                # only if the table allows a non-existent workspace_id — otherwise
                # we skip gracefully.
                for _i in range(50):
                    cur.execute(
                        """
                        INSERT INTO public.workspace_members
                               (member_id, workspace_id, role, membership_status)
                        VALUES (%s, %s, 'Viewer', 'active')
                        """,
                        (str(uuid.uuid4()), workspace_id),
                    )

                # The 51st insert must raise workspace_member_cap_exceeded
                raised = False
                try:
                    cur.execute(
                        """
                        INSERT INTO public.workspace_members
                               (member_id, workspace_id, role, membership_status)
                        VALUES (%s, %s, 'Viewer', 'active')
                        """,
                        (str(uuid.uuid4()), workspace_id),
                    )
                except psycopg2.errors.RaiseException as exc:
                    raised = True
                    assert "workspace_member_cap_exceeded" in str(exc), (
                        f"Expected 'workspace_member_cap_exceeded' in exception "
                        f"message, got: {exc}"
                    )
                except psycopg2.DatabaseError as exc:
                    raised = True
                    assert "workspace_member_cap_exceeded" in str(exc), (
                        f"Expected 'workspace_member_cap_exceeded' in exception "
                        f"message, got: {exc}"
                    )

                assert raised, (
                    "FAIL: 51st INSERT into workspace_members did NOT raise an "
                    "exception. The trigger `trg_workspace_member_cap` must reject "
                    "inserts when active member count is already 50."
                )

            except psycopg2.errors.ForeignKeyViolation:
                # FK to public.workspaces or public.users cannot be satisfied
                # without real rows — skip the functional path gracefully.
                cur.execute("ROLLBACK TO SAVEPOINT functional_cap_test;")
                pytest.skip(
                    "Functional cap test skipped: INSERT blocked by FK constraints "
                    "(workspace or user rows required). "
                    "The structural trigger check (test_workspace_member_cap_trigger_exists) "
                    "already validates the cap logic."
                )
            except psycopg2.errors.InsufficientPrivilege:
                cur.execute("ROLLBACK TO SAVEPOINT functional_cap_test;")
                pytest.skip(
                    "Functional cap test skipped: insufficient DB privileges for INSERT. "
                    "The structural trigger check already validates the cap logic."
                )
            finally:
                # Always roll back — we never want to leave test data behind
                conn.rollback()

    finally:
        conn.close()
