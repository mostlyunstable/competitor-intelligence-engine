import { usePolling } from '../hooks'
import { api } from '../lib/api'
import { formatDate } from '../lib/utils'
import { BarChart3, Download, FileText, TrendingUp } from 'lucide-react'

export default function ReportsPage() {
  const { data: summary, loading } = usePolling(() => api.getSummary(), 30000)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <div className="flex items-center gap-2">
          <a href={api.getCompareCsvUrl()} className="btn-secondary" download>
            <Download size={16} /> Export CSV
          </a>
          <a href={api.getExportZipUrl()} className="btn-primary" download>
            <Download size={16} /> Export ZIP
          </a>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="stat-card">
          <BarChart3 size={18} className="text-brand-600" />
          <div className="text-xl font-bold">{summary?.length || 0}</div>
          <div className="text-xs text-gray-500">Competitors Tracked</div>
        </div>
        <div className="stat-card">
          <FileText size={18} className="text-purple-600" />
          <div className="text-xl font-bold">
            {summary?.reduce((sum: number, s: any) => sum + (s.services_count || 0), 0) || 0}
          </div>
          <div className="text-xs text-gray-500">Total Services</div>
        </div>
        <div className="stat-card">
          <TrendingUp size={18} className="text-green-600" />
          <div className="text-xl font-bold">
            {summary?.reduce((sum: number, s: any) => sum + (s.pricing_count || 0), 0) || 0}
          </div>
          <div className="text-xs text-gray-500">Total Pricing Records</div>
        </div>
      </div>

      {/* Competitor Comparison Table */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Competitor Comparison</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="table-header">Competitor</th>
                <th className="table-header">Status</th>
                <th className="table-header">Frequency</th>
                <th className="table-header text-right">Services</th>
                <th className="table-header text-right">Pricing</th>
                <th className="table-header text-right">Content</th>
                <th className="table-header text-right">Social</th>
                <th className="table-header text-right">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i}><td colSpan={8} className="p-4"><div className="skeleton h-10 w-full" /></td></tr>
                ))
              ) : !summary || summary.length === 0 ? (
                <tr><td colSpan={8} className="p-8 text-center text-gray-400">No data available</td></tr>
              ) : (
                summary.map((s: any) => {
                  const total = (s.services_count || 0) + (s.pricing_count || 0) + (s.content_count || 0) + (s.socials_count || 0)
                  return (
                    <tr key={s.id} className="hover:bg-gray-50">
                      <td className="table-cell font-medium">{s.name}</td>
                      <td className="table-cell">
                        {s.enabled ? <span className="badge-success">Active</span> : <span className="badge-danger">Disabled</span>}
                      </td>
                      <td className="table-cell"><span className="badge-neutral">{s.collection_frequency}</span></td>
                      <td className="table-cell text-right">{s.services_count}</td>
                      <td className="table-cell text-right">{s.pricing_count}</td>
                      <td className="table-cell text-right">{s.content_count}</td>
                      <td className="table-cell text-right">{s.socials_count}</td>
                      <td className="table-cell text-right font-semibold">{total}</td>
                    </tr>
                  )
                })
              )}
            </tbody>
            {summary && summary.length > 0 && (
              <tfoot className="bg-gray-50 border-t border-gray-200">
                <tr>
                  <td className="table-cell font-semibold">Totals</td>
                  <td className="table-cell"></td>
                  <td className="table-cell"></td>
                  <td className="table-cell text-right font-semibold">{summary.reduce((s: number, r: any) => s + (r.services_count || 0), 0)}</td>
                  <td className="table-cell text-right font-semibold">{summary.reduce((s: number, r: any) => s + (r.pricing_count || 0), 0)}</td>
                  <td className="table-cell text-right font-semibold">{summary.reduce((s: number, r: any) => s + (r.content_count || 0), 0)}</td>
                  <td className="table-cell text-right font-semibold">{summary.reduce((s: number, r: any) => s + (r.socials_count || 0), 0)}</td>
                  <td className="table-cell text-right font-bold">{summary.reduce((s: number, r: any) => s + (r.services_count || 0) + (r.pricing_count || 0) + (r.content_count || 0) + (r.socials_count || 0), 0)}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>
    </div>
  )
}
