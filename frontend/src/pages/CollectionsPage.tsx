import { useState, useCallback } from 'react'
import { useDashboard } from '../context/DashboardContext'
import { usePolling } from '../hooks'
import { api } from '../lib/api'
import { formatDate, timeAgo } from '../lib/utils'
import {
  Play, Pause, RefreshCw, Activity, Clock, CheckCircle,
  XCircle
} from 'lucide-react'
import type { CollectionLog } from '../types'

export default function CollectionsPage() {
  const [competitorFilter, setCompetitorFilter] = useState<number | undefined>()
  const [refreshing, setRefreshing] = useState(false)

  const { stats, scheduler, refresh } = useDashboard()

  const fetchData = useCallback(() => api.getLogs({
    competitor_id: competitorFilter,
    page_size: 30,
  }), [competitorFilter])

  const { data: logsData, loading, refresh: refreshLogs } = usePolling(fetchData, 10000)

  const logs = logsData?.logs || []

  const handlePauseScheduler = async () => {
    try {
      await api.pauseScheduler()
      refresh.scheduler()
    } catch { /* usePolling handles errors */ }
  }

  const handleResumeScheduler = async () => {
    try {
      await api.resumeScheduler()
      refresh.scheduler()
    } catch { /* usePolling handles errors */ }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-surface-900">Collection Monitoring</h1>
        <div className="flex items-center gap-2">
          {scheduler?.is_running ? (
            <button onClick={handlePauseScheduler} className="btn-secondary">
              <Pause size={16} /> Pause Scheduler
            </button>
          ) : (
            <button onClick={handleResumeScheduler} className="btn-primary">
              <Play size={16} /> Resume Scheduler
            </button>
          )}
          <button onClick={async () => { setRefreshing(true); try { await refresh.all() } catch { /* usePolling handles errors */ } finally { setRefreshing(false) } }} disabled={refreshing} className="btn-secondary disabled:opacity-50">
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="stat-card">
          <Activity size={18} className="text-brand-600" />
          <div className="text-xl font-bold">{stats?.collections_running || 0}</div>
          <div className="text-xs text-surface-500">Running Now</div>
        </div>
        <div className="stat-card">
          <Clock size={18} className="text-yellow-600" />
          <div className="text-xl font-bold">{stats?.queue_size || 0}</div>
          <div className="text-xs text-surface-500">Queued Jobs</div>
        </div>
        <div className="stat-card">
          <CheckCircle size={18} className="text-emerald-600" />
          <div className="text-xl font-bold">{stats?.successful_collections || 0}</div>
          <div className="text-xs text-surface-500">Successful</div>
        </div>
        <div className="stat-card">
          <XCircle size={18} className="text-red-600" />
          <div className="text-xl font-bold">{stats?.failed_collections || 0}</div>
          <div className="text-xs text-surface-500">Failed</div>
        </div>
      </div>

      {/* Scheduler Status */}
      <div className="card p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${scheduler?.is_running ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            <div>
              <h3 className="font-semibold text-surface-900">Scheduler</h3>
              <p className="text-sm text-surface-500">
                {scheduler?.is_running ? `Running (check every ${scheduler?.interval_seconds}s)` : 'Stopped'}
              </p>
            </div>
          </div>
          <div className="text-sm text-surface-500">
            Last collection: {stats?.last_collection ? timeAgo(stats.last_collection) : 'Never'}
          </div>
        </div>
      </div>

      {/* Collection Timeline */}
      <div className="card">
        <div className="px-5 py-4 border-b border-surface-100 flex items-center justify-between">
          <h2 className="font-semibold text-surface-900">Collection History</h2>
          <div className="flex items-center gap-2">
            <input
              type="number"
              placeholder="Competitor ID"
              value={competitorFilter || ''}
              onChange={(e) => setCompetitorFilter(e.target.value ? parseInt(e.target.value) : undefined)}
              className="input w-36"
            />
          </div>
        </div>
        <div className="divide-y divide-surface-50 max-h-[600px] overflow-auto">
          {loading && logs.length === 0 ? (
            [...Array(5)].map((_, i) => (
              <div key={i} className="p-4"><div className="skeleton h-16 w-full" /></div>
            ))
          ) : logs.length === 0 ? (
            <div className="p-8 text-center text-surface-400">No collection logs yet</div>
          ) : (
            logs.map((log: CollectionLog) => (
              <div key={log.id} className="px-5 py-4 flex items-center gap-4 hover:bg-surface-50">
                {log.success ? (
                  <CheckCircle size={20} className="text-emerald-500 flex-shrink-0" />
                ) : (
                  <XCircle size={20} className="text-red-500 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm text-surface-900">
                      {log.competitor_name || `Competitor #${log.competitor_id}`}
                    </span>
                    <span className={`badge ${log.success ? 'badge-success' : 'badge-danger'}`}>
                      {log.success ? 'Success' : 'Failed'}
                    </span>
                  </div>
                  <div className="text-xs text-surface-400 mt-1">
                    {formatDate(log.start_time)} &middot; {log.duration_seconds ? `${log.duration_seconds.toFixed(1)}s` : '-'} &middot; {log.records_collected} records
                  </div>
                  {log.errors?.length > 0 && (
                    <div className="mt-2 text-xs text-red-600 bg-red-50 rounded p-2">
                      {log.errors.slice(0, 2).join('; ')}
                    </div>
                  )}
                </div>
                <button
                  onClick={async () => { try { await api.triggerCollection(log.competitor_id); refreshLogs() } catch { /* errors shown by usePolling */ } }}
                  className="btn-secondary btn-sm"
                >
                  <RefreshCw size={12} /> Retry
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
