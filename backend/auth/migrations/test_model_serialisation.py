"""
test_model_serialisation.py
----------------------------
Property-based tests for model serialisation round-trips.

Properties:
  - Property 21: AuditLogEntry serialisation round-trip  (Requirement 10.2)
  - Property 28: JWT claims JSON round-trip              (Requirement 13.1)
  - Property 30: WorkspaceMember serialisation round-trip (Requirement 13.3)

Run standalone (from repo root):
    pytest backend/auth/migrations/test_model_serialisation.py -v

Or from within this directory:
    cd backend/auth/migrations && pytest test_model_serialisation.py -v
"""

import json
import os
import sys
from datetime import UTC

# ---------------------------------------------------------------------------
# Path setup — import model files directly via importlib to bypass
# backend/__init__.py and auth/models/__init__.py, both of which trigger
# the heavy ML pipeline (SentenceTransformer) that is irrelevant here.
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_MODELS_DIR = os.path.abspath(os.path.join(_HERE, "..", "models"))

import importlib.util as _ilu


def _load_module(name: str, filepath: str):
    """Load a single .py file as a module without executing any __init__.py."""
    spec = _ilu.spec_from_file_location(name, filepath)
    mod = _ilu.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_audit_mod = _load_module("_auth_models_audit", os.path.join(_MODELS_DIR, "audit.py"))
_workspace_mod = _load_module("_auth_models_workspace", os.path.join(_MODELS_DIR, "workspace.py"))

AuditLogEntry: type = _audit_mod.AuditLogEntry
AuditEventType = _audit_mod.AuditEventType
WorkspaceMember: type = _workspace_mod.WorkspaceMember

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

_AUDIT_EVENT_TYPES = [
    "user_registered",
    "user_login_success",
    "user_login_failure",
    "user_logout",
    "account_locked",
    "password_reset_requested",
    "password_reset_completed",
    "role_changed",
    "workspace_created",
    "workspace_member_added",
    "workspace_member_removed",
    "workspace_deleted",
    "token_refresh",
    "suspicious_token_reuse",
]

_ROLES = ["Admin", "Analyst", "Viewer"]
_MEMBERSHIP_STATUSES = ["active", "pending", "removed"]

_uuid_str = st.uuids().map(str)
_nullable_uuid_str = st.none() | _uuid_str
_utc_datetime = st.datetimes(timezones=st.just(UTC))
_nullable_utc_datetime = st.none() | _utc_datetime


# ---------------------------------------------------------------------------
# Property 21 — AuditLogEntry serialisation round-trip
# **Validates: Requirements 10.2**
# ---------------------------------------------------------------------------

@given(
    entry_id=_uuid_str,
    event_type=st.sampled_from(_AUDIT_EVENT_TYPES),
    user_id=_nullable_uuid_str,
    workspace_id=_nullable_uuid_str,
    timestamp=_utc_datetime,
    source_ip=st.ip_addresses(v=4).map(str),
    detail=st.text(max_size=2000),
)
@settings(max_examples=100)
def test_audit_log_entry_round_trip(
    entry_id, event_type, user_id, workspace_id, timestamp, source_ip, detail
):
    """
    **Validates: Requirements 10.2**

    Property 21: Constructing an AuditLogEntry from arbitrary valid field
    values, serialising it to a dict with model_dump(), then deserialising
    back via model_validate() must produce an equal model.
    """
    entry = AuditLogEntry(
        entry_id=entry_id,
        event_type=event_type,
        user_id=user_id,
        workspace_id=workspace_id,
        timestamp=timestamp,
        source_ip=source_ip,
        detail=detail,
    )
    round_tripped = AuditLogEntry.model_validate(entry.model_dump())
    assert round_tripped == entry, (
        f"AuditLogEntry round-trip failed.\n"
        f"Original:    {entry!r}\n"
        f"Round-tripped: {round_tripped!r}"
    )


# ---------------------------------------------------------------------------
# Property 28 — JWT claims JSON round-trip
# **Validates: Requirements 13.1**
# ---------------------------------------------------------------------------

@given(
    sub=_uuid_str,
    role=st.sampled_from(_ROLES),
    workspace_id=_uuid_str,
    exp=st.integers(min_value=1),
    iss=st.text(min_size=1, max_size=200),
)
@settings(max_examples=100)
def test_jwt_claims_round_trip(sub, role, workspace_id, exp, iss):
    """
    **Validates: Requirements 13.1**

    Property 28: Building a dict of JWT claims (sub, role, workspace_id,
    exp, iss) with arbitrary valid values, serialising to JSON and
    deserialising back must produce an equal dict.

    This validates that JSON serialisation of standard JWT claim types
    (str, int) is lossless.
    """
    claims = {
        "sub": sub,
        "role": role,
        "workspace_id": workspace_id,
        "exp": exp,
        "iss": iss,
    }
    serialised = json.dumps(claims)
    round_tripped = json.loads(serialised)
    assert round_tripped == claims, (
        f"JWT claims round-trip failed.\n"
        f"Original:    {claims!r}\n"
        f"Round-tripped: {round_tripped!r}"
    )


# ---------------------------------------------------------------------------
# Property 30 — WorkspaceMember serialisation round-trip
# **Validates: Requirements 13.3**
# ---------------------------------------------------------------------------

@given(
    member_id=_uuid_str,
    user_id=_uuid_str,
    workspace_id=_uuid_str,
    role=st.sampled_from(_ROLES),
    membership_status=st.sampled_from(_MEMBERSHIP_STATUSES),
    invited_at=_utc_datetime,
    activated_at=_nullable_utc_datetime,
    expires_at=_nullable_utc_datetime,
)
@settings(max_examples=100)
def test_workspace_member_round_trip(
    member_id,
    user_id,
    workspace_id,
    role,
    membership_status,
    invited_at,
    activated_at,
    expires_at,
):
    """
    **Validates: Requirements 13.3**

    Property 30: Constructing a WorkspaceMember from arbitrary valid field
    values, serialising it to a dict with model_dump(), then deserialising
    back via model_validate() must produce an equal model.
    """
    member = WorkspaceMember(
        member_id=member_id,
        user_id=user_id,
        workspace_id=workspace_id,
        role=role,
        membership_status=membership_status,
        invited_at=invited_at,
        activated_at=activated_at,
        expires_at=expires_at,
    )
    round_tripped = WorkspaceMember.model_validate(member.model_dump())
    assert round_tripped == member, (
        f"WorkspaceMember round-trip failed.\n"
        f"Original:    {member!r}\n"
        f"Round-tripped: {round_tripped!r}"
    )
