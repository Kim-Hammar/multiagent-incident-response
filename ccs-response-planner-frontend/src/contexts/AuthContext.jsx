import { createContext, useContext, useEffect, useState } from 'react'
import { API_LOGIN_URL } from '../components/Common/constants'

const AuthContext = createContext(null)

function AuthProvider({ children }) {
  const savedToken = localStorage.getItem('token')
  const savedUser = localStorage.getItem('user')
  const hasSession = !!(savedToken && savedUser)

  const [isAuthenticated, setIsAuthenticated] = useState(hasSession)
  const [user, setUser] = useState(hasSession ? savedUser : null)
  const [token, setToken] = useState(hasSession ? savedToken : null)
  const [validating, setValidating] = useState(hasSession)

  useEffect(() => {
    if (!hasSession) return
    const validate = async () => {
      try {
        const res = await fetch(API_LOGIN_URL, {
          headers: { Authorization: `Bearer ${savedToken}` }
        })
        if (!res.ok) {
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          setToken(null)
          setUser(null)
          setIsAuthenticated(false)
        }
      } finally {
        setValidating(false)
      }
    }
    void validate()
  }, [])

  const login = (newToken, username) => {
    localStorage.setItem('token', newToken)
    localStorage.setItem('user', username)
    setToken(newToken)
    setUser(username)
    setIsAuthenticated(true)
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
    setIsAuthenticated(false)
  }

  if (validating) {
    return null
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

function useAuth() {
  return useContext(AuthContext)
}

export { AuthProvider, useAuth }
