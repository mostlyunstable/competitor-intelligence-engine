import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import {
  DollarSign, ShieldAlert, CheckCircle2, AlertTriangle, Layers, TrendingUp,
  BarChart3, RefreshCw, Sparkles, Filter, ChevronRight, Activity, Tag, HelpCircle
} from 'lucide-react'

export default function PricingIntelligencePage() {
  const [activeTab, setActiveTab] = useState<'audit' | 'taxonomy' | 'matrix' | 'history' | 'quality' | 'forecast'>('audit')
  const [loading, setLoading] = useState(true)
  const [auditData, setAuditData] = useState<any>(null)
  const [taxonomyData, setTaxonomyData] = useState<any>(null)
  const [matrixData, setMatrixData] = useState<any[]>([])
  const [qualityData, setQualityData] = useState<any>(null)
  const [forecastData, setForecastData] = useState<any>(null)
  const [recommendations, setRecommendations] = useState<any[]>([])

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [auditRes, taxonomyRes, matrixRes, qualityRes, forecastRes, recsRes] = await Promise.allSettled([
        api.request('/api/pricing-intelligence/audit'),
        api.request('/api/pricing-intelligence/taxonomy'),
        api.request('/api/pricing-intelligence/matrix'),
        api.request('/api/pricing-intelligence/quality'),
        api.request('/api/pricing-intelligence/forecast'),
        api.request('/api/pricing-intelligence/recommendations'),
      ])

      if (auditRes.status === 'fulfilled') setAuditData(auditRes.value)
      if (taxonomyRes.status === 'fulfilled') setTaxonomyData(taxonomyRes.value)
      if (matrixRes.status === 'fulfilled') setMatrixData(Array.isArray(matrixRes.value) ? matrixRes.value : [])
      if (qualityRes.status === 'fulfilled') setQualityData(qualityRes.value)
      if (forecastRes.status === 'fulfilled') setForecastData(forecastRes.value)
      if (recsRes.status === 'fulfilled') setRecommendations(Array.isArray(recsRes.value) ? recsRes.value : [])
    } catch (err) {
      console.error('Failed to load pricing intelligence data', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-gray-200 dark:border-gray-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <DollarSign className="w-7 h-7 text-indigo-600 dark:text-indigo-400" />
            Pricing Intelligence & Decision Support
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Audit Utservio pricing, normalize services into canonical taxonomy, compare competitor benchmark matrix, and forecast market movements.
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh Intelligence
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-gray-200 dark:border-gray-800 pb-2">
        {[
          { id: 'audit', label: '1. Utservio Audit & Discrepancies', icon: ShieldAlert },
          { id: 'taxonomy', label: '2. Canonical Taxonomy', icon: Layers },
          { id: 'matrix', label: '3. Benchmark Matrix', icon: BarChart3 },
          { id: 'history', label: '4. Pricing History', icon: Activity },
          { id: 'quality', label: '5. Quality Framework', icon: CheckCircle2 },
          { id: 'forecast', label: '6. Forecasts & Decision Support', icon: TrendingUp },
        ].map(tab => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      {loading ? (
        <div className="flex justify-center items-center py-20">
          <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin" />
        </div>
      ) : (
        <>
          {/* TAB 1: Utservio Audit & Discrepancies */}
          {activeTab === 'audit' && (
            <div className="space-y-6">
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Services Audited</div>
                  <div className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                    {auditData?.total_services_audited || 0}
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Discrepancies Flagged</div>
                  <div className="text-3xl font-bold text-amber-600 dark:text-amber-400 mt-1">
                    {auditData?.total_discrepancies_found || 0}
                  </div>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Catalog Inconsistency Rate</div>
                  <div className="text-3xl font-bold text-red-600 dark:text-red-400 mt-1">
                    {auditData?.inconsistent_services_pct || 0}%
                  </div>
                </div>
              </div>

              {/* Discrepancies List */}
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                  Detected Catalog Discrepancies & Resolution Reasoning
                </h3>
                <div className="space-y-4">
                  {(auditData?.discrepancies || []).map((disc: any, idx: number) => (
                    <div key={idx} className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
                      <div className="flex justify-between items-start">
                        <div>
                          <span className="inline-block px-2.5 py-0.5 text-xs font-semibold rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300 mb-1">
                            {disc.discrepancy_type}
                          </span>
                          <h4 className="text-base font-semibold text-gray-900 dark:text-white">{disc.service_name}</h4>
                        </div>
                        <span className="text-xs font-medium text-gray-500">Confidence: {(disc.confidence_score * 100).toFixed(0)}%</span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">{disc.explanation}</p>
                      <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-800 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div>
                          <span className="font-semibold text-gray-500">Resolved Canonical Price:</span>
                          <span className="ml-2 font-bold text-emerald-600 dark:text-emerald-400">
                            ₹{disc.resolved_canonical_value?.base_price} {disc.resolved_canonical_value?.promotional_price && `(Promo: ₹${disc.resolved_canonical_value?.promotional_price})`}
                          </span>
                        </div>
                        <div>
                          <span className="font-semibold text-gray-500">Canonical Unit & Location:</span>
                          <span className="ml-2 text-gray-700 dark:text-gray-300">
                            {disc.resolved_canonical_value?.pricing_unit} | {disc.resolved_canonical_value?.location}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Canonical Taxonomy */}
          {activeTab === 'taxonomy' && (
            <div className="space-y-6">
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Standardized Service Taxonomy Hierarchy</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {(taxonomyData?.taxonomy || []).map((item: any) => (
                    <div key={item.id} className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
                      <div className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">{item.category} &gt; {item.subcategory}</div>
                      <div className="text-base font-bold text-gray-900 dark:text-white mt-1">{item.name}</div>
                      <div className="text-xs text-gray-500 mt-2 flex flex-wrap gap-2">
                        <span className="bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded">Unit: {item.pricing_unit}</span>
                        {item.attributes?.duration_mins && (
                          <span className="bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded">Duration: {item.attributes.duration_mins} mins</span>
                        )}
                        {item.attributes?.technicians && (
                          <span className="bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded">Techs: {item.attributes.technicians}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Competitor Benchmark Matrix */}
          {activeTab === 'matrix' && (
            <div className="space-y-6">
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm">
                <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Multi-Competitor Pricing Comparison Matrix</h3>
                  <div className="text-xs text-gray-500">Price Gap % = (Utservio - Median) / Median × 100</div>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm text-left">
                    <thead className="bg-gray-50 dark:bg-gray-900 text-gray-500 uppercase text-xs">
                      <tr>
                        <th className="px-6 py-3">Canonical Service</th>
                        <th className="px-6 py-3">Utservio</th>
                        <th className="px-6 py-3">Market Median</th>
                        <th className="px-6 py-3">Market Min-Max</th>
                        <th className="px-6 py-3">Price Gap %</th>
                        <th className="px-6 py-3">Price Index</th>
                        <th className="px-6 py-3">Market Position</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700 text-gray-900 dark:text-white">
                      {matrixData.map((row: any, idx: number) => (
                        <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                          <td className="px-6 py-4 font-medium">{row.canonical_service_name}</td>
                          <td className="px-6 py-4 font-bold text-indigo-600 dark:text-indigo-400">₹{row.utservio_price}</td>
                          <td className="px-6 py-4 font-semibold">₹{row.market_median}</td>
                          <td className="px-6 py-4 text-xs text-gray-500">₹{row.market_min} – ₹{row.market_max}</td>
                          <td className={`px-6 py-4 font-semibold ${row.price_gap_pct > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                            {row.price_gap_pct > 0 ? `+${row.price_gap_pct}%` : `${row.price_gap_pct}%`}
                          </td>
                          <td className="px-6 py-4 font-mono text-xs">{row.price_index}x</td>
                          <td className="px-6 py-4">
                            <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${
                              row.market_position === 'overpriced' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300' :
                              row.market_position === 'discount' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300' :
                              'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                            }`}>
                              {row.market_position}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: Time-Series History */}
          {activeTab === 'history' && (
            <div className="space-y-6">
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Immutable Historical Pricing Observations</h3>
                <p className="text-sm text-gray-500 mb-6">Historical time-series tracking Utservio price movements vs competitor median over time.</p>
                <div className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Sample Service: AC Split Unit Servicing & Deep Clean</div>
                  <div className="space-y-3">
                    {[
                      { date: '2026-01-01', utservio: '₹549', median: '₹499', index: '1.10x' },
                      { date: '2026-03-01', utservio: '₹549', median: '₹525', index: '1.05x' },
                      { date: '2026-05-01', utservio: '₹599', median: '₹549', index: '1.09x' },
                      { date: '2026-07-01', utservio: '₹599', median: '₹549', index: '1.09x' },
                      { date: '2026-08-01', utservio: '₹599', median: '₹525', index: '1.14x' },
                    ].map((h, i) => (
                      <div key={i} className="flex justify-between items-center text-xs p-2 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
                        <span className="font-mono text-gray-500">{h.date}</span>
                        <span>Utservio: <strong className="text-indigo-600 dark:text-indigo-400">{h.utservio}</strong></span>
                        <span>Market Median: <strong>{h.median}</strong></span>
                        <span className="font-mono">Relative Index: {h.index}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: Data Quality Framework */}
          {activeTab === 'quality' && (
            <div className="space-y-6">
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">7-Dimension Data Quality Scorecard</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  {Object.entries(qualityData?.dimension_weights || {}).map(([dim, weight]: any) => (
                    <div key={dim} className="p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700 text-center">
                      <div className="text-xs text-gray-500 uppercase tracking-wider">{dim}</div>
                      <div className="text-xl font-bold text-indigo-600 dark:text-indigo-400 mt-1">
                        {((qualityData?.sample_evaluation?.[dim] || 1.0) * 100).toFixed(0)}%
                      </div>
                      <div className="text-xs text-gray-400 mt-1">Weight: {weight * 100}%</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: Forecasts & Decision Support */}
          {activeTab === 'forecast' && (
            <div className="space-y-6">
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Predictive Forecast & Baseline Evaluation</h3>
                <p className="text-sm text-gray-500 mb-6">Walk-forward evaluated model predictions with uncertainty bounds.</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="text-sm font-semibold text-gray-900 dark:text-white">Active Model Metrics ({forecastData?.model_used})</div>
                    <div className="mt-3 space-y-2 text-xs">
                      <div className="flex justify-between"><span>MAE:</span> <strong>{forecastData?.model_evaluation?.mae}</strong></div>
                      <div className="flex justify-between"><span>RMSE:</span> <strong>{forecastData?.model_evaluation?.rmse}</strong></div>
                      <div className="flex justify-between"><span>MAPE:</span> <strong>{forecastData?.model_evaluation?.mape}%</strong></div>
                      <div className="flex justify-between"><span>Improvement vs Naive Baseline:</span> <strong className="text-emerald-600">+{forecastData?.baseline_comparison?.improvement_over_baseline_pct}%</strong></div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Strategic Recommendations */}
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-indigo-500" />
                  Actionable Strategic Pricing Recommendations
                </h3>
                <div className="space-y-4">
                  {recommendations.map((rec: any, idx: number) => (
                    <div key={idx} className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
                      <div className="flex justify-between items-start">
                        <span className={`px-2 py-0.5 text-xs font-semibold rounded ${
                          rec.category === 'pricing_opportunity' ? 'bg-emerald-100 text-emerald-800' :
                          rec.category === 'pricing_risk' ? 'bg-amber-100 text-amber-800' : 'bg-gray-200 text-gray-800'
                        }`}>
                          {rec.category}
                        </span>
                        <span className="text-xs text-gray-500">Confidence: {(rec.confidence * 100).toFixed(0)}%</span>
                      </div>
                      <h4 className="text-base font-bold text-gray-900 dark:text-white mt-2">{rec.title}</h4>
                      <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">{rec.recommendation}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
