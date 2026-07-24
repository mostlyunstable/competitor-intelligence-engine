import { useState, useCallback, useEffect } from 'react'
import { usePolling } from '../hooks'
import { api } from '../lib/api'
import {
  Brain, Sparkles, Target, TrendingUp, AlertTriangle,
  Lightbulb, BarChart3, Shield, RefreshCw, Zap, Loader2,
  Clock, ThumbsUp, ThumbsDown, Coins, Download
} from 'lucide-react'

export default function AiInsightsPage() {
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const { data: competitors } = usePolling(
    () => api.getCompetitors({ page_size: 50, enabled: true }),
    60000
  )

  const competitorList = competitors?.competitors || competitors?.items || []

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Brain size={24} className="text-brand-600" />
        <h1 className="text-2xl font-bold text-surface-900">AI Insights</h1>
      </div>

      <p className="text-sm text-surface-500">
        Select a competitor to analyze their scraped data with AI. The analysis covers market position, pricing, strengths, weaknesses, and strategic recommendations.
      </p>

      {/* Competitor selector */}
      <div className="flex flex-wrap gap-2">
        {competitorList.map((c: any) => (
          <button
            key={c.id}
            onClick={() => setSelectedId(c.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
              selectedId === c.id
                ? 'bg-brand-600 text-white border-brand-600'
                : 'bg-white text-surface-700 border-surface-200 hover:border-brand-300'
            }`}
          >
            {c.name}
          </button>
        ))}
      </div>

      {/* Insight panel */}
      {selectedId && <InsightPanel key={selectedId} competitorId={selectedId} />}

      {!selectedId && (
        <div className="card p-12 text-center">
          <Brain size={48} className="mx-auto text-surface-300 mb-4" />
          <h3 className="text-lg font-medium text-surface-700">Select a competitor to view AI insights</h3>
        </div>
      )}
    </div>
  )
}


function InsightPanel({ competitorId }: { competitorId: number }) {
  const { data: existing, loading, error, refresh } = usePolling(
    () => api.getAiInsights(competitorId).catch(() => null),
    60000
  )
  const [analyzing, setAnalyzing] = useState(false)
  const [insight, setInsight] = useState<any>(existing)
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null)

  // Sync insight from polling whenever it updates
  useEffect(() => {
    if (existing) setInsight(existing)
  }, [existing])

  // Auto-trigger analysis on mount if no insight exists
  useEffect(() => {
    if (!loading && !existing && !analyzeError) {
      handleAnalyze()
    }
  }, [loading]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleAnalyze = useCallback(async () => {
    setAnalyzing(true)
    setAnalyzeError(null)
    setFeedback(null)
    try {
      await api.analyzeCompetitor(competitorId)
      // Poll until done
      let attempts = 0
      const poll = setInterval(async () => {
        attempts++
        try {
          const result = await api.getAiInsights(competitorId)
          if (result?.processing_status === 'completed' || result?.processing_status === 'failed' || attempts > 30) {
            clearInterval(poll)
            setInsight(result)
            setAnalyzing(false)
            refresh()
          }
        } catch {
          if (attempts > 30) { clearInterval(poll); setAnalyzing(false) }
        }
      }, 2000)
    } catch (e: any) {
      setAnalyzeError(e.message || 'Analysis failed')
      setAnalyzing(false)
    }
  }, [competitorId, refresh])

  const handleFeedback = useCallback(async (rating: 'up' | 'down') => {
    if (!insight?.id) return
    try {
      await fetch(`/api/ai/insight/${insight.id}/feedback?rating=${rating === 'up' ? 2 : 1}`, {
        method: 'POST',
        headers: { 'Authorization': `Basic ${localStorage.getItem('auth') || ''}` },
      })
      setFeedback(rating)
    } catch {}
  }, [insight])

  const handleExport = useCallback(() => {
    if (!insight) return
    const text = [
      `# AI Intelligence Report`,
      `Competitor ID: ${competitorId}`,
      `Confidence: ${(insight.confidence_score * 100).toFixed(0)}%`,
      `Model: ${insight.llm_model}`,
      `Tokens: ${insight.total_tokens?.toLocaleString() || 'N/A'}`,
      `Cost: $${insight.estimated_cost_usd?.toFixed(4) || 'N/A'}`,
      '',
      `## Summary`,
      insight.summary,
      '',
      `## Market Position`,
      insight.market_position,
      '',
      `## Key Differentiators`,
      ...(insight.key_differentiators || []).map((d: string) => `- ${d}`),
      '',
      `## Feature Gaps`,
      ...(insight.feature_gaps || []).map((g: string) => `- ${g}`),
      '',
      `## Strategic Moves`,
      ...(insight.strategic_moves || []).map((m: string) => `- ${m}`),
      '',
      `## Recommendations`,
      ...(insight.recommendations || []).map((r: string) => `- ${r}`),
      '',
      `## Latest Updates`,
      ...(insight.latest_updates || []).map((u: string) => `- ${u}`),
    ].join('\n')

    const blob = new Blob([text], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ai-insight-${competitorId}.md`
    a.click()
    URL.revokeObjectURL(url)
  }, [insight, competitorId])

  if (loading && !insight) {
    return <div className="skeleton h-64 w-full" />
  }

  return (
    <div className="space-y-4">
      {/* Analyze button */}
      <div className="card p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {insight?.confidence_score != null && (
            <span className="text-sm text-surface-600">
              Confidence: <span className="font-medium">{(insight.confidence_score * 100).toFixed(0)}%</span>
            </span>
          )}
          {insight?.llm_model && (
            <span className="text-xs text-surface-400">via {insight.llm_model}</span>
          )}
        </div>
        <button onClick={handleAnalyze} disabled={analyzing} className="btn-primary disabled:opacity-50">
          {analyzing ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
          {analyzing ? 'Analyzing...' : insight ? 'Re-analyze' : 'Analyze'}
        </button>
      </div>

      {analyzeError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-700">{analyzeError}</p>
        </div>
      )}

      {!insight && !analyzing && (
        <div className="card p-8 text-center">
          <p className="text-surface-500 mb-4">No insights yet for this competitor.</p>
          <button onClick={handleAnalyze} className="btn-primary">
            <Sparkles size={16} /> Generate Insights
          </button>
        </div>
      )}

      {analyzing && !insight && (
        <div className="card p-12 text-center">
          <Loader2 size={40} className="mx-auto text-brand-600 animate-spin mb-4" />
          <h3 className="text-lg font-medium text-surface-700">Analyzing competitor data...</h3>
          <p className="text-sm text-surface-500 mt-1">AI is reviewing scraped services, pricing, content, and social data</p>
        </div>
      )}

      {insight && (
        <>
          {/* Confidence Gauge */}
          {insight.confidence_score != null && (
            <div className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-surface-700">Confidence Score</span>
                <span className="text-lg font-bold text-surface-900">{(insight.confidence_score * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full bg-surface-200 rounded-full h-2.5">
                <div
                  className={`h-2.5 rounded-full transition-all ${
                    insight.confidence_score >= 0.8 ? 'bg-green-500' :
                    insight.confidence_score >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${insight.confidence_score * 100}%` }}
                />
              </div>
            </div>
          )}

          {insight.summary && <Card icon={Target} color="text-brand-600" title="Summary">
            <p className="text-sm text-surface-700 leading-relaxed">{insight.summary}</p>
          </Card>}

          {insight.market_position && <Card icon={TrendingUp} color="text-emerald-600" title="Market Position">
            <p className="text-sm text-surface-700">{insight.market_position}</p>
          </Card>}

          {insight.key_differentiators?.length > 0 && <Card icon={Zap} color="text-yellow-600" title="Key Differentiators">
            <Bullets items={insight.key_differentiators} color="bg-yellow-500" />
          </Card>}

          {insight.feature_gaps?.length > 0 && <Card icon={AlertTriangle} color="text-orange-600" title="Feature Gaps">
            <Bullets items={insight.feature_gaps} color="bg-orange-500" />
          </Card>}

          {insight.pricing_analysis && Object.keys(insight.pricing_analysis).length > 0 && (
            <Card icon={BarChart3} color="text-purple-600" title="Pricing Analysis">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(insight.pricing_analysis).map(([key, value]) => (
                  <div key={key} className="bg-surface-50 rounded-lg p-3">
                    <div className="text-xs font-medium text-surface-500 uppercase">{key.replace(/_/g, ' ')}</div>
                    <div className="text-sm text-surface-900 mt-1">{String(value)}</div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {insight.strategic_moves?.length > 0 && <Card icon={Shield} color="text-blue-600" title="Strategic Moves">
            <Bullets items={insight.strategic_moves} color="bg-blue-500" />
          </Card>}

          {insight.recommendations?.length > 0 && <Card icon={Lightbulb} color="text-brand-600" title="Recommendations">
            <Bullets items={insight.recommendations} color="bg-brand-500" />
          </Card>}

          {insight.latest_updates?.length > 0 && <Card icon={Clock} color="text-surface-600" title="Latest Updates">
            <Bullets items={insight.latest_updates} color="bg-surface-500" />
          </Card>}

          {/* Cost & Feedback */}
          <div className="card p-4 flex items-center justify-between">
            <div className="flex items-center gap-4 text-sm text-surface-500">
              {insight.total_tokens > 0 && (
                <span className="flex items-center gap-1">
                  <Coins size={14} />
                  {insight.total_tokens.toLocaleString()} tokens
                </span>
              )}
              {insight.estimated_cost_usd > 0 && (
                <span>${insight.estimated_cost_usd.toFixed(4)}</span>
              )}
              {insight.llm_model && (
                <span className="text-xs text-surface-400">{insight.llm_model}</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleExport}
                className="p-1.5 text-surface-400 hover:text-surface-600 hover:bg-surface-50 rounded-lg"
                title="Export report"
              >
                <Download size={16} />
              </button>
              <span className="text-xs text-surface-400 mr-1">Helpful?</span>
              <button
                onClick={() => handleFeedback('up')}
                disabled={feedback !== null}
                className={`p-1.5 rounded-lg transition-colors ${feedback === 'up' ? 'bg-green-100 text-green-600' : feedback ? 'text-surface-300' : 'text-surface-400 hover:text-green-600 hover:bg-green-50'}`}
                title="Yes, helpful"
              >
                <ThumbsUp size={16} />
              </button>
              <button
                onClick={() => handleFeedback('down')}
                disabled={feedback !== null}
                className={`p-1.5 rounded-lg transition-colors ${feedback === 'down' ? 'bg-red-100 text-red-600' : feedback ? 'text-surface-300' : 'text-surface-400 hover:text-red-600 hover:bg-red-50'}`}
                title="Not helpful"
              >
                <ThumbsDown size={16} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}


function Card({ icon: Icon, color, title, children }: {
  icon: typeof Target; color: string; title: string; children: React.ReactNode
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-3">
        <Icon size={16} className={color} />
        <h3 className="font-semibold text-surface-900">{title}</h3>
      </div>
      {children}
    </div>
  )
}


function Bullets({ items, color }: { items: string[]; color: string }) {
  return (
    <ul className="space-y-2">
      {items.map((item: string, i: number) => (
        <li key={i} className="flex items-start gap-2 text-sm text-surface-700">
          <span className={`mt-1.5 w-1.5 h-1.5 rounded-full ${color} flex-shrink-0`} />
          {item}
        </li>
      ))}
    </ul>
  )
}
