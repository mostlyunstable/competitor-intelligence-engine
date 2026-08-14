import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import type { ForecastReport } from '../types'
import { FileText, Download, RefreshCw, AlertTriangle, Lightbulb, Target, TrendingUp, MapPin } from 'lucide-react'

export default function ForecastReportPage() {
  const [report, setReport] = useState<ForecastReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    loadReport()
  }, [])

  const loadReport = async () => {
    setLoading(true)
    try {
      const data = await api.getForecastReport()
      setReport(data)
    } catch { /* ignore */ }
    setLoading(false)
  }

  const handleRegenerate = async () => {
    setGenerating(true)
    try {
      await api.generatePredictions()
      await loadReport()
    } catch { /* ignore */ }
    setGenerating(false)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-surface-500">Loading forecast report...</div>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Forecast Report</h1>
            <p className="text-sm text-surface-500 mt-1">Comprehensive competitive intelligence forecast</p>
          </div>
          <button onClick={handleRegenerate} disabled={generating} className="btn-primary">
            <RefreshCw size={16} className={generating ? 'animate-spin' : ''} />
            {generating ? 'Generating...' : 'Generate Report'}
          </button>
        </div>
        <div className="card text-center py-12">
          <FileText size={48} className="mx-auto text-surface-300 mb-3" />
          <p className="text-surface-500">No report generated yet. Click "Generate Report" to create one.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">{report.title}</h1>
          <p className="text-sm text-surface-500 mt-1">Generated: {new Date(report.generated_at).toLocaleString()}</p>
        </div>
        <button onClick={handleRegenerate} disabled={generating} className="btn-primary">
          <RefreshCw size={16} className={generating ? 'animate-spin' : ''} />
          {generating ? 'Generating...' : 'Regenerate'}
        </button>
      </div>

      {/* Executive Summary */}
      <div className="card bg-brand-50 dark:bg-brand-900/10 border-brand-200 dark:border-brand-800">
        <h2 className="font-semibold text-surface-900 dark:text-white mb-2">Executive Summary</h2>
        <p className="text-sm text-surface-700 dark:text-surface-300">{report.executive_summary}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risks */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle size={18} className="text-red-500" />
            <h2 className="font-semibold text-surface-900 dark:text-white">Risks ({report.risks.length})</h2>
          </div>
          {report.risks.length === 0 ? (
            <p className="text-sm text-surface-500">No risks identified.</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-auto">
              {report.risks.slice(0, 5).map((r, i) => (
                <div key={i} className="p-2 bg-surface-50 dark:bg-surface-800 rounded text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-surface-900 dark:text-white">{r.competitor_name}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      r.risk_level === 'critical' ? 'bg-red-100 text-red-700' :
                      r.risk_level === 'high' ? 'bg-orange-100 text-orange-700' :
                      'bg-surface-100 text-surface-600'
                    }`}>{r.risk_level}</span>
                  </div>
                  <div className="text-xs text-surface-500">{r.risk_type.replace(/_/g, ' ')}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Opportunities */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Lightbulb size={18} className="text-yellow-500" />
            <h2 className="font-semibold text-surface-900 dark:text-white">Opportunities ({report.opportunities.length})</h2>
          </div>
          {report.opportunities.length === 0 ? (
            <p className="text-sm text-surface-500">No opportunities detected.</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-auto">
              {report.opportunities.slice(0, 5).map((o, i) => (
                <div key={i} className="p-2 bg-surface-50 dark:bg-surface-800 rounded text-sm">
                  <div className="font-medium text-surface-900 dark:text-white">{o.title}</div>
                  <div className="text-xs text-surface-500">Score: {o.opportunity_score.toFixed(0)} | {o.opportunity_type.replace(/_/g, ' ')}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recommendations */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Target size={18} className="text-brand-600" />
            <h2 className="font-semibold text-surface-900 dark:text-white">Recommendations ({report.recommendations.length})</h2>
          </div>
          {report.recommendations.length === 0 ? (
            <p className="text-sm text-surface-500">No recommendations.</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-auto">
              {report.recommendations.slice(0, 5).map((r, i) => (
                <div key={i} className="p-2 bg-surface-50 dark:bg-surface-800 rounded text-sm">
                  <div className="font-medium text-surface-900 dark:text-white">{r.title}</div>
                  <div className="text-xs text-surface-500">{r.category.replace(/_/g, ' ')} | Confidence: {(r.confidence_score * 100).toFixed(0)}%</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Growth Forecasts */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={18} className="text-green-500" />
            <h2 className="font-semibold text-surface-900 dark:text-white">Growth Forecasts ({report.predictions.growth_forecasts.length})</h2>
          </div>
          {report.predictions.growth_forecasts.length === 0 ? (
            <p className="text-sm text-surface-500">No growth data.</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-auto">
              {report.predictions.growth_forecasts.slice(0, 5).map((g, i) => (
                <div key={i} className="p-2 bg-surface-50 dark:bg-surface-800 rounded text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-surface-900 dark:text-white">{g.competitor_name}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      g.growth_level === 'high' ? 'bg-green-100 text-green-700' :
                      g.growth_level === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-surface-100 text-surface-600'
                    }`}>{g.growth_level}</span>
                  </div>
                  <div className="text-xs text-surface-500">{g.growth_percentage} | Score: {g.growth_score.toFixed(0)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Business Actions */}
      {report.business_actions.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-surface-900 dark:text-white mb-4">Recommended Business Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {report.business_actions.map((a, i) => (
              <div key={i} className="p-3 bg-surface-50 dark:bg-surface-800 rounded-lg border border-surface-200 dark:border-surface-700">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    a.priority === 'high' ? 'bg-red-100 text-red-700' :
                    a.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-surface-100 text-surface-600'
                  }`}>{a.priority}</span>
                  <span className="text-xs text-surface-500">{a.type}</span>
                </div>
                <h3 className="text-sm font-medium text-surface-900 dark:text-white">{a.title}</h3>
                <p className="text-xs text-surface-500 mt-1">{a.action}</p>
                {a.expected_benefit && (
                  <p className="text-xs text-green-600 mt-1">Benefit: {a.expected_benefit}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Regional Insights */}
      {report.regional_insights.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <MapPin size={18} className="text-purple-500" />
            <h2 className="font-semibold text-surface-900 dark:text-white">Regional Insights</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {report.regional_insights.map((r, i) => (
              <div key={i} className="p-3 bg-surface-50 dark:bg-surface-800 rounded-lg">
                <div className="font-medium text-surface-900 dark:text-white text-sm">{r.region}</div>
                <div className="text-xs text-surface-500">Score: {r.opportunity_score.toFixed(0)}</div>
                <div className="text-xs text-surface-600 dark:text-surface-400 mt-1">{r.action}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
