/**
 * useWorkspaceGuard — redirects to /workspaces if the user
 * is authenticated but no workspace has been selected.
 *
 * workspaceId is now persisted in localStorage via AuthContext,
 * so this guard only triggers when genuinely no workspace exists.
 */
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function useWorkspaceGuard() {
  const { isAuthenticated, isLoading, workspaceId } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    // Wait for auth to initialise before making redirect decisions
    if (isLoading) return
    if (isAuthenticated && !workspaceId) {
      void navigate('/workspaces', { replace: true })
    }
  }, [isLoading, isAuthenticated, workspaceId, navigate])

  // Ready when: not loading AND authenticated AND has a workspace
  const isReady = !isLoading && isAuthenticated && !!workspaceId
  return { isReady }
}
