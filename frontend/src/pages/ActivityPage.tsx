import { useState, useEffect, useCallback } from 'react'
import { api } from '../lib/api'
import { timeAgo } from '../lib/utils'
import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react'

export default function ActivityPage() {
  const [items, setItems] = useState<any[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const pageSize = 30

  const loadPage = useCallback(async (p: number) => {
    setLoading(true)
    try {
      const offset = (p - 1) * pageSize
      const result = await api.getFeed(pageSize, offset)
      setItems(result.items)
      setTotal(result.total)
      setPage(p)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadPage(1) }, [loadPage])

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await loadPage(page)
    } finally {
      setRefreshing(false)
    }
  }, [loadPage, page])

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-surface-900">All Activity</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-surface-500">{total} total events</span>
          <button onClick={handleRefresh} disabled={refreshing} className="btn-secondary disabled:opacity-50">
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      <div className="card">
        <div className="divide-y divide-surface-50">
          {loading && items.length === 0 ? (
            <div className="p-8 text-center text-surface-400 text-sm">Loading...</div>
          ) : items.length === 0 ? (
            <div className="p-8 text-center text-surface-400 text-sm">No activity yet</div>
          ) : (
            items.map((item: any, i: number) => (
              <div key={i} className="px-5 py-3 flex items-start gap-3 hover:bg-surface-50">
                <div className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${
                  item.type === 'collection_success' ? 'bg-emerald-500' :
                  item.type === 'collection_failure' ? 'bg-red-500' : 'bg-brand-500'
                }`} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-surface-900">{item.message}</p>
                  <p className="text-xs text-surface-400">{timeAgo(item.timestamp)}</p>
                </div>
                {item.duration_seconds != null && (
                  <span className="text-xs text-surface-400">{item.duration_seconds}s</span>
                )}
              </div>
            ))
          )}
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-surface-100">
            <span className="text-sm text-surface-500">
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => loadPage(page - 1)}
                disabled={page <= 1 || loading}
                className="px-3 py-1.5 text-sm rounded-lg border border-surface-200 text-surface-700 hover:bg-surface-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
              >
                <ChevronLeft size={14} /> Prev
              </button>
              <button
                onClick={() => loadPage(page + 1)}
                disabled={page >= totalPages || loading}
                className="px-3 py-1.5 text-sm rounded-lg border border-surface-200 text-surface-700 hover:bg-surface-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
