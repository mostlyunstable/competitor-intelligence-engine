import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../App'
import {
  LayoutDashboard, Users, Activity, FileText, BarChart3,
  Settings, LogOut, Search, Bell, ChevronDown, GitCompare,
  Brain, Menu, X
} from 'lucide-react'
import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../lib/api'
import { useWebSocket } from '../hooks/useWebSocket'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Overview' },
  { to: '/competitors', icon: Users, label: 'Competitors' },
  { to: '/competitors/compare', icon: GitCompare, label: 'Compare' },
  { to: '/collections', icon: Activity, label: 'Collections' },
  { to: '/logs', icon: FileText, label: 'Logs' },
  { to: '/reports', icon: BarChart3, label: 'Reports' },
  { to: '/ai', icon: Brain, label: 'AI Insights' },
  { to: '/admin', icon: Settings, label: 'Administration' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[] | null>(null)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [notifications, setNotifications] = useState<{ type: string; message: string; time: string }[]>([])
  const [showNotifications, setShowNotifications] = useState(false)
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('theme') === 'dark')
  const searchRef = useRef<HTMLDivElement>(null)
  const notifRef = useRef<HTMLDivElement>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Dark mode toggle
  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
    localStorage.setItem('theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  // WebSocket for real-time notifications
  const { connected } = useWebSocket({
    onCollectionCompleted: useCallback((data: { competitor_name: string; records_collected: number }) => {
      setNotifications(prev => [{
        type: 'success',
        message: `Collection completed: ${data.competitor_name} (${data.records_collected} records)`,
        time: new Date().toISOString(),
      }, ...prev].slice(0, 20))
    }, []),
    onCollectionFailed: useCallback((data: { competitor_name: string; error: string }) => {
      setNotifications(prev => [{
        type: 'error',
        message: `Collection failed: ${data.competitor_name} — ${data.error}`,
        time: new Date().toISOString(),
      }, ...prev].slice(0, 20))
    }, []),
    onChangesDetected: useCallback((data: { competitor_id: number }) => {
      setNotifications(prev => [{
        type: 'info',
        message: `Changes detected for competitor #${data.competitor_id}`,
        time: new Date().toISOString(),
      }, ...prev].slice(0, 20))
    }, []),
  })

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setSearchResults(null); setShowNotifications(false) }
    }
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) setSearchResults(null)
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setShowNotifications(false)
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

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Mobile hamburger */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="fixed top-3 left-3 z-50 p-2 bg-surface-900 text-white rounded-lg lg:hidden"
        aria-label="Toggle menu"
      >
        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
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

        <nav className="flex-1 p-3 space-y-1">
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

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden lg:ml-0">
        {/* Top bar */}
        <header className="h-14 bg-white dark:bg-surface-900 border-b border-surface-200 dark:border-surface-800 flex items-center justify-between px-6">
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
                  <button
                    onClick={() => setSearchResults(null)}
                    className="w-full px-4 py-2 text-xs text-surface-500 hover:bg-surface-50"
                  >
                    Close
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} title={connected ? 'Connected' : 'Disconnected'} />

            <button
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 text-surface-400 hover:text-surface-700 dark:hover:text-surface-200"
              title={darkMode ? 'Light mode' : 'Dark mode'}
            >
              {darkMode ? '☀️' : '🌙'}
            </button>

            <div ref={notifRef} className="relative">
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative p-2 text-surface-400 hover:text-surface-700 dark:hover:text-surface-200"
              >
                <Bell size={18} />
                {notifications.length > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] rounded-full flex items-center justify-center">
                    {notifications.length > 9 ? '9+' : notifications.length}
                  </span>
                )}
              </button>
              {showNotifications && (
                <div className="absolute right-0 top-full mt-1 w-80 bg-white dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-lg shadow-lg z-50 max-h-96 overflow-auto">
                  <div className="p-3 border-b border-surface-200 dark:border-surface-700 flex items-center justify-between">
                    <span className="text-sm font-medium text-surface-900 dark:text-white">Notifications</span>
                    {notifications.length > 0 && (
                      <button onClick={() => setNotifications([])} className="text-xs text-surface-400 hover:text-surface-600">Clear all</button>
                    )}
                  </div>
                  {notifications.length === 0 ? (
                    <div className="p-4 text-sm text-surface-500 text-center">No notifications</div>
                  ) : (
                    notifications.map((n, i) => (
                      <div key={i} className="px-3 py-2.5 border-b border-surface-100 dark:border-surface-800 last:border-0">
                        <div className={`text-xs font-medium ${n.type === 'error' ? 'text-red-600' : n.type === 'success' ? 'text-green-600' : 'text-blue-600'}`}>
                          {n.type === 'error' ? 'Error' : n.type === 'success' ? 'Success' : 'Info'}
                        </div>
                        <div className="text-sm text-surface-700 dark:text-surface-300 mt-0.5">{n.message}</div>
                        <div className="text-[10px] text-surface-400 mt-1">{new Date(n.time).toLocaleTimeString()}</div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

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

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
