import { useState, useCallback } from 'react'
import { useDashboard } from '../context/DashboardContext'
import { usePolling } from '../hooks'
import { api } from '../lib/api'
import { formatDate, timeAgo } from '../lib/utils'
import {
  Play, Pause, RefreshCw, Activity, Clock, CheckCircle,
  XCircle, Filter
} from 'lucide-react'
import type { CollectionLog } from '../types'
import { PageHeader, MetricCard, StatusBadge, EmptyState, LoadingState } from '../components/ui'

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
      <PageHeader
        title="Collection Pipeline & Scheduler"
        description="Monitor active web scraping extractions, background jobs, and scheduler status."
        icon={Activity}
        actions={
          <>
            {scheduler?.is_running ? (
              <button onClick={handlePauseScheduler} className="btn-secondary">
                <Pause size={16} /> Pause Scheduler
              </button>
            ) : (
              <button onClick={handleResumeScheduler} className="btn-primary">
                <Play size={16} /> Resume Scheduler
              </button>
            )}
            <button
              onClick={async () => { setRefreshing(true); try { await refresh.all() } catch { /* usePolling handles errors */ } finally { setRefreshing(false) } }}
              disabled={refreshing}
              className="btn-secondary disabled:opacity-50"
            >
              <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} /> Refresh
            </button>
          </>
        }
      />

      {/* Status KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard title="Running Now" value={stats?.collections_running || 0} icon={Activity} color="text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30" />
        <MetricCard title="Queued Jobs" value={stats?.queue_size || 0} icon={Clock} color="text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30" />
        <MetricCard title="Successful Collections" value={stats?.successful_collections || 0} icon={CheckCircle} color="text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30" />
        <MetricCard title="Failed Extractions" value={stats?.failed_collections || 0} icon={XCircle} color="text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30" />
      </div>

      {/* Scheduler Status Container */}
      <div className="card p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${scheduler?.is_running ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            <div>
              <h3 className="font-bold text-surface-900 dark:text-white">Scheduler Pipeline</h3>
              <p className="text-sm text-surface-500 dark:text-surface-400">
                {scheduler?.is_running ? `Running (polling interval every ${scheduler?.interval_seconds}s)` : 'Scheduler Paused'}
              </p>
            </div>
          </div>
          <div className="text-xs text-surface-500 font-medium">
            Last collection trigger: {stats?.last_collection ? timeAgo(stats.last_collection) : 'Never'}
          </div>
        </div>
      </div>

      {/* Active Collection Logs */}
      <div className="card">
        <div className="px-5 py-4 border-b border-surface-200 dark:border-surface-800 flex items-center justify-between">
          <h2 className="font-bold text-surface-900 dark:text-white">Active Collection Logs</h2>
          <span className="text-xs text-surface-500">Auto-refreshing every 10s</span>
        </div>

        {loading && logs.length === 0 ? (
          <LoadingState type="table" rows={5} />
        ) : logs.length === 0 ? (
          <EmptyState title="No collection logs recorded" description="Trigger a collection from Competitors tab to initiate jobs." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-50 dark:bg-surface-800/80 border-b border-surface-200 dark:border-surface-700">
                <tr>
                  <th className="table-header">Competitor Target</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Started At</th>
                  <th className="table-header">Duration</th>
                  <th className="table-header text-right">Items Extracted</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
                {logs.map((log: CollectionLog) => (
                  <tr key={log.id} className="hover:bg-surface-50 dark:hover:bg-surface-800/50 transition">
                    <td className="table-cell font-bold text-surface-900 dark:text-white">{log.competitor_name || `Competitor #${log.competitor_id}`}</td>
                    <td className="table-cell">
                      <StatusBadge status={log.success ? 'Success' : 'Failed'} />
                    </td>
                    <td className="table-cell font-mono text-xs text-surface-500">{formatDate(log.start_time)}</td>
                    <td className="table-cell font-mono text-xs text-surface-500">{log.duration_seconds ? `${log.duration_seconds.toFixed(2)}s` : 'N/A'}</td>
                    <td className="table-cell text-right font-mono font-bold text-brand-600 dark:text-brand-400">{log.records_collected || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
