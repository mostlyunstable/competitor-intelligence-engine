import { useState } from 'react'
import { usePolling } from '../hooks'
import { api } from '../lib/api'
import { formatDate, timeAgo } from '../lib/utils'
import {
  Settings, Database, Server, Activity, Clock, Bell,
  CheckCircle, XCircle, AlertTriangle, RefreshCw, Cpu, HardDrive, FileJson
} from 'lucide-react'

function StatusIndicator({ status, label }: { status: string; label: string }) {
  const colors: Record<string, string> = {
    healthy: 'bg-emerald-500', connected: 'bg-emerald-500', running: 'bg-emerald-500',
    degraded: 'bg-yellow-500', stopped: 'bg-red-500', unhealthy: 'bg-red-500',
    unknown: 'bg-surface-400',
  }
  return (
    <div className="flex items-center justify-between py-3 border-b border-surface-50 last:border-0">
      <div className="flex items-center gap-3">
        <div className={`w-2.5 h-2.5 rounded-full ${colors[status] || 'bg-surface-400'}`} />
        <span className="text-sm text-surface-700">{label}</span>
      </div>
      <span className={`text-sm font-medium capitalize ${
        status === 'healthy' || status === 'connected' || status === 'running'
          ? 'text-emerald-700' : status === 'degraded' ? 'text-yellow-700'
          : status === 'stopped' || status === 'unhealthy' ? 'text-red-700'
          : 'text-surface-500'
      }`}>{status}</span>
    </div>
  )
}

export default function AdminPage() {
  const { data: health, loading, refresh: refreshHealth } = usePolling(() => api.getHealth(), 20000)
  const { data: schedulerStatus, refresh: refreshScheduler } = usePolling(() => api.getSchedulerStatus(), 15000)
  const { data: telemetry } = usePolling(() => api.getTelemetry(), 10000)
  const { data: metrics } = usePolling(() => api.getMetricsJson(), 30000)
  const { data: config } = usePolling(() => api.getConfig(), 30000)
  const [resyncing, setResyncing] = useState(false)
  const [resyncResult, setResyncResult] = useState<string | null>(null)

  const handleResync = async () => {
    setResyncing(true)
    setResyncResult(null)
    try {
      const result = await api.resyncConfig()
      setResyncResult(`Reloaded ${result.reloaded} competitors from config file. Synced: ${result.synced?.synced || 0}`)
    } catch (e: any) {
      setResyncResult(`Error: ${e.message}`)
    } finally {
      setResyncing(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-surface-900">System Administration</h1>
        <button onClick={() => { refreshHealth(); refreshScheduler() }} className="btn-secondary">
          <RefreshCw size={16} /> Refresh All
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Health */}
        <div className="card">
          <div className="px-5 py-4 border-b border-surface-100 flex items-center gap-2">
            <Server size={16} className="text-brand-600" />
            <h2 className="font-semibold text-surface-900">System Health</h2>
          </div>
          <div className="p-5">
            <div className="mb-4">
              <div className={`text-lg font-bold ${
                health?.status === 'healthy' ? 'text-emerald-700' : 'text-yellow-700'
              }`}>
                {health?.status?.toUpperCase() || 'CHECKING...'}
              </div>
            </div>
            {health?.checks ? (
              <div>
                <StatusIndicator status={health.checks.database?.status || 'unknown'} label="Database" />
                <StatusIndicator status={health.checks.scheduler?.status || 'unknown'} label="Scheduler" />
                <StatusIndicator status={health.checks.queue?.status || 'unknown'} label="Message Queue" />
                <StatusIndicator status={health.checks.collection?.status || 'unknown'} label="Collection Service" />
                <StatusIndicator status={health.checks.memory?.status || 'unknown'} label="Memory" />
              </div>
            ) : (
              <div className="text-sm text-surface-400">Loading health data...</div>
            )}
          </div>
        </div>

        {/* Scheduler Management */}
        <div className="card">
          <div className="px-5 py-4 border-b border-surface-100 flex items-center gap-2">
            <Clock size={16} className="text-brand-600" />
            <h2 className="font-semibold text-surface-900">Scheduler Management</h2>
          </div>
          <div className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-surface-600">Status</span>
              <div className="flex items-center gap-2">
                <div className={`w-2.5 h-2.5 rounded-full ${schedulerStatus?.is_running ? 'bg-emerald-500' : 'bg-red-500'}`} />
                <span className="text-sm font-medium">{schedulerStatus?.is_running ? 'Running' : 'Stopped'}</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-surface-600">Check Interval</span>
              <span className="text-sm font-medium">{schedulerStatus?.interval_seconds || '-'}s</span>
            </div>
            <div className="flex gap-2 pt-2">
              {schedulerStatus?.is_running ? (
                <button onClick={async () => { await api.pauseScheduler(); refreshScheduler() }} className="btn-secondary">
                  Pause
                </button>
              ) : (
                <button onClick={async () => { await api.resumeScheduler(); refreshScheduler() }} className="btn-primary">
                  Resume
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Resource Usage */}
        <div className="card">
          <div className="px-5 py-4 border-b border-surface-100 flex items-center gap-2">
            <Cpu size={16} className="text-purple-600" />
            <h2 className="font-semibold text-surface-900">Resource Usage</h2>
          </div>
          <div className="p-5 space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-surface-600">CPU Usage</span>
                <span className="font-medium">{telemetry?.cpu_percent || 0}%</span>
              </div>
              <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                <div className="h-full bg-brand-500 rounded-full transition-all" style={{ width: `${telemetry?.cpu_percent || 0}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-surface-600">Memory</span>
                <span className="font-medium">{telemetry?.memory_mb || 0} MB / {(telemetry?.memory_total_gb || 0) * 1024} MB</span>
              </div>
              <div className="h-2 bg-surface-100 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full transition-all" style={{
                  width: `${telemetry?.memory_total_gb ? (telemetry.memory_mb / (telemetry.memory_total_gb * 1024)) * 100 : 0}%`
                }} />
              </div>
            </div>
            <div className="flex items-center justify-between pt-2">
              <span className="text-sm text-surface-600">Active Crawls</span>
              <span className="text-sm font-medium">{telemetry?.active_crawls || 0}</span>
            </div>
          </div>
        </div>

        {/* Configuration */}
        <div className="card">
          <div className="px-5 py-4 border-b border-surface-100 flex items-center gap-2">
            <Settings size={16} className="text-surface-600" />
            <h2 className="font-semibold text-surface-900">Configuration</h2>
          </div>
          <div className="p-5 space-y-3">
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-surface-600">Environment</span>
              <span className="badge-info">{config?.environment || '...'}</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-surface-600">Queue Backend</span>
              <span className={config?.queue_backend === 'redis' ? 'badge-success' : 'badge-neutral'}>{config?.queue_backend || '...'}</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-surface-600">Webhooks</span>
              {config?.webhooks_enabled ? (
                <span className="badge-success">Enabled{config.webhooks_slack ? ' (Slack)' : ''}{config.webhooks_teams ? ' (Teams)' : ''}</span>
              ) : (
                <span className="badge-neutral">Disabled</span>
              )}
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-surface-600">LLM</span>
              {config?.llm_enabled ? (
                <span className="badge-success">{config.llm_provider} / {config.llm_model}</span>
              ) : (
                <span className="badge-neutral">Disabled</span>
              )}
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-surface-600">Cache</span>
              <span className={config?.cache_enabled ? 'badge-success' : 'badge-neutral'}>{config?.cache_enabled ? 'Enabled' : 'Disabled'}</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-surface-600">Stealth Mode</span>
              <span className={config?.stealth_enabled ? 'badge-success' : 'badge-neutral'}>{config?.stealth_enabled ? 'Enabled' : 'Disabled'}</span>
            </div>
            <div className="pt-3 border-t border-surface-100">
              <p className="text-xs text-surface-500 mb-2">Edit <code className="bg-surface-100 px-1 rounded">.env</code> or <code className="bg-surface-100 px-1 rounded">competitors.json</code> to change settings.</p>
              <button onClick={handleResync} disabled={resyncing} className="btn-secondary btn-sm w-full">
                <FileJson size={14} /> {resyncing ? 'Re-syncing...' : 'Re-sync Competitors from Config'}
              </button>
              {resyncResult && (
                <p className={`text-xs mt-2 ${resyncResult.startsWith('Error') ? 'text-red-600' : 'text-emerald-600'}`}>{resyncResult}</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Metrics */}
      {metrics && (
        <div className="card">
          <div className="px-5 py-4 border-b border-surface-100 flex items-center gap-2">
            <Activity size={16} className="text-emerald-600" />
            <h2 className="font-semibold text-surface-900">Prometheus Metrics</h2>
          </div>
          <div className="p-5">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(metrics.counters || {}).map(([key, value]) => (
                <div key={key} className="p-3 bg-surface-50 rounded-lg">
                  <div className="text-xs text-surface-500 font-mono">{key}</div>
                  <div className="text-lg font-bold text-surface-900">{String(value)}</div>
                </div>
              ))}
              {Object.entries(metrics.gauges || {}).map(([key, value]) => (
                <div key={key} className="p-3 bg-surface-50 rounded-lg">
                  <div className="text-xs text-surface-500 font-mono">{key}</div>
                  <div className="text-lg font-bold text-surface-900">{String(value)}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
