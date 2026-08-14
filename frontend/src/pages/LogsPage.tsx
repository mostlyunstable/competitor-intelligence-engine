import { useState, useCallback } from 'react'
import { usePolling } from '../hooks'
import { api } from '../lib/api'
import { formatDate } from '../lib/utils'
import { Filter, ChevronLeft, ChevronRight, RefreshCw, FileText } from 'lucide-react'
import type { CollectionLog } from '../types'
import { PageHeader, StatusBadge, EmptyState, LoadingState } from '../components/ui'

export default function LogsPage() {
  const [competitorId, setCompetitorId] = useState<number | undefined>()
  const [successFilter, setSuccessFilter] = useState<boolean | undefined>()
  const [page, setPage] = useState(1)

  const fetchData = useCallback(() => api.getLogs({
    competitor_id: competitorId,
    success: successFilter,
    page,
    page_size: 30,
  }), [competitorId, successFilter, page])

  const { data, loading, refresh } = usePolling(fetchData, 15000)
  const [refreshing, setRefreshing] = useState(false)

  const logs = data?.logs || []
  const totalPages = data?.total_pages || 1

  return (
    <div className="space-y-6">
      <PageHeader
        title="Execution & Audit Logs"
        description="Detailed collection history, HTTP request metrics, and extraction error logs."
        icon={FileText}
        actions={
          <button
            onClick={async () => { setRefreshing(true); try { await refresh() } catch { /* usePolling handles errors */ } finally { setRefreshing(false) } }}
            disabled={refreshing}
            className="btn-secondary disabled:opacity-50"
          >
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} /> Refresh
          </button>
        }
      />

      {/* Filters Bar */}
      <div className="card p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-surface-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-surface-500">Filter Logs:</span>
          </div>
          <input
            type="number"
            placeholder="Competitor ID"
            value={competitorId || ''}
            onChange={(e) => { setCompetitorId(e.target.value ? parseInt(e.target.value) : undefined); setPage(1) }}
            className="input w-36 py-2 text-xs"
          />
          <select
            value={successFilter === undefined ? '' : String(successFilter)}
            onChange={(e) => {
              const v = e.target.value
              setSuccessFilter(v === '' ? undefined : v === 'true')
              setPage(1)
            }}
            className="input w-auto py-2 text-xs cursor-pointer"
          >
            <option value="">All Statuses</option>
            <option value="true">Success Only</option>
            <option value="false">Failed Only</option>
          </select>
        </div>
      </div>

      {/* Logs Table */}
      <div className="card overflow-hidden">
        {loading && logs.length === 0 ? (
          <LoadingState type="table" rows={6} />
        ) : logs.length === 0 ? (
          <EmptyState title="No log records found" description="Try broadening your filter options." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-50 dark:bg-surface-800/80 border-b border-surface-200 dark:border-surface-700">
                <tr>
                  <th className="table-header">Status</th>
                  <th className="table-header">Competitor Target</th>
                  <th className="table-header">Start Time</th>
                  <th className="table-header">Duration</th>
                  <th className="table-header text-right">Records Extracted</th>
                  <th className="table-header">Errors / Warnings</th>
                  <th className="table-header text-center">Retries</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
                {logs.map((log: CollectionLog) => (
                  <tr key={log.id} className="hover:bg-surface-50 dark:hover:bg-surface-800/50 transition">
                    <td className="table-cell">
                      <StatusBadge status={log.success ? 'Success' : 'Failed'} />
                    </td>
                    <td className="table-cell font-bold text-surface-900 dark:text-white">{log.competitor_name || `Competitor #${log.competitor_id}`}</td>
                    <td className="table-cell font-mono text-xs text-surface-500">{formatDate(log.start_time)}</td>
                    <td className="table-cell font-mono text-xs text-surface-500">{log.duration_seconds ? `${log.duration_seconds.toFixed(1)}s` : '-'}</td>
                    <td className="table-cell text-right font-mono font-bold text-brand-600 dark:text-brand-400">{log.records_collected}</td>
                    <td className="table-cell">
                      {log.errors?.length > 0 ? (
                        <div className="text-xs text-red-600 dark:text-red-400 max-w-xs truncate font-mono" title={log.errors.join('\n')}>
                          {log.errors[0]}
                        </div>
                      ) : (
                        <span className="text-xs text-surface-400 font-mono">None</span>
                      )}
                    </td>
                    <td className="table-cell text-center font-mono text-xs text-surface-500">{log.retry_count || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="p-4 border-t border-surface-200 dark:border-surface-800 flex items-center justify-between">
            <span className="text-xs text-surface-500">Page {page} of {totalPages}</span>
            <div className="flex items-center gap-2">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="btn-secondary btn-sm disabled:opacity-50">
                <ChevronLeft size={14} /> Previous
              </button>
              <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="btn-secondary btn-sm disabled:opacity-50">
                Next <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
