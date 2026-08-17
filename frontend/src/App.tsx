import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, createContext, useContext } from 'react'
import { api } from './lib/api'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
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
import AiInsightsPage from './pages/AiInsightsPage'
import CopilotPage from './pages/CopilotPage'
import PredictiveIntelligenceSuitePage from './pages/PredictiveIntelligenceSuitePage'
import PricingIntelligencePage from './pages/PricingIntelligencePage'
import PredictionsPage from './pages/PredictionsPage'
import MLPerformancePage from './pages/MLPerformancePage'
import KnowledgeGraphPage from './pages/KnowledgeGraphPage'
import GeoIntelligencePage from './pages/GeoIntelligencePage'
import RiskAnalysisPage from './pages/RiskAnalysisPage'
import ForecastsPage from './pages/ForecastsPage'
import ScenariosPage from './pages/ScenariosPage'
import DataQualityPage from './pages/DataQualityPage'
import RecommendationsPage from './pages/RecommendationsPage'
import PredictiveBenchmarkPage from './pages/PredictiveBenchmarkPage'
import ForecastReportPage from './pages/ForecastReportPage'
import ConfidenceDashboardPage from './pages/ConfidenceDashboardPage'
import { DashboardProvider } from './context/DashboardContext'

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
                <DashboardProvider>
                  <Layout>
                    <ErrorBoundary key={window.location.pathname}>
                      <Routes>
                        <Route path="/" element={<OverviewPage />} />
                        <Route path="/competitors" element={<CompetitorsPage />} />
                        <Route path="/competitors/compare" element={<CompetitorComparePage />} />
                        <Route path="/competitors/:id" element={<CompetitorProfilePage />} />
                        <Route path="/collections" element={<CollectionsPage />} />
                        <Route path="/logs" element={<LogsPage />} />
                        <Route path="/reports" element={<ReportsPage />} />
                        <Route path="/activity" element={<ActivityPage />} />
                        <Route path="/ai" element={<AiInsightsPage />} />
                        <Route path="/predictive-intelligence" element={<PredictiveIntelligenceSuitePage />} />
                        <Route path="/predictions" element={<PredictionsPage />} />
                        <Route path="/pricing-intelligence" element={<PricingIntelligencePage />} />
                        <Route path="/ml-performance" element={<MLPerformancePage />} />
                        <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
                        <Route path="/geo-intelligence" element={<GeoIntelligencePage />} />
                        <Route path="/risk-analysis" element={<RiskAnalysisPage />} />
                        <Route path="/forecasts" element={<ForecastsPage />} />
                        <Route path="/scenarios" element={<ScenariosPage />} />
                        <Route path="/data-quality" element={<DataQualityPage />} />
                        <Route path="/recommendations" element={<RecommendationsPage />} />
                        <Route path="/benchmarks" element={<PredictiveBenchmarkPage />} />
                        <Route path="/forecast-reports" element={<ForecastReportPage />} />
                        <Route path="/confidence" element={<ConfidenceDashboardPage />} />
                        <Route path="/copilot" element={<CopilotPage />} />
                        <Route path="/admin" element={<AdminPage />} />
                      </Routes>
                    </ErrorBoundary>
                  </Layout>
                </DashboardProvider>
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  )
}
