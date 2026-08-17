import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import type { GeoCity, GeoMapData } from '../types'
import { MapPin, RefreshCw, TrendingUp, AlertTriangle, CheckCircle, Search, Compass, Building2, Layers } from 'lucide-react'

export default function GeoIntelligencePage() {
  const [cities, setCities] = useState<GeoCity[]>([])
  const [mapData, setMapData] = useState<GeoMapData | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [tierFilter, setTierFilter] = useState<string>('all')
  const [coverageFilter, setCoverageFilter] = useState<string>('all')
  const [activeTab, setActiveTab] = useState<'grid' | 'opportunities' | 'states'>('grid')

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [citiesRes, mapRes, analysisRes] = await Promise.allSettled([
        api.getGeoCities(),
        api.getGeoMapData(),
        api.getGeoAnalysis(),
      ])

      let loadedCities: GeoCity[] = []
      if (citiesRes.status === 'fulfilled' && Array.isArray(citiesRes.value) && citiesRes.value.length > 0) {
        loadedCities = citiesRes.value
      } else if (analysisRes.status === 'fulfilled' && analysisRes.value && Array.isArray((analysisRes.value as any).city_analysis)) {
        loadedCities = (analysisRes.value as any).city_analysis
      }

      if (mapRes.status === 'fulfilled' && mapRes.value) {
        setMapData(mapRes.value)
      }

      setCities(loadedCities)
    } catch {
      // safe fallback
    }
    setLoading(false)
  }

  const filteredCities = cities.filter(c => {
    const matchesSearch = c.city.toLowerCase().includes(searchQuery.toLowerCase()) || c.state.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesTier = tierFilter === 'all' || c.tier.toString() === tierFilter
    const matchesCoverage = coverageFilter === 'all' || (c.coverage || '').toLowerCase() === coverageFilter.toLowerCase()
    return matchesSearch && matchesTier && matchesCoverage
  })

  const topOpportunity = [...cities].sort((a, b) => (b.opportunity || 0) - (a.opportunity || 0)).slice(0, 5)
  const coveredCount = cities.filter(c => (c.coverage || '').toLowerCase() === 'covered').length
  const partialCount = cities.filter(c => (c.coverage || '').toLowerCase() === 'partial').length
  const uncoveredCount = cities.filter(c => (c.coverage || '').toLowerCase() === 'uncovered').length
  const highSaturation = cities.filter(c => (c.saturation || 0) > 0.4)

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
        <span className="text-sm text-surface-500">Loading Geographic Intelligence...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Geographic Intelligence</h1>
          <p className="text-surface-600 dark:text-surface-400 mt-1">
            Market coverage density, competitor saturation, and geographic expansion paths across Indian territories.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            className="flex items-center gap-2 px-4 py-2 bg-surface-100 dark:bg-surface-800 rounded-lg hover:bg-surface-200 dark:hover:bg-surface-700 text-surface-700 dark:text-surface-300 transition-colors"
          >
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-surface-500">Monitored Cities</p>
            <Building2 className="w-4 h-4 text-brand-500" />
          </div>
          <p className="text-2xl font-extrabold text-surface-900 dark:text-white mt-2">{cities.length}</p>
          <p className="text-xs text-surface-500 mt-1">Tier 1, Tier 2 & Tier 3 Hubs</p>
        </div>

        <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-surface-500">Covered Markets</p>
            <CheckCircle className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-2">{coveredCount}</p>
          <p className="text-xs text-surface-500 mt-1">{partialCount} partially active</p>
        </div>

        <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-surface-500">Expansion White-Space</p>
            <Compass className="w-4 h-4 text-blue-500" />
          </div>
          <p className="text-2xl font-extrabold text-blue-600 dark:text-blue-400 mt-2">{uncoveredCount}</p>
          <p className="text-xs text-surface-500 mt-1">High-opportunity cities</p>
        </div>

        <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-surface-500">High Saturation</p>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-2xl font-extrabold text-amber-600 dark:text-amber-400 mt-2">{highSaturation.length}</p>
          <p className="text-xs text-surface-500 mt-1">Intense competitor density</p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-surface-200 dark:border-surface-800">
        <button
          onClick={() => setActiveTab('grid')}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'grid'
              ? 'border-brand-500 text-brand-600 dark:text-brand-400'
              : 'border-transparent text-surface-500 hover:text-surface-700 dark:hover:text-surface-300'
          }`}
        >
          City Market Matrix
        </button>
        <button
          onClick={() => setActiveTab('opportunities')}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'opportunities'
              ? 'border-brand-500 text-brand-600 dark:text-brand-400'
              : 'border-transparent text-surface-500 hover:text-surface-700 dark:hover:text-surface-300'
          }`}
        >
          Expansion Pathways
        </button>
        <button
          onClick={() => setActiveTab('states')}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'states'
              ? 'border-brand-500 text-brand-600 dark:text-brand-400'
              : 'border-transparent text-surface-500 hover:text-surface-700 dark:hover:text-surface-300'
          }`}
        >
          State & Regional Capacity
        </button>
      </div>

      {/* Tab: Expansion Pathways */}
      {activeTab === 'opportunities' && (
        <div className="space-y-4">
          <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-brand-500" />
              <h2 className="text-lg font-bold text-surface-900 dark:text-white">Top Geographic Expansion Opportunities</h2>
            </div>
            <p className="text-sm text-surface-600 dark:text-surface-400 mb-6">
              Ranked by high population demand, low competitor penetration, and favorable service margins.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              {topOpportunity.map((c, i) => (
                <div
                  key={c.city}
                  className={`p-4 rounded-xl border transition-all ${
                    i === 0
                      ? 'border-brand-400 bg-brand-50/50 dark:bg-brand-900/10 shadow-sm ring-1 ring-brand-400/20'
                      : 'border-surface-200 dark:border-surface-700 bg-surface-50/50 dark:bg-surface-800/30'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <MapPin className="w-5 h-5 text-brand-500" />
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300">
                      Rank #{i + 1}
                    </span>
                  </div>
                  <h3 className="font-bold text-surface-900 dark:text-white">{c.city}</h3>
                  <p className="text-xs text-surface-500">{c.state} • Tier {c.tier}</p>
                  <div className="mt-3 pt-3 border-t border-surface-200 dark:border-surface-700">
                    <div className="text-xs text-surface-500">Opportunity Score</div>
                    <div className="text-base font-extrabold text-emerald-600 dark:text-emerald-400">
                      {c.opportunity != null ? (c.opportunity * 100).toFixed(0) : '0'}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab: State & Regional Capacity */}
      {activeTab === 'states' && mapData && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {mapData.states.map(state => (
            <div key={state.name} className="bg-white dark:bg-surface-900 rounded-xl p-5 border border-surface-200 dark:border-surface-700 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-bold text-surface-900 dark:text-white">{state.name}</h3>
                <span className="text-xs px-2 py-0.5 rounded-full bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-300 font-mono">
                  {state.capital}
                </span>
              </div>
              <div className="space-y-2 mt-3 text-xs">
                <div className="flex justify-between text-surface-500">
                  <span>State Population</span>
                  <span className="font-semibold text-surface-900 dark:text-white">{(state.population / 1000000).toFixed(1)}M</span>
                </div>
                <div className="flex justify-between text-surface-500">
                  <span>GDP / Capita</span>
                  <span className="font-semibold font-mono text-brand-600">₹{state.gdp_per_capita.toLocaleString()}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab: Main Grid */}
      {activeTab === 'grid' && (
        <div className="space-y-4">
          {/* Filters & Search */}
          <div className="flex flex-col md:flex-row items-center justify-between gap-3 bg-white dark:bg-surface-900 p-4 rounded-xl border border-surface-200 dark:border-surface-700 shadow-sm">
            <div className="relative w-full md:w-80">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-surface-400" />
              <input
                type="text"
                placeholder="Search city or state..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-sm bg-surface-50 dark:bg-surface-800 rounded-lg border border-surface-200 dark:border-surface-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto">
              <select
                value={tierFilter}
                onChange={e => setTierFilter(e.target.value)}
                className="text-xs px-3 py-2 bg-surface-50 dark:bg-surface-800 rounded-lg border border-surface-200 dark:border-surface-700 text-surface-700 dark:text-surface-300"
              >
                <option value="all">All Tiers</option>
                <option value="1">Tier 1 Metros</option>
                <option value="2">Tier 2 Growth Hubs</option>
                <option value="3">Tier 3 Emerging</option>
              </select>

              <select
                value={coverageFilter}
                onChange={e => setCoverageFilter(e.target.value)}
                className="text-xs px-3 py-2 bg-surface-50 dark:bg-surface-800 rounded-lg border border-surface-200 dark:border-surface-700 text-surface-700 dark:text-surface-300"
              >
                <option value="all">All Coverage</option>
                <option value="covered">Covered</option>
                <option value="partial">Partial</option>
                <option value="uncovered">Uncovered</option>
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="bg-white dark:bg-surface-900 rounded-xl border border-surface-200 dark:border-surface-700 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-surface-50 dark:bg-surface-800 border-b border-surface-200 dark:border-surface-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">City</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">State</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Tier</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Population</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Competitors</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Market Saturation</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Opportunity</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">Market Demand</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-200 dark:divide-surface-700 text-sm">
                  {filteredCities.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-6 py-12 text-center text-surface-400">
                        No geographic data matches your search.
                      </td>
                    </tr>
                  ) : (
                    filteredCities.map(c => (
                      <tr key={c.city} className="hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors">
                        <td className="px-6 py-4 font-semibold text-surface-900 dark:text-white flex items-center gap-2">
                          <MapPin className="w-4 h-4 text-brand-500 flex-shrink-0" />
                          {c.city}
                        </td>
                        <td className="px-6 py-4 text-surface-600 dark:text-surface-400">{c.state}</td>
                        <td className="px-6 py-4">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-surface-100 dark:bg-surface-800 font-mono text-surface-700 dark:text-surface-300">
                            Tier {c.tier}
                          </span>
                        </td>
                        <td className="px-6 py-4 font-mono text-surface-700 dark:text-surface-300">
                          {c.population ? `${(c.population / 1000000).toFixed(1)}M` : '-'}
                        </td>
                        <td className="px-6 py-4 font-bold text-brand-600 dark:text-brand-400">
                          {c.competitor_count || 0}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <div className="w-20 bg-surface-200 dark:bg-surface-700 rounded-full h-2 overflow-hidden">
                              <div
                                className={`h-2 rounded-full ${
                                  (c.saturation || 0) > 0.4
                                    ? 'bg-red-500'
                                    : (c.saturation || 0) > 0.2
                                    ? 'bg-amber-500'
                                    : 'bg-emerald-500'
                                }`}
                                style={{ width: `${Math.min(100, Math.max(5, (c.saturation || 0) * 100))}%` }}
                              />
                            </div>
                            <span className="text-xs font-mono text-surface-600 dark:text-surface-400">
                              {c.saturation != null ? (c.saturation * 100).toFixed(0) : '0'}%
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`font-semibold ${
                              (c.opportunity || 0) > 0.3
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : (c.opportunity || 0) > 0.15
                                ? 'text-amber-600 dark:text-amber-400'
                                : 'text-surface-500'
                            }`}
                          >
                            {c.opportunity != null ? (c.opportunity * 100).toFixed(0) : '0'}%
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium ${
                              (c.coverage || '').toLowerCase() === 'covered'
                                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400'
                                : (c.coverage || '').toLowerCase() === 'partial'
                                ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400'
                                : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                            }`}
                          >
                            {(c.coverage || '').toLowerCase() === 'covered' ? (
                              <CheckCircle className="w-3 h-3" />
                            ) : (
                              <AlertTriangle className="w-3 h-3" />
                            )}
                            {c.coverage || 'Uncovered'}
                          </span>
                        </td>
                        <td className="px-6 py-4 capitalize text-surface-600 dark:text-surface-300">
                          {c.demand || 'Medium'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
