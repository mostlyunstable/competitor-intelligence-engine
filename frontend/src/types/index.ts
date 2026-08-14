export interface Competitor {
  id: number
  name: string
  website_url: string
  enabled: boolean
  collection_frequency: string
  modules: string[]
  tags: string[]
  notes: string | null
  created_at: string | null
  updated_at: string | null
  last_collected: string | null
  failed_collections: number
  total_collections: number
}

export interface CompetitorDetail {
  competitor: Competitor
  services: Service[]
  pricing: Pricing[]
  content: Content[]
  social: Social[]
  tech_stack: TechStack[]
  sources: Source[]
  pages: Page[]
  collection_logs: CollectionLog[]
}

export interface Service {
  id: number
  name: string
  description: string | null
  collected_at: string | null
}

export interface Pricing {
  id: number
  service_name: string
  base_price: number | null
  currency: string | null
  category: string | null
  collected_at: string | null
}

export interface Content {
  id: number
  title: string
  url: string
  content_type: string | null
  collected_at: string | null
}

export interface Social {
  id: number
  platform: string
  url: string
  username: string | null
  collected_at: string | null
}

export interface TechStack {
  id: number
  technology_name: string
  category: string | null
  confidence: number | null
}

export interface Source {
  id: number
  url: string
  page_type: string | null
  is_active: boolean
  last_crawled_at: string | null
}

export interface Page {
  id: number
  url: string
  status_code: number | null
  title: string | null
}

export interface CollectionLog {
  id: number
  competitor_id: number
  competitor_name?: string
  start_time: string | null
  end_time: string | null
  success: boolean
  duration_seconds: number | null
  records_collected: number
  errors: string[]
  retry_count: number
}

export interface DashboardStats {
  total_competitors: number
  active_competitors: number
  collections_running: number
  successful_collections: number
  failed_collections: number
  total_collections: number
  success_rate: number
  queue_size: number
  scheduler_status: string
  last_collection: string | null
  urls_discovered: number
  pages_crawled: number
  services_extracted: number
  pricing_extracted: number
  content_extracted: number
  social_extracted: number
  db_status: string
  api_status: string
}

export interface FeedItem {
  type: string
  message: string
  timestamp: string
  competitor_id?: number
  competitor_name?: string
  duration_seconds?: number
}

export interface SystemHealth {
  status: string
  checks: Record<string, { status: string; latency_ms?: number; running?: boolean; queue_size?: number }>
}

export interface PaginatedResponse<T> {
  total: number
  page: number
  page_size: number
  total_pages: number
  [key: string]: T[] | number
}

export interface Telemetry {
  cpu_percent: number
  memory_mb: number
  memory_total_gb: number
  active_crawls: number
}

export interface SchedulerStatus {
  is_running: boolean
  running: boolean
  next_run: string | null
  interval_seconds: number | null
}

export interface ScoreBreakdownDimension {
  score: number
  details: Record<string, unknown>
}

export interface CompetitorScoreResponse {
  competitor_id: number
  name: string
  score: {
    total: number
    grade: string
    tier: string
    breakdown: {
      location: ScoreBreakdownDimension
      digital_presence: ScoreBreakdownDimension
      service_quality: ScoreBreakdownDimension
      trust: ScoreBreakdownDimension
      market_relevance: ScoreBreakdownDimension
    }
  }
  location: {
    is_indian: boolean
    is_chennai: boolean
    city: string | null
    state: string | null
    confidence: number
    evidence: string[]
  }
  enhanced_data: Record<string, unknown>
}

export interface AiInsight {
  id: number
  competitor_id: number
  summary: string | null
  key_differentiators: string[] | null
  market_position: string | null
  confidence_score: number | null
  data_quality_score: number | null
  pricing_analysis: Record<string, unknown> | null
  feature_gaps: string[] | null
  strategic_moves: string[] | null
  recommendations: string[] | null
  latest_updates: string[] | null
  llm_provider: string | null
  llm_model: string | null
  prompt_version: string | null
  processing_status: string | null
  prompt_tokens: number | null
  completion_tokens: number | null
  total_tokens: number | null
  estimated_cost_usd: number | null
  created_at: string | null
  updated_at: string | null
}

export interface Change {
  id?: number
  change_type: string
  entity_type?: string
  entity_name?: string
  data_type?: string
  old_value: string | null
  new_value: string | null
  detected_at: string
}

// ─── Sprint 7: Predictive Intelligence Types ─────────────────────────────────

export interface MarketTrend {
  category: string
  direction: string
  strength: number
  description: string
  average_price?: number
  sample_count?: number
  service_count?: number
  content_count?: number
}

export interface GrowthForecast {
  competitor_id: number
  competitor_name?: string
  growth_level: string
  growth_score: number
  growth_percentage: string
  confidence_score: number
  breakdown: Record<string, number>
  metrics: {
    services_last_30: number
    services_last_90: number
    pricing_last_30: number
    content_last_30: number
    changes_last_30: number
    successful_collections: number
  }
  predicted_at: string
}

export interface ExpansionForecast {
  region: string
  expansion_probability: number
  expansion_score: number
  expected_timeline: string
  priority: string
  factors: Record<string, number>
  population: number
  tier: number
  market_demand: string
}

export interface CompetitorRisk {
  competitor_id: number
  competitor_name?: string
  risk_type: string
  risk_level: string
  risk_score: number
  likelihood: number
  business_impact: string
  mitigation: string
  detected_at: string
}

export interface BusinessOpportunity {
  opportunity_type: string
  title: string
  description: string
  opportunity_score: number
  roi_estimate: string | null
  priority: string
  recommended_action: string
  affected_regions: string[]
  affected_competitors: number[]
  detected_at: string
}

export interface StrategicRecommendation {
  competitor_id: number
  competitor_name?: string
  category: string
  title: string
  recommendation: string
  why: string
  expected_benefit: string
  risk_level: string
  confidence_score: number
  priority: string
  generated_at: string
  applied: boolean
}

export interface PredictiveBenchmark {
  competitor_id: number
  competitor_name?: string
  current_rank: number
  predicted_rank: number
  growth_score: number
  innovation_score: number
  expansion_score: number
  risk_score: number
  overall_prediction: string
  benchmark_data: Record<string, number>
  generated_at: string
}

export interface ForecastReport {
  title: string
  executive_summary: string
  predictions: {
    growth_forecasts: GrowthForecast[]
    market_trends: Record<string, unknown>
  }
  risks: CompetitorRisk[]
  opportunities: BusinessOpportunity[]
  recommendations: StrategicRecommendation[]
  benchmark_data: PredictiveBenchmark[]
  regional_insights: { region: string; opportunity_score: number; action: string }[]
  business_actions: { type: string; title: string; action: string; priority: string; expected_benefit: string }[]
  generated_at: string
}

export interface TrendAnalysis {
  pricing_trends: MarketTrend[]
  service_trends: MarketTrend[]
  content_trends: MarketTrend[]
  collection_health: {
    active_competitors: number
    dormant_competitors: number
    total_tracked: number
    collection_health: string
  }
  emerging_trends: MarketTrend[]
  analyzed_at: string
}

// ─── Sprint 7.1: Enhanced Intelligence Types ─────────────────────────────

export interface ConfidenceScore {
  confidence_score: number
  reliability_level: 'low' | 'medium' | 'high'
  prediction_stability: 'volatile' | 'moderate' | 'stable'
  factors: Record<string, number>
  weights: Record<string, number>
}

export interface Explainability {
  why: string
  evidence: string[]
  feature_importance: Record<string, number>
  data_sources: string[]
  business_reasoning: string
}

export interface IndustryBenchmark {
  competitor_id: number
  competitor_name: string
  overall_score: number
  percentile: number
  z_score: number
  vs_average: number
  vs_top_performer: number
  dimension_percentiles: Record<string, number>
  category: string
  grade: string
  rank: number
  industry_stats: { mean: number; top_score: number; total_competitors: number }
  benchmarked_at: string
}

export interface AdvancedScore {
  competitor_id: number
  competitor_name: string
  overall_score: number
  grade: string
  dimensions: Record<string, number>
  scored_at: string
}

export interface DataQualityReport {
  competitor_id: number
  competitor_name: string
  completeness_score: number
  freshness_score: number
  accuracy_score: number
  extraction_rate: number
  missing_values: string[]
  overall_quality: string
  evaluated_at: string
}

export interface ScenarioSimulation {
  scenario: string
  competitor_id: number | null
  params: Record<string, unknown>
  business_impact: {
    revenue_impact: string
    market_share_impact: string
    competitive_advantage: string
  }
  risk_analysis: {
    risk_level: string
    mitigation_needed: string[]
  }
  recommended_strategy: string
  simulated_at: string
}

export interface LearningAccuracyReport {
  total_predictions: number
  recorded_outcomes: number
  overall_accuracy: number | null
  average_accuracy: number | null
  by_type: Record<string, { accuracy: number; count: number }>
}

export interface ConfidenceDriftReport {
  drift: string
  details?: Record<string, unknown>
}

export interface FeatureEffectiveness {
  features: { name: string; importance: number }[]
}

export interface ModelVersion {
  version: string
  model_type: string
  trained_at: string
  training_samples: number
  metrics: Record<string, number>
}

export interface ScenarioDefinition {
  type: string
  name: string
  description: string
}

// ─── Sprint 7.2 Types ────────────────────────────────────────────────────

export interface GraphNode {
  id: string
  type: string
  name: string
  properties: Record<string, unknown>
}

export interface GraphEdge {
  source: string
  target: string
  relationship: string
  weight: number
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  stats: GraphStats
}

export interface GraphStats {
  total_nodes: number
  total_edges: number
  nodes_by_type: Record<string, number>
  built_at: string | null
}

export interface GraphNeighbor {
  node: { id: string; type: string; name: string }
  relationship: string
  weight: number
}

export interface MarketCluster {
  cluster_id: string
  members: string[]
  member_ids: number[]
  size: number
}

export interface HiddenCompetitor {
  competitor_a: string
  competitor_b: string
  shared_categories: number
  hidden_competitor_id: number
}

export interface SearchResult {
  content: string
  source_type: string
  source_id: number
  score: number
  match_type?: string
}

export interface CopilotResponse {
  answer: string
  confidence: number
  sources: { type: string; id: number; relevance: number }[]
  suggested_follow_ups: string[]
  conversation_id: string
}

export interface AgentResult {
  status: string
  data: Record<string, unknown>
  confidence: number
  time_ms: number
}

export interface CoordinatedResult {
  results: Record<string, AgentResult>
  merged_summary: string
  overall_confidence: number
  execution_time_ms: number
}

export interface MLModel {
  name: string
  available: boolean
  type: string
  display_name?: string
  description?: string
}

export interface MLForecastResult {
  model_type: string
  predictions: number[]
  confidence_intervals: [number, number][]
  metrics: Record<string, number>
  feature_importance: Record<string, number>
}

export interface MLEvaluation {
  model_type: string
  mae: number
  rmse: number
  mape: number
  r2: number
  cv_score: number
  training_time_ms: number
}

export interface StreamingStats {
  queue_size: number
  history_size: number
  ws_connections: number
  sse_connections: number
  subscriptions: number
  events_by_type: Record<string, number>
  running: boolean
}

export interface GeoCity {
  city: string
  state: string
  lat: number
  lon: number
  population: number
  tier: number
  competitor_count: number
  saturation: number
  opportunity: number
  coverage: string
  demand: string
}

export interface GeoHeatmapPoint {
  lat: number
  lon: number
  intensity: number
  label: string
  value: number
}

export interface GeoMapData {
  cities: { name: string; lat: number; lon: number; tier: number; population: number; competitors: number; state: string }[]
  states: { name: string; capital: string; population: number; gdp_per_capita: number }[]
}

export interface ContributingFactor {
  factor: string
  impact: string
  direction: string
  description: string
}

export interface CompetitorServicePricingPrediction {
  service: string
  utservio_price: number
  competitor: string
  current_competitor_price: number
  predicted_service: string
  service_probability: number
  likelihood_category: string
  predicted_price: number
  price_range: { lower: number; upper: number }
  price_difference: number
  price_gap_percentage: number
  confidence: number
  confidence_level: string
  horizon_days: number
  training_observations: number
  data_quality_score: number
  model: string
  strategic_insight: string
  insight_category: string
  contributing_factors: ContributingFactor[]
}

export interface DBPredictionResult {
  competitor_id: number
  competitor: string
  service: string
  canonical_service_id?: number
  utservio_current_price: number
  current_competitor_price: number
  predicted_price: number
  lower_bound: number
  upper_bound: number
  service_probability: number
  predicted_service_available: string
  price_gap_percentage: number
  confidence_score: number
  confidence_level: string
  prediction_horizon_days: number
  training_data_size: number
  historical_period: string
  data_quality_score: number
  comparability_status: 'comparable' | 'insufficient_comparability' | 'insufficient_data'
  model_name: string
  model_version: string
  strategic_insight: string
  contributing_factors: ContributingFactor[]
  recommendation_note?: string
}

export interface DBPredictionFeedback {
  total_predictions_evaluated: number
  mean_absolute_error: number
  mean_absolute_percentage_error: number
  feedback_records_added: number
  accuracy_score: number
  status: string
}
