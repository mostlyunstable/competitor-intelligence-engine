import { useState, useCallback } from 'react'
import { useDashboard } from '../context/DashboardContext'
import { usePolling } from '../hooks'
import { api } from '../lib/api'
import { formatDate, timeAgo } from '../lib/utils'
import {
  Users, Activity, CheckCircle, XCircle, TrendingUp, Clock,
  Database, Zap, RefreshCw, ExternalLink, LayoutDashboard
} from 'lucide-react'
import type { FeedItem } from '../types'
import { PageHeader, MetricCard, StatusBadge, EmptyState, LoadingState } from '../components/ui'

export default function OverviewPage() {
  const { stats, health, telemetry, loading, refresh } = useDashboard()
  const { data: feedPage, refresh: refetchFeed } = usePolling(() => api.getFeed(20, 0), 20000)

  const [refreshing, setRefreshing] = useState(false)
  const feed = feedPage?.items || []

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await Promise.all([refresh.stats(), refetchFeed(), refresh.health()])
    } catch { /* usePolling handles errors */ }
    finally {
      setRefreshing(false)
    }
  }, [refresh, refetchFeed])

  if (loading.stats && !stats) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Dashboard Overview"
          description="Real-time monitoring and competitive intelligence metrics."
          icon={LayoutDashboard}
        />
        <LoadingState rows={8} />
      </div>
    )
  }

  const s = stats as typeof stats | null

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard Overview"
        description="Real-time database records, competitor tracking status, and telemetry."
        icon={LayoutDashboard}
        actions={
          <>
            <div className="flex items-center gap-2 text-xs text-surface-500 font-medium">
              <Clock className="w-3.5 h-3.5" />
              Updated {timeAgo(new Date().toISOString())}
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="btn-secondary"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </>
        }
      />

      {/* KPI Cards Grid */}
      <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 transition-opacity duration-200 ${refreshing ? 'opacity-60' : ''}`}>
        <MetricCard title="Total Competitors" value={s?.total_competitors || 0} icon={Users} color="text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/30" />
        <MetricCard title="Active Competitors" value={s?.active_competitors || 0} icon={Users} color="text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30" />
        <MetricCard title="Collections Running" value={s?.collections_running || 0} icon={Activity} color="text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30" />
        <MetricCard title="Success Rate" value={`${s?.success_rate || 0}%`} icon={TrendingUp} color="text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30" />
        <MetricCard title="Successful Collections" value={s?.successful_collections || 0} icon={CheckCircle} color="text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30" />
        <MetricCard title="Failed Collections" value={s?.failed_collections || 0} icon={XCircle} color="text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30" />
        <MetricCard title="Services Extracted" value={s?.services_extracted || 0} icon={Zap} color="text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/30" />
        <MetricCard title="URLs Discovered" value={s?.urls_discovered || 0} icon={Database} color="text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="card">
          <div className="px-5 py-4 border-b border-surface-200 dark:border-surface-800">
            <h2 className="font-bold text-surface-900 dark:text-white">Recent Activity</h2>
          </div>
          <div className="divide-y divide-surface-100 dark:divide-surface-800 max-h-96 overflow-auto">
            {!feed || feed.length === 0 ? (
              <EmptyState title="No recent activity" description="Collection events will appear here." />
            ) : (
              feed.map((item: FeedItem, i) => (
                <div key={i} className="px-5 py-3 flex items-start gap-3 hover:bg-surface-50 dark:hover:bg-surface-800/50 transition">
                  <div className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${
                    item.type === 'collection_success' ? 'bg-emerald-500' :
                    item.type === 'collection_failure' ? 'bg-red-500' : 'bg-brand-500'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-surface-900 dark:text-surface-100 truncate">{item.message}</p>
                    <p className="text-xs text-surface-500 dark:text-surface-400">{timeAgo(item.timestamp)}</p>
                  </div>
                </div>
              ))
            )}
          </div>
          {feed && feed.length > 0 && (
            <div className="border-t border-surface-200 dark:border-surface-800">
              <a
                href="/activity"
                target="_blank"
                rel="noopener noreferrer"
                className="w-full px-5 py-3 text-sm font-semibold text-brand-600 dark:text-brand-400 hover:bg-surface-50 dark:hover:bg-surface-800 flex items-center justify-center gap-2 transition"
              >
                View all activity <ExternalLink size={14} />
              </a>
            </div>
          )}
        </div>

        {/* System Status */}
        <div className="card">
          <div className="px-5 py-4 border-b border-surface-200 dark:border-surface-800">
            <h2 className="font-bold text-surface-900 dark:text-white">System Status</h2>
          </div>
          <div className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-surface-600 dark:text-surface-400">Scheduler</span>
              <StatusBadge status={s?.scheduler_status || 'unknown'} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-surface-600 dark:text-surface-400">Database</span>
              <StatusBadge status={health?.checks?.database?.status || 'checking...'} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-surface-600 dark:text-surface-400">Queue</span>
              <StatusBadge status={`${s?.queue_size || 0} pending`} variant="neutral" />
            </div>

            <div className="pt-3 border-t border-surface-200 dark:border-surface-800">
              <h3 className="text-xs font-bold uppercase tracking-wider text-surface-500 dark:text-surface-400 mb-3">Resources</h3>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-xs font-semibold text-surface-600 dark:text-surface-400 mb-1">
                    <span>CPU Usage</span>
                    <span>{telemetry?.cpu_percent || 0}%</span>
                  </div>
                  <div className="h-2 bg-surface-100 dark:bg-surface-800 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-600 rounded-full transition-all duration-300" style={{ width: `${telemetry?.cpu_percent || 0}%` }} />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs font-semibold text-surface-600 dark:text-surface-400 mb-1">
                    <span>Memory Allocation</span>
                    <span>{telemetry?.memory_mb || 0} MB</span>
                  </div>
                  <div className="h-2 bg-surface-100 dark:bg-surface-800 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-600 rounded-full transition-all duration-300" style={{
                      width: `${telemetry?.memory_total_gb ? (telemetry.memory_mb / (telemetry.memory_total_gb * 1024)) * 100 : 0}%`
                    }} />
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-surface-200 dark:border-surface-800">
              <h3 className="text-xs font-bold uppercase tracking-wider text-surface-500 dark:text-surface-400 mb-1">Last Collection</h3>
              <p className="text-sm font-medium text-surface-900 dark:text-surface-200">{formatDate(s?.last_collection ?? null)}</p>
            </div>

            <div className="pt-3 border-t border-surface-200 dark:border-surface-800">
              <a
                href="/logs"
                target="_blank"
                rel="noopener noreferrer"
                className="w-full btn-secondary py-2 text-xs font-semibold justify-center"
              >
                View system logs <ExternalLink size={14} />
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
