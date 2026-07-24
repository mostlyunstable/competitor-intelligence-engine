import { useState, useEffect, useCallback, useRef } from 'react'

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number = 30000,
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
    } catch (e: any) {
      if (mountedRef.current) setError(e.message || 'Failed to fetch')
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

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value)
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay)
    return () => clearTimeout(handler)
  }, [value, delay])
  return debouncedValue
}
