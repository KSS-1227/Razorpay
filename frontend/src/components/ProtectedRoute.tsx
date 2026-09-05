/**
 * ProtectedRoute — guards routes that require authentication.
 * Shows a full-screen animated loader while session state is resolving.
 */
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { FullScreenLoader } from './ui/FullScreenLoader'

export default function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <FullScreenLoader message="Verifying session…" />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <Outlet />
}
