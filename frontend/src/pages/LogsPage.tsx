import { useState, useCallback } from 'react'
import { usePolling } from '../hooks'
import { api } from '../lib/api'
import { formatDate } from '../lib/utils'
import { FileText, Filter, Download, ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react'

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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-surface-900">Collection Logs</h1>
        <button onClick={async () => { setRefreshing(true); try { await refresh() } finally { setRefreshing(false) } }} disabled={refreshing} className="btn-secondary disabled:opacity-50"><RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} /> Refresh</button>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-surface-400" />
            <span className="text-sm text-surface-500">Filters:</span>
          </div>
          <input
            type="number"
            placeholder="Competitor ID"
            value={competitorId || ''}
            onChange={(e) => { setCompetitorId(e.target.value ? parseInt(e.target.value) : undefined); setPage(1) }}
            className="input w-36"
          />
          <select
            value={successFilter === undefined ? '' : String(successFilter)}
            onChange={(e) => {
              const v = e.target.value
              setSuccessFilter(v === '' ? undefined : v === 'true')
              setPage(1)
            }}
            className="input w-auto"
          >
            <option value="">All Status</option>
            <option value="true">Success Only</option>
            <option value="false">Failed Only</option>
          </select>
        </div>
      </div>

      {/* Logs Table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="bg-surface-50 border-b border-surface-200">
            <tr>
              <th className="table-header">Status</th>
              <th className="table-header">Competitor</th>
              <th className="table-header">Start Time</th>
              <th className="table-header">Duration</th>
              <th className="table-header">Records</th>
              <th className="table-header">Errors</th>
              <th className="table-header">Retries</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-50">
            {loading && logs.length === 0 ? (
              [...Array(5)].map((_, i) => (
                <tr key={i}><td colSpan={7} className="p-4"><div className="skeleton h-10 w-full" /></td></tr>
              ))
            ) : logs.length === 0 ? (
              <tr><td colSpan={7} className="p-8 text-center text-surface-400">No logs found</td></tr>
            ) : (
              logs.map((log: any) => (
                <tr key={log.id} className="hover:bg-surface-50">
                  <td className="table-cell">
                    {log.success ? (
                      <span className="badge-success">Success</span>
                    ) : (
                      <span className="badge-danger">Failed</span>
                    )}
                  </td>
                  <td className="table-cell font-medium">{log.competitor_name || `#${log.competitor_id}`}</td>
                  <td className="table-cell text-surface-500 text-xs">{formatDate(log.start_time)}</td>
                  <td className="table-cell text-surface-500">{log.duration_seconds ? `${log.duration_seconds.toFixed(1)}s` : '-'}</td>
                  <td className="table-cell">{log.records_collected}</td>
                  <td className="table-cell">
                    {log.errors?.length > 0 ? (
                      <div className="text-xs text-red-600 max-w-xs truncate" title={log.errors.join('\n')}>
                        {log.errors.length} error(s)
                      </div>
                    ) : '-'}
                  </td>
                  <td className="table-cell">{log.retry_count}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        <div className="px-4 py-3 border-t border-surface-100 flex items-center justify-between">
          <span className="text-sm text-surface-500">
            Page {page} of {totalPages} ({data?.total || 0} total)
          </span>
          <div className="flex items-center gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1} className="btn-secondary btn-sm">
              <ChevronLeft size={14} /> Prev
            </button>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="btn-secondary btn-sm">
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
