/**
 * RequireRole — hides and disables UI when the current user lacks the
 * required permission. Shows a tooltip with "Insufficient permissions".
 *
 * Requirements: 10.7
 */
import type { ReactNode } from 'react'
import { usePermission } from './usePermission'

interface RequireRoleProps {
  /** The permission string required to see/use the children. */
  requiredPermission: string
  children: ReactNode
}

export default function RequireRole({ requiredPermission, children }: RequireRoleProps) {
  const hasPermission = usePermission(requiredPermission)

  if (hasPermission) {
    return <>{children}</>
  }

  return (
    <span
      title="Insufficient permissions"
      aria-label="Insufficient permissions"
      style={{ display: 'none' }}
      aria-hidden="true"
      aria-disabled="true"
    >
      {children}
    </span>
  )
}
