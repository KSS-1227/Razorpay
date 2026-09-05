/**
 * usePermission hook — returns true if the current user's role includes
 * the given action/permission.
 *
 * Requirements: 10.7
 */
import { useAuth } from '../../auth/AuthContext'

/** Client-side permission matrix — mirrors backend ROLE_PERMISSIONS. */
const ROLE_PERMISSIONS: Record<string, Set<string>> = {
  Admin: new Set([
    'UPLOAD_DOCUMENT',
    'EXECUTE_QUERY',
    'VIEW_GRAPH',
    'GENERATE_REPORT',
    'READ_REPORT',
    'MANAGE_MEMBERS',
    'DELETE_WORKSPACE',
    'VIEW_AUDIT_LOG',
  ]),
  Analyst: new Set([
    'UPLOAD_DOCUMENT',
    'EXECUTE_QUERY',
    'VIEW_GRAPH',
    'GENERATE_REPORT',
    'READ_REPORT',
  ]),
  Viewer: new Set(['VIEW_GRAPH', 'READ_REPORT']),
}

/**
 * Returns true if the authenticated user's role grants the given permission.
 *
 * @param action - One of the permission string values (e.g. "UPLOAD_DOCUMENT").
 */
export function usePermission(action: string): boolean {
  const { user } = useAuth()
  if (!user) return false
  return ROLE_PERMISSIONS[user.role]?.has(action) ?? false
}
