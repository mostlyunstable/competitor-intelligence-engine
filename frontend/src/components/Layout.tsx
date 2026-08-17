import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../App'
import {
  LayoutDashboard, Users, Activity, FileText, BarChart3,
  Settings, LogOut, Search, ChevronDown, GitCompare,
  Brain, Menu, X, TrendingUp, Globe, Bot, Cpu,
  Play, Sparkles, Loader2, DollarSign,
} from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { api } from '../lib/api'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Overview' },
  { to: '/competitors', icon: Users, label: 'Competitors' },
  { to: '/competitors/compare', icon: GitCompare, label: 'Compare' },
  { to: '/pricing-intelligence', icon: DollarSign, label: 'Pricing Matrix' },
  { to: '/predictive-intelligence', icon: Sparkles, label: 'Predictive Suite' },
  { to: '/knowledge-graph', icon: Cpu, label: 'Knowledge Graph' },
  { to: '/geo-intelligence', icon: Globe, label: 'Geo Intelligence' },
  { to: '/risk-analysis', icon: TrendingUp, label: 'Risk Analysis' },
  { to: '/ai', icon: Brain, label: 'AI Insights' },
  { to: '/copilot', icon: Bot, label: 'AI Copilot' },
  { to: '/collections', icon: Activity, label: 'Collections' },
  { to: '/reports', icon: BarChart3, label: 'Reports' },
  { to: '/logs', icon: FileText, label: 'Logs' },
  { to: '/admin', icon: Settings, label: 'Administration' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<{ competitor_id: number; name: string; context: string }[] | null>(null)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('theme') === 'dark')
  const searchRef = useRef<HTMLDivElement>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [collecting, setCollecting] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [actionStatus, setActionStatus] = useState<string | null>(null)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
    localStorage.setItem('theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSearchResults(null)
    }
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) setSearchResults(null)
    }
    document.addEventListener('keydown', handleEscape)
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    try {
      const result = await api.search(searchQuery)
      setSearchResults(result.results || [])
    } catch {
      setSearchResults([])
    }
  }

  const handleCollectAll = async () => {
    setCollecting(true)
    setActionStatus('Collecting data...')
    try {
      const result = await api.getCompetitors({ enabled: true, page_size: 50 })
      const items = result.competitors || []
      const results = await Promise.allSettled(
        items.map(c => api.triggerCollection(c.id))
      )
      const ok = results.filter(r => r.status === 'fulfilled').length
      setActionStatus(`Collected ${ok}/${items.length}`)
    } catch {
      setActionStatus('Collection failed')
    }
    setCollecting(false)
    setTimeout(() => setActionStatus(null), 4000)
  }

  const handleGeneratePredictions = async () => {
    setGenerating(true)
    setActionStatus('Generating predictions...')
    try {
      await api.generatePredictions()
      setActionStatus('Predictions generated')
    } catch {
      setActionStatus('Generation failed')
    }
    setGenerating(false)
    setTimeout(() => setActionStatus(null), 4000)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="fixed top-3 left-3 z-50 p-2 bg-surface-900 text-white rounded-lg lg:hidden"
        aria-label="Toggle menu"
      >
        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      <aside className={`
        fixed lg:static inset-y-0 left-0 z-40 w-64 bg-surface-950 dark:bg-surface-950 border-r border-surface-800 flex flex-col transform transition-transform duration-200
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="p-5 border-b border-surface-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-brand-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">U</span>
            </div>
            <div>
              <h1 className="text-base font-bold text-white">Utservio</h1>
              <p className="text-xs text-surface-400">Intelligence Engine</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                isActive ? 'sidebar-link-active' : 'sidebar-link text-surface-400 hover:text-white hover:bg-surface-800'
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-surface-800">
          <button onClick={handleLogout} className="sidebar-link w-full text-red-400 hover:bg-surface-800 hover:text-red-300">
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden lg:ml-0">
        <header className="h-14 bg-white/80 dark:bg-surface-900/80 backdrop-blur-md border-b border-surface-200 dark:border-surface-800 flex items-center justify-between px-6 sticky top-0 z-30">
          <div className="flex items-center gap-4 flex-1">
            <div ref={searchRef} className="relative max-w-md w-full">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400" />
              <input
                type="text"
                placeholder="Search competitors, data..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="input pl-9"
              />
              {searchResults && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-lg shadow-lg z-50 max-h-80 overflow-auto">
                  {searchResults.length === 0 ? (
                    <div className="p-4 text-sm text-surface-500 text-center">No results found</div>
                  ) : (
                    searchResults.map((r, i) => (
                      <button
                        key={i}
                        onClick={() => {
                          navigate(`/competitors/${r.competitor_id}`)
                          setSearchResults(null)
                          setSearchQuery('')
                        }}
                        className="w-full px-4 py-3 text-left hover:bg-surface-50 border-b border-surface-100 last:border-0"
                      >
                        <div className="font-medium text-sm text-surface-900">{r.name}</div>
                        <div className="text-xs text-surface-500">{r.context}</div>
                      </button>
                    ))
                  )}
                  <button onClick={() => setSearchResults(null)} className="w-full px-4 py-2 text-xs text-surface-500 hover:bg-surface-50">
                    Close
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {actionStatus && (
              <span className="text-xs text-surface-500 dark:text-surface-400 mr-2">{actionStatus}</span>
            )}

            <button
              onClick={handleCollectAll}
              disabled={collecting || generating}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-surface-100 dark:bg-surface-800 hover:bg-surface-200 dark:hover:bg-surface-700 text-surface-700 dark:text-surface-300 rounded-lg disabled:opacity-50 transition-colors"
              title="Collect data from all enabled competitors"
            >
              {collecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              Collect All
            </button>

            <button
              onClick={handleGeneratePredictions}
              disabled={collecting || generating}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-brand-500 hover:bg-brand-600 text-white rounded-lg disabled:opacity-50 transition-colors"
              title="Generate AI predictions from collected data"
            >
              {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              Predict
            </button>

            <div className="w-px h-6 bg-surface-200 dark:bg-surface-700 mx-1" />

            <button
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 text-surface-400 hover:text-surface-700 dark:hover:text-surface-200"
              title={darkMode ? 'Light mode' : 'Dark mode'}
            >
              {darkMode ? '☀️' : '🌙'}
            </button>

            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 text-sm text-surface-700 hover:text-surface-900"
              >
                <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center text-brand-700 font-medium">
                  A
                </div>
                <ChevronDown size={14} />
              </button>
              {showUserMenu && (
                <div className="absolute right-0 top-full mt-1 w-48 bg-white dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-lg shadow-lg z-50">
                  <button
                    onClick={handleLogout}
                    className="w-full px-4 py-2.5 text-left text-sm text-red-600 hover:bg-red-50 rounded-lg"
                  >
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
