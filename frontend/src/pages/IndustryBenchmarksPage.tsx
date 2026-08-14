import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import type { IndustryBenchmark } from '../types'
import { Trophy, RefreshCw, Target, BarChart3, Award, Zap, Shield } from 'lucide-react'

export default function IndustryBenchmarksPage() {
  const [data, setData] = useState<IndustryBenchmark[]>([])
  const [catBenchmarks, setCatBenchmarks] = useState<Record<string, { category: string; competitor_count: number; average_services: number; max_services: number; leaders: { competitor_name: string; service_count: number }[] }>>({})
  const [selectedComp, setSelectedComp] = useState<IndustryBenchmark | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [benchmarks, categories] = await Promise.all([
        api.getIndustryBenchmarks().catch(() => []),
        api.getCategoryBenchmarks().catch(() => ({})),
      ])
      setData(benchmarks)
      setCatBenchmarks(categories as Record<string, { category: string; competitor_count: number; average_services: number; max_services: number; leaders: { competitor_name: string; service_count: number }[] }>)
    } catch { /* ignore */ }
    setLoading(false)
  }

  const gradeColor = (g: string) => {
    if (g === 'A') return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
    if (g === 'B') return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
    if (g === 'C') return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
    return 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400'
  }

  const dimLabel: Record<string, string> = {
    market_presence: 'Market Presence',
    growth_potential: 'Growth',
    innovation_score: 'Innovation',
    pricing_competitiveness: 'Pricing',
    regional_strength: 'Regional',
    digital_presence: 'Digital',
    service_diversity: 'Diversity',
    customer_reach: 'Reach',
    technology_adoption: 'Tech',
    content_authority: 'Content',
  }

  const getTopDimensions = (dimPct: Record<string, number>, n = 2) => {
    return Object.entries(dimPct)
      .sort(([, a], [, b]) => b - a)
      .slice(0, n)
      .map(([k, v]) => ({ label: dimLabel[k] || k, pct: Math.round(v * 100) }))
  }

  const getWeakDimension = (dimPct: Record<string, number>) => {
    const worst = Object.entries(dimPct).sort(([, a], [, b]) => a - b)[0]
    return worst ? { label: dimLabel[worst[0]] || worst[0], pct: Math.round(worst[1] * 100) } : null
  }

  const DimensionBar = ({ pct }: { pct: number }) => (
    <div className="w-full h-1.5 bg-surface-200 dark:bg-surface-700 rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-blue-500' : pct >= 20 ? 'bg-yellow-500' : 'bg-red-400'}`} style={{ width: `${pct}%` }} />
    </div>
  )

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" /></div>
  }

  const sorted = [...data].sort((a, b) => b.overall_score - a.overall_score)
  const topComp = sorted[0]
  const industryMean = sorted.length ? (sorted.reduce((s, b) => s + b.overall_score, 0) / sorted.length) : 0

  const avgDimensionPct: Record<string, number> = {}
  if (sorted.length) {
    const allDims = new Set(sorted.flatMap(b => Object.keys(b.dimension_percentiles || {})))
    for (const dim of allDims) {
      const vals = sorted.map(b => (b.dimension_percentiles || {})[dim] ?? 0)
      avgDimensionPct[dim] = vals.reduce((s, v) => s + v, 0) / vals.length
    }
  }
  const strongestDim = Object.entries(avgDimensionPct).sort(([, a], [, b]) => b - a)[0]
  const weakestDim = Object.entries(avgDimensionPct).sort(([, a], [, b]) => a - b)[0]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Industry Benchmarks</h1>
          <p className="text-surface-600 dark:text-surface-400 mt-1">Competitive intelligence across the Indian home services market</p>
        </div>
        <button onClick={loadData} className="flex items-center gap-2 px-4 py-2 bg-surface-100 dark:bg-surface-800 rounded-lg hover:bg-surface-200 dark:hover:bg-surface-700 text-surface-700 dark:text-surface-300">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-surface-900 rounded-xl p-5 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-2 mb-2"><Trophy className="w-5 h-5 text-yellow-500" /><span className="text-sm font-medium text-surface-500">Top Performer</span></div>
          <p className="text-xl font-bold text-surface-900 dark:text-white">{topComp?.competitor_name || 'N/A'}</p>
          <p className="text-sm text-surface-500">Score {topComp?.overall_score.toFixed(1) || '—'} · Grade {topComp?.grade || '—'}</p>
        </div>
        <div className="bg-white dark:bg-surface-900 rounded-xl p-5 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-2 mb-2"><BarChart3 className="w-5 h-5 text-brand-500" /><span className="text-sm font-medium text-surface-500">Industry Average</span></div>
          <p className="text-xl font-bold text-surface-900 dark:text-white">{industryMean.toFixed(1)}</p>
          <p className="text-sm text-surface-500">{sorted.length} competitors tracked</p>
        </div>
        <div className="bg-white dark:bg-surface-900 rounded-xl p-5 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-2 mb-2"><Zap className="w-5 h-5 text-green-500" /><span className="text-sm font-medium text-surface-500">Strongest Dimension</span></div>
          <p className="text-xl font-bold text-surface-900 dark:text-white">{strongestDim ? dimLabel[strongestDim[0]] || strongestDim[0] : 'N/A'}</p>
          <p className="text-sm text-surface-500">Avg {strongestDim ? Math.round(strongestDim[1] * 100) : '—'}th percentile</p>
        </div>
        <div className="bg-white dark:bg-surface-900 rounded-xl p-5 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-2 mb-2"><Shield className="w-5 h-5 text-red-500" /><span className="text-sm font-medium text-surface-500">Weakest Dimension</span></div>
          <p className="text-xl font-bold text-surface-900 dark:text-white">{weakestDim ? dimLabel[weakestDim[0]] || weakestDim[0] : 'N/A'}</p>
          <p className="text-sm text-surface-500">Avg {weakestDim ? Math.round(weakestDim[1] * 100) : '—'}th percentile</p>
        </div>
      </div>

      {/* Rankings Table */}
      <div className="bg-white dark:bg-surface-900 rounded-xl border border-surface-200 dark:border-surface-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-surface-200 dark:border-surface-700">
          <h2 className="font-semibold text-surface-900 dark:text-white">Competitor Rankings</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-50 dark:bg-surface-800">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-medium text-surface-500 uppercase w-12">#</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-surface-500 uppercase">Competitor</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-surface-500 uppercase w-16">Grade</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-surface-500 uppercase w-20">Score</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-surface-500 uppercase">Top Strengths</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-surface-500 uppercase">Weak Spot</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-surface-500 uppercase w-28">Dimension Profile</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
              {sorted.map((b, i) => {
                const tops = getTopDimensions(b.dimension_percentiles || {})
                const weak = getWeakDimension(b.dimension_percentiles || {})
                const dimValues = Object.values(b.dimension_percentiles || {})
                const avgDim = dimValues.length ? dimValues.reduce((s, v) => s + v, 0) / dimValues.length : 0

                return (
                  <tr key={b.competitor_id}
                    className={`hover:bg-surface-50 dark:hover:bg-surface-800/50 cursor-pointer transition-colors ${selectedComp?.competitor_id === b.competitor_id ? 'bg-brand-50 dark:bg-brand-900/10' : ''}`}
                    onClick={() => setSelectedComp(selectedComp?.competitor_id === b.competitor_id ? null : b)}>
                    <td className="px-5 py-3 text-sm font-medium text-surface-500">
                      {i === 0 ? <Trophy className="w-4 h-4 text-yellow-500 inline" /> : `#${i + 1}`}
                    </td>
                    <td className="px-5 py-3">
                      <p className="text-sm font-semibold text-surface-900 dark:text-white">{b.competitor_name}</p>
                    </td>
                    <td className="px-5 py-3">
                      <span className={`text-xs px-2 py-1 rounded-full font-bold ${gradeColor(b.grade)}`}>{b.grade}</span>
                    </td>
                    <td className="px-5 py-3 text-sm font-bold text-surface-900 dark:text-white">{b.overall_score.toFixed(1)}</td>
                    <td className="px-5 py-3">
                      <div className="flex flex-wrap gap-1.5">
                        {tops.map(t => (
                          <span key={t.label} className={`text-xs px-2 py-0.5 rounded-full font-medium ${t.pct >= 70 ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'}`}>
                            {t.label} {t.pct}%
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      {weak && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 font-medium">
                          {weak.label} {weak.pct}%
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <DimensionBar pct={Math.round(avgDim * 100)} />
                        <span className="text-xs text-surface-500 w-8 text-right">{Math.round(avgDim * 100)}%</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Dimension Breakdown (selected competitor) */}
      {selectedComp && (
        <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-surface-900 dark:text-white">
              {selectedComp.competitor_name} — Dimension Breakdown
            </h2>
            <span className={`text-xs px-2 py-1 rounded-full font-bold ${gradeColor(selectedComp.grade)}`}>Grade {selectedComp.grade}</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(selectedComp.dimension_percentiles || {}).map(([dim, val]) => {
              const pct = Math.round(val * 100)
              return (
                <div key={dim} className="p-3 bg-surface-50 dark:bg-surface-800 rounded-lg">
                  <p className="text-xs text-surface-500 mb-1">{dimLabel[dim] || dim}</p>
                  <p className={`text-lg font-bold ${pct >= 70 ? 'text-green-600 dark:text-green-400' : pct >= 40 ? 'text-blue-600 dark:text-blue-400' : pct >= 20 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-500 dark:text-red-400'}`}>{pct}%</p>
                  <DimensionBar pct={pct} />
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Category Benchmarks */}
      {Object.keys(catBenchmarks).length > 0 && (
        <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700">
          <h2 className="font-semibold text-surface-900 dark:text-white mb-4">Category Benchmarks</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.values(catBenchmarks).map(cat => (
              <div key={cat.category} className="p-4 bg-surface-50 dark:bg-surface-800 rounded-lg border border-surface-200 dark:border-surface-700">
                <h3 className="text-sm font-semibold text-surface-900 dark:text-white mb-2">{cat.category}</h3>
                <div className="space-y-1 text-xs text-surface-500">
                  <p>{cat.competitor_count} competitors · avg {cat.average_services} services</p>
                  <p>Max: {cat.max_services} services</p>
                  {cat.leaders.length > 0 && (
                    <p className="text-brand-600 dark:text-brand-400 font-medium">
                      Leader: {cat.leaders[0].competitor_name} ({cat.leaders[0].service_count})
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
