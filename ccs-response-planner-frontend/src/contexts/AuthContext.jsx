import { createContext, useContext, useState } from 'react'

const AuthContext = createContext(null)

function AuthProvider({ children }) {
  const savedToken = localStorage.getItem('token')
  const savedUser = localStorage.getItem('user')
  const hasSession = !!(savedToken && savedUser)

  const [isAuthenticated, setIsAuthenticated] = useState(hasSession)
  const [user, setUser] = useState(hasSession ? savedUser : null)
  const [token, setToken] = useState(hasSession ? savedToken : null)

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
