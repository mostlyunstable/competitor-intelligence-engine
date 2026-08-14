import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import type { PredictiveBenchmark } from '../types'
import { Trophy, TrendingUp, Lightbulb, Shield, MapPin } from 'lucide-react'

export default function PredictiveBenchmarkPage() {
  const [benchmarks, setBenchmarks] = useState<PredictiveBenchmark[]>([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<'growth_score' | 'innovation_score' | 'expansion_score' | 'risk_score'>('growth_score')

  useEffect(() => {
    loadBenchmarks()
  }, [])

  const loadBenchmarks = async () => {
    setLoading(true)
    try {
      const data = await api.getPredictiveBenchmarks()
      setBenchmarks(data)
    } catch { /* ignore */ }
    setLoading(false)
  }

  const sorted = [...benchmarks].sort((a, b) => b[sortBy] - a[sortBy])

  const predictionColor = (p: string) => {
    if (p === 'high_growth') return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
    if (p === 'medium_growth') return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
    if (p === 'declining') return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
    return 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400'
  }

  const scoreBar = (score: number, color: string) => (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-surface-200 dark:bg-surface-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(score, 100)}%` }} />
      </div>
      <span className="text-xs text-surface-500 w-8 text-right">{score.toFixed(0)}</span>
    </div>
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-surface-500">Loading benchmarks...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Predictive Benchmarking</h1>
        <p className="text-sm text-surface-500 mt-1">Compare current and projected competitor performance</p>
      </div>

      {/* Sort Controls */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-surface-500">Sort by:</span>
        {[
          { key: 'growth_score' as const, label: 'Growth', icon: TrendingUp },
          { key: 'innovation_score' as const, label: 'Innovation', icon: Lightbulb },
          { key: 'expansion_score' as const, label: 'Expansion', icon: MapPin },
          { key: 'risk_score' as const, label: 'Risk', icon: Shield },
        ].map(s => (
          <button
            key={s.key}
            onClick={() => setSortBy(s.key)}
            className={`flex items-center gap-1 text-xs px-3 py-1.5 rounded-full border transition-colors ${
              sortBy === s.key
                ? 'bg-brand-600 text-white border-brand-600'
                : 'bg-white dark:bg-surface-800 text-surface-600 dark:text-surface-400 border-surface-200 dark:border-surface-700'
            }`}
          >
            <s.icon size={12} />
            {s.label}
          </button>
        ))}
      </div>

      {/* Benchmark Table */}
      {sorted.length === 0 ? (
        <div className="card text-center py-12">
          <Trophy size={48} className="mx-auto text-surface-300 mb-3" />
          <p className="text-surface-500">No benchmark data yet. Generate predictions to create benchmarks.</p>
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-surface-500 border-b border-surface-200 dark:border-surface-700">
                <th className="pb-3 font-medium">Rank</th>
                <th className="pb-3 font-medium">Competitor</th>
                <th className="pb-3 font-medium">Prediction</th>
                <th className="pb-3 font-medium">Current → Predicted</th>
                <th className="pb-3 font-medium">Growth</th>
                <th className="pb-3 font-medium">Innovation</th>
                <th className="pb-3 font-medium">Expansion</th>
                <th className="pb-3 font-medium">Risk</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((b, i) => (
                <tr key={b.competitor_id} className="border-b border-surface-100 dark:border-surface-800 hover:bg-surface-50 dark:hover:bg-surface-800/50">
                  <td className="py-3">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                      i === 0 ? 'bg-yellow-100 text-yellow-700' :
                      i === 1 ? 'bg-surface-200 text-surface-600' :
                      i === 2 ? 'bg-orange-100 text-orange-700' :
                      'bg-surface-100 text-surface-500'
                    }`}>
                      {i + 1}
                    </div>
                  </td>
                  <td className="py-3 font-medium text-surface-900 dark:text-white">
                    {b.competitor_name || `Competitor #${b.competitor_id}`}
                  </td>
                  <td className="py-3">
                    <span className={`text-xs px-2 py-1 rounded-full ${predictionColor(b.overall_prediction)}`}>
                      {b.overall_prediction.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="py-3 text-surface-600 dark:text-surface-400">
                    #{b.current_rank} → #{b.predicted_rank}
                    {b.predicted_rank < b.current_rank && (
                      <span className="text-green-500 text-xs ml-1">↑</span>
                    )}
                  </td>
                  <td className="py-3">{scoreBar(b.growth_score, 'bg-green-500')}</td>
                  <td className="py-3">{scoreBar(b.innovation_score, 'bg-blue-500')}</td>
                  <td className="py-3">{scoreBar(b.expansion_score, 'bg-purple-500')}</td>
                  <td className="py-3">{scoreBar(b.risk_score, 'bg-red-500')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
