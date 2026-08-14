import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import type { GraphData, GraphStats, MarketCluster, HiddenCompetitor } from '../types'
import { Network, Users, Link, Search, RefreshCw, Eye, Zap } from 'lucide-react'

export default function KnowledgeGraphPage() {
  const [graph, setGraph] = useState<GraphData | null>(null)
  const [clusters, setClusters] = useState<MarketCluster[]>([])
  const [hidden, setHidden] = useState<HiddenCompetitor[]>([])
  const [influence, setInfluence] = useState<Record<string, number>>({})
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<{ id: string; type: string; name: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [building, setBuilding] = useState(false)
  const [activeTab, setActiveTab] = useState<'overview' | 'clusters' | 'hidden' | 'influence'>('overview')

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [g, c, h, inf] = await Promise.all([
        api.getGraph().catch(() => null),
        api.getGraphClusters().catch(() => []),
        api.getHiddenCompetitors().catch(() => []),
        api.getGraphInfluence().catch(() => ({})),
      ])
      setGraph(g)
      setClusters(c)
      setHidden(h)
      setInfluence(inf)
    } catch { /* ignore */ }
    setLoading(false)
  }

  const buildGraph = async () => {
    setBuilding(true)
    try {
      await api.buildGraph()
      await loadData()
    } catch { /* ignore */ }
    setBuilding(false)
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    try {
      setSearchResults(await api.searchGraph(searchQuery))
    } catch { /* ignore */ }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" /></div>
  }

  const stats = graph?.stats

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Knowledge Graph</h1>
          <p className="text-surface-600 dark:text-surface-400 mt-1">Explore competitor relationships, clusters, and influence</p>
        </div>
        <div className="flex gap-2">
          <button onClick={buildGraph} disabled={building} className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium">
            <RefreshCw className={`w-4 h-4 ${building ? 'animate-spin' : ''}`} />
            {building ? 'Building...' : 'Build Graph'}
          </button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
            <p className="text-sm text-surface-500">Total Nodes</p>
            <p className="text-2xl font-bold text-surface-900 dark:text-white">{stats.total_nodes}</p>
          </div>
          <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
            <p className="text-sm text-surface-500">Total Edges</p>
            <p className="text-2xl font-bold text-surface-900 dark:text-white">{stats.total_edges}</p>
          </div>
          <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
            <p className="text-sm text-surface-500">Clusters</p>
            <p className="text-2xl font-bold text-surface-900 dark:text-white">{clusters.length}</p>
          </div>
          <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
            <p className="text-sm text-surface-500">Node Types</p>
            <p className="text-2xl font-bold text-surface-900 dark:text-white">{Object.keys(stats.nodes_by_type).length}</p>
          </div>
        </div>
      )}

      <div className="flex gap-2 border-b border-surface-200 dark:border-surface-700 pb-2">
        {(['overview', 'clusters', 'hidden', 'influence'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${activeTab === tab ? 'bg-brand-500 text-white' : 'text-surface-600 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-800'}`}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="space-y-4">
          <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700">
            <h2 className="text-lg font-semibold text-surface-900 dark:text-white mb-4">Search Graph</h2>
            <div className="flex gap-2">
              <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSearch()}
                className="flex-1 rounded-lg border border-surface-300 dark:border-surface-600 bg-white dark:bg-surface-800 px-3 py-2 text-surface-900 dark:text-white" placeholder="Search nodes..." />
              <button onClick={handleSearch} className="bg-brand-500 text-white px-4 py-2 rounded-lg"><Search className="w-4 h-4" /></button>
            </div>
            {searchResults.length > 0 && (
              <div className="mt-4 space-y-2">
                {searchResults.map(r => (
                  <div key={r.id} className="flex items-center gap-3 p-3 bg-surface-50 dark:bg-surface-800 rounded-lg">
                    <span className="text-xs px-2 py-1 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-400 rounded">{r.type}</span>
                    <span className="text-sm font-medium text-surface-900 dark:text-white">{r.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          {stats && (
            <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700">
              <h2 className="text-lg font-semibold text-surface-900 dark:text-white mb-4">Node Distribution</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(stats.nodes_by_type).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between p-3 bg-surface-50 dark:bg-surface-800 rounded-lg">
                    <span className="text-sm text-surface-700 dark:text-surface-300 capitalize">{type}</span>
                    <span className="text-sm font-bold text-brand-600">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'clusters' && (
        <div className="space-y-4">
          {clusters.length === 0 ? (
            <div className="bg-white dark:bg-surface-900 rounded-xl p-8 border border-surface-200 dark:border-surface-700 text-center">
              <Network className="w-12 h-12 text-surface-300 mx-auto mb-3" />
              <p className="text-surface-500">Build the graph to discover market clusters</p>
            </div>
          ) : clusters.map((c, i) => (
            <div key={i} className="bg-white dark:bg-surface-900 rounded-xl p-5 border border-surface-200 dark:border-surface-700">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-surface-900 dark:text-white">Cluster {i + 1}</h3>
                <span className="text-sm text-surface-500">{c.size} members</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {c.members.map((name, j) => (
                  <span key={j} className="px-3 py-1 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-400 rounded-full text-sm">{name}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'hidden' && (
        <div className="space-y-4">
          {hidden.length === 0 ? (
            <div className="bg-white dark:bg-surface-900 rounded-xl p-8 border border-surface-200 dark:border-surface-700 text-center">
              <Eye className="w-12 h-12 text-surface-300 mx-auto mb-3" />
              <p className="text-surface-500">No hidden competitors detected</p>
            </div>
          ) : hidden.map((h, i) => (
            <div key={i} className="bg-white dark:bg-surface-900 rounded-xl p-5 border border-surface-200 dark:border-surface-700">
              <div className="flex items-center gap-3">
                <Users className="w-5 h-5 text-brand-500" />
                <div>
                  <p className="font-medium text-surface-900 dark:text-white">{h.competitor_a} ↔ {h.competitor_b}</p>
                  <p className="text-sm text-surface-500">{h.shared_categories} shared categories</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'influence' && (
        <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700">
          <h2 className="text-lg font-semibold text-surface-900 dark:text-white mb-4">Influence Scores (PageRank)</h2>
          {Object.keys(influence).length === 0 ? (
            <p className="text-surface-500">Build the graph to see influence scores</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(influence).sort(([, a], [, b]) => b - a).map(([id, score]) => {
                const name = id.replace('competitor:', '')
                return (
                  <div key={id} className="flex items-center gap-3">
                    <span className="text-sm text-surface-700 dark:text-surface-300 w-20 text-right">#{name}</span>
                    <div className="flex-1 bg-surface-200 dark:bg-surface-700 rounded-full h-3">
                      <div className="bg-brand-500 h-3 rounded-full" style={{ width: `${score * 100}%` }} />
                    </div>
                    <span className="text-sm font-medium text-surface-700 dark:text-surface-300 w-12">{(score * 100).toFixed(1)}%</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
