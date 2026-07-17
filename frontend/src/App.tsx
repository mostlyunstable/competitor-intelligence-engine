import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect, createContext, useContext } from 'react'
import { api } from './lib/api'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import OverviewPage from './pages/OverviewPage'
import CompetitorsPage from './pages/CompetitorsPage'
import CompetitorProfilePage from './pages/CompetitorProfilePage'
import CompetitorComparePage from './pages/CompetitorComparePage'
import CollectionsPage from './pages/CollectionsPage'
import LogsPage from './pages/LogsPage'
import ReportsPage from './pages/ReportsPage'
import AdminPage from './pages/AdminPage'
import ActivityPage from './pages/ActivityPage'

const AuthContext = createContext<{
  isAuthenticated: boolean
  login: (u: string, p: string) => void
  logout: () => void
  markUnauthenticated: () => void
}>({ isAuthenticated: false, login: () => {}, logout: () => {}, markUnauthenticated: () => {} })

export const useAuth = () => useContext(AuthContext)

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(api.isAuthenticated())

  const login = (username: string, password: string) => {
    api.setCredentials(username, password)
    setIsAuthenticated(true)
  }

  const logout = () => {
    api.clearCredentials()
    setIsAuthenticated(false)
  }

  const markUnauthenticated = () => {
    setIsAuthenticated(false)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, markUnauthenticated }}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <Layout>
                  <Routes>
                    <Route path="/" element={<OverviewPage />} />
                    <Route path="/competitors" element={<CompetitorsPage />} />
                    <Route path="/competitors/compare" element={<CompetitorComparePage />} />
                    <Route path="/competitors/:id" element={<CompetitorProfilePage />} />
                    <Route path="/collections" element={<CollectionsPage />} />
                    <Route path="/logs" element={<LogsPage />} />
                    <Route path="/reports" element={<ReportsPage />} />
                    <Route path="/activity" element={<ActivityPage />} />
                    <Route path="/admin" element={<AdminPage />} />
                  </Routes>
                </Layout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  )
}
