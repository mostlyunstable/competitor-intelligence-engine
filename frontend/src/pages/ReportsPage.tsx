import { useState, useCallback } from 'react'
import { usePolling } from '../hooks'
import { api } from '../lib/api'
import { BarChart3, Download, FileText, TrendingUp, FileDown, RefreshCw } from 'lucide-react'
import { PageHeader, MetricCard, StatusBadge, EmptyState, LoadingState } from '../components/ui'

export default function ReportsPage() {
  const { data: summary, loading, refresh } = usePolling(() => api.getSummary(), 30000)
  const [refreshing, setRefreshing] = useState(false)

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await refresh()
    } finally {
      setRefreshing(false)
    }
  }, [refresh])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Intelligence Reports & Exports"
        description="Comprehensive summary metrics, cross-competitor benchmarks, and data exports."
        icon={BarChart3}
        actions={
          <>
            <button onClick={handleRefresh} disabled={refreshing} className="btn-secondary disabled:opacity-50">
              <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} /> Refresh
            </button>
            <a href={api.getCompareCsvUrl()} className="btn-secondary" download>
              <Download size={16} /> Export CSV
            </a>
            <a href={api.getPdfExportUrl()} className="btn-secondary" download>
              <FileDown size={16} /> Export PDF
            </a>
            <a href={api.getExportZipUrl()} className="btn-primary" download>
              <Download size={16} /> Full ZIP Bundle
            </a>
          </>
        }
      />

      {/* Summary KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="Competitors Tracked" value={summary?.length || 0} icon={BarChart3} color="text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/30" />
        <MetricCard title="Total Services Extracted" value={summary?.reduce((sum: number, s: any) => sum + (s.services_count || 0), 0) || 0} icon={FileText} color="text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/30" />
        <MetricCard title="Total Pricing Records" value={summary?.reduce((sum: number, s: any) => sum + (s.pricing_count || 0), 0) || 0} icon={TrendingUp} color="text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30" />
      </div>

      {/* Competitor Summary Table */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-surface-200 dark:border-surface-800">
          <h2 className="font-bold text-surface-900 dark:text-white">Competitor Extraction Metrics Summary</h2>
        </div>
        {loading && !summary ? (
          <LoadingState type="table" rows={5} />
        ) : !summary || summary.length === 0 ? (
          <EmptyState title="No summary records available" description="Run collection pipelines to populate competitor records." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-50 dark:bg-surface-800/80 border-b border-surface-200 dark:border-surface-700">
                <tr>
                  <th className="table-header">Competitor Target</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Frequency</th>
                  <th className="table-header text-right">Services</th>
                  <th className="table-header text-right">Pricing</th>
                  <th className="table-header text-right">Content</th>
                  <th className="table-header text-right">Social</th>
                  <th className="table-header text-right">Total Extracted</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
                {summary.map((s: any) => {
                  const total = (s.services_count || 0) + (s.pricing_count || 0) + (s.content_count || 0) + (s.socials_count || 0)
                  return (
                    <tr key={s.id} className="hover:bg-surface-50 dark:hover:bg-surface-800/50 transition">
                      <td className="table-cell font-bold text-surface-900 dark:text-white">{s.name}</td>
                      <td className="table-cell">
                        <StatusBadge status={s.enabled ? 'Active' : 'Disabled'} />
                      </td>
                      <td className="table-cell font-mono text-xs text-surface-500 uppercase">{s.collection_frequency}</td>
                      <td className="table-cell text-right font-mono font-medium text-surface-700 dark:text-surface-300">{s.services_count}</td>
                      <td className="table-cell text-right font-mono font-medium text-surface-700 dark:text-surface-300">{s.pricing_count}</td>
                      <td className="table-cell text-right font-mono text-surface-500">{s.content_count}</td>
                      <td className="table-cell text-right font-mono text-surface-500">{s.socials_count}</td>
                      <td className="table-cell text-right font-mono font-bold text-brand-600 dark:text-brand-400">{total}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
