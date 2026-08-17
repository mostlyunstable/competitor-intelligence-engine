import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import type { GrowthForecast, ExpansionForecast } from '../types'
import { TrendingUp, MapPin, Clock, ChevronDown, ChevronUp } from 'lucide-react'

export default function ForecastsPage() {
  const [growth, setGrowth] = useState<GrowthForecast[]>([])
  const [selectedCompetitor, setSelectedCompetitor] = useState<number | null>(null)
  const [expansion, setExpansion] = useState<ExpansionForecast[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedRow, setExpandedRow] = useState<number | null>(null)

  useEffect(() => {
    loadGrowth()
  }, [])

  const loadGrowth = async () => {
    setLoading(true)
    try {
      const data = await api.getGrowthForecasts()
      setGrowth(data)
      if (data.length > 0 && !selectedCompetitor) {
        setSelectedCompetitor(data[0].competitor_id)
        loadExpansion(data[0].competitor_id)
      }
    } catch { /* ignore */ }
    setLoading(false)
  }

  const loadExpansion = async (cid: number) => {
    try {
      const data = await api.getExpansionForecast(cid)
      setExpansion(data)
    } catch { /* ignore */ }
  }

  const handleSelectCompetitor = (cid: number) => {
    setSelectedCompetitor(cid)
    loadExpansion(cid)
  }

  const levelColor = (l: string) => {
    if (l === 'high') return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
    if (l === 'medium') return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
    return 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-surface-500">Loading forecasts...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Forecasts</h1>
        <p className="text-sm text-surface-500 mt-1">Growth and regional expansion forecasts</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Growth Forecast List */}
        <div className="lg:col-span-2 card">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={18} className="text-brand-600" />
            <h2 className="font-semibold text-surface-900 dark:text-white">Growth Forecasts</h2>
          </div>
          {growth.length === 0 ? (
            <p className="text-sm text-surface-500">No growth data available.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-surface-500 border-b border-surface-200 dark:border-surface-700">
                    <th className="pb-2 font-medium">Competitor</th>
                    <th className="pb-2 font-medium">Level</th>
                    <th className="pb-2 font-medium">Score</th>
                    <th className="pb-2 font-medium">Growth</th>
                    <th className="pb-2 font-medium">Confidence</th>
                    <th className="pb-2 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {growth.map((g) => (
                    <tr
                      key={g.competitor_id}
                      className={`border-b border-surface-100 dark:border-surface-800 cursor-pointer hover:bg-surface-50 dark:hover:bg-surface-800/50 ${
                        selectedCompetitor === g.competitor_id ? 'bg-brand-50 dark:bg-brand-900/10' : ''
                      }`}
                      onClick={() => handleSelectCompetitor(g.competitor_id)}
                    >
                      <td className="py-3 font-medium text-surface-900 dark:text-white">
                        {g.competitor_name || `Competitor #${g.competitor_id}`}
                      </td>
                      <td className="py-3">
                        <span className={`text-xs px-2 py-1 rounded-full ${levelColor(g.growth_level)}`}>
                          {g.growth_level}
                        </span>
                      </td>
                      <td className="py-3 text-surface-700 dark:text-surface-300">{g.growth_score != null ? Number(g.growth_score).toFixed(1) : '-'}</td>
                      <td className="py-3 text-surface-700 dark:text-surface-300">{g.growth_percentage || '-'}</td>
                      <td className="py-3 text-surface-700 dark:text-surface-300">{g.confidence_score != null ? (Number(g.confidence_score) * 100).toFixed(0) : '0'}%</td>
                      <td className="py-3">
                        <button
                          onClick={(e) => { e.stopPropagation(); setExpandedRow(expandedRow === g.competitor_id ? null : g.competitor_id) }}
                          className="text-surface-400 hover:text-surface-600"
                        >
                          {expandedRow === g.competitor_id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Expanded Details */}
          {expandedRow && (() => {
            const g = growth.find(x => x.competitor_id === expandedRow)
            if (!g) return null
            return (
              <div className="mt-4 p-4 bg-surface-50 dark:bg-surface-800 rounded-lg border border-surface-200 dark:border-surface-700">
                <h3 className="text-sm font-medium text-surface-900 dark:text-white mb-3">Breakdown</h3>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {Object.entries(g.breakdown || {}).map(([key, val]) => (
                    <div key={key} className="text-center">
                      <div className="text-lg font-bold text-brand-600">{val != null ? Number(val).toFixed(1) : '-'}</div>
                      <div className="text-xs text-surface-500">{key.replace(/_/g, ' ')}</div>
                    </div>
                  ))}
                </div>
                <div className="mt-3 grid grid-cols-3 md:grid-cols-6 gap-2 text-xs text-surface-500">
                  <div>Services (30d): {g.metrics.services_last_30}</div>
                  <div>Services (90d): {g.metrics.services_last_90}</div>
                  <div>Pricing (30d): {g.metrics.pricing_last_30}</div>
                  <div>Content (30d): {g.metrics.content_last_30}</div>
                  <div>Changes (30d): {g.metrics.changes_last_30}</div>
                  <div>Collections: {g.metrics.successful_collections}</div>
                </div>
              </div>
            )
          })()}
        </div>

        {/* Regional Expansion */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <MapPin size={18} className="text-brand-600" />
            <h2 className="font-semibold text-surface-900 dark:text-white">Regional Expansion</h2>
          </div>
          {expansion.length === 0 ? (
            <p className="text-sm text-surface-500">
              {selectedCompetitor ? 'No expansion data for this competitor.' : 'Select a competitor to view expansion forecasts.'}
            </p>
          ) : (
            <div className="space-y-3">
              {expansion.slice(0, 8).map((e, i) => (
                <div key={i} className="p-3 bg-surface-50 dark:bg-surface-800 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-surface-900 dark:text-white">{e.region}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${levelColor(e.priority)}`}>
                      {e.priority}
                    </span>
                  </div>
                  <div className="w-full h-2 bg-surface-200 dark:bg-surface-700 rounded-full overflow-hidden mb-2">
                    <div
                      className="h-full bg-brand-500 rounded-full transition-all"
                      style={{ width: `${(e.expansion_probability || 0) * 100}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs text-surface-500">
                    <span>{e.expansion_probability != null ? (Number(e.expansion_probability) * 100).toFixed(0) : '0'}% probability</span>
                    <span className="flex items-center gap-1">
                      <Clock size={10} />
                      {e.expected_timeline}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
