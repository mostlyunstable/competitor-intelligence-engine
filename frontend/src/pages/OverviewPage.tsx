import { usePolling } from '../hooks'
import { api } from '../lib/api'
import { formatDate, timeAgo, formatDuration } from '../lib/utils'
import {
  Users, Activity, CheckCircle, XCircle, TrendingUp, Clock,
  Database, Cpu, Zap, ArrowUpRight, AlertTriangle
} from 'lucide-react'

function StatCard({ label, value, icon: Icon, color, sub }: {
  label: string; value: string | number; icon: any; color: string; sub?: string
}) {
  return (
    <div className="stat-card">
      <div className="flex items-center justify-between">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
          <Icon size={20} className="text-white" />
        </div>
        {sub && <span className="text-xs text-surface-400">{sub}</span>}
      </div>
      <div className="text-2xl font-bold text-surface-900">{value}</div>
      <div className="text-sm text-surface-500">{label}</div>
    </div>
  )
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    healthy: 'bg-emerald-500', running: 'bg-emerald-500', connected: 'bg-emerald-500',
    degraded: 'bg-amber-500', stopped: 'bg-red-500', unhealthy: 'bg-red-500',
  }
  return <span className={`inline-block w-2 h-2 rounded-full ${colors[status] || 'bg-surface-400'}`} />
}

export default function OverviewPage() {
  const { data: stats, loading: statsLoading } = usePolling(() => api.getStats(), 15000)
  const { data: feed } = usePolling(() => api.getFeed(15), 20000)
  const { data: health } = usePolling(() => api.getHealth(), 30000)
  const { data: telemetry } = usePolling(() => api.getTelemetry(), 10000)

  if (statsLoading && !stats) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-surface-900">Dashboard Overview</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="card p-5"><div className="skeleton h-20 w-full" /></div>
          ))}
        </div>
      </div>
    )
  }

  const s = stats || {}

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-surface-900">Dashboard Overview</h1>
        <div className="flex items-center gap-2 text-sm text-surface-500">
          <Clock size={14} />
          Last updated: {timeAgo(new Date().toISOString())}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Competitors" value={s.total_competitors || 0} icon={Users} color="bg-brand-600" />
        <StatCard label="Active Competitors" value={s.active_competitors || 0} icon={Users} color="bg-green-600" />
        <StatCard label="Collections Running" value={s.collections_running || 0} icon={Activity} color="bg-blue-600" />
        <StatCard label="Success Rate" value={`${s.success_rate || 0}%`} icon={TrendingUp} color="bg-emerald-600" />
        <StatCard label="Successful Collections" value={s.successful_collections || 0} icon={CheckCircle} color="bg-green-500" />
        <StatCard label="Failed Collections" value={s.failed_collections || 0} icon={XCircle} color="bg-red-500" />
        <StatCard label="Services Extracted" value={s.services_extracted || 0} icon={Zap} color="bg-purple-600" />
        <StatCard label="Pages Crawled" value={s.pages_crawled || 0} icon={Database} color="bg-orange-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activity */}
        <div className="lg:col-span-2 card">
          <div className="px-5 py-4 border-b border-surface-100">
            <h2 className="font-semibold text-surface-900">Recent Activity</h2>
          </div>
          <div className="divide-y divide-surface-50 max-h-96 overflow-auto">
            {!feed || feed.length === 0 ? (
              <div className="p-8 text-center text-surface-400 text-sm">No recent activity</div>
            ) : (
              feed.map((item: any, i: number) => (
                <div key={i} className="px-5 py-3 flex items-start gap-3 hover:bg-surface-50">
                  <div className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${
                    item.type === 'collection_success' ? 'bg-emerald-500' :
                    item.type === 'collection_failure' ? 'bg-red-500' : 'bg-brand-500'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-surface-900 truncate">{item.message}</p>
                    <p className="text-xs text-surface-400">{timeAgo(item.timestamp)}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* System Status */}
        <div className="card">
          <div className="px-5 py-4 border-b border-surface-100">
            <h2 className="font-semibold text-surface-900">System Status</h2>
          </div>
          <div className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-surface-600">Scheduler</span>
              <div className="flex items-center gap-2">
                <StatusDot status={s.scheduler_status === 'running' ? 'healthy' : 'stopped'} />
                <span className="text-sm font-medium text-surface-900">{s.scheduler_status || 'unknown'}</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-surface-600">Database</span>
              <div className="flex items-center gap-2">
                <StatusDot status={health?.checks?.database?.status || 'unknown'} />
                <span className="text-sm font-medium text-surface-900">{health?.checks?.database?.status || 'checking...'}</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-surface-600">API</span>
              <div className="flex items-center gap-2">
                <StatusDot status="healthy" />
                <span className="text-sm font-medium text-surface-900">healthy</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-surface-600">Queue</span>
              <div className="flex items-center gap-2">
                <StatusDot status="healthy" />
                <span className="text-sm font-medium text-surface-900">{s.queue_size || 0} pending</span>
              </div>
            </div>

            <div className="pt-3 border-t border-surface-100">
              <h3 className="text-sm font-medium text-surface-900 mb-3">Resources</h3>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-xs text-surface-500 mb-1">
                    <span>CPU</span>
                    <span>{telemetry?.cpu_percent || 0}%</span>
                  </div>
                  <div className="h-1.5 bg-surface-100 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-500 rounded-full" style={{ width: `${telemetry?.cpu_percent || 0}%` }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs text-surface-500 mb-1">
                    <span>Memory</span>
                    <span>{telemetry?.memory_mb || 0} MB</span>
                  </div>
                  <div className="h-1.5 bg-surface-100 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full" style={{
                      width: `${telemetry?.memory_total_gb ? (telemetry.memory_mb / (telemetry.memory_total_gb * 1024)) * 100 : 0}%`
                    }} />
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-surface-100">
              <h3 className="text-sm font-medium text-surface-900 mb-2">Last Collection</h3>
              <p className="text-sm text-surface-600">{formatDate(s.last_collection)}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
