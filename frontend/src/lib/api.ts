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
  TrendAnalysis,
  GrowthForecast,
  ExpansionForecast,
  CompetitorRisk,
  BusinessOpportunity,
  StrategicRecommendation,
  PredictiveBenchmark,
  ForecastReport,
  MarketTrend,
  IndustryBenchmark,
  AdvancedScore,
  DataQualityReport,
  ScenarioSimulation,
  ScenarioDefinition,
  LearningAccuracyReport,
  ConfidenceDriftReport,
  FeatureEffectiveness,
  ModelVersion,
  ConfidenceScore,
  Explainability,
  GraphData,
  GraphStats,
  GraphNeighbor,
  MarketCluster,
  HiddenCompetitor,
  SearchResult as RAGSearchResult,
  CopilotResponse,
  CoordinatedResult,
  MLModel,
  MLForecastResult,
  MLEvaluation,
  StreamingStats,
  GeoCity,
  GeoHeatmapPoint,
  GeoMapData,
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

  // ─── Sprint 7: Predictions ───────────────────────────────────────────────

  async getMarketTrends(days = 90): Promise<TrendAnalysis> {
    return this.request(`/api/predictions/trends?days=${days}`)
  }

  async getEmergingTrends(): Promise<MarketTrend[]> {
    return this.request('/api/predictions/trends/emerging')
  }

  async getGrowthForecasts(): Promise<GrowthForecast[]> {
    return this.request('/api/predictions/growth')
  }

  async getCompetitorGrowth(competitorId: number): Promise<GrowthForecast> {
    return this.request(`/api/predictions/growth/${competitorId}`)
  }

  async getExpansionForecast(competitorId: number): Promise<ExpansionForecast[]> {
    return this.request(`/api/predictions/expansion/${competitorId}`)
  }

  async getAllRisks(): Promise<CompetitorRisk[]> {
    return this.request('/api/predictions/risks')
  }

  async getCompetitorRisks(competitorId: number): Promise<CompetitorRisk[]> {
    return this.request(`/api/predictions/risks/${competitorId}`)
  }

  async getOpportunities(): Promise<BusinessOpportunity[]> {
    return this.request('/api/predictions/opportunities')
  }

  async getAllRecommendations(): Promise<StrategicRecommendation[]> {
    return this.request('/api/predictions/recommendations')
  }

  async getCompetitorRecommendations(competitorId: number): Promise<StrategicRecommendation[]> {
    return this.request(`/api/predictions/recommendations/${competitorId}`)
  }

  async getPredictiveBenchmarks(): Promise<PredictiveBenchmark[]> {
    return this.request('/api/predictions/benchmarks')
  }

  async getCompetitorBenchmark(competitorId: number): Promise<PredictiveBenchmark> {
    return this.request(`/api/predictions/benchmarks/${competitorId}`)
  }

  async getForecastReport(): Promise<ForecastReport> {
    return this.request('/api/predictions/report')
  }

  async getFullPredictions(competitorId: number): Promise<Record<string, unknown>> {
    return this.request(`/api/predictions/full/${competitorId}`)
  }

  async generatePredictions(): Promise<{ status: string; saved_predictions: number; saved_trends: number; saved_benchmarks: number }> {
    return this.request('/api/predictions/generate', { method: 'POST' })
  }

  // ─── Sprint 7.1: Enhanced Endpoints ─────────────────────────────────────

  async getIndustryBenchmarks(): Promise<IndustryBenchmark[]> {
    return this.request('/api/predictions/industry-benchmarks')
  }

  async getIndustryBenchmarkCompetitor(competitorId: number): Promise<IndustryBenchmark> {
    return this.request(`/api/predictions/industry-benchmarks/${competitorId}`)
  }

  async getCategoryBenchmarks(): Promise<Record<string, unknown>> {
    return this.request('/api/predictions/industry-benchmarks/categories')
  }

  async getAdvancedScores(): Promise<AdvancedScore[]> {
    return this.request('/api/predictions/scores')
  }

  async getDataQualityAll(): Promise<DataQualityReport[]> {
    return this.request('/api/predictions/data-quality')
  }

  async getDataQuality(competitorId: number): Promise<DataQualityReport> {
    return this.request(`/api/predictions/data-quality/${competitorId}`)
  }

  async listScenarios(): Promise<ScenarioDefinition[]> {
    return this.request('/api/predictions/scenarios')
  }

  async runScenario(scenarioType: string, competitorId?: number, params?: Record<string, unknown>): Promise<ScenarioSimulation> {
    const url = `/api/predictions/scenarios/${scenarioType}` + (competitorId ? `?competitor_id=${competitorId}` : '')
    return this.request(url, { method: 'POST', body: params ? JSON.stringify(params) : undefined, headers: params ? { 'Content-Type': 'application/json' } : undefined })
  }

  async getLearningAccuracy(): Promise<LearningAccuracyReport> {
    return this.request('/api/predictions/learning/accuracy')
  }

  async getConfidenceDrift(): Promise<ConfidenceDriftReport> {
    return this.request('/api/predictions/learning/drift')
  }

  async getFeatureEffectiveness(): Promise<FeatureEffectiveness> {
    return this.request('/api/predictions/learning/features')
  }

  async getModelVersions(): Promise<ModelVersion[]> {
    return this.request('/api/predictions/learning/models')
  }

  async getGrowthWithConfidence(competitorId: number): Promise<GrowthForecast & { confidence: ConfidenceScore; explanation: Explainability }> {
    return this.request(`/api/predictions/growth/${competitorId}/confidence`)
  }

  async getRisksExplained(competitorId: number): Promise<(CompetitorRisk & { explanation: Explainability })[]> {
    return this.request(`/api/predictions/risks/${competitorId}/explained`)
  }

  async getOpportunitiesExplained(): Promise<(BusinessOpportunity & { explanation: Explainability })[]> {
    return this.request('/api/predictions/opportunities/explained')
  }

  async getRecommendationsExplained(): Promise<(StrategicRecommendation & { explanation: Explainability })[]> {
    return this.request('/api/predictions/recommendations/explained')
  }

  async getBenchmarksExplained(): Promise<(PredictiveBenchmark & { explanation: Explainability })[]> {
    return this.request('/api/predictions/benchmarks/explained')
  }

  async getEnhancedReport(): Promise<ForecastReport & { data_quality: DataQualityReport[]; learning: { accuracy_report: LearningAccuracyReport; confidence_drift: ConfidenceDriftReport } }> {
    return this.request('/api/predictions/report/enhanced')
  }

  // ─── Sprint 7.2: Knowledge Graph ───────────────────────────────────────

  async buildGraph(): Promise<{ nodes: number; edges: number }> {
    return this.request('/api/graph/build')
  }

  async getGraph(): Promise<GraphData> {
    return this.request('/api/graph')
  }

  async getGraphStats(): Promise<GraphStats> {
    return this.request('/api/graph/stats')
  }

  async searchGraph(q: string, limit = 10): Promise<{ id: string; type: string; name: string }[]> {
    return this.request(`/api/graph/search?q=${encodeURIComponent(q)}&limit=${limit}`)
  }

  async getGraphNeighbors(competitorId: number, relationship?: string): Promise<GraphNeighbor[]> {
    const rel = relationship ? `&relationship=${relationship}` : ''
    return this.request(`/api/graph/competitor/${competitorId}/neighbors${rel}`)
  }

  async getGraphPath(source: string, target: string): Promise<{ nodes: string[]; edges: { source: string; target: string; relationship: string; weight: number }[]; total_weight: number } | null> {
    return this.request(`/api/graph/path?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`)
  }

  async getGraphClusters(): Promise<MarketCluster[]> {
    return this.request('/api/graph/clusters')
  }

  async getHiddenCompetitors(): Promise<HiddenCompetitor[]> {
    return this.request('/api/graph/hidden-competitors')
  }

  async getGraphInfluence(): Promise<Record<string, number>> {
    return this.request('/api/graph/influence')
  }

  async getCompetitorsInCity(city: string): Promise<{ id: string; name: string }[]> {
    return this.request(`/api/graph/city/${encodeURIComponent(city)}`)
  }

  async getCompetitorsInCategory(category: string): Promise<{ id: string; name: string }[]> {
    return this.request(`/api/graph/category/${encodeURIComponent(category)}`)
  }

  // ─── Sprint 7.2: RAG ──────────────────────────────────────────────────

  async buildRagIndex(): Promise<Record<string, number>> {
    return this.request('/api/rag/index')
  }

  async getRagStats(): Promise<Record<string, unknown>> {
    return this.request('/api/rag/stats')
  }

  async searchRag(q: string, limit = 10, sourceType?: string): Promise<RAGSearchResult[]> {
    let url = `/api/rag/search?q=${encodeURIComponent(q)}&limit=${limit}`
    if (sourceType) url += `&source_type=${sourceType}`
    return this.request(url)
  }

  async getRagContext(q: string, limit = 5): Promise<RAGSearchResult[]> {
    return this.request(`/api/rag/context?q=${encodeURIComponent(q)}&limit=${limit}`)
  }

  // ─── Sprint 7.2: Copilot ──────────────────────────────────────────────

  async askCopilot(question: string, conversationId?: string): Promise<CopilotResponse> {
    return this.request('/api/copilot/ask', {
      method: 'POST',
      body: JSON.stringify({ question, conversation_id: conversationId }),
      headers: { 'Content-Type': 'application/json' },
    })
  }

  async getCopilotConversations(): Promise<{ id: string; turns: number; last_message: string }[]> {
    return this.request('/api/copilot/conversations')
  }

  async getCopilotHistory(conversationId: string): Promise<{ role: string; content: string; timestamp: string }[]> {
    return this.request(`/api/copilot/conversations/${conversationId}`)
  }

  // ─── Sprint 7.2: Multi-Agent ──────────────────────────────────────────

  async coordinateAgents(): Promise<CoordinatedResult> {
    return this.request('/api/agents/coordinate')
  }

  async getAgentTypes(): Promise<{ value: string; label: string }[]> {
    return this.request('/api/agents/types')
  }

  // ─── Sprint 7.2: ML Forecasting ────────────────────────────────────────

  async getMLModels(): Promise<MLModel[]> {
    return this.request('/api/ml/models')
  }

  async mlForecast(values: number[], steps = 30, model = 'linear_regression'): Promise<MLForecastResult> {
    return this.request('/api/ml/forecast', {
      method: 'POST',
      body: JSON.stringify({ values, steps, model }),
      headers: { 'Content-Type': 'application/json' },
    })
  }

  async mlEvaluate(values: number[], model = 'linear_regression'): Promise<MLEvaluation> {
    return this.request('/api/ml/evaluate', {
      method: 'POST',
      body: JSON.stringify({ values, steps: 1, model }),
      headers: { 'Content-Type': 'application/json' },
    })
  }

  async mlCompetitorTimeSeries(competitorId: number, metric: string): Promise<{ competitor_id: number; metric: string; values: number[]; labels: string[]; total: number }> {
    return this.request(`/api/ml/competitor-timeseries/${competitorId}?metric=${metric}`)
  }

  async mlSelectBest(values: number[]): Promise<{ best_model: string; metrics: Record<string, number> }> {
    return this.request('/api/ml/select-best', {
      method: 'POST',
      body: JSON.stringify({ values, steps: 1 }),
      headers: { 'Content-Type': 'application/json' },
    })
  }

  async mlForecastCompetitor(competitorId: number, metric: string, steps: number = 7, model?: string): Promise<{
    historical: { labels: string[]; values: number[] }
    forecast: { labels: string[]; values: number[]; ci: [number, number][] }
    model: { name: string; mae: number; rmse: number; r2: number }
    trend: { direction: string; momentum: number; long_term_trend: number; change_pct: number; recent_avg: number; prev_avg: number }
  }> {
    let url = `/api/ml/forecast/${competitorId}?metric=${metric}&steps=${steps}`
    if (model) url += `&model=${model}`
    return this.request(url)
  }

  async mlForecastAll(metric: string, steps: number = 7) {
    return this.request(`/api/ml/forecast-all?metric=${metric}&steps=${steps}`)
  }

  async getMLHistory(): Promise<Record<string, unknown>[]> {
    return this.request('/api/ml/history')
  }

  // ─── Sprint 7.2: Streaming ────────────────────────────────────────────

  async getStreamingStats(): Promise<StreamingStats> {
    return this.request('/api/streaming/stats')
  }

  async getStreamingEvents(eventType?: string, limit = 50): Promise<Record<string, unknown>[]> {
    let url = `/api/streaming/events?limit=${limit}`
    if (eventType) url += `&event_type=${eventType}`
    return this.request(url)
  }

  // ─── Sprint 7.2: Geographic Intelligence ──────────────────────────────

  async getGeoAnalysis(): Promise<Record<string, unknown>> {
    return this.request('/api/geo/analyze')
  }

  async getGeoMapData(): Promise<GeoMapData> {
    return this.request('/api/geo/map-data')
  }

  async getGeoHeatmap(): Promise<GeoHeatmapPoint[]> {
    return this.request('/api/geo/heatmap')
  }

  async getGeoCities(): Promise<GeoCity[]> {
    return this.request('/api/geo/cities')
  }

  async compareGeoCities(cities: string[]): Promise<Record<string, unknown>[]> {
    return this.request(`/api/geo/compare?cities=${cities.join(',')}`)
  }
}

export const api = new ApiClient()
