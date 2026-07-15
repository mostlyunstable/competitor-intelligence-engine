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
  competitor_id: number
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
