import { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react'
import { api } from '../lib/api'
import type { DashboardStats, SystemHealth, Telemetry, SchedulerStatus } from '../types'

interface DashboardData {
  stats: DashboardStats | null
  health: SystemHealth | null
  telemetry: Telemetry | null
  scheduler: SchedulerStatus | null
}

interface DashboardContextValue extends DashboardData {
  loading: {
    stats: boolean
    health: boolean
    telemetry: boolean
    scheduler: boolean
  }
  error: {
    stats: string | null
    health: string | null
    telemetry: string | null
    scheduler: string | null
  }
  refresh: {
    stats: () => Promise<void>
    health: () => Promise<void>
    telemetry: () => Promise<void>
    scheduler: () => Promise<void>
    all: () => Promise<void>
  }
}

const DashboardContext = createContext<DashboardContextValue | null>(null)

function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  enabled: boolean = true
) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const fetcherRef = useRef(fetcher)
  const mountedRef = useRef(true)
  fetcherRef.current = fetcher

  const refresh = useCallback(async (initial = false) => {
    if (!mountedRef.current) return
    if (initial) setLoading(true)
    try {
      const result = await fetcherRef.current()
      if (mountedRef.current) {
        setData(result)
        setError(null)
      }
    } catch (e: unknown) {
      if (mountedRef.current) setError(e instanceof Error ? e.message : 'Failed to fetch')
    } finally {
      if (mountedRef.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    if (!enabled) return
    refresh(true)
    const id = setInterval(() => refresh(false), intervalMs)
    return () => { mountedRef.current = false; clearInterval(id) }
  }, [enabled, intervalMs, refresh])

  return { data, loading, error, refresh }
}

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const statsPoll = usePolling(() => api.getStats(), 15000)
  const healthPoll = usePolling(() => api.getHealth(), 30000)
  const telemetryPoll = usePolling(() => api.getTelemetry(), 10000)
  const schedulerPoll = usePolling(() => api.getSchedulerStatus(), 15000)

  const refreshAll = useCallback(async () => {
    await Promise.all([
      statsPoll.refresh(),
      healthPoll.refresh(),
      telemetryPoll.refresh(),
      schedulerPoll.refresh(),
    ])
  }, [statsPoll.refresh, healthPoll.refresh, telemetryPoll.refresh, schedulerPoll.refresh])

  const value: DashboardContextValue = {
    stats: statsPoll.data,
    health: healthPoll.data,
    telemetry: telemetryPoll.data,
    scheduler: schedulerPoll.data,
    loading: {
      stats: statsPoll.loading,
      health: healthPoll.loading,
      telemetry: telemetryPoll.loading,
      scheduler: schedulerPoll.loading,
    },
    error: {
      stats: statsPoll.error,
      health: healthPoll.error,
      telemetry: telemetryPoll.error,
      scheduler: schedulerPoll.error,
    },
    refresh: {
      stats: statsPoll.refresh,
      health: healthPoll.refresh,
      telemetry: telemetryPoll.refresh,
      scheduler: schedulerPoll.refresh,
      all: refreshAll,
    },
  }

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  )
}

export function useDashboard() {
  const context = useContext(DashboardContext)
  if (!context) {
    throw new Error('useDashboard must be used within a DashboardProvider')
  }
  return context
}