import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import type { StrategicRecommendation } from '../types'
import { Target, CheckCircle, Circle, ChevronDown, ChevronUp } from 'lucide-react'

export default function RecommendationsPage() {
  const [recs, setRecs] = useState<StrategicRecommendation[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<string>('all')

  useEffect(() => {
    loadRecs()
  }, [])

  const loadRecs = async () => {
    setLoading(true)
    try {
      const data = await api.getAllRecommendations()
      setRecs(data)
    } catch { /* ignore */ }
    setLoading(false)
  }

  const priorityColor = (p: string) => {
    if (p === 'high') return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
    if (p === 'medium') return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
    return 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400'
  }

  const riskColor = (l: string) => {
    if (l === 'high' || l === 'critical') return 'text-red-600'
    if (l === 'medium') return 'text-yellow-600'
    return 'text-green-600'
  }

  const categories = ['all', ...new Set(recs.map(r => r.category))]
  const filtered = categoryFilter === 'all' ? recs : recs.filter(r => r.category === categoryFilter)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-surface-500">Loading recommendations...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Strategic Recommendations</h1>
        <p className="text-sm text-surface-500 mt-1">AI-generated actionable business recommendations</p>
      </div>

      {/* Category Filter */}
      <div className="flex flex-wrap gap-2">
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setCategoryFilter(cat)}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              categoryFilter === cat
                ? 'bg-brand-600 text-white border-brand-600'
                : 'bg-white dark:bg-surface-800 text-surface-600 dark:text-surface-400 border-surface-200 dark:border-surface-700 hover:border-brand-300'
            }`}
          >
            {cat === 'all' ? 'All' : cat.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card text-center">
          <div className="text-2xl font-bold text-brand-600">{recs.length}</div>
          <div className="text-xs text-surface-500">Total Recommendations</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-green-600">{recs.filter(r => r.priority === 'high').length}</div>
          <div className="text-xs text-surface-500">High Priority</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-surface-600">{recs.filter(r => !r.applied).length}</div>
          <div className="text-xs text-surface-500">Pending</div>
        </div>
      </div>

      {/* Recommendation Cards */}
      {filtered.length === 0 ? (
        <div className="card text-center py-12">
          <Target size={48} className="mx-auto text-surface-300 mb-3" />
          <p className="text-surface-500">No recommendations yet. Generate predictions to get recommendations.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((r) => (
            <div key={r.competitor_id + r.category + r.title} className="card">
              <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpandedId(expandedId === r.competitor_id ? null : r.competitor_id)}
              >
                <div className="flex items-center gap-3">
                  {r.applied ? (
                    <CheckCircle size={18} className="text-green-500" />
                  ) : (
                    <Circle size={18} className="text-surface-300" />
                  )}
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-surface-900 dark:text-white">{r.title}</h3>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">
                        {r.category.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="text-xs text-surface-500 mt-0.5">
                      {r.competitor_name || `Competitor #${r.competitor_id}`}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2 py-1 rounded-full ${priorityColor(r.priority)}`}>
                    {r.priority}
                  </span>
                  <span className={`text-xs font-medium ${riskColor(r.risk_level)}`}>
                    {r.risk_level} risk
                  </span>
                  <span className="text-xs text-surface-500">{(r.confidence_score * 100).toFixed(0)}%</span>
                  {expandedId === r.competitor_id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </div>
              </div>

              {expandedId === r.competitor_id && (
                <div className="mt-4 pt-4 border-t border-surface-200 dark:border-surface-700 space-y-3">
                  <div>
                    <div className="text-xs font-medium text-surface-500 mb-1">Recommendation</div>
                    <p className="text-sm text-surface-700 dark:text-surface-300">{r.recommendation}</p>
                  </div>
                  <div>
                    <div className="text-xs font-medium text-surface-500 mb-1">Why</div>
                    <p className="text-sm text-surface-700 dark:text-surface-300">{r.why}</p>
                  </div>
                  <div>
                    <div className="text-xs font-medium text-surface-500 mb-1">Expected Benefit</div>
                    <p className="text-sm text-surface-700 dark:text-surface-300">{r.expected_benefit}</p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
