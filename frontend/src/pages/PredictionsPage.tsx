import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Lightbulb, Target, BarChart3, Zap } from 'lucide-react'

interface TrendSummary { category: string; direction: string; strength: number; description: string }
interface GrowthSummary { competitor_id: number; competitor_name?: string; growth_level: string; growth_score: number; growth_percentage: string; confidence_score: number }
interface RiskSummary { competitor_name?: string; risk_type: string; risk_level: string; risk_score: number; business_impact: string }
interface OppSummary { title: string; opportunity_type: string; opportunity_score: number; priority: string }
interface RecSummary { title: string; category: string; confidence_score: number; priority: string }

export default function PredictionsPage() {
  const [trends, setTrends] = useState<TrendSummary[]>([])
  const [growth, setGrowth] = useState<GrowthSummary[]>([])
  const [risks, setRisks] = useState<RiskSummary[]>([])
  const [opps, setOpps] = useState<OppSummary[]>([])
  const [recs, setRecs] = useState<RecSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  useEffect(() => { loadAll() }, [])

  const loadAll = async () => {
    setLoading(true)
    try {
      const [t, g, r, o, rc] = await Promise.all([
        api.getMarketTrends(30).catch(() => null),
        api.getGrowthForecasts().catch(() => []),
        api.getAllRisks().catch(() => []),
        api.getOpportunities().catch(() => []),
        api.getAllRecommendations().catch(() => []),
      ])
      if (t) setTrends([...(t.pricing_trends || []), ...(t.service_trends || [])].slice(0, 3))
      setGrowth(g.slice(0, 5))
      setRisks(r.filter((x: RiskSummary) => x.risk_level === 'critical' || x.risk_level === 'high').slice(0, 5))
      setOpps(o.slice(0, 3))
      setRecs(rc.slice(0, 5))
    } catch { /* partial data is fine */ }
    setLoading(false)
  }

  const handleGenerate = async () => {
    setGenerating(true)
    try { await api.generatePredictions(); await loadAll() } catch { /* ignore */ }
    setGenerating(false)
  }

  const riskColor = (l: string) => {
    if (l === 'critical') return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
    if (l === 'high') return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
    return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
  }

  const priorityColor = (p: string) => {
    if (p === 'high') return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
    if (p === 'medium') return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
    return 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400'
  }

  const trendIcon = (d: string) => {
    if (d === 'increasing' || d === 'emerging') return <TrendingUp size={14} className="text-green-500" />
    if (d === 'decreasing') return <TrendingDown size={14} className="text-red-500" />
    return <Minus size={14} className="text-surface-400" />
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" /></div>
  }

  const hasData = risks.length || growth.length || recs.length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Predictions</h1>
          <p className="text-sm text-surface-500 mt-1">AI-powered competitive intelligence</p>
        </div>
        <button onClick={handleGenerate} disabled={generating} className="btn-primary">
          <Zap size={16} />
          {generating ? 'Generating...' : 'Generate'}
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-2 mb-1"><AlertTriangle className="w-4 h-4 text-red-500" /><span className="text-xs text-surface-500">Risks</span></div>
          <p className="text-2xl font-bold text-surface-900 dark:text-white">{risks.length}</p>
        </div>
        <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-2 mb-1"><Lightbulb className="w-4 h-4 text-yellow-500" /><span className="text-xs text-surface-500">Opportunities</span></div>
          <p className="text-2xl font-bold text-surface-900 dark:text-white">{opps.length}</p>
        </div>
        <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-2 mb-1"><Target className="w-4 h-4 text-brand-500" /><span className="text-xs text-surface-500">Recommendations</span></div>
          <p className="text-2xl font-bold text-surface-900 dark:text-white">{recs.length}</p>
        </div>
        <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-2 mb-1"><BarChart3 className="w-4 h-4 text-blue-500" /><span className="text-xs text-surface-500">Growing</span></div>
          <p className="text-2xl font-bold text-surface-900 dark:text-white">{growth.filter(g => g.growth_level === 'high').length}</p>
        </div>
      </div>

      {!hasData && (
        <div className="bg-white dark:bg-surface-900 rounded-xl p-8 border border-surface-200 dark:border-surface-700 text-center">
          <Zap className="w-8 h-8 text-surface-400 mx-auto mb-3" />
          <p className="text-surface-500">No predictions generated yet. Click Generate to analyze your competitive landscape.</p>
        </div>
      )}

      {/* Top Risks — most actionable */}
      {risks.length > 0 && (
        <div className="bg-white dark:bg-surface-900 rounded-xl border border-surface-200 dark:border-surface-700 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-200 dark:border-surface-700 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            <h2 className="font-semibold text-surface-900 dark:text-white">Risks to Watch</h2>
          </div>
          <div className="divide-y divide-surface-200 dark:divide-surface-700">
            {risks.map((r, i) => (
              <div key={i} className="px-6 py-3 flex items-center justify-between hover:bg-surface-50 dark:hover:bg-surface-800/50">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-surface-900 dark:text-white truncate">{r.competitor_name}</p>
                  <p className="text-xs text-surface-500 truncate">{r.business_impact}</p>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  <span className="text-xs text-surface-400 whitespace-nowrap">{r.risk_type.replace(/_/g, ' ')}</span>
                  <span className={`text-xs px-2 py-1 rounded-full whitespace-nowrap font-medium ${riskColor(r.risk_level)}`}>{r.risk_level}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Growth + Recommendations — side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {growth.length > 0 && (
          <div className="bg-white dark:bg-surface-900 rounded-xl border border-surface-200 dark:border-surface-700 overflow-hidden">
            <div className="px-6 py-4 border-b border-surface-200 dark:border-surface-700 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-blue-500" />
              <h2 className="font-semibold text-surface-900 dark:text-white">Growth Signals</h2>
            </div>
            <div className="divide-y divide-surface-200 dark:divide-surface-700">
              {growth.slice(0, 4).map((g, i) => (
                <div key={i} className="px-6 py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-surface-900 dark:text-white">{g.competitor_name}</p>
                    <p className="text-xs text-surface-500">{g.growth_percentage} · {(g.confidence_score * 100).toFixed(0)}% confidence</p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${priorityColor(g.growth_level)}`}>{g.growth_level}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {recs.length > 0 && (
          <div className="bg-white dark:bg-surface-900 rounded-xl border border-surface-200 dark:border-surface-700 overflow-hidden">
            <div className="px-6 py-4 border-b border-surface-200 dark:border-surface-700 flex items-center gap-2">
              <Target className="w-4 h-4 text-brand-500" />
              <h2 className="font-semibold text-surface-900 dark:text-white">Recommendations</h2>
            </div>
            <div className="divide-y divide-surface-200 dark:divide-surface-700">
              {recs.slice(0, 4).map((r, i) => (
                <div key={i} className="px-6 py-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">{r.category}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${priorityColor(r.priority)}`}>{r.priority}</span>
                  </div>
                  <p className="text-sm font-medium text-surface-900 dark:text-white">{r.title}</p>
                  <p className="text-xs text-surface-500">{(r.confidence_score * 100).toFixed(0)}% confidence</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Market Trends — compact row */}
      {trends.length > 0 && (
        <div className="bg-white dark:bg-surface-900 rounded-xl p-5 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-brand-500" />
            <h2 className="font-semibold text-surface-900 dark:text-white text-sm">Market Trends</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {trends.map((t, i) => (
              <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-50 dark:bg-surface-800 rounded-full text-xs">
                {trendIcon(t.direction)}
                <span className="text-surface-700 dark:text-surface-300 font-medium">{t.category}</span>
                <span className="text-surface-400">·</span>
                <span className="text-surface-500">{t.direction}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
