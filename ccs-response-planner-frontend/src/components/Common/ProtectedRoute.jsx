import { Navigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext.jsx'
import { LOGIN_RESOURCE } from './constants'

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) {
    return <Navigate to={`/${LOGIN_RESOURCE}`} replace state={{ redirected: true }} />
  }
  return children
}

export default ProtectedRoute
