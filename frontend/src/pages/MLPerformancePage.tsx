import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Area, AreaChart, Legend,
  ComposedChart, Bar, Scatter, ZAxis, Cell,
} from 'recharts'
import { api } from '../lib/api'
import type { Competitor, MLModel, MLEvaluation } from '../types'
import {
  Play, RefreshCw, CheckCircle, XCircle,
  TrendingUp, TrendingDown, Minus, Zap, BarChart3, Activity,
  Target, Clock, ChevronDown,
} from 'lucide-react'

interface ForecastResult {
  historical: { labels: string[]; values: number[] }
  forecast: { labels: string[]; values: number[]; ci: [number, number][] }
  model: { name: string; mae: number; rmse: number; r2: number }
  trend: {
    direction: string; momentum: number; long_term_trend: number
    change_pct: number; recent_avg: number; prev_avg: number
  }
}

interface ChartPoint {
  date: string
  actual: number | null
  forecast: number | null
  ciLow: number | null
  ciHigh: number | null
}

const METRIC_LABELS: Record<string, string> = {
  base_price: 'Base Service Price (₹)',
  min_price: 'Minimum / Tiered Entry Price (₹)',
  max_price: 'Maximum Service Price (₹)',
  promotional_discount: 'Promotional Discount (%)',
  services: 'Active Service Listings Count',
  add_on_pricing: 'Add-On Service Pricing (₹)',
  quote_required: 'Quote-Required Commercial Listings',
  surging_priority: 'Emergency Surge Surcharge (%)',
  location_premium: 'Regional Price Tiering Variance (%)',
  pricing: 'Catalog Pricing Entries',
  content: 'Content Items',
  changes: 'Changes Detected',
}

const TREND_COLORS: Record<string, string> = {
  growing: '#22c55e',
  declining: '#ef4444',
  stable: '#94a3b8',
  recovering: '#3b82f6',
  cooling: '#f59e0b',
}

export default function MLPerformancePage() {
  const [competitors, setCompetitors] = useState<Competitor[]>([])
  const [models, setModels] = useState<MLModel[]>([])
  const [evaluations, setEvaluations] = useState<MLEvaluation[]>([])
  const [selectedCompetitor, setSelectedCompetitor] = useState<number>(0)
  const [selectedMetric, setSelectedMetric] = useState('services')
  const [selectedModel, setSelectedModel] = useState('linear_regression')
  const [fetching, setFetching] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [loading, setLoading] = useState(true)

  const [forecast, setForecast] = useState<ForecastResult | null>(null)
  const [forecastSteps, setForecastSteps] = useState(7)
  const [forecastModel, setForecastModel] = useState<string>('auto')
  const [forecasting, setForecasting] = useState(false)
  const [collecting, setCollecting] = useState(false)

  useEffect(() => {
    Promise.all([
      api.getCompetitors({ page_size: 100 }).then(r => setCompetitors(r.competitors || [])),
      api.getMLModels().then(setModels),
    ]).finally(() => setLoading(false))
  }, [])

  const fetchForecast = useCallback(async () => {
    if (!selectedCompetitor) return
    setForecasting(true)
    try {
      const modelParam = forecastModel === 'auto' ? undefined : forecastModel
      const result = await api.mlForecastCompetitor(selectedCompetitor, selectedMetric, forecastSteps, modelParam)
      setForecast(result)
      // Auto-evaluate all models so comparison table is always fresh
      if (result.historical.values.length >= 3) {
        const results = await Promise.all(
          models.filter(m => m.available).map(m => api.mlEvaluate(result.historical.values, m.name).catch(() => null))
        )
        setEvaluations(results.filter(Boolean) as MLEvaluation[])
      }
    } catch {
      setForecast(null)
    }
    setForecasting(false)
  }, [selectedCompetitor, selectedMetric, forecastSteps, forecastModel, models])

  useEffect(() => {
    if (selectedCompetitor) fetchForecast()
  }, [selectedCompetitor, selectedMetric, forecastSteps, forecastModel])

  const collectData = async () => {
    if (!selectedCompetitor) return
    setCollecting(true)
    try {
      await api.triggerCollection(selectedCompetitor)
      await new Promise(r => setTimeout(r, 2000))
      await fetchForecast()
    } catch { /* ignore */ }
    setCollecting(false)
  }

  const evaluateAll = async (overrideValues?: number[]) => {
    const data = overrideValues || forecast?.historical.values
    if (!data || data.length < 3) return
    setEvaluating(true)
    try {
      const results = await Promise.all(
        models.filter(m => m.available).map(m => api.mlEvaluate(data, m.name).catch(() => null))
      )
      setEvaluations(results.filter(Boolean) as MLEvaluation[])
    } catch { /* ignore */ }
    setEvaluating(false)
  }

  const chartData = useMemo<ChartPoint[]>(() => {
    if (!forecast) return []
    const points: ChartPoint[] = []
    const allLabels = [...forecast.historical.labels, ...forecast.forecast.labels]
    const allValues = [...forecast.historical.values, ...forecast.forecast.values]
    const maxIdx = Math.max(allLabels.length, 1)

    for (let i = 0; i < maxIdx; i++) {
      const isHistorical = i < forecast.historical.labels.length
      const point: ChartPoint = { date: allLabels[i] || '', actual: null, forecast: null, ciLow: null, ciHigh: null }

      if (isHistorical) {
        point.actual = allValues[i]
      } else {
        const fIdx = i - forecast.historical.labels.length
        point.forecast = forecast.forecast.values[fIdx] ?? null
        if (forecast.forecast.ci[fIdx]) {
          point.ciLow = forecast.forecast.ci[fIdx][0]
          point.ciHigh = forecast.forecast.ci[fIdx][1]
        }
      }
      points.push(point)
    }
    return points
  }, [forecast])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
      </div>
    )
  }

  const bestModel = evaluations.length > 1
    ? evaluations.reduce((best, e) => e.rmse < best.rmse ? e : best)
    : null

  const selectedComp = competitors.find(c => c.id === selectedCompetitor)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-surface-900 dark:text-white">ML Performance</h1>
        <p className="text-surface-500 dark:text-surface-400 mt-1">
          Forecast models on real competitive data
        </p>
      </div>

      {/* Controls Bar */}
      <div className="bg-white dark:bg-surface-900 rounded-xl p-4 border border-surface-200 dark:border-surface-700 flex flex-wrap items-end gap-4">
        <div className="flex-1 min-w-[160px]">
          <label className="block text-xs font-medium text-surface-500 uppercase tracking-wide mb-1">Competitor</label>
          <select value={selectedCompetitor} onChange={e => setSelectedCompetitor(Number(e.target.value))}
            className="w-full rounded-lg border border-surface-300 dark:border-surface-600 bg-white dark:bg-surface-800 px-3 py-2 text-sm text-surface-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500">
            <option value={0}>Select competitor...</option>
            {competitors.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div className="min-w-[140px]">
          <label className="block text-xs font-medium text-surface-500 uppercase tracking-wide mb-1">Metric</label>
          <select value={selectedMetric} onChange={e => setSelectedMetric(e.target.value)}
            className="w-full rounded-lg border border-surface-300 dark:border-surface-600 bg-white dark:bg-surface-800 px-3 py-2 text-sm text-surface-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500">
            {Object.entries(METRIC_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div className="min-w-[120px]">
          <label className="block text-xs font-medium text-surface-500 uppercase tracking-wide mb-1">Forecast</label>
          <select value={forecastSteps} onChange={e => setForecastSteps(Number(e.target.value))}
            className="w-full rounded-lg border border-surface-300 dark:border-surface-600 bg-white dark:bg-surface-800 px-3 py-2 text-sm text-surface-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500">
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
          </select>
        </div>
        <div className="min-w-[150px]">
          <label className="block text-xs font-medium text-surface-500 uppercase tracking-wide mb-1">Model</label>
          <select value={forecastModel} onChange={e => setForecastModel(e.target.value)}
            className="w-full rounded-lg border border-surface-300 dark:border-surface-600 bg-white dark:bg-surface-800 px-3 py-2 text-sm text-surface-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500">
            <option value="auto">Auto (Best fit)</option>
            {models.filter(m => m.available).map(m => (
              <option key={m.name} value={m.name}>{m.name}</option>
            ))}
          </select>
        </div>
        <div className="flex items-end gap-2">
          <button onClick={collectData} disabled={!selectedCompetitor || collecting}
            className="flex items-center gap-2 bg-surface-100 dark:bg-surface-800 hover:bg-surface-200 dark:hover:bg-surface-700 disabled:opacity-40 text-surface-700 dark:text-surface-300 px-3 py-2 rounded-lg text-sm font-medium transition-colors border border-surface-200 dark:border-surface-700">
            <RefreshCw className={`w-4 h-4 ${collecting ? 'animate-spin' : ''}`} />
            {collecting ? 'Collecting...' : 'Collect'}
          </button>
          <button onClick={fetchForecast} disabled={!selectedCompetitor || forecasting}
            className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            <Zap className={`w-4 h-4 ${forecasting ? 'animate-pulse' : ''}`} />
            {forecasting ? 'Forecasting...' : 'Run Forecast'}
          </button>
          <button onClick={() => evaluateAll()} disabled={evaluating || !forecast || timeSeriesLength(forecast) < 3}
            className="flex items-center gap-2 bg-surface-100 dark:bg-surface-800 hover:bg-surface-200 dark:hover:bg-surface-700 disabled:opacity-40 text-surface-700 dark:text-surface-300 px-4 py-2 rounded-lg text-sm font-medium transition-colors border border-surface-200 dark:border-surface-700">
            <BarChart3 className="w-4 h-4" />
            {evaluating ? 'Evaluating...' : 'Evaluate All'}
          </button>
        </div>
        {selectedComp && (
          <div className="text-xs text-surface-400 w-full pt-1">
            {selectedComp.name} · {METRIC_LABELS[selectedMetric]} · {forecastSteps}d · {forecastModel === 'auto' ? 'best model' : forecastModel}
          </div>
        )}
      </div>

      {/* Trend Summary */}
      {forecast && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <TrendCard
            label="Direction"
            value={forecast.trend.direction}
            icon={trendIcon(forecast.trend.direction)}
            color={TREND_COLORS[forecast.trend.direction] || '#94a3b8'}
          />
          <TrendCard
            label="30-Day Δ"
            value={`${forecast.trend.change_pct > 0 ? '+' : ''}${forecast.trend.change_pct}%`}
            color={forecast.trend.change_pct > 0 ? '#22c55e' : forecast.trend.change_pct < 0 ? '#ef4444' : '#94a3b8'}
          />
          <TrendCard
            label="Momentum"
            value={`${forecast.trend.momentum > 0 ? '+' : ''}${forecast.trend.momentum.toFixed(2)}`}
            color={forecast.trend.momentum > 0 ? '#22c55e' : forecast.trend.momentum < 0 ? '#ef4444' : '#94a3b8'}
          />
          <TrendCard
            label="Recent Avg"
            value={forecast.trend.recent_avg.toFixed(1)}
            sub={`prev: ${forecast.trend.prev_avg.toFixed(1)}`}
          />
          <TrendCard
            label="Best Model"
            value={bestModel ? bestModel.model_type : (evaluations.length === 1 ? `${evaluations[0].model_type} (only)` : 'N/A')}
            color="#f97316"
          />
        </div>
      )}

      {/* Main Chart */}
      {forecast && chartData.length > 0 && (
        <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-surface-900 dark:text-white">
              {METRIC_LABELS[selectedMetric]} — Historical + Forecast
            </h2>
            <div className="flex items-center gap-4 text-xs text-surface-500">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-brand-500" /> Actual
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-blue-500" /> Forecast
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-blue-200 dark:bg-blue-800" /> 95% CI
              </span>
            </div>
          </div>
          <div className="h-[340px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="ciGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.03} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-surface-200 dark:text-surface-700" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: 'currentColor' }}
                  className="text-surface-400"
                  tickLine={false}
                  axisLine={{ stroke: 'currentColor', className: 'text-surface-300 dark:text-surface-600' }}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fontSize: 11, fill: 'currentColor' }}
                  className="text-surface-400"
                  tickLine={false}
                  axisLine={false}
                  width={45}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgb(15 23 42)',
                    border: '1px solid rgb(51 65 85)',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: '#f8fafc',
                    padding: '10px 14px',
                  }}
                />
                <ReferenceLine
                  x={forecast.historical.labels[forecast.historical.labels.length - 1]}
                  stroke="#94a3b8"
                  strokeDasharray="4 4"
                  label={{ value: 'Today', position: 'insideTopRight', fill: '#94a3b8', fontSize: 11 }}
                />
                {/* CI area */}
                <Area type="monotone" dataKey="ciHigh" stroke="none" fill="url(#ciGradient)" />
                <Area type="monotone" dataKey="ciLow" stroke="none" fill="white" />
                {/* Actual line */}
                <Line
                  type="monotone" dataKey="actual" stroke="#f97316" strokeWidth={2.5}
                  dot={{ r: 3, fill: '#f97316', strokeWidth: 0 }}
                  activeDot={{ r: 5, stroke: '#f97316', strokeWidth: 2, fill: 'white' }}
                  connectNulls={false}
                />
                {/* Forecast line */}
                <Line
                  type="monotone" dataKey="forecast" stroke="#3b82f6" strokeWidth={2}
                  strokeDasharray="6 3"
                  dot={{ r: 2, fill: '#3b82f6', strokeWidth: 0 }}
                  activeDot={{ r: 4, stroke: '#3b82f6', strokeWidth: 2, fill: 'white' }}
                  connectNulls={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          {/* Model Stats Bar */}
          <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-surface-500 border-t border-surface-100 dark:border-surface-800 pt-3">
            <span className="flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5" /> Model: <strong className="text-surface-700 dark:text-surface-300">{forecast.model.name}</strong>
            </span>
            <span className="flex items-center gap-1.5">
              <Target className="w-3.5 h-3.5" /> R²: <strong className="text-surface-700 dark:text-surface-300">{forecast.model.r2.toFixed(4)}</strong>
            </span>
            <span className="flex items-center gap-1.5">
              <BarChart3 className="w-3.5 h-3.5" /> RMSE: <strong className="text-surface-700 dark:text-surface-300">{forecast.model.rmse.toFixed(4)}</strong>
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" /> MAE: <strong className="text-surface-700 dark:text-surface-300">{forecast.model.mae.toFixed(4)}</strong>
            </span>
          </div>
        </div>
      )}

      {/* Model Evaluation Results */}
      {evaluations.length > 0 && (
        <div className="bg-white dark:bg-surface-900 rounded-xl border border-surface-200 dark:border-surface-700 overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-100 dark:border-surface-800">
            <h2 className="text-lg font-semibold text-surface-900 dark:text-white">Model Comparison</h2>
            <p className="text-xs text-surface-500 mt-1">Lower RMSE = better fit · Highlighted = best model</p>
          </div>
          <table className="w-full">
            <thead className="bg-surface-50 dark:bg-surface-800/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-surface-500 uppercase tracking-wider">Model</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase tracking-wider">MAE</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase tracking-wider">RMSE</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase tracking-wider">MAPE</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase tracking-wider">R²</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-500 uppercase tracking-wider">Time</th>
                {evaluations.length > 1 && (
                  <th className="px-6 py-3 text-center text-xs font-medium text-surface-500 uppercase tracking-wider">Rank</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
              {[...evaluations].sort((a, b) => a.rmse - b.rmse).map((e, idx) => {
                const isBest = bestModel?.model_type === e.model_type
                return (
                  <tr key={e.model_type}
                    className={`transition-colors ${isBest ? 'bg-brand-50/50 dark:bg-brand-900/10' : 'hover:bg-surface-50 dark:hover:bg-surface-800/30'}`}>
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-medium ${isBest ? 'text-brand-600 dark:text-brand-400' : 'text-surface-900 dark:text-white'}`}>
                          {e.model_type}
                        </span>
                        {isBest && (
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-brand-500 text-white uppercase tracking-wider">
                            Best
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-sm text-right text-surface-700 dark:text-surface-300 tabular-nums">
                      {e.mae.toFixed(4)}
                    </td>
                    <td className="px-4 py-3.5 text-sm text-right tabular-nums">
                      <span className={isBest ? 'font-semibold text-brand-600 dark:text-brand-400' : 'text-surface-700 dark:text-surface-300'}>
                        {e.rmse.toFixed(4)}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-sm text-right text-surface-700 dark:text-surface-300 tabular-nums">
                      {e.mape.toFixed(2)}%
                    </td>
                    <td className="px-4 py-3.5 text-sm text-right tabular-nums">
                      <span className={e.r2 >= 0.8 ? 'text-green-600 dark:text-green-400 font-medium' : e.r2 >= 0.5 ? 'text-amber-600 dark:text-amber-400' : 'text-red-500 dark:text-red-400'}>
                        {e.r2.toFixed(4)}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-sm text-right text-surface-500 tabular-nums">
                      {e.training_time_ms.toFixed(0)}ms
                    </td>
                    {evaluations.length > 1 && (
                      <td className="px-6 py-3.5 text-center">
                        {idx < 3 && (
                          <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                            idx === 0 ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                            : idx === 1 ? 'bg-surface-200 text-surface-600 dark:bg-surface-700 dark:text-surface-400'
                            : 'bg-orange-100 text-orange-600 dark:bg-orange-900/20 dark:text-orange-400'
                          }`}>
                            #{idx + 1}
                          </span>
                        )}
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Model Comparison Chart */}
      {evaluations.length > 1 && (
        <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700">
          <h2 className="text-lg font-semibold text-surface-900 dark:text-white mb-4">Model Accuracy Comparison</h2>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={[...evaluations].sort((a, b) => a.rmse - b.rmse).map(e => ({
                  name: e.model_type,
                  rmse: e.rmse,
                  r2: e.r2,
                }))}
                margin={{ top: 10, right: 20, bottom: 30, left: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-surface-200 dark:text-surface-700" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'currentColor' }} className="text-surface-400" angle={-35} textAnchor="end" />
                <YAxis yAxisId="rmse" tick={{ fontSize: 11, fill: 'currentColor' }} className="text-surface-400" width={50} />
                <YAxis yAxisId="r2" orientation="right" tick={{ fontSize: 11, fill: 'currentColor' }} className="text-surface-400" width={50} domain={[0, 1]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgb(15 23 42)',
                    border: '1px solid rgb(51 65 85)',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: '#f8fafc',
                  }}
                />
                <Bar yAxisId="rmse" dataKey="rmse" fill="#f97316" radius={[4, 4, 0, 0]} name="RMSE" />
                <Line yAxisId="r2" type="monotone" dataKey="r2" stroke="#22c55e" strokeWidth={2} dot={{ r: 4, fill: '#22c55e' }} name="R²" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Available Models Grid */}
      <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700">
        <h2 className="text-lg font-semibold text-surface-900 dark:text-white mb-4">Available Models</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {models.map(m => (
            <div key={m.name}
              className={`p-3 rounded-lg border transition-colors ${m.available
                ? 'border-surface-200 dark:border-surface-700 hover:border-brand-300 dark:hover:border-brand-600 cursor-default'
                : 'border-surface-200 dark:border-surface-700 opacity-50'}`}>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-surface-900 dark:text-white">{m.name}</span>
                {m.available
                  ? <CheckCircle className="w-4 h-4 text-green-500" />
                  : <XCircle className="w-4 h-4 text-red-400" />}
              </div>
              <span className="text-[11px] mt-1 inline-block px-2 py-0.5 bg-surface-100 dark:bg-surface-800 text-surface-500 rounded-full">
                {m.type}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function timeSeriesLength(f: ForecastResult): number {
  return f?.historical?.values?.length || 0
}

function trendIcon(direction: string) {
  switch (direction) {
    case 'growing': return <TrendingUp className="w-4 h-4" />
    case 'declining': return <TrendingDown className="w-4 h-4" />
    case 'recovering': return <TrendingUp className="w-4 h-4" />
    case 'cooling': return <TrendingDown className="w-4 h-4" />
    default: return <Minus className="w-4 h-4" />
  }
}

function TrendCard({ label, value, icon, color, sub }: {
  label: string; value: string; icon?: React.ReactNode; color?: string; sub?: string
}) {
  return (
    <div className="bg-white dark:bg-surface-900 rounded-xl p-3.5 border border-surface-200 dark:border-surface-700">
      <p className="text-[11px] font-medium text-surface-500 uppercase tracking-wide">{label}</p>
      <div className="flex items-center gap-2 mt-1">
        {icon && <span style={{ color }}>{icon}</span>}
        <span className="text-lg font-bold text-surface-900 dark:text-white capitalize" style={color ? { color } : undefined}>
          {value}
        </span>
      </div>
      {sub && <p className="text-[11px] text-surface-400 mt-0.5">{sub}</p>}
    </div>
  )
}
