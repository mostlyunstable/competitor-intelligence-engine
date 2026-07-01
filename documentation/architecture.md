# Architecture

## Overview

The Competitor Intelligence Engine is a data collection service. It periodically fetches public information from competitor websites and stores structured data in PostgreSQL.

This service does not analyze data. It collects it.

## Design Principles

1. **Collector-based architecture**: Each data type has its own collector. Adding a new data type means adding a new collector, not modifying existing code.

2. **Configuration over code**: Competitors are defined in configuration, not in code. Adding a competitor requires zero code changes.

3. **Transactional writes**: Each collector writes its results within a single database transaction. If anything fails, the entire collector's output rolls back.

4. **Graceful degradation**: If one collector fails (e.g., pricing page is down), other collectors continue. A failure in one module does not block the entire collection.

## Data Flow

```
Trigger (manual or scheduler)
  -> CollectionService
    -> Load competitor config
    -> For each enabled module:
      -> Call module-specific Collector
        -> Fetch page (httpx, with Playwright fallback)
        -> Parse HTML via Parser
        -> Write structured data to database
    -> Write CollectionLog
    -> Return results
```

## Modules

| Module | Collector | Parser | Data Written |
|--------|-----------|--------|--------------|
| discovery | DiscoveryCollector | DiscoveryParser | New URLs to crawl |
| company | CompanyCollector | CompanyParser | Company info |
| services | ServiceCollector | ServiceParser | Service listings |
| pricing | PricingCollector | PricingParser | Pricing data |
| content | ContentCollector | ContentParser | Blog posts, articles |
| social | SocialCollector | SocialParser | Social profiles |

## Database Schema

### competitors

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique identifier |
| name | VARCHAR(255) NOT NULL UNIQUE | Company name |
| website_url | VARCHAR(2048) NOT NULL | Primary website URL |
| enabled | BOOLEAN DEFAULT TRUE | Whether to collect |
| collection_frequency | ENUM | hourly, daily, weekly |
| modules | JSON | Which modules to run |
| tags | JSON | User-defined tags |
| notes | TEXT | Additional notes |
| created_at | TIMESTAMP | When added |
| updated_at | TIMESTAMP | Last modified |

### competitor_sources

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique identifier |
| competitor_id | INTEGER FK -> competitors | Parent competitor |
| url | VARCHAR(2048) NOT NULL | Discovered URL |
| page_type | VARCHAR(100) | What kind of page |
| discovered_at | TIMESTAMP | When found |
| last_crawled_at | TIMESTAMP | When last fetched |
| is_active | BOOLEAN | Still accessible |

UNIQUE: `(competitor_id, url)`

### competitor_pages

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique identifier |
| competitor_id | INTEGER FK -> competitors | Parent competitor |
| source_id | INTEGER FK -> sources (SET NULL) | Source URL |
| content_hash | VARCHAR(64) NOT NULL | SHA-256 of content |
| raw_html | TEXT | Original HTML |
| raw_json | JSON | Structured extraction |
| metadata | JSON | Collection metadata |
| collected_at | TIMESTAMP | When collected |
| collection_status | ENUM | success, failed, partial |

UNIQUE: `(competitor_id, source_id, content_hash)`

### competitor_services

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique identifier |
| competitor_id | INTEGER FK -> competitors | Parent competitor |
| service_category | VARCHAR(255) | Category |
| service_name | VARCHAR(500) | Name |
| description | TEXT | Description |
| estimated_duration | VARCHAR(100) | Time estimate |
| starting_price | DECIMAL(10,2) | Price |
| currency | VARCHAR(3) | Currency code |
| available_add_ons | JSON | Add-ons |
| membership_available | BOOLEAN | Membership option |
| offers | JSON | Current offers |
| discounts | JSON | Discount info |
| content_hash | VARCHAR(64) NOT NULL | SHA-256 of canonical fields |
| collected_at | TIMESTAMP | When collected |

UNIQUE: `(competitor_id, content_hash)`

### competitor_pricing

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique identifier |
| competitor_id | INTEGER FK -> competitors | Parent competitor |
| service_name | VARCHAR(500) | What service |
| category | VARCHAR(255) | Category |
| base_price | DECIMAL(10,2) | Regular price |
| promotional_price | DECIMAL(10,2) | Sale price |
| currency | VARCHAR(3) | Currency code |
| discount | DECIMAL(10,2) | Discount amount |
| membership_pricing | JSON | Membership prices |
| subscription_plans | JSON | Subscription options |
| content_hash | VARCHAR(64) NOT NULL | SHA-256 of canonical fields |
| collected_at | TIMESTAMP | When collected |

UNIQUE: `(competitor_id, content_hash)`

### competitor_content

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique identifier |
| competitor_id | INTEGER FK -> competitors | Parent competitor |
| title | VARCHAR(1000) | Content title |
| author | VARCHAR(255) | Author name |
| publish_date | DATE | When published |
| url | VARCHAR(2048) NOT NULL | Content URL |
| summary | TEXT | Short summary |
| raw_content | TEXT | Full content |
| content_type | VARCHAR(100) | blog, article, press_release |
| content_hash | VARCHAR(64) NOT NULL | SHA-256 of canonical fields |
| collected_at | TIMESTAMP | When collected |

UNIQUE: `(competitor_id, url)`

### competitor_social

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique identifier |
| competitor_id | INTEGER FK -> competitors | Parent competitor |
| platform | ENUM | linkedin, facebook, instagram, twitter, youtube, pinterest, threads |
| profile_url | VARCHAR(2048) NOT NULL | Profile URL |
| username | VARCHAR(255) | Platform username |
| collected_at | TIMESTAMP | When collected |

UNIQUE: `(competitor_id, platform)`

### collection_logs

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique identifier |
| competitor_id | INTEGER FK -> competitors | What was collected |
| start_time | TIMESTAMP | When collection started |
| end_time | TIMESTAMP | When collection ended |
| success | BOOLEAN | Whether it succeeded |
| duration_seconds | DECIMAL(10,2) | How long it took |
| records_collected | INTEGER | How many records |
| errors | JSON | Error messages |
| retry_count | INTEGER | Retries attempted |
| created_at | TIMESTAMP | Log entry created |

### raw_storage

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique identifier |
| competitor_id | INTEGER FK -> competitors | Parent competitor |
| source_url | VARCHAR(2048) NOT NULL | Page URL |
| content_hash | VARCHAR(64) NOT NULL | SHA-256 of HTML + URL |
| raw_html | TEXT | Original HTML |
| raw_json | JSON | Structured extraction |
| metadata | JSON | Collection metadata |
| collected_at | TIMESTAMP | When collected |
| collection_status | VARCHAR(50) | success, failed, partial |

UNIQUE: `(competitor_id, source_url)`

## Error Handling

- Collector failures are isolated per module
- HTTP retries with exponential backoff (configurable)
- Collection timeout per run (configurable, default 300s)
- All failures logged with structured context
- Partial results stored even if some modules fail
