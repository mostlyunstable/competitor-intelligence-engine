from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    url: str = Field(default="postgresql+asyncpg://utservio:changeme@localhost:5432/utservio_ci")
    echo: bool = Field(default=False)
    pool_size: int = Field(default=10)
    max_overflow: int = Field(default=20)
    pool_timeout: int = Field(default=30)
    pool_recycle: int = Field(default=1800)


class CollectorSettings(BaseModel):
    max_concurrent_requests: int = Field(default=10, ge=1, le=100)
    collection_timeout: int = Field(default=300, ge=30, le=3600)
    rate_limit_per_second: float = Field(default=0.5, ge=0.1, le=10.0)
    user_agent: str = Field(default="UtservioCI/1.0")
    retry_attempts: int = Field(default=3, ge=1, le=10)
    retry_delay: float = Field(default=1.0, ge=0.1, le=10.0)
    playwright_timeout: int = Field(default=60000, ge=5000, le=120000)
    primary_selector: str = Field(default="body")
    enable_conditional_get: bool = Field(default=True)
    enable_content_hash_skip: bool = Field(default=True)


class CacheSettings(BaseModel):
    enabled: bool = Field(default=True)
    max_entries: int = Field(default=10000, ge=100, le=1000000)
    default_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    respect_cache_control: bool = Field(default=True)


class DiscoverySettings(BaseModel):
    max_pages_per_competitor: int = Field(default=50, ge=5, le=500)
    max_depth: int = Field(default=2, ge=1, le=5)
    same_domain_only: bool = Field(default=True)
    fetch_sitemap: bool = Field(default=True)
    fetch_robots_txt: bool = Field(default=True)
    parse_nav: bool = Field(default=True)
    parse_footer: bool = Field(default=True)
    parse_internal_links: bool = Field(default=True)


class SchedulerSettings(BaseModel):
    enabled: bool = Field(default=True)
    check_interval_seconds: int = Field(default=60, ge=10)


class QueueSettings(BaseModel):
    backend: str = Field(default="memory")  # memory, redis
    redis_url: str = Field(default="redis://localhost:6379")
    queue_name: str = Field(default="crawl_queue")
    num_workers: int = Field(default=1, ge=1, le=10)


class WebhookSettings(BaseModel):
    enabled: bool = Field(default=False)
    slack_webhook_url: str = Field(default="")
    teams_webhook_url: str = Field(default="")


class LLMSettings(BaseModel):
    enabled: bool = Field(default=False)
    provider: str = Field(default="gemini")
    api_key: str = Field(default="")
    model_name: str = Field(default="gemini-2.5-flash")


class StealthSettings(BaseModel):
    enabled: bool = Field(default=True)
    proxy_url: str = Field(default="")
    proxy_urls: list[str] = Field(default_factory=list)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CI_",
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: str = Field(default="development")
    log_level: str = Field(default="info")
    debug: bool = Field(default=False)
    api_key: str = Field(default="")

    staging_database_url: str = Field(
        default="postgresql+asyncpg://utservio:changeme@localhost:5433/utservio_ci_staging"
    )
    staging_redis_url: str = Field(default="redis://localhost:6380")
    staging_vault_url: str = Field(default="http://localhost:8201")

    production_database_url: str = Field(default="")
    production_redis_url: str = Field(default="")
    production_vault_url: str = Field(default="")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    collector: CollectorSettings = Field(default_factory=CollectorSettings)
    discovery: DiscoverySettings = Field(default_factory=DiscoverySettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    queue: QueueSettings = Field(default_factory=QueueSettings)
    webhook: WebhookSettings = Field(default_factory=WebhookSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    stealth: StealthSettings = Field(default_factory=StealthSettings)

    competitors_config_path: str = Field(default="./competitors.json")

    @property
    def is_staging(self) -> bool:
        return self.environment == "staging"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


_settings_instance: Settings | None = None


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def reset_settings() -> None:
    global _settings_instance
    _settings_instance = None
