import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import type { DataQualityReport } from '../types'
import { CheckCircle, AlertTriangle, XCircle, RefreshCw } from 'lucide-react'

export default function DataQualityPage() {
  const [data, setData] = useState<DataQualityReport[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      setData(await api.getDataQualityAll())
    } catch { /* ignore */ }
    setLoading(false)
  }

  const qualityColor = (q: string) => {
    if (q === 'excellent') return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
    if (q === 'good') return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
    if (q === 'fair') return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
    return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
  }

  const qualityIcon = (q: string) => {
    if (q === 'excellent' || q === 'good') return <CheckCircle className="w-4 h-4" />
    if (q === 'fair') return <AlertTriangle className="w-4 h-4" />
    return <XCircle className="w-4 h-4" />
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Data Quality</h1>
          <p className="text-surface-600 dark:text-surface-400 mt-1">Evaluate data completeness, freshness, and accuracy per competitor</p>
        </div>
        <button onClick={loadData} className="flex items-center gap-2 px-4 py-2 bg-surface-100 dark:bg-surface-800 rounded-lg hover:bg-surface-200 dark:hover:bg-surface-700 text-surface-700 dark:text-surface-300">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Excellent', count: data.filter(d => d.overall_quality === 'excellent').length, color: 'text-green-600' },
          { label: 'Good', count: data.filter(d => d.overall_quality === 'good').length, color: 'text-blue-600' },
          { label: 'Fair', count: data.filter(d => d.overall_quality === 'fair').length, color: 'text-yellow-600' },
          { label: 'Poor', count: data.filter(d => d.overall_quality === 'poor').length, color: 'text-red-600' },
        ].map(s => (
          <div key={s.label} className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
            <p className="text-sm text-surface-500 dark:text-surface-400">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color}`}>{s.count}</p>
          </div>
        ))}
      </div>

      <div className="bg-white dark:bg-surface-900 rounded-xl border border-surface-200 dark:border-surface-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-surface-50 dark:bg-surface-800">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Competitor</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Quality</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Completeness</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Freshness</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Accuracy</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Extraction Rate</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Missing</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
            {data.map(d => (
              <tr key={d.competitor_id} className="hover:bg-surface-50 dark:hover:bg-surface-800/50">
                <td className="px-6 py-4 text-sm font-medium text-surface-900 dark:text-white">{d.competitor_name}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${qualityColor(d.overall_quality)}`}>
                    {qualityIcon(d.overall_quality)}
                    {d.overall_quality}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-surface-700 dark:text-surface-300">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-surface-200 dark:bg-surface-700 rounded-full h-2">
                      <div className="bg-brand-500 h-2 rounded-full" style={{ width: `${d.completeness_score * 100}%` }} />
                    </div>
                    <span>{Math.round(d.completeness_score * 100)}%</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-surface-700 dark:text-surface-300">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-surface-200 dark:bg-surface-700 rounded-full h-2">
                      <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${d.freshness_score * 100}%` }} />
                    </div>
                    <span>{Math.round(d.freshness_score * 100)}%</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-surface-700 dark:text-surface-300">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-surface-200 dark:bg-surface-700 rounded-full h-2">
                      <div className="bg-green-500 h-2 rounded-full" style={{ width: `${d.accuracy_score * 100}%` }} />
                    </div>
                    <span>{Math.round(d.accuracy_score * 100)}%</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-surface-700 dark:text-surface-300">{Math.round(d.extraction_rate * 100)}%</td>
                <td className="px-6 py-4 text-sm text-surface-500 dark:text-surface-400">
                  {d.missing_values.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {d.missing_values.slice(0, 3).map((v, i) => (
                        <span key={i} className="px-1.5 py-0.5 bg-red-100 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded text-xs">{v}</span>
                      ))}
                      {d.missing_values.length > 3 && <span className="text-xs">+{d.missing_values.length - 3}</span>}
                    </div>
                  ) : (
                    <span className="text-green-500">None</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
