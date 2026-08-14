import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import type { LearningAccuracyReport, ConfidenceDriftReport, FeatureEffectiveness, ModelVersion } from '../types'
import { BarChart3, Activity, Cpu, TrendingUp, RefreshCw } from 'lucide-react'

export default function ConfidenceDashboardPage() {
  const [accuracy, setAccuracy] = useState<LearningAccuracyReport | null>(null)
  const [drift, setDrift] = useState<ConfidenceDriftReport | null>(null)
  const [features, setFeatures] = useState<FeatureEffectiveness | null>(null)
  const [models, setModels] = useState<ModelVersion[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [a, d, f, m] = await Promise.all([
        api.getLearningAccuracy(),
        api.getConfidenceDrift(),
        api.getFeatureEffectiveness(),
        api.getModelVersions(),
      ])
      setAccuracy(a)
      setDrift(d)
      setFeatures(f)
      setModels(m)
    } catch { /* ignore */ }
    setLoading(false)
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">Confidence Dashboard</h1>
          <p className="text-surface-600 dark:text-surface-400 mt-1">Prediction accuracy, confidence drift, and feature effectiveness</p>
        </div>
        <button onClick={loadData} className="flex items-center gap-2 px-4 py-2 bg-surface-100 dark:bg-surface-800 rounded-lg hover:bg-surface-200 dark:hover:bg-surface-700 text-surface-700 dark:text-surface-300">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-surface-900 rounded-xl p-5 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <BarChart3 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-sm text-surface-500 dark:text-surface-400">Total Predictions</p>
              <p className="text-2xl font-bold text-surface-900 dark:text-white">{accuracy?.total_predictions || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-surface-900 rounded-xl p-5 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <Activity className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-sm text-surface-500 dark:text-surface-400">Recorded Outcomes</p>
              <p className="text-2xl font-bold text-surface-900 dark:text-white">{accuracy?.recorded_outcomes || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-surface-900 rounded-xl p-5 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
              <TrendingUp className="w-5 h-5 text-brand-600 dark:text-brand-400" />
            </div>
            <div>
              <p className="text-sm text-surface-500 dark:text-surface-400">Average Accuracy</p>
              <p className="text-2xl font-bold text-surface-900 dark:text-white">
                {accuracy?.average_accuracy ? `${Math.round(accuracy.average_accuracy * 100)}%` : 'N/A'}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-surface-900 rounded-xl p-5 border border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Cpu className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-sm text-surface-500 dark:text-surface-400">Confidence Drift</p>
              <p className="text-2xl font-bold text-surface-900 dark:text-white capitalize">
                {drift?.drift || 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700">
          <h2 className="text-lg font-semibold text-surface-900 dark:text-white mb-4">Accuracy by Prediction Type</h2>
          {accuracy && Object.keys(accuracy.by_type).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(accuracy.by_type).map(([type, info]) => (
                <div key={type} className="flex items-center justify-between">
                  <span className="text-sm text-surface-700 dark:text-surface-300 capitalize">{type.replace(/_/g, ' ')}</span>
                  <div className="flex items-center gap-3">
                    <div className="w-24 bg-surface-200 dark:bg-surface-700 rounded-full h-2">
                      <div className="bg-brand-500 h-2 rounded-full" style={{ width: `${info.accuracy * 100}%` }} />
                    </div>
                    <span className="text-sm font-medium text-surface-700 dark:text-surface-300 w-12 text-right">
                      {Math.round(info.accuracy * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-surface-500 dark:text-surface-400">No accuracy data yet. Record outcomes to see results.</p>
          )}
        </div>

        <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700">
          <h2 className="text-lg font-semibold text-surface-900 dark:text-white mb-4">Feature Effectiveness</h2>
          {features && features.features.length > 0 ? (
            <div className="space-y-3">
              {[...features.features].sort((a, b) => b.importance - a.importance).map(f => (
                <div key={f.name} className="flex items-center justify-between">
                  <span className="text-sm text-surface-700 dark:text-surface-300 capitalize">{f.name.replace(/_/g, ' ')}</span>
                  <div className="flex items-center gap-3">
                    <div className="w-24 bg-surface-200 dark:bg-surface-700 rounded-full h-2">
                      <div className="bg-green-500 h-2 rounded-full" style={{ width: `${f.importance * 100}%` }} />
                    </div>
                    <span className="text-sm font-medium text-surface-700 dark:text-surface-300 w-12 text-right">
                      {Math.round(f.importance * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-surface-500 dark:text-surface-400">No feature data available.</p>
          )}
        </div>
      </div>

      <div className="bg-white dark:bg-surface-900 rounded-xl p-6 border border-surface-200 dark:border-surface-700">
        <h2 className="text-lg font-semibold text-surface-900 dark:text-white mb-4">Model Versions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {models.map((m, i) => (
            <div key={i} className="bg-surface-50 dark:bg-surface-800 rounded-lg p-4 border border-surface-200 dark:border-surface-700">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-surface-900 dark:text-white">{m.version}</span>
                <span className="text-xs px-2 py-1 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-400 rounded-full">{m.model_type}</span>
              </div>
              <p className="text-xs text-surface-500 dark:text-surface-400">Trained: {new Date(m.trained_at).toLocaleDateString()}</p>
              <p className="text-xs text-surface-500 dark:text-surface-400">Samples: {m.training_samples}</p>
              {Object.keys(m.metrics).length > 0 && (
                <div className="mt-2 space-y-1">
                  {Object.entries(m.metrics).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs">
                      <span className="text-surface-500 dark:text-surface-400 capitalize">{k.replace(/_/g, ' ')}</span>
                      <span className="text-surface-700 dark:text-surface-300">{typeof v === 'number' ? v.toFixed(2) : v}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
