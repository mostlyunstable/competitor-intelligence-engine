import { useParams, useNavigate } from 'react-router-dom'
import { useState, useCallback } from 'react'
import { usePolling } from '../hooks'
import { api } from '../lib/api'
import { formatDate, timeAgo } from '../lib/utils'
import {
  ArrowLeft, Globe, Play, Edit, ExternalLink, Clock,
  CheckCircle, XCircle, Code, DollarSign, FileText,
  Users, Share2, Database, History, RefreshCw, GitCompare,
  Brain, Plus, Minus
} from 'lucide-react'

export default function CompetitorProfilePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const competitorId = parseInt(id || '0')

  const { data, loading, refresh } = usePolling(() => api.getCompetitor(competitorId), 30000)
  const { data: extracted, refresh: refreshExtracted } = usePolling(() => api.getExtracted(competitorId), 60000)
  const { data: changes } = usePolling(() => api.getChanges(competitorId, 20), 30000)
  const { data: aiInsight } = usePolling(() => api.getAiInsights(competitorId).catch(() => null), 60000)
  const { data: scoreData } = usePolling(() => api.getCompetitorScore(competitorId).catch(() => null), 60000)
  const [refreshing, setRefreshing] = useState(false)

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await Promise.all([refresh(), refreshExtracted()])
    } finally {
      setRefreshing(false)
    }
  }, [refresh, refreshExtracted])

  if (loading && !data) {
    return <div className="space-y-4">{[...Array(3)].map((_, i) => <div key={i} className="skeleton h-32 w-full" />)}</div>
  }

  if (!data) return <div className="text-center py-12 text-surface-500">Competitor not found</div>

  const { competitor: c, services, pricing, content, social, tech_stack, sources, pages, collection_logs } = data

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/competitors')} className="p-2 hover:bg-surface-100 rounded-lg">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-surface-900">{c.name}</h1>
            {c.enabled ? <span className="badge-success">Active</span> : <span className="badge-danger">Disabled</span>}
          </div>
          <div className="flex items-center gap-2 text-sm text-surface-500 mt-1">
            <Globe size={14} />
            <a href={c.website_url} target="_blank" rel="noopener noreferrer" className="hover:text-brand-600 flex items-center gap-1">
              {c.website_url} <ExternalLink size={12} />
            </a>
          </div>
        </div>
        <button onClick={handleRefresh} disabled={refreshing} className="btn-secondary disabled:opacity-50">
          <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} /> Refresh
        </button>
        <button onClick={async () => { await api.triggerCollection(competitorId) }} className="btn-primary">
          <Play size={16} /> Collect Now
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {[
          { label: 'Services', value: services?.length || 0, icon: Code, color: 'text-purple-600' },
          { label: 'Pricing', value: pricing?.length || 0, icon: DollarSign, color: 'text-emerald-600' },
          { label: 'Content', value: content?.length || 0, icon: FileText, color: 'text-brand-600' },
          { label: 'Social', value: social?.length || 0, icon: Share2, color: 'text-pink-600' },
          { label: 'Tech Stack', value: tech_stack?.length || 0, icon: Database, color: 'text-orange-600' },
          { label: 'Sources', value: sources?.length || 0, icon: Globe, color: 'text-surface-600' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="stat-card">
            <Icon size={18} className={color} />
            <div className="text-xl font-bold text-surface-900">{value}</div>
            <div className="text-xs text-surface-500">{label}</div>
          </div>
        ))}
      </div>

      {/* Competitor Score */}
      {scoreData && (
        <div className="card">
          <div className="px-5 py-4 border-b border-surface-100 flex items-center gap-2">
            <Brain size={16} className="text-brand-600" />
            <h2 className="font-semibold text-surface-900">Competitor Score</h2>
          </div>
          <div className="p-5">
            <div className="flex items-center gap-6 mb-4">
              <div className="text-center">
                <div className="text-4xl font-bold text-surface-900">{scoreData.score.total.toFixed(1)}</div>
                <div className="text-sm text-surface-500">Total Score</div>
              </div>
              <div className="text-center">
                <div className={`text-4xl font-bold ${
                  scoreData.score.grade === 'A' ? 'text-green-600' :
                  scoreData.score.grade === 'B' ? 'text-blue-600' :
                  scoreData.score.grade === 'C' ? 'text-yellow-600' :
                  scoreData.score.grade === 'D' ? 'text-orange-600' :
                  'text-red-600'
                }`}>{scoreData.score.grade}</div>
                <div className="text-sm text-surface-500">Grade</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-semibold text-surface-900">{scoreData.score.tier}</div>
                <div className="text-sm text-surface-500">Tier</div>
              </div>
              {scoreData.location.is_chennai && (
                <div className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                  Chennai Based
                </div>
              )}
              {scoreData.location.is_indian && !scoreData.location.is_chennai && (
                <div className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                  India Based
                </div>
              )}
            </div>

            {/* Score Breakdown */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {[
                { label: 'Location', score: scoreData.score.breakdown.location.score, color: 'bg-green-500' },
                { label: 'Digital', score: scoreData.score.breakdown.digital_presence.score, color: 'bg-blue-500' },
                { label: 'Service', score: scoreData.score.breakdown.service_quality.score, color: 'bg-purple-500' },
                { label: 'Trust', score: scoreData.score.breakdown.trust.score, color: 'bg-orange-500' },
                { label: 'Market', score: scoreData.score.breakdown.market_relevance.score, color: 'bg-pink-500' },
              ].map(({ label, score, color }) => (
                <div key={label} className="text-center">
                  <div className="relative h-2 bg-surface-100 rounded-full overflow-hidden mb-2">
                    <div className={`absolute left-0 top-0 h-full ${color}`} style={{ width: `${score}%` }} />
                  </div>
                  <div className="text-sm font-medium text-surface-700">{score.toFixed(0)}%</div>
                  <div className="text-xs text-surface-500">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="space-y-6">
        {/* Services */}
        {services?.length > 0 && (
          <div className="card">
            <div className="px-5 py-4 border-b border-surface-100 flex items-center gap-2">
              <Code size={16} className="text-purple-600" />
              <h2 className="font-semibold text-surface-900">Services ({services.length})</h2>
            </div>
            <div className="divide-y divide-surface-50">
              {services.map((s: any) => (
                <div key={s.id} className="px-5 py-3">
                  <div className="font-medium text-sm text-surface-900">{s.name}</div>
                  {s.description && <div className="text-xs text-surface-500 mt-1">{s.description}</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pricing */}
        {pricing?.length > 0 && (
          <div className="card">
            <div className="px-5 py-4 border-b border-surface-100 flex items-center gap-2">
              <DollarSign size={16} className="text-emerald-600" />
              <h2 className="font-semibold text-surface-900">Pricing ({pricing.length})</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-surface-50">
                  <tr>
                    <th className="table-header">Service</th>
                    <th className="table-header">Price</th>
                    <th className="table-header">Currency</th>
                    <th className="table-header">Category</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-50">
                  {pricing.map((p: any) => (
                    <tr key={p.id}>
                      <td className="table-cell font-medium">{p.service_name}</td>
                      <td className="table-cell">{p.base_price || '-'}</td>
                      <td className="table-cell">{p.currency || '-'}</td>
                      <td className="table-cell">{p.category || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tech Stack */}
        {tech_stack?.length > 0 && (
          <div className="card">
            <div className="px-5 py-4 border-b border-surface-100 flex items-center gap-2">
              <Database size={16} className="text-orange-600" />
              <h2 className="font-semibold text-surface-900">Technology Stack ({tech_stack.length})</h2>
            </div>
            <div className="p-5 flex flex-wrap gap-2">
              {tech_stack.map((t: any) => (
                <div key={t.id} className="px-3 py-2 bg-surface-50 rounded-lg border border-surface-200">
                  <div className="text-sm font-medium text-surface-900">{t.technology_name}</div>
                  {t.category && <div className="text-xs text-surface-500">{t.category}</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Content */}
        {content?.length > 0 && (
          <div className="card">
            <div className="px-5 py-4 border-b border-surface-100 flex items-center gap-2">
              <FileText size={16} className="text-brand-600" />
              <h2 className="font-semibold text-surface-900">Content ({content.length})</h2>
            </div>
            <div className="divide-y divide-surface-50 max-h-80 overflow-auto">
              {content.map((c: any) => (
                <div key={c.id} className="px-5 py-3 flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-surface-900">{c.title}</div>
                    <div className="text-xs text-surface-400">{c.content_type}</div>
                  </div>
                  <a href={c.url} target="_blank" rel="noopener noreferrer" className="text-brand-600 hover:underline text-xs flex items-center gap-1">
                    View <ExternalLink size={10} />
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Social */}
        {social?.length > 0 && (
          <div className="card">
            <div className="px-5 py-4 border-b border-surface-100 flex items-center gap-2">
              <Share2 size={16} className="text-pink-600" />
              <h2 className="font-semibold text-surface-900">Social Profiles ({social.length})</h2>
            </div>
            <div className="divide-y divide-surface-50">
              {social.map((s: any) => (
                <div key={s.id} className="px-5 py-3 flex items-center justify-between">
                  <div>
                    <span className="badge-info">{s.platform}</span>
                    <span className="text-sm text-surface-900 ml-2">{s.username || s.url}</span>
                  </div>
                  <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-brand-600 hover:underline text-xs flex items-center gap-1">
                    Visit <ExternalLink size={10} />
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Collection History */}
        {collection_logs?.length > 0 && (
          <div className="card">
            <div className="px-5 py-4 border-b border-surface-100 flex items-center gap-2">
              <History size={16} className="text-surface-600" />
              <h2 className="font-semibold text-surface-900">Collection History ({collection_logs.length})</h2>
            </div>
            <div className="divide-y divide-surface-50 max-h-80 overflow-auto">
              {collection_logs.map((l: any) => (
                <div key={l.id} className="px-5 py-3 flex items-center gap-3">
                  {l.success ? (
                    <CheckCircle size={16} className="text-emerald-500" />
                  ) : (
                    <XCircle size={16} className="text-red-500" />
                  )}
                  <div className="flex-1">
                    <div className="text-sm text-surface-900">
                      {l.success ? 'Successful' : 'Failed'} collection
                    </div>
                    <div className="text-xs text-surface-400">
                      {formatDate(l.start_time)} {l.duration_seconds ? `(${l.duration_seconds.toFixed(1)}s)` : ''}
                    </div>
                  </div>
                  <div className="text-sm text-surface-500">{l.records_collected} records</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Changes */}
        {changes && changes.length > 0 && (
          <div className="card">
            <div className="px-5 py-4 border-b border-surface-100 flex items-center gap-2">
              <GitCompare size={16} className="text-blue-600" />
              <h2 className="font-semibold text-surface-900">Recent Changes ({changes.length})</h2>
            </div>
            <div className="divide-y divide-surface-50 max-h-80 overflow-auto">
              {changes.map((ch: any) => (
                <div key={ch.id} className="px-5 py-3 flex items-center gap-3">
                  <div className="flex-shrink-0">
                    {ch.change_type === 'added' ? (
                      <Plus size={16} className="text-emerald-500" />
                    ) : ch.change_type === 'removed' ? (
                      <Minus size={16} className="text-red-500" />
                    ) : (
                      <GitCompare size={16} className="text-blue-500" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="text-sm text-surface-900">
                      <span className="font-medium">{ch.entity_type}</span>
                      {ch.entity_name && <span className="text-surface-600"> — {ch.entity_name}</span>}
                    </div>
                    <div className="text-xs text-surface-400">{ch.change_type}</div>
                  </div>
                  <div className="text-xs text-surface-400">{timeAgo(ch.detected_at)}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AI Insights */}
        {aiInsight && (
          <div className="card">
            <div className="px-5 py-4 border-b border-surface-100 flex items-center gap-2">
              <Brain size={16} className="text-brand-600" />
              <h2 className="font-semibold text-surface-900">AI Insights</h2>
              <span className="ml-auto text-xs text-surface-500">
                Confidence: {(aiInsight.confidence_score * 100).toFixed(0)}%
              </span>
            </div>
            <div className="p-5 space-y-4">
              {aiInsight.summary && (
                <div>
                  <div className="text-xs font-medium text-surface-500 uppercase mb-1">Summary</div>
                  <p className="text-sm text-surface-700">{aiInsight.summary}</p>
                </div>
              )}
              {aiInsight.market_position && (
                <div>
                  <div className="text-xs font-medium text-surface-500 uppercase mb-1">Market Position</div>
                  <p className="text-sm text-surface-700">{aiInsight.market_position}</p>
                </div>
              )}
              {aiInsight.key_differentiators?.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-surface-500 uppercase mb-1">Key Differentiators</div>
                  <ul className="space-y-1">
                    {aiInsight.key_differentiators.map((d: string, i: number) => (
                      <li key={i} className="text-sm text-surface-700 flex items-start gap-2">
                        <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-brand-500 flex-shrink-0" />
                        {d}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {aiInsight.recommendations?.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-surface-500 uppercase mb-1">Recommendations</div>
                  <ul className="space-y-1">
                    {aiInsight.recommendations.map((r: string, i: number) => (
                      <li key={i} className="text-sm text-surface-700 flex items-start gap-2">
                        <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0" />
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
