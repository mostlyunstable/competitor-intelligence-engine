import { useState, useEffect, useCallback, useMemo } from 'react'
import { api } from '../lib/api'
import { safeHostname } from '../lib/utils'
import { GitCompare, Check, Plus, X, RefreshCw, BarChart3, PieChart, Radar } from 'lucide-react'
import type { Competitor } from '../types'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadarChart, Radar as RechartsRadar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  PieChart as RechartsPie, Pie, Cell,
  Treemap,
} from 'recharts'

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

const COLORS = ['#ff8811', '#10b981', '#8b5cf6', '#f59e0b']

export default function CompetitorComparePage() {
  const [competitors, setCompetitors] = useState<Competitor[]>([])
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [comparison, setComparison] = useState<CompetitorData[]>([])
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [activeChart, setActiveChart] = useState<'bar' | 'radar' | 'pie' | 'treemap'>('bar')

  const loadCompetitors = useCallback(async () => {
    try {
      const data = await api.getCompetitors({ page_size: 50 })
      setCompetitors(data.competitors || data.items || [])
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
      }
    } catch {
      // errors shown by usePolling
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [loadCompetitors, selectedIds])

  useEffect(() => {
    if (selectedIds.length >= 2) {
      setLoading(true)
      api.compareCompetitors(selectedIds).then(data => {
        setComparison(data)
      }).catch(() => {}).finally(() => setLoading(false))
    } else {
      setComparison([])
    }
  }, [selectedIds])

  const toggleCompetitor = (id: number) => {
    setSelectedIds(prev => {
      if (prev.includes(id)) return prev.filter(i => i !== id)
      if (prev.length >= 4) return prev
      return [...prev, id]
    })
  }

  const totalEntities = (c: CompetitorData) =>
    c.services_count + c.pricing_count + c.social_count + c.content_count

  // Chart data
  const barData = useMemo(() =>
    comparison.map((c, i) => ({
      name: c.name.length > 15 ? c.name.slice(0, 15) + '...' : c.name,
      Services: c.services_count,
      Pricing: c.pricing_count,
      Content: c.content_count,
      Social: c.social_count,
    })),
    [comparison]
  )

  const radarData = useMemo(() => {
    const maxVals = {
      services: Math.max(...comparison.map(c => c.services_count), 1),
      pricing: Math.max(...comparison.map(c => c.pricing_count), 1),
      content: Math.max(...comparison.map(c => c.content_count), 1),
      social: Math.max(...comparison.map(c => c.social_count), 1),
    }
    return ['Services', 'Pricing', 'Content', 'Social'].map(cat => {
      const entry: Record<string, number | string> = { category: cat }
      comparison.forEach(c => {
        const key = cat.toLowerCase() as keyof Pick<CompetitorData, 'services_count' | 'pricing_count' | 'content_count' | 'social_count'>
        const countKey = `${key}_count` as keyof CompetitorData
        entry[c.name] = Math.round(((c[countKey] as number) / maxVals[key as keyof typeof maxVals]) * 100)
      })
      return entry
    })
  }, [comparison])

  const pieData = useMemo(() =>
    comparison.map(c => ({
      name: c.name,
      value: totalEntities(c),
    })),
    [comparison]
  )

  const treemapData = useMemo(() =>
    comparison.flatMap(c => [
      { name: `${c.name} Services`, size: c.services_count, color: COLORS[0] },
      { name: `${c.name} Pricing`, size: c.pricing_count, color: COLORS[1] },
      { name: `${c.name} Content`, size: c.content_count, color: COLORS[2] },
      { name: `${c.name} Social`, size: c.social_count, color: COLORS[3] },
    ]).filter(d => d.size > 0),
    [comparison]
  )

  const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string }) => {
    if (!active || !payload?.length) return null
    return (
      <div className="bg-white dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-lg shadow-lg p-3">
        <p className="text-sm font-medium text-surface-900 dark:text-white mb-1">{label}</p>
        {payload.map((p, i) => (
          <p key={i} className="text-xs" style={{ color: p.color }}>
            {p.name}: {p.value}
          </p>
        ))}
      </div>
    )
  }

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
          {competitors.map((c) => {
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
                      <th key={c.id} className="text-center px-5 py-3 text-sm font-medium text-surface-900">{c.name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-50">
                  <tr>
                    <td className="px-5 py-3 text-sm text-surface-600">Website</td>
                    {comparison.map(c => (
                      <td key={c.id} className="px-5 py-3 text-sm text-center">
                        <a href={c.website_url} target="_blank" rel="noopener noreferrer" className="text-brand-600 hover:underline">
                          {safeHostname(c.website_url)}
                        </a>
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-5 py-3 text-sm text-surface-600">Modules</td>
                    {comparison.map(c => (
                      <td key={c.id} className="px-5 py-3 text-sm text-center">
                        <div className="flex flex-wrap justify-center gap-1">
                          {(c.modules || []).map((m: string) => (
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

          {/* Chart Type Selector */}
          <div className="flex items-center gap-2">
            {[
              { key: 'bar' as const, icon: BarChart3, label: 'Bar' },
              { key: 'radar' as const, icon: Radar, label: 'Radar' },
              { key: 'pie' as const, icon: PieChart, label: 'Pie' },
              { key: 'treemap' as const, icon: BarChart3, label: 'Treemap' },
            ].map(({ key, icon: Icon, label }) => (
              <button
                key={key}
                onClick={() => setActiveChart(key)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  activeChart === key
                    ? 'bg-brand-500 text-white'
                    : 'bg-surface-100 text-surface-600 hover:bg-surface-200'
                }`}
              >
                <Icon size={14} /> {label}
              </button>
            ))}
          </div>

          {/* Interactive Charts */}
          <div className="card p-5">
            {activeChart === 'bar' && (
              <div>
                <h3 className="font-semibold text-surface-900 mb-4">Data Coverage by Category</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={barData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Bar dataKey="Services" fill="#ff8811" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Pricing" fill="#10b981" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Content" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Social" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {activeChart === 'radar' && (
              <div>
                <h3 className="font-semibold text-surface-900 mb-4">Multi-Dimensional Comparison</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#e5e5e5" />
                    <PolarAngleAxis dataKey="category" tick={{ fontSize: 12 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} />
                    {comparison.map((c, i) => (
                      <RechartsRadar
                        key={c.id}
                        name={c.name}
                        dataKey={c.name}
                        stroke={COLORS[i]}
                        fill={COLORS[i]}
                        fillOpacity={0.15}
                      />
                    ))}
                    <Legend />
                    <Tooltip content={<CustomTooltip />} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            )}

            {activeChart === 'pie' && (
              <div>
                <h3 className="font-semibold text-surface-900 mb-4">Total Data Distribution</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <RechartsPie>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={120}
                      paddingAngle={3}
                      dataKey="value"
                      label={({ name, percent }: { name?: string; percent?: number }) => `${name || ''} ${((percent || 0) * 100).toFixed(0)}%`}
                    >
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </RechartsPie>
                </ResponsiveContainer>
              </div>
            )}

            {activeChart === 'treemap' && (
              <div>
                <h3 className="font-semibold text-surface-900 mb-4">Data Volume Treemap</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <Treemap
                    data={treemapData}
                    dataKey="size"
                    nameKey="name"
                    stroke="#fff"
                    fill="#8884d8"
                    content={(props: Record<string, unknown>) => {
                      const x = props.x as number; const y = props.y as number; const width = props.width as number; const height = props.height as number; const name = props.name as string; const color = props.color as string
                      return (
                      <g>
                        <rect x={x} y={y} width={width} height={height} fill={color} stroke="#fff" strokeWidth={2} rx={4} />
                        {width > 60 && height > 30 && (
                          <>
                            <text x={x + width / 2} y={y + height / 2 - 6} textAnchor="middle" fill="#fff" fontSize={11} fontWeight={600}>
                              {(name || '').split(' ').pop()}
                            </text>
                            <text x={x + width / 2} y={y + height / 2 + 10} textAnchor="middle" fill="#fff" fontSize={10} opacity={0.8}>
                              {treemapData.find(d => d.name === name)?.size}
                            </text>
                          </>
                        )}
                      </g>
                    )}}
                  />
                </ResponsiveContainer>
              </div>
            )}
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
