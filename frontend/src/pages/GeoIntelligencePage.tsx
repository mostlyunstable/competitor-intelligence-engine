import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import type { GeoCity, GeoMapData } from '../types'
import { MapPin, RefreshCw, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react'

export default function GeoIntelligencePage() {
  const [cities, setCities] = useState<GeoCity[]>([])
  const [mapData, setMapData] = useState<GeoMapData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [c, m] = await Promise.all([
        api.getGeoCities().catch(() => []),
        api.getGeoMapData().catch(() => null),
      ])
      setCities(c)
      setMapData(m)
    } catch { /* ignore */ }
    setLoading(false)
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" /></div>
  }

  const topOpportunity = cities.filter(c => c.opportunity > 0).slice(0, 5)
  const uncovered = cities.filter(c => c.coverage === 'uncovered')
  const saturated = cities.filter(c => c.saturation > 0.5)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Geographic Intelligence</h1>
          <p className="text-surface-600 dark:text-surface-400 mt-1">Market coverage, opportunity maps, and expansion paths</p>
        </div>
        <button onClick={loadData} className="flex items-center gap-2 px-4 py-2 bg-surface-100 dark:bg-surface-800 rounded-lg hover:bg-surface-200 dark:hover:bg-surface-700 text-surface-700 dark:text-surface-300">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
          <p className="text-sm text-surface-500">Total Cities</p>
          <p className="text-2xl font-bold text-surface-900 dark:text-white">{cities.length}</p>
        </div>
        <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
          <p className="text-sm text-surface-500">Covered</p>
          <p className="text-2xl font-bold text-green-600">{cities.filter(c => c.coverage === 'covered').length}</p>
        </div>
        <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
          <p className="text-sm text-surface-500">Uncovered</p>
          <p className="text-2xl font-bold text-red-600">{uncovered.length}</p>
        </div>
        <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
          <p className="text-sm text-surface-500">High Saturation</p>
          <p className="text-2xl font-bold text-yellow-600">{saturated.length}</p>
        </div>
      </div>

      <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700">
        <h2 className="text-lg font-semibold text-surface-900 dark:text-white mb-4">Top Opportunities</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {topOpportunity.map((c, i) => (
            <div key={c.city} className={`p-4 rounded-xl border ${i === 0 ? 'border-brand-400 bg-brand-50 dark:bg-brand-900/10' : 'border-surface-200 dark:border-surface-700'}`}>
              <MapPin className="w-5 h-5 text-brand-500 mb-2" />
              <h3 className="font-semibold text-surface-900 dark:text-white">{c.city}</h3>
              <p className="text-xs text-surface-500">{c.state} • Tier {c.tier}</p>
              <p className="text-sm font-medium text-green-600 mt-1">Opportunity: {(c.opportunity * 100).toFixed(0)}%</p>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white dark:bg-surface-900 rounded-xl border border-surface-200 dark:border-surface-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-surface-50 dark:bg-surface-800">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">City</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Tier</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Population</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Competitors</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Saturation</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Opportunity</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Coverage</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase">Demand</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-200 dark:divide-surface-700">
            {[...cities].sort((a, b) => b.opportunity - a.opportunity).map(c => (
              <tr key={c.city} className="hover:bg-surface-50 dark:hover:bg-surface-800/50">
                <td className="px-6 py-4 text-sm font-medium text-surface-900 dark:text-white">{c.city}</td>
                <td className="px-6 py-4 text-sm text-surface-700 dark:text-surface-300">T{c.tier}</td>
                <td className="px-6 py-4 text-sm text-surface-700 dark:text-surface-300">{(c.population / 1000000).toFixed(1)}M</td>
                <td className="px-6 py-4 text-sm font-medium text-brand-600">{c.competitor_count}</td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-surface-200 dark:bg-surface-700 rounded-full h-2">
                      <div className={`h-2 rounded-full ${c.saturation > 0.5 ? 'bg-red-500' : c.saturation > 0.2 ? 'bg-yellow-500' : 'bg-green-500'}`} style={{ width: `${c.saturation * 100}%` }} />
                    </div>
                    <span className="text-sm text-surface-600 dark:text-surface-400">{(c.saturation * 100).toFixed(0)}%</span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`text-sm font-medium ${c.opportunity > 0.3 ? 'text-green-600' : c.opportunity > 0.1 ? 'text-yellow-600' : 'text-surface-500'}`}>
                    {(c.opportunity * 100).toFixed(0)}%
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full ${
                    c.coverage === 'covered' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                    : c.coverage === 'partial' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                    : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                  }`}>
                    {c.coverage === 'covered' ? <CheckCircle className="w-3 h-3" /> : c.coverage === 'partial' ? <AlertTriangle className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                    {c.coverage}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-surface-700 dark:text-surface-300 capitalize">{c.demand}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
