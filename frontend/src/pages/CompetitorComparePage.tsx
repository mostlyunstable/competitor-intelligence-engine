import { useState, useEffect, useCallback } from 'react'
import { api } from '../lib/api'
import { BarChart } from '../components/Charts'
import { GitCompare, Check, Plus, X, RefreshCw } from 'lucide-react'

interface CompetitorData {
  id: number
  name: string
  website_url: string
  modules: string[]
  services_count: number
  pricing_count: number
  social_count: number
  content_count: number
}

export default function CompetitorComparePage() {
  const [competitors, setCompetitors] = useState<any[]>([])
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [comparison, setComparison] = useState<CompetitorData[]>([])
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const loadCompetitors = useCallback(async () => {
    try {
      const data = await api.getCompetitors({ page_size: 50 })
      setCompetitors(data.competitors || data || [])
    } catch {}
  }, [])

  useEffect(() => { loadCompetitors() }, [loadCompetitors])

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await loadCompetitors()
      if (selectedIds.length >= 2) {
        setLoading(true)
        const data = await api.compareCompetitors(selectedIds)
        setComparison(data)
        setLoading(false)
      }
    } finally {
      setRefreshing(false)
    }
  }, [loadCompetitors, selectedIds])

  useEffect(() => {
    if (selectedIds.length >= 2) {
      setLoading(true)
      api.compareCompetitors(selectedIds).then(data => {
        setComparison(data)
        setLoading(false)
      }).catch(() => setLoading(false))
    } else {
      setComparison([])
    }
  }, [selectedIds])

  const toggleCompetitor = (id: number) => {
    setSelectedIds(prev => {
      if (prev.includes(id)) {
        return prev.filter(i => i !== id)
      }
      if (prev.length >= 4) return prev
      return [...prev, id]
    })
  }

  const totalEntities = (c: CompetitorData) =>
    c.services_count + c.pricing_count + c.social_count + c.content_count

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <GitCompare size={24} className="text-brand-500" />
          <h1 className="text-2xl font-bold text-surface-900">Competitor Comparison</h1>
        </div>
        <button onClick={handleRefresh} disabled={refreshing} className="btn-secondary disabled:opacity-50">
          <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      {/* Selector */}
      <div className="card p-5">
        <h2 className="font-semibold text-surface-900 mb-3">Select competitors to compare (2-4)</h2>
        <div className="flex flex-wrap gap-2">
          {competitors.map((c: any) => {
            const selected = selectedIds.includes(c.id)
            const disabled = !selected && selectedIds.length >= 4
            return (
              <button
                key={c.id}
                onClick={() => toggleCompetitor(c.id)}
                disabled={disabled}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  selected
                    ? 'bg-brand-500 text-white'
                    : disabled
                    ? 'bg-surface-100 text-surface-400 cursor-not-allowed'
                    : 'bg-surface-100 text-surface-700 hover:bg-surface-200'
                }`}
              >
                {selected && <Check size={14} />}
                {c.name}
                {selected && <X size={14} onClick={(e) => { e.stopPropagation(); toggleCompetitor(c.id) }} />}
              </button>
            )
          })}
        </div>
      </div>

      {/* Comparison Table */}
      {loading && (
        <div className="card p-8 text-center text-surface-400">Loading comparison...</div>
      )}

      {!loading && comparison.length >= 2 && (
        <>
          {/* Summary Table */}
          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-surface-50 border-b border-surface-100">
                    <th className="text-left px-5 py-3 text-sm font-medium text-surface-600">Metric</th>
                    {comparison.map(c => (
                      <th key={c.id} className="text-center px-5 py-3 text-sm font-medium text-surface-900">
                        {c.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-50">
                  <tr>
                    <td className="px-5 py-3 text-sm text-surface-600">Website</td>
                    {comparison.map(c => (
                      <td key={c.id} className="px-5 py-3 text-sm text-center">
                        <a href={c.website_url} target="_blank" rel="noopener noreferrer" className="text-brand-600 hover:underline">
                          {new URL(c.website_url).hostname}
                        </a>
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-5 py-3 text-sm text-surface-600">Modules</td>
                    {comparison.map(c => (
                      <td key={c.id} className="px-5 py-3 text-sm text-center">
                        <div className="flex flex-wrap justify-center gap-1">
                          {c.modules.map((m: string) => (
                            <span key={m} className="text-xs bg-surface-100 text-surface-600 px-1.5 py-0.5 rounded">{m}</span>
                          ))}
                        </div>
                      </td>
                    ))}
                  </tr>
                  <tr className="bg-surface-50">
                    <td className="px-5 py-3 text-sm font-medium text-surface-900">Services</td>
                    {comparison.map(c => (
                      <td key={c.id} className="px-5 py-3 text-sm text-center font-medium text-surface-900">{c.services_count}</td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-5 py-3 text-sm font-medium text-surface-900">Pricing</td>
                    {comparison.map(c => (
                      <td key={c.id} className="px-5 py-3 text-sm text-center font-medium text-surface-900">{c.pricing_count}</td>
                    ))}
                  </tr>
                  <tr className="bg-surface-50">
                    <td className="px-5 py-3 text-sm font-medium text-surface-900">Social Profiles</td>
                    {comparison.map(c => (
                      <td key={c.id} className="px-5 py-3 text-sm text-center font-medium text-surface-900">{c.social_count}</td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-5 py-3 text-sm font-medium text-surface-900">Content</td>
                    {comparison.map(c => (
                      <td key={c.id} className="px-5 py-3 text-sm text-center font-medium text-surface-900">{c.content_count}</td>
                    ))}
                  </tr>
                  <tr className="bg-brand-50">
                    <td className="px-5 py-3 text-sm font-semibold text-brand-900">Total Entities</td>
                    {comparison.map(c => (
                      <td key={c.id} className="px-5 py-3 text-sm text-center font-semibold text-brand-900">{totalEntities(c)}</td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card p-5">
              <h3 className="font-semibold text-surface-900 mb-4">Data Coverage</h3>
              <BarChart
                data={comparison.map((c, i) => ({
                  label: c.name.length > 12 ? c.name.slice(0, 12) + '...' : c.name,
                  value: totalEntities(c),
                  color: ['bg-brand-500', 'bg-emerald-500', 'bg-purple-500', 'bg-amber-500'][i],
                }))}
                height={150}
              />
            </div>
            <div className="card p-5">
              <h3 className="font-semibold text-surface-900 mb-4">Services vs Pricing</h3>
              <BarChart
                data={comparison.flatMap(c => [
                  { label: `${c.name.slice(0, 8)} Svc`, value: c.services_count, color: 'bg-blue-500' },
                  { label: `${c.name.slice(0, 8)} Prn`, value: c.pricing_count, color: 'bg-emerald-500' },
                ])}
                height={150}
              />
            </div>
          </div>
        </>
      )}

      {!loading && selectedIds.length >= 2 && comparison.length < 2 && (
        <div className="card p-8 text-center text-surface-400">
          No data available for the selected competitors.
        </div>
      )}

      {selectedIds.length < 2 && (
        <div className="card p-8 text-center text-surface-400">
          Select at least 2 competitors to compare.
        </div>
      )}
    </div>
  )
}
