"""
Audit models.

Shared Pydantic models used by the audit service and routes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

# ============================================================================
# Audit Event Types
# ============================================================================

AuditEventType = Literal[
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


# ============================================================================
# Audit Log Entry
# ============================================================================

class AuditLogEntry(BaseModel):
    """Represents one audit log entry."""

    entry_id: str

    event_type: AuditEventType

    user_id: str | None = None

    workspace_id: str | None = None

    timestamp: datetime

    source_ip: str

    detail: str

    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================================
# Cursor Page
# ============================================================================

class AuditLogPage(BaseModel):
    """Cursor-paginated audit log response."""

    entries: list[AuditLogEntry]

    next_cursor: str | None = None

    model_config = ConfigDict(
        from_attributes=True
    )
