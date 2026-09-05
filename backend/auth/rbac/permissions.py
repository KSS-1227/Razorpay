"""
Permission definitions and role-to-permission mapping for the RBAC system.

Defines all 8 permissions and the exact permission sets for each role
(Admin, Analyst, Viewer).

Requirements: 5.1
"""
from enum import Enum


class Permission(str, Enum):
    UPLOAD_DOCUMENT = "UPLOAD_DOCUMENT"
    EXECUTE_QUERY = "EXECUTE_QUERY"
    VIEW_GRAPH = "VIEW_GRAPH"
    GENERATE_REPORT = "GENERATE_REPORT"
    READ_REPORT = "READ_REPORT"
    MANAGE_MEMBERS = "MANAGE_MEMBERS"
    DELETE_WORKSPACE = "DELETE_WORKSPACE"
    VIEW_AUDIT_LOG = "VIEW_AUDIT_LOG"


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "Admin": {
        Permission.UPLOAD_DOCUMENT,
        Permission.EXECUTE_QUERY,
        Permission.VIEW_GRAPH,
        Permission.GENERATE_REPORT,
        Permission.READ_REPORT,
        Permission.MANAGE_MEMBERS,
        Permission.DELETE_WORKSPACE,
        Permission.VIEW_AUDIT_LOG,
    },
    "Analyst": {
        Permission.UPLOAD_DOCUMENT,
        Permission.EXECUTE_QUERY,
        Permission.VIEW_GRAPH,
        Permission.GENERATE_REPORT,
        Permission.READ_REPORT,
    },
    "Viewer": {
        Permission.VIEW_GRAPH,
        Permission.READ_REPORT,
    },
}
