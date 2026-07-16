const API_BASE = ''

class ApiClient {
  private credentials: string | null = null

  setCredentials(username: string, password: string) {
    this.credentials = btoa(`${username}:${password}`)
    localStorage.setItem('auth', this.credentials)
  }

  clearCredentials() {
    this.credentials = null
    localStorage.removeItem('auth')
  }

  isAuthenticated(): boolean {
    if (!this.credentials) {
      this.credentials = localStorage.getItem('auth')
    }
    return !!this.credentials
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    }

    if (this.credentials) {
      headers['Authorization'] = `Basic ${this.credentials}`
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    })

    if (response.status === 401) {
      this.clearCredentials()
      throw new Error('Unauthorized')
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    if (response.status === 204) return undefined as T
    return response.json()
  }

  // Dashboard
  async getStats() {
    return this.request<any>('/api/dashboard/stats')
  }

  async getFeed(limit = 20) {
    return this.request<any[]>(`/api/dashboard/feed?limit=${limit}`)
  }

  async getSummary() {
    return this.request<any[]>('/api/dashboard/summary')
  }

  // Competitors
  async getCompetitors(params?: { search?: string; enabled?: boolean; frequency?: string; page?: number; page_size?: number }) {
    const searchParams = new URLSearchParams()
    if (params?.search) searchParams.set('search', params.search)
    if (params?.enabled !== undefined) searchParams.set('enabled', String(params.enabled))
    if (params?.frequency) searchParams.set('frequency', params.frequency)
    if (params?.page) searchParams.set('page', String(params.page))
    if (params?.page_size) searchParams.set('page_size', String(params.page_size))
    const qs = searchParams.toString()
    return this.request<any>(`/api/dashboard/competitors${qs ? `?${qs}` : ''}`)
  }

  async getCompetitor(id: number) {
    return this.request<any>(`/api/dashboard/competitors/${id}`)
  }

  async createCompetitor(data: any) {
    return this.request<any>('/api/dashboard/competitors', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateCompetitor(id: number, data: any) {
    return this.request<any>(`/api/dashboard/competitors/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteCompetitor(id: number) {
    return this.request<any>(`/api/dashboard/competitors/${id}`, {
      method: 'DELETE',
    })
  }

  async duplicateCompetitor(id: number) {
    return this.request<any>(`/api/dashboard/competitors/${id}/duplicate`, {
      method: 'POST',
    })
  }

  async bulkDelete(ids: number[]) {
    return this.request<any>('/api/dashboard/competitors/bulk/delete', {
      method: 'POST',
      body: JSON.stringify({ competitor_ids: ids }),
    })
  }

  async bulkEnable(ids: number[]) {
    return this.request<any>('/api/dashboard/competitors/bulk/enable', {
      method: 'POST',
      body: JSON.stringify({ competitor_ids: ids }),
    })
  }

  async bulkDisable(ids: number[]) {
    return this.request<any>('/api/dashboard/competitors/bulk/disable', {
      method: 'POST',
      body: JSON.stringify({ competitor_ids: ids }),
    })
  }

  async bulkUpdateFrequency(ids: number[], frequency: string) {
    return this.request<any>('/api/dashboard/competitors/bulk/frequency', {
      method: 'POST',
      body: JSON.stringify({ competitor_ids: ids, frequency }),
    })
  }

  // Collection
  async triggerCollection(competitorId: number) {
    return this.request<any>(`/api/dashboard/collect/${competitorId}`, {
      method: 'POST',
    })
  }

  async cancelCollection(competitorId: number) {
    return this.request<any>(`/api/dashboard/collect/${competitorId}/cancel`, {
      method: 'POST',
    })
  }

  async retryCollection(competitorId: number) {
    return this.request<any>(`/api/dashboard/collect/${competitorId}/retry`, {
      method: 'POST',
    })
  }

  // Logs
  async getLogs(params?: { competitor_id?: number; success?: boolean; page?: number; page_size?: number }) {
    const searchParams = new URLSearchParams()
    if (params?.competitor_id) searchParams.set('competitor_id', String(params.competitor_id))
    if (params?.success !== undefined) searchParams.set('success', String(params.success))
    if (params?.page) searchParams.set('page', String(params.page))
    if (params?.page_size) searchParams.set('page_size', String(params.page_size))
    const qs = searchParams.toString()
    return this.request<any>(`/api/dashboard/logs${qs ? `?${qs}` : ''}`)
  }

  // Health
  async getHealth() {
    return this.request<any>('/api/dashboard/health')
  }

  async getSystemHealth() {
    return this.request<any>('/health')
  }

  // Scheduler
  async getSchedulerStatus() {
    return this.request<any>('/api/dashboard/scheduler/status')
  }

  async pauseScheduler() {
    return this.request<any>('/api/dashboard/scheduler/pause', { method: 'POST' })
  }

  async resumeScheduler() {
    return this.request<any>('/api/dashboard/scheduler/resume', { method: 'POST' })
  }

  // Search
  async search(q: string) {
    return this.request<any>(`/api/dashboard/search?q=${encodeURIComponent(q)}`)
  }

  // Telemetry
  async getTelemetry() {
    return this.request<any>('/api/dashboard/telemetry')
  }

  // Extracted Data
  async getExtracted(competitorId: number) {
    return this.request<any>(`/api/dashboard/extracted/${competitorId}`)
  }

  // Live Logs
  async getLiveLogs(competitorId: number) {
    return this.request<any[]>(`/api/dashboard/live_logs/${competitorId}`)
  }

  // Exports
  getCompareCsvUrl() {
    return `${API_BASE}/api/dashboard/compare/csv`
  }

  getExportZipUrl() {
    return `${API_BASE}/api/dashboard/export/zip`
  }

  getRawHtmlUrl(competitorId: number) {
    return `${API_BASE}/api/dashboard/raw/${competitorId}`
  }

  // Metrics
  async getMetricsJson() {
    return this.request<any>('/metrics/json')
  }
}

export const api = new ApiClient()
