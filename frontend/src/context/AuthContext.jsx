import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]   = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const savedToken = localStorage.getItem('termscope_token')
    const savedUser  = localStorage.getItem('termscope_user')
    if (savedToken && savedUser) {
      setToken(savedToken)
      setUser(JSON.parse(savedUser))
    }
    setLoading(false)
  }, [])

  const signIn = (userData, jwt) => {
    localStorage.setItem('termscope_token', jwt)
    localStorage.setItem('termscope_user', JSON.stringify(userData))
    setToken(jwt)
    setUser(userData)
  }

  const signOut = () => {
    localStorage.removeItem('termscope_token')
    localStorage.removeItem('termscope_user')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, signIn, signOut, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
