import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext.jsx'
import { API_LOGIN_URL, LOGIN_RESOURCE, RESPONSE_PLANNER_RESOURCE } from '../Common/constants'
import './Login.css'

const ALERT_VISIBLE_MS = 3000
const ALERT_FADE_MS = 500

/**
 * The login page component
 */
function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [errorFading, setErrorFading] = useState(false)
  const [showRedirected, setShowRedirected] = useState(false)
  const [redirectedFading, setRedirectedFading] = useState(false)
  const { isAuthenticated, user, login, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (location.state?.redirected) {
      setShowRedirected(true)
      const fadeTimer = setTimeout(() => setRedirectedFading(true), ALERT_VISIBLE_MS)
      const hideTimer = setTimeout(() => {
        setShowRedirected(false)
        setRedirectedFading(false)
      }, ALERT_VISIBLE_MS + ALERT_FADE_MS)
      return () => {
        clearTimeout(fadeTimer)
        clearTimeout(hideTimer)
      }
    }
  }, [location.state])

  useEffect(() => {
    if (error) {
      setErrorFading(false)
      const fadeTimer = setTimeout(() => setErrorFading(true), ALERT_VISIBLE_MS)
      const hideTimer = setTimeout(() => {
        setError('')
        setErrorFading(false)
      }, ALERT_VISIBLE_MS + ALERT_FADE_MS)
      return () => {
        clearTimeout(fadeTimer)
        clearTimeout(hideTimer)
      }
    }
  }, [error])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const res = await fetch(API_LOGIN_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error || 'Login failed')
        return
      }
      login(data.token, data.username)
      navigate(`/${RESPONSE_PLANNER_RESOURCE}`)
    } catch {
      setError('Login failed')
    }
  }

  const handleLogout = () => {
    logout()
    navigate(`/${LOGIN_RESOURCE}`)
  }

  if (isAuthenticated) {
    return (
      <div className="Login">
        <div className="card login-card mx-auto">
          <div className="card-body">
            <h2 className="card-title mb-4">Login</h2>
            <p>
              You are logged in as <strong>{user}</strong>.
            </p>
            <button className="btn btn-dark btn-block" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="Login">
      <div className="card login-card mx-auto">
        <div className="card-body">
          <h2 className="card-title mb-4">Login</h2>
          {showRedirected && (
            <div
              className={`alert alert-warning login-alert ${redirectedFading ? 'login-alert-fade' : ''}`}
              role="alert"
            >
              You need to be logged in to access that page.
            </div>
          )}
          {error && (
            <div
              className={`alert alert-danger login-alert ${errorFading ? 'login-alert-fade' : ''}`}
              role="alert"
            >
              {error}
            </div>
          )}
          <form onSubmit={handleSubmit}>
            <div className="form-group mb-3">
              <label htmlFor="username">Username</label>
              <input
                type="text"
                className="form-control"
                id="username"
                placeholder="Enter username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div className="form-group mb-3">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                className="form-control"
                id="password"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <button type="submit" className="btn btn-dark btn-block">
              Sign in
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

export default Login
