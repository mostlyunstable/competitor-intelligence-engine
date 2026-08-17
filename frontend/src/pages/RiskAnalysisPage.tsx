import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import type { CompetitorRisk } from '../types'
import { AlertTriangle, Shield, TrendingDown } from 'lucide-react'

export default function RiskAnalysisPage() {
  const [risks, setRisks] = useState<CompetitorRisk[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    loadRisks()
  }, [])

  const loadRisks = async () => {
    setLoading(true)
    try {
      const data = await api.getAllRisks()
      setRisks(data)
    } catch { /* ignore */ }
    setLoading(false)
  }

  const riskColor = (l: string) => {
    if (l === 'critical') return 'bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800'
    if (l === 'high') return 'bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800'
    if (l === 'medium') return 'bg-yellow-100 text-yellow-700 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800'
    return 'bg-surface-100 text-surface-600 border-surface-200 dark:bg-surface-800 dark:text-surface-400 dark:border-surface-700'
  }

  const riskIcon = (level: string) => {
    if (level === 'critical' || level === 'high') return <AlertTriangle size={16} className="text-red-500" />
    if (level === 'medium') return <Shield size={16} className="text-yellow-500" />
    return <Shield size={16} className="text-surface-400" />
  }

  const filtered = filter === 'all' ? risks : risks.filter(r => r.risk_level === filter)

  const stats = {
    critical: risks.filter(r => r.risk_level === 'critical').length,
    high: risks.filter(r => r.risk_level === 'high').length,
    medium: risks.filter(r => r.risk_level === 'medium').length,
    low: risks.filter(r => r.risk_level === 'low').length,
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-surface-500">Loading risk analysis...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Risk Analysis</h1>
        <p className="text-sm text-surface-500 mt-1">Identified competitive risks and mitigation strategies</p>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Critical', count: stats.critical, color: 'text-red-600' },
          { label: 'High', count: stats.high, color: 'text-orange-600' },
          { label: 'Medium', count: stats.medium, color: 'text-yellow-600' },
          { label: 'Low', count: stats.low, color: 'text-surface-600' },
        ].map(s => (
          <button
            key={s.label}
            onClick={() => setFilter(filter === s.label.toLowerCase() ? 'all' : s.label.toLowerCase())}
            className={`card text-center py-3 ${filter === s.label.toLowerCase() ? 'ring-2 ring-brand-500' : ''}`}
          >
            <div className={`text-2xl font-bold ${s.color}`}>{s.count}</div>
            <div className="text-xs text-surface-500">{s.label} Risk{s.count !== 1 ? 's' : ''}</div>
          </button>
        ))}
      </div>

      {/* Filter */}
      {filter !== 'all' && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-surface-500">Filtered by:</span>
          <span className="text-sm font-medium text-surface-900 dark:text-white capitalize">{filter}</span>
          <button onClick={() => setFilter('all')} className="text-xs text-brand-600 hover:underline">Clear</button>
        </div>
      )}

      {/* Risk Cards */}
      {filtered.length === 0 ? (
        <div className="card text-center py-12">
          <Shield size={48} className="mx-auto text-surface-300 mb-3" />
          <p className="text-surface-500">No risks detected. Generate predictions to analyze risks.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((r, i) => (
            <div key={i} className={`card border-l-4 ${riskColor(r.risk_level)}`}>
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  {riskIcon(r.risk_level)}
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-surface-900 dark:text-white">
                        {r.competitor_name || `Competitor #${r.competitor_id}`}
                      </h3>
                      <span className="text-xs text-surface-500">•</span>
                      <span className="text-xs text-surface-500 capitalize">{r.risk_type.replace(/_/g, ' ')}</span>
                    </div>
                    <p className="text-sm text-surface-600 dark:text-surface-400 mt-1">{r.business_impact}</p>
                    <div className="mt-3 p-3 bg-surface-50 dark:bg-surface-800 rounded-lg">
                      <div className="text-xs font-medium text-surface-500 mb-1">Mitigation</div>
                      <p className="text-sm text-surface-700 dark:text-surface-300">{r.mitigation}</p>
                    </div>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-lg font-bold text-surface-900 dark:text-white">{r.risk_score != null ? Number(r.risk_score).toFixed(0) : '-'}</div>
                  <div className="text-xs text-surface-500">Risk Score</div>
                  <div className="text-xs text-surface-500 mt-1">{r.likelihood != null ? (Number(r.likelihood) * 100).toFixed(0) : '0'}% likely</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
