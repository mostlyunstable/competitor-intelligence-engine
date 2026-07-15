import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../App'
import {
  LayoutDashboard, Users, Activity, FileText, BarChart3,
  Settings, LogOut, Search, Bell, ChevronDown
} from 'lucide-react'
import { useState } from 'react'
import { api } from '../lib/api'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Overview' },
  { to: '/competitors', icon: Users, label: 'Competitors' },
  { to: '/collections', icon: Activity, label: 'Collections' },
  { to: '/logs', icon: FileText, label: 'Logs' },
  { to: '/reports', icon: BarChart3, label: 'Reports' },
  { to: '/admin', icon: Settings, label: 'Administration' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[] | null>(null)
  const [showUserMenu, setShowUserMenu] = useState(false)

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
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-5 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-brand-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">U</span>
            </div>
            <div>
              <h1 className="text-base font-bold text-gray-900">Utservio</h1>
              <p className="text-xs text-gray-500">Intelligence Engine</p>
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
                isActive ? 'sidebar-link-active' : 'sidebar-link'
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-gray-200">
          <button onClick={handleLogout} className="sidebar-link w-full text-red-600 hover:bg-red-50">
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6">
          <div className="flex items-center gap-4 flex-1">
            <div className="relative max-w-md w-full">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search competitors, data..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="input pl-9"
              />
              {searchResults && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-80 overflow-auto">
                  {searchResults.length === 0 ? (
                    <div className="p-4 text-sm text-gray-500 text-center">No results found</div>
                  ) : (
                    searchResults.map((r, i) => (
                      <button
                        key={i}
                        onClick={() => {
                          navigate(`/competitors/${r.competitor_id}`)
                          setSearchResults(null)
                          setSearchQuery('')
                        }}
                        className="w-full px-4 py-3 text-left hover:bg-gray-50 border-b border-gray-100 last:border-0"
                      >
                        <div className="font-medium text-sm text-gray-900">{r.name}</div>
                        <div className="text-xs text-gray-500">{r.context}</div>
                      </button>
                    ))
                  )}
                  <button
                    onClick={() => setSearchResults(null)}
                    className="w-full px-4 py-2 text-xs text-gray-500 hover:bg-gray-50"
                  >
                    Close
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button className="relative p-2 text-gray-500 hover:text-gray-700">
              <Bell size={18} />
            </button>
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900"
              >
                <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center text-brand-700 font-medium">
                  A
                </div>
                <ChevronDown size={14} />
              </button>
              {showUserMenu && (
                <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
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
