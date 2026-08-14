import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import type { ScenarioSimulation, ScenarioDefinition, Competitor } from '../types'
import { Play, AlertTriangle, TrendingUp, Shield, Target, Zap } from 'lucide-react'

const scenarioIcons: Record<string, typeof Play> = {
  competitor_price_cut: TrendingUp,
  competitor_expansion: Target,
  new_competitor: AlertTriangle,
  demand_increase: TrendingUp,
  demand_decrease: Shield,
}

export default function ScenariosPage() {
  const [scenarios, setScenarios] = useState<ScenarioDefinition[]>([])
  const [competitors, setCompetitors] = useState<Competitor[]>([])
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null)
  const [selectedCompetitor, setSelectedCompetitor] = useState<number | null>(null)
  const [result, setResult] = useState<ScenarioSimulation | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    Promise.all([
      api.listScenarios().then(setScenarios).catch(() => {}),
      api.getCompetitors().then(d => setCompetitors(d.competitors)).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  const runScenario = async () => {
    if (!selectedScenario) return
    setRunning(true)
    setResult(null)
    try {
      const r = await api.runScenario(selectedScenario, selectedCompetitor || undefined)
      setResult(r)
    } catch { /* ignore */ }
    setRunning(false)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Scenario Simulation</h1>
        <p className="text-surface-600 dark:text-surface-400 mt-1">Simulate what-if scenarios to understand competitive dynamics</p>
      </div>

      <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700">
        <h2 className="text-lg font-semibold text-surface-900 dark:text-white mb-4">Configure Scenario</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">Scenario Type</label>
            <select
              value={selectedScenario || ''}
              onChange={e => setSelectedScenario(e.target.value)}
              className="w-full rounded-lg border border-surface-300 dark:border-surface-600 bg-white dark:bg-surface-800 px-3 py-2 text-surface-900 dark:text-white"
            >
              <option value="">Select a scenario...</option>
              {scenarios.map(s => (
                <option key={s.type} value={s.type}>{s.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">Target Competitor (optional)</label>
            <select
              value={selectedCompetitor || ''}
              onChange={e => setSelectedCompetitor(e.target.value ? Number(e.target.value) : null)}
              className="w-full rounded-lg border border-surface-300 dark:border-surface-600 bg-white dark:bg-surface-800 px-3 py-2 text-surface-900 dark:text-white"
            >
              <option value="">All competitors</option>
              {competitors.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={runScenario}
              disabled={!selectedScenario || running}
              className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white px-6 py-2 rounded-lg font-medium"
            >
              <Play className="w-4 h-4" />
              {running ? 'Running...' : 'Run Simulation'}
            </button>
          </div>
        </div>
        {selectedScenario && (
          <p className="mt-3 text-sm text-surface-600 dark:text-surface-400">
            {scenarios.find(s => s.type === selectedScenario)?.description}
          </p>
        )}
      </div>

      {result && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
                <Zap className="w-5 h-5 text-brand-600 dark:text-brand-400" />
              </div>
              <h2 className="text-lg font-semibold text-surface-900 dark:text-white">
                Scenario: {result.scenario.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-green-50 dark:bg-green-900/10 rounded-lg p-4 border border-green-200 dark:border-green-800">
                <h3 className="text-sm font-semibold text-green-700 dark:text-green-400 mb-2">Business Impact</h3>
                <div className="space-y-1 text-sm text-surface-700 dark:text-surface-300">
                  <p><span className="font-medium">Revenue:</span> {result.business_impact.revenue_impact}</p>
                  <p><span className="font-medium">Market Share:</span> {result.business_impact.market_share_impact}</p>
                  <p><span className="font-medium">Competitive Advantage:</span> {result.business_impact.competitive_advantage}</p>
                </div>
              </div>

              <div className="bg-red-50 dark:bg-red-900/10 rounded-lg p-4 border border-red-200 dark:border-red-800">
                <h3 className="text-sm font-semibold text-red-700 dark:text-red-400 mb-2">Risk Analysis</h3>
                <div className="space-y-1 text-sm text-surface-700 dark:text-surface-300">
                  <p><span className="font-medium">Level:</span> {result.risk_analysis.risk_level}</p>
                  <div>
                    <span className="font-medium">Mitigations:</span>
                    <ul className="mt-1 list-disc list-inside">
                      {result.risk_analysis.mitigation_needed.map((m, i) => (
                        <li key={i}>{m}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              <div className="bg-blue-50 dark:bg-blue-900/10 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
                <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-2">Recommended Strategy</h3>
                <p className="text-sm text-surface-700 dark:text-surface-300">{result.recommended_strategy}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        {scenarios.map(s => {
          const Icon = scenarioIcons[s.type] || Zap
          return (
            <button
              key={s.type}
              onClick={() => setSelectedScenario(s.type)}
              className={`p-4 rounded-xl border text-left transition-all ${
                selectedScenario === s.type
                  ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
                  : 'border-surface-200 dark:border-surface-700 bg-white dark:bg-surface-900 hover:border-brand-300'
              }`}
            >
              <Icon className="w-5 h-5 text-brand-500 mb-2" />
              <h3 className="text-sm font-semibold text-surface-900 dark:text-white">{s.name}</h3>
              <p className="text-xs text-surface-500 dark:text-surface-400 mt-1">{s.description}</p>
            </button>
          )
        })}
      </div>
    </div>
  )
}
