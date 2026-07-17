import { useState, useCallback, useRef } from 'react'
import { usePolling } from '../hooks'
import { useWebSocket } from '../hooks/useWebSocket'
import { api } from '../lib/api'
import { formatDate, timeAgo, formatDuration } from '../lib/utils'
import { BarChart } from '../components/Charts'
import {
  Users, Activity, CheckCircle, XCircle, TrendingUp, Clock,
  Database, Cpu, Zap, ArrowUpRight, AlertTriangle, Wifi, WifiOff, BarChart3,
  ExternalLink
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

interface LiveEvent {
  id: number
  type: string
  data: any
  timestamp: string
}

export default function OverviewPage() {
  const { data: stats, loading: statsLoading, refresh: refetchStats } = usePolling(() => api.getStats(), 15000)
  const { data: feedPage, refresh: refetchFeed } = usePolling(() => api.getFeed(20, 0), 20000)
  const { data: health } = usePolling(() => api.getHealth(), 30000)
  const { data: telemetry } = usePolling(() => api.getTelemetry(), 10000)
  const { data: trends } = usePolling(() => api.getTrends(14), 60000)
  const [liveEvents, setLiveEvents] = useState<LiveEvent[]>([])
  const eventIdRef = useRef(0)

  const feed = feedPage?.items || []

  const handleWsMessage = useCallback((msg: any) => {
    eventIdRef.current += 1
    const evt = { id: eventIdRef.current, ...msg }
    setLiveEvents(prev => [...prev.slice(-19), evt])
    if (msg.type === 'collection_completed' || msg.type === 'collection_failed') {
      refetchStats()
      refetchFeed()
    }
  }, [refetchStats, refetchFeed])

  const { connected } = useWebSocket({
    onMessage: handleWsMessage,
  })

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
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            {connected ? (
              <><Wifi size={14} className="text-emerald-500" /><span className="text-emerald-600">Live</span></>
            ) : (
              <><WifiOff size={14} className="text-red-500" /><span className="text-red-600">Disconnected</span></>
            )}
          </div>
          <div className="flex items-center gap-2 text-sm text-surface-500">
            <Clock size={14} />
            Last updated: {timeAgo(new Date().toISOString())}
          </div>
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
        <StatCard label="URLs Discovered" value={s.urls_discovered || 0} icon={Database} color="bg-orange-500" />
      </div>

      {/* Trends Charts */}
      {trends && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 size={18} className="text-brand-500" />
              <h3 className="font-semibold text-surface-900">Collections (Last 14 Days)</h3>
            </div>
            <BarChart
              data={(trends.daily_collections || []).map((d: any) => ({
                label: new Date(d.date).toLocaleDateString('en', { weekday: 'short' }),
                value: d.total,
                color: 'bg-brand-500',
              }))}
              height={120}
            />
          </div>
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 size={18} className="text-emerald-500" />
              <h3 className="font-semibold text-surface-900">Records Collected (Last 14 Days)</h3>
            </div>
            <BarChart
              data={(trends.daily_records || []).map((d: any) => ({
                label: new Date(d.date).toLocaleDateString('en', { weekday: 'short' }),
                value: d.records,
                color: 'bg-emerald-500',
              }))}
              height={120}
            />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Live Events */}
        <div className="lg:col-span-1 card">
          <div className="px-5 py-4 border-b border-surface-100 flex items-center justify-between">
            <h2 className="font-semibold text-surface-900">Live Events</h2>
            {liveEvents.length > 0 && (
              <span className="text-xs bg-brand-100 text-brand-700 px-2 py-0.5 rounded-full">
                {liveEvents.length}
              </span>
            )}
          </div>
          <div className="divide-y divide-surface-50 max-h-96 overflow-auto">
            {liveEvents.length === 0 ? (
              <div className="p-8 text-center text-surface-400 text-sm">
                Waiting for live events...
              </div>
            ) : (
              liveEvents.map((event) => (
                <div key={event.id} className="px-5 py-3 hover:bg-surface-50">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`inline-block w-2 h-2 rounded-full ${
                      event.type === 'collection_completed' ? 'bg-emerald-500' :
                      event.type === 'collection_failed' ? 'bg-red-500' :
                      event.type === 'collection_started' ? 'bg-blue-500' :
                      event.type === 'changes_detected' ? 'bg-amber-500' :
                      'bg-surface-400'
                    }`} />
                    <span className="text-xs font-medium text-surface-700">
                      {event.type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                  </div>
                  {event.type === 'collection_completed' && (
                    <p className="text-xs text-surface-600 ml-4">
                      {event.data.competitor_name} — {event.data.records_collected} records in {event.data.elapsed_seconds}s
                    </p>
                  )}
                  {event.type === 'collection_failed' && (
                    <p className="text-xs text-red-600 ml-4">
                      {event.data.competitor_name} — {event.data.error?.slice(0, 50)}
                    </p>
                  )}
                  {event.type === 'collection_started' && (
                    <p className="text-xs text-surface-600 ml-4">
                      {event.data.competitor_name}
                    </p>
                  )}
                  {event.type === 'changes_detected' && (
                    <p className="text-xs text-amber-600 ml-4">
                      {event.data.changes?.length || 0} changes found
                    </p>
                  )}
                  <p className="text-xs text-surface-400 ml-4 mt-0.5">{timeAgo(event.timestamp)}</p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="lg:col-span-1 card">
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
          {feed && feed.length > 0 && (
            <div className="border-t border-surface-100">
              <a
                href="/activity"
                target="_blank"
                rel="noopener noreferrer"
                className="w-full px-5 py-3 text-sm text-brand-600 hover:bg-surface-50 flex items-center justify-center gap-2"
              >
                View all activity <ExternalLink size={14} />
              </a>
            </div>
          )}
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
              <span className="text-sm text-surface-600">WebSocket</span>
              <div className="flex items-center gap-2">
                <StatusDot status={connected ? 'healthy' : 'stopped'} />
                <span className="text-sm font-medium text-surface-900">{connected ? 'connected' : 'disconnected'}</span>
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
