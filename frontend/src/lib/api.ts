import type {
  Competitor,
  CompetitorDetail,
  CollectionLog,
  DashboardStats,
  FeedItem,
  SystemHealth,
  Telemetry,
  Service,
  Pricing,
  Content,
  Social,
  AiInsight,
  CompetitorScoreResponse,
  SchedulerStatus,
} from '../types'

const API_BASE = ''

interface CompetitorListResponse {
  total: number
  page: number
  page_size: number
  total_pages: number
  competitors: Competitor[]
  items?: Competitor[]
}

interface BulkActionResponse {
  status: string
  message: string
  deleted?: number
  enabled?: number
  disabled?: number
  reloaded?: boolean
  synced?: boolean
}

interface SearchResult {
  query: string
  results: { competitor_id: number; name: string; context: string }[]
  total: number
}

interface AiStatus {
  total_insights: number
  average_confidence: number
  last_analysis: string | null
  pending_analyses: number
}

interface DiscoveryResult {
  discovered: { name: string; url: string; score: number }[]
}

interface SystemConfig {
  environment: string
  debug: boolean
  queue_backend: string
  webhooks_enabled: boolean
  webhooks_slack: boolean
  webhooks_teams: boolean
  llm_enabled: boolean
  llm_provider: string
  llm_model: string
  cache_enabled: boolean
  stealth_enabled: boolean
  scheduler_enabled: boolean
  scheduler_interval: number
  config_path: string
}

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

    let response: Response
    try {
      response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
      })
    } catch {
      throw new Error('Backend is unreachable — try again in a moment')
    }

    if (response.status === 401) {
      throw new Error('Invalid credentials — please log in again')
    }

    if (!response.ok) {
      let detail = `Request failed (HTTP ${response.status})`
      try {
        const body = await response.json()
        if (body.detail) detail = body.detail
      } catch { /* ignore parse error */ }
      throw new Error(detail)
    }

    if (response.status === 204) return undefined as T
    return response.json()
  }

  // Dashboard
  async getStats(): Promise<DashboardStats> {
    return this.request<DashboardStats>('/api/dashboard/stats')
  }

  async getFeed(limit = 20, offset = 0): Promise<{ items: FeedItem[]; total: number; has_more: boolean }> {
    return this.request(`/api/dashboard/feed?limit=${limit}&offset=${offset}`)
  }

  async getSummary(): Promise<{ competitor_id: number; name: string; last_collected: string | null; services_count: number; pricing_count: number; content_count: number; social_count: number }[]> {
    return this.request('/api/dashboard/summary')
  }

  // Competitors
  async getCompetitors(params?: { search?: string; enabled?: boolean; frequency?: string; page?: number; page_size?: number }): Promise<CompetitorListResponse> {
    const searchParams = new URLSearchParams()
    if (params?.search) searchParams.set('search', params.search)
    if (params?.enabled !== undefined) searchParams.set('enabled', String(params.enabled))
    if (params?.frequency) searchParams.set('frequency', params.frequency)
    if (params?.page) searchParams.set('page', String(params.page))
    if (params?.page_size) searchParams.set('page_size', String(params.page_size))
    const qs = searchParams.toString()
    return this.request(`/api/dashboard/competitors${qs ? `?${qs}` : ''}`)
  }

  async getCompetitor(id: number): Promise<CompetitorDetail> {
    return this.request(`/api/dashboard/competitors/${id}`)
  }

  async createCompetitor(data: Partial<Competitor>): Promise<{ status: string; competitor: Competitor }> {
    return this.request('/api/dashboard/competitors', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateCompetitor(id: number, data: Partial<Competitor>): Promise<{ status: string; competitor: Competitor }> {
    return this.request(`/api/dashboard/competitors/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteCompetitor(id: number): Promise<BulkActionResponse> {
    return this.request(`/api/dashboard/competitors/${id}`, {
      method: 'DELETE',
    })
  }

  async duplicateCompetitor(id: number): Promise<{ status: string; competitor: Competitor }> {
    return this.request(`/api/dashboard/competitors/${id}/duplicate`, {
      method: 'POST',
    })
  }

  async bulkDelete(ids: number[]): Promise<BulkActionResponse> {
    return this.request('/api/dashboard/competitors/bulk/delete', {
      method: 'POST',
      body: JSON.stringify({ competitor_ids: ids }),
    })
  }

  async bulkEnable(ids: number[]): Promise<BulkActionResponse> {
    return this.request('/api/dashboard/competitors/bulk/enable', {
      method: 'POST',
      body: JSON.stringify({ competitor_ids: ids }),
    })
  }

  async bulkDisable(ids: number[]): Promise<BulkActionResponse> {
    return this.request('/api/dashboard/competitors/bulk/disable', {
      method: 'POST',
      body: JSON.stringify({ competitor_ids: ids }),
    })
  }

  async bulkUpdateFrequency(ids: number[], frequency: string): Promise<BulkActionResponse> {
    return this.request('/api/dashboard/competitors/bulk/frequency', {
      method: 'POST',
      body: JSON.stringify({ competitor_ids: ids, frequency }),
    })
  }

  // Collection
  async triggerCollection(competitorId: number): Promise<{ status: string; competitor_id: number }> {
    return this.request(`/api/dashboard/collect/${competitorId}`, {
      method: 'POST',
    })
  }

  async cancelCollection(competitorId: number): Promise<{ status: string }> {
    return this.request(`/api/dashboard/collect/${competitorId}/cancel`, {
      method: 'POST',
    })
  }

  async retryCollection(competitorId: number): Promise<{ status: string }> {
    return this.request(`/api/dashboard/collect/${competitorId}/retry`, {
      method: 'POST',
    })
  }

  // Logs
  async getLogs(params?: { competitor_id?: number; success?: boolean; page?: number; page_size?: number }): Promise<{ total: number; logs: CollectionLog[]; page: number; page_size: number; total_pages: number }> {
    const searchParams = new URLSearchParams()
    if (params?.competitor_id) searchParams.set('competitor_id', String(params.competitor_id))
    if (params?.success !== undefined) searchParams.set('success', String(params.success))
    if (params?.page) searchParams.set('page', String(params.page))
    if (params?.page_size) searchParams.set('page_size', String(params.page_size))
    const qs = searchParams.toString()
    return this.request(`/api/dashboard/logs${qs ? `?${qs}` : ''}`)
  }

  // Health
  async getHealth(): Promise<SystemHealth> {
    return this.request('/api/dashboard/health')
  }

  async getSystemHealth(): Promise<SystemHealth> {
    return this.request('/health')
  }

  // Scheduler
  async getSchedulerStatus(): Promise<SchedulerStatus> {
    return this.request('/api/dashboard/scheduler/status')
  }

  async pauseScheduler(): Promise<{ status: string }> {
    return this.request('/api/dashboard/scheduler/pause', { method: 'POST' })
  }

  async resumeScheduler(): Promise<{ status: string }> {
    return this.request('/api/dashboard/scheduler/resume', { method: 'POST' })
  }

  // Search
  async search(q: string): Promise<SearchResult> {
    return this.request(`/api/dashboard/search?q=${encodeURIComponent(q)}`)
  }

  // Telemetry
  async getTelemetry(): Promise<Telemetry> {
    return this.request('/api/dashboard/telemetry')
  }

  // Config
  async getConfig(): Promise<SystemConfig> {
    return this.request('/api/dashboard/config')
  }

  async resyncConfig(): Promise<{ status: string; synced: { status: string; synced: number; skipped: number } }> {
    return this.request('/api/dashboard/config/resync', { method: 'POST' })
  }

  // Trends
  async getTrends(days = 30): Promise<{ days: number; trends: { date: string; collections: number; successful: number; failed: number; records: number }[] }> {
    return this.request(`/api/dashboard/trends?days=${days}`)
  }

  // Compare
  async compareCompetitors(ids: number[]): Promise<(Competitor & { services: Service[]; pricing: Pricing[]; content: Content[]; social: Social[]; services_count: number; pricing_count: number; social_count: number; content_count: number })[]> {
    return this.request(`/api/dashboard/compare?competitor_ids=${ids.join(',')}`)
  }

  // Changes
  async getChanges(competitorId: number, limit = 50): Promise<{ change_type: string; data_type: string; old_value: string | null; new_value: string | null; detected_at: string }[]> {
    return this.request(`/api/dashboard/competitors/${competitorId}/changes?limit=${limit}`)
  }

  // Extracted Data
  async getExtracted(competitorId: number): Promise<Record<string, unknown>> {
    return this.request(`/api/dashboard/extracted/${competitorId}`)
  }

  // Live Logs
  async getLiveLogs(competitorId: number): Promise<CollectionLog[]> {
    return this.request(`/api/dashboard/live_logs/${competitorId}`)
  }

  // Exports
  getCompareCsvUrl(): string {
    return `${API_BASE}/api/dashboard/compare/csv`
  }

  getExportZipUrl(): string {
    return `${API_BASE}/api/dashboard/export/zip`
  }

  getPdfExportUrl(): string {
    return `${API_BASE}/api/dashboard/export/pdf`
  }

  getRawHtmlUrl(competitorId: number): string {
    return `${API_BASE}/api/dashboard/raw/${competitorId}`
  }

  // AI
  async getAiInsights(competitorId: number): Promise<AiInsight> {
    return this.request(`/api/ai/competitor/${competitorId}`)
  }

  async analyzeCompetitor(competitorId: number): Promise<{ status: string; competitor_id: number }> {
    return this.request(`/api/ai/analyze/${competitorId}`, { method: 'POST' })
  }

  async analyzeBatch(competitorIds?: number[]): Promise<{ status: string; queued: number }> {
    return this.request('/api/ai/analyze/batch', {
      method: 'POST',
      body: JSON.stringify(competitorIds),
    })
  }

  async deleteAiInsights(competitorId: number): Promise<{ status: string }> {
    return this.request(`/api/ai/competitor/${competitorId}`, { method: 'DELETE' })
  }

  async getAiStatus(): Promise<AiStatus> {
    return this.request('/api/ai/status')
  }

  // Metrics
  async getMetricsJson(): Promise<Record<string, unknown>> {
    return this.request('/metrics/json')
  }

  // Competitor Scoring
  async getCompetitorScore(competitorId: number): Promise<CompetitorScoreResponse> {
    return this.request(`/competitor/${competitorId}/score`)
  }

  async getAllScores(): Promise<{ total: number; scores: { competitor_id: number; name: string; total_score: number; grade: string; tier: string; is_chennai: boolean; is_indian: boolean }[] }> {
    return this.request('/scores')
  }

  // Competitor Discovery
  async discoverCompetitors(queries?: string[], numResults?: number): Promise<DiscoveryResult> {
    return this.request('/discover', {
      method: 'POST',
      body: JSON.stringify({ queries: queries || [], num_results: numResults || 10 }),
    })
  }
}

export const api = new ApiClient()
