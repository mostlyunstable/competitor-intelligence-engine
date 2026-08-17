import enum
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class CollectionFrequency(enum.StrEnum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class CollectionStatus(enum.StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class SocialPlatform(enum.StrEnum):
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    PINTEREST = "pinterest"
    THREADS = "threads"


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    website_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    collection_frequency: Mapped[CollectionFrequency] = mapped_column(
        Enum(CollectionFrequency, name="collection_frequency_enum", create_constraint=True),
        default=CollectionFrequency.DAILY,
        nullable=False,
    )
    modules: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    sources: Mapped[list["CompetitorSource"]] = relationship(
        "CompetitorSource", back_populates="competitor", cascade="all, delete-orphan"
    )
    services: Mapped[list["CompetitorService"]] = relationship(
        "CompetitorService", back_populates="competitor", cascade="all, delete-orphan"
    )
    pricing: Mapped[list["CompetitorPricing"]] = relationship(
        "CompetitorPricing", back_populates="competitor", cascade="all, delete-orphan"
    )
    content: Mapped[list["CompetitorContent"]] = relationship(
        "CompetitorContent", back_populates="competitor", cascade="all, delete-orphan"
    )
    ai_insight: Mapped["CompetitorAIInsight"] = relationship("CompetitorAIInsight", back_populates="competitor", cascade="all, delete-orphan", uselist=False)
    social_profiles: Mapped[list["CompetitorSocial"]] = relationship(
        "CompetitorSocial", back_populates="competitor", cascade="all, delete-orphan"
    )
    collection_logs: Mapped[list["CollectionLog"]] = relationship(
        "CollectionLog", back_populates="competitor", cascade="all, delete-orphan"
    )
    change_events: Mapped[list["CompetitorChangeEvent"]] = relationship(
        "CompetitorChangeEvent", back_populates="competitor", cascade="all, delete-orphan"
    )

    __table_args__ = ({"comment": "Registered competitor websites"},)


class CompetitorSource(Base):
    __tablename__ = "competitor_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    page_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="sources")

    __table_args__ = (
        UniqueConstraint("competitor_id", "url", name="uq_competitor_source_url"),
        Index("ix_competitor_source_competitor_id", "competitor_id"),
        Index("ix_competitor_source_url", "url"),
        {"comment": "Discovered URLs per competitor"},
    )


class CompetitorService(Base):
    __tablename__ = "competitor_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False
    )
    service_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service_name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    starting_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    available_add_ons: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    membership_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    offers: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    discounts: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    provenance: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="services")

    __table_args__ = (
        Index("ix_competitor_service_competitor_id", "competitor_id"),
        UniqueConstraint("competitor_id", "content_hash", name="uq_competitor_service_hash"),
        Index("ix_services_comp_date", "competitor_id", "collected_at"),
        {"comment": "Service listings collected from competitors"},
    )


class CompetitorPricing(Base):
    __tablename__ = "competitor_pricing"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False
    )
    service_name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    base_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    promotional_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    discount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    membership_pricing: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    subscription_plans: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    provenance: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="pricing")

    __table_args__ = (
        Index("ix_competitor_pricing_competitor_id", "competitor_id"),
        UniqueConstraint("competitor_id", "content_hash", name="uq_competitor_pricing_hash"),
        Index("ix_pricing_comp_date", "competitor_id", "collected_at"),
        {"comment": "Pricing data collected from competitors"},
    )


class CompetitorContent(Base):
    __tablename__ = "competitor_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    provenance: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="content")

    __table_args__ = (
        UniqueConstraint("competitor_id", "url", name="uq_competitor_content_url"),
        Index("ix_competitor_content_competitor_id", "competitor_id"),
        Index("ix_competitor_content_url", "url"),
        Index("ix_competitor_content_content_hash", "content_hash"),
        {"comment": "Blog posts, articles, and press releases"},
    )


class CompetitorSocial(Base):
    __tablename__ = "competitor_social"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[SocialPlatform] = mapped_column(
        Enum(SocialPlatform, name="social_platform_enum", create_constraint=True),
        nullable=False,
    )
    profile_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="social_profiles")

    __table_args__ = (
        UniqueConstraint("competitor_id", "platform", name="uq_competitor_social_platform"),
        Index("ix_competitor_social_competitor_id", "competitor_id"),
        {"comment": "Social media profiles per competitor"},
    )


class CollectionLog(Base):
    __tablename__ = "collection_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    records_collected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="collection_logs")

    __table_args__ = (
        Index("ix_collection_log_competitor_id", "competitor_id"),
        Index("ix_collection_log_start_time", "start_time"),
        Index("ix_collection_log_success", "success"),
        {"comment": "Audit trail of all collection runs"},
    )


class RawStorage(Base):
    __tablename__ = "raw_storage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False
    )
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    storage_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    extracted_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    collection_status: Mapped[CollectionStatus] = mapped_column(
        Enum(CollectionStatus, name="collection_status_enum", create_constraint=True),
        default=CollectionStatus.SUCCESS,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "competitor_id",
            "source_url",
            name="uq_raw_storage_competitor_url",
        ),
        Index("ix_raw_storage_competitor_id", "competitor_id"),
        Index("ix_raw_storage_source_url", "source_url"),
        Index("ix_raw_storage_content_hash", "content_hash"),
        Index("ix_raw_storage_extracted_data_gin", "extracted_data", postgresql_using="gin"),
        {"comment": "Original HTML snapshots and raw data"},
    )


class ChangeLog(Base):
    __tablename__ = "change_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False
    )
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)  # services, pricing, content, social
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)  # added, removed, modified
    record_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_change_log_competitor_id", "competitor_id"),
        Index("ix_change_log_data_type", "data_type"),
        Index("ix_change_log_detected_at", "detected_at"),
        {"comment": "Tracks changes between collections"},
    )


class CompetitorChangeEvent(Base):
    __tablename__ = "competitor_change_events"
    __table_args__ = (
        Index("ix_change_event_competitor_id", "competitor_id"),
        Index("ix_change_event_event_type", "event_type"),
        Index("ix_change_event_detected_at", "detected_at"),
        Index("ix_change_event_comp_date", "competitor_id", "detected_at"),
        {"comment": "Tracks granular change deltas for predictive analysis"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(100))
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    magnitude: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)

    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="change_events")


class CompetitorAIInsight(Base):
    """
    Stores AI-generated intelligence and insights about a competitor.
    Updated continuously as new data is collected.
    """
    __tablename__ = "competitor_ai_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    competitor_id: Mapped[int] = mapped_column(
        ForeignKey("competitors.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Core attributes from AI analysis
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    key_differentiators: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    market_position: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    data_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Complex nested JSON data
    pricing_analysis: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    feature_gaps: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    strategic_moves: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)

    # Recommendations
    recommendations: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    latest_updates: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)

    # Provenance
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    processing_status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed", index=True)

    # Cost tracking
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="ai_insight")
    feedbacks: Mapped[list["AIInsightFeedback"]] = relationship(
        "AIInsightFeedback", back_populates="insight", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_ai_insight_llm_provider", "llm_provider"),
        Index("ix_ai_insight_prompt_version", "prompt_version"),
    )


class AIInsightFeedback(Base):
    """User feedback on AI insights for quality tracking."""
    __tablename__ = "ai_insight_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    insight_id: Mapped[int] = mapped_column(
        ForeignKey("competitor_ai_insights.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=thumbs down, 2=thumbs up
    comment: Mapped[str] = mapped_column(Text, nullable=True, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    insight: Mapped["CompetitorAIInsight"] = relationship("CompetitorAIInsight", back_populates="feedbacks")


# ─── Sprint 7: Predictive Intelligence Models ────────────────────────────────


class PredictionType(enum.StrEnum):
    GROWTH = "growth"
    PRICING = "pricing"
    SERVICE_LAUNCH = "service_launch"
    MARKET_MOVEMENT = "market_movement"
    EXPANSION = "expansion"


class TrendDirection(enum.StrEnum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    EMERGING = "emerging"


class RiskLevel(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GrowthLevel(enum.StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ChangeEventType(StrEnum):
    PRICE_CHANGE = "PRICE_CHANGE"
    SERVICE_LAUNCH = "SERVICE_LAUNCH"
    SERVICE_DISCONTINUATION = "SERVICE_DISCONTINUATION"
    REGIONAL_EXPANSION = "REGIONAL_EXPANSION"
    CONTENT_UPDATE = "CONTENT_UPDATE"
    STRATEGIC_SHIFT = "STRATEGIC_SHIFT"


class CompetitorPrediction(Base):
    """Stores predictive intelligence for a competitor."""
    __tablename__ = "competitor_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    competitor_id: Mapped[int] = mapped_column(
        ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prediction_type: Mapped[PredictionType] = mapped_column(
        Enum(PredictionType, name="prediction_type_enum", create_constraint=True),
        nullable=False, index=True
    )
    prediction_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="heuristic_v1")

    __table_args__ = (
        Index("ix_prediction_competitor_type", "competitor_id", "prediction_type"),
        {"comment": "Predictive intelligence per competitor"},
    )


class MarketTrend(Base):
    """Stores detected market trends."""
    __tablename__ = "market_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    direction: Mapped[TrendDirection] = mapped_column(
        Enum(TrendDirection, name="trend_direction_enum", create_constraint=True),
        nullable=False
    )
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    affected_competitors: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_trend_category_direction", "category", "direction"),
        {"comment": "Detected market trends"},
    )


class RegionalExpansion(Base):
    """Stores regional expansion forecasts."""
    __tablename__ = "regional_expansions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    competitor_id: Mapped[int] = mapped_column(
        ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    region: Mapped[str] = mapped_column(String(255), nullable=False)
    expansion_probability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expansion_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_timeline: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    factors: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_expansion_competitor_region", "competitor_id", "region"),
        {"comment": "Regional expansion forecasts"},
    )


class CompetitorRisk(Base):
    """Stores risk analysis for competitors."""
    __tablename__ = "competitor_risks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    competitor_id: Mapped[int] = mapped_column(
        ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    risk_type: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level_enum", create_constraint=True),
        nullable=False
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    likelihood: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    business_impact: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mitigation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_risk_competitor_type", "competitor_id", "risk_type"),
        {"comment": "Competitor risk analysis"},
    )


class BusinessOpportunity(Base):
    """Stores detected business opportunities."""
    __tablename__ = "business_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    opportunity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    opportunity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    roi_estimate: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False, default="")
    affected_regions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    affected_competitors: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        {"comment": "Detected business opportunities"},
    )


class StrategicRecommendation(Base):
    """Stores AI-generated strategic recommendations."""
    __tablename__ = "strategic_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    why: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_benefit: Mapped[str] = mapped_column(Text, nullable=False, default="")
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="recommendation_risk_level_enum", create_constraint=True),
        nullable=False, default=RiskLevel.LOW
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        {"comment": "Strategic recommendations"},
    )


class PredictiveBenchmark(Base):
    """Stores predictive benchmarking data."""
    __tablename__ = "predictive_benchmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    competitor_id: Mapped[int] = mapped_column(
        ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    current_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    predicted_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    growth_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    innovation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expansion_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overall_prediction: Mapped[str] = mapped_column(String(20), nullable=False, default="stable")
    benchmark_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("competitor_id", name="uq_benchmark_competitor"),
        {"comment": "Predictive benchmarking data"},
    )


class ForecastReport(Base):
    """Stores generated forecast reports."""
    __tablename__ = "forecast_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    predictions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    risks: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    opportunities: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    recommendations: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    benchmark_data: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    regional_insights: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    business_actions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    report_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        {"comment": "Generated forecast reports"},
    )


class PredictionEvaluation(Base):
    __tablename__ = "prediction_evaluations"
    __table_args__ = (
        Index("ix_pred_eval_competitor_id", "competitor_id"),
        Index("ix_pred_eval_prediction_type", "prediction_type"),
        Index("ix_pred_eval_evaluated_at", "evaluated_at"),
        {"comment": "Historical backtesting and actual vs. forecast validation"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    actual_value: Mapped[float | None] = mapped_column(Float)
    error_margin: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)
    model_used: Mapped[str | None] = mapped_column(String(100))
    evaluation_notes: Mapped[str | None] = mapped_column(Text)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    competitor = relationship("Competitor")


class CanonicalService(Base):
    __tablename__ = "canonical_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    pricing_unit: Mapped[str] = mapped_column(String(50), nullable=False, default="per_service")
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    mappings: Mapped[list["ServiceMapping"]] = relationship("ServiceMapping", back_populates="canonical_service")
    observations: Mapped[list["PriceObservation"]] = relationship("PriceObservation", back_populates="canonical_service")

    __table_args__ = (
        {"comment": "Standardized canonical service taxonomy"},
    )


class ServiceMapping(Base):
    __tablename__ = "service_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    original_service_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    canonical_service_id: Mapped[int] = mapped_column(Integer, ForeignKey("canonical_services.id", ondelete="CASCADE"), nullable=False, index=True)
    competitor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("competitors.id", ondelete="SET NULL"), nullable=True, index=True)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    matching_methodology: Mapped[str] = mapped_column(String(100), nullable=False, default="exact_match")
    human_validation_status: Mapped[str] = mapped_column(String(50), nullable=False, default="validated")
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    canonical_service: Mapped["CanonicalService"] = relationship("CanonicalService", back_populates="mappings")

    __table_args__ = (
        Index("ix_service_mapping_comp_canonical", "competitor_id", "canonical_service_id"),
        {"comment": "Mappings from raw service names to canonical services"},
    )


class PriceObservation(Base):
    __tablename__ = "price_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("competitor_services.id", ondelete="SET NULL"), nullable=True, index=True)
    competitor_id: Mapped[int] = mapped_column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    canonical_service_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("canonical_services.id", ondelete="SET NULL"), nullable=True, index=True)
    original_service_name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="Pan India")
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    pricing_unit: Mapped[str] = mapped_column(String(50), nullable=False, default="per_service")
    price_type: Mapped[str] = mapped_column(String(50), nullable=False, default="standard")
    discount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="website")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    validation_status: Mapped[str] = mapped_column(String(50), nullable=False, default="validated")
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    canonical_service: Mapped["CanonicalService"] = relationship("CanonicalService", back_populates="observations")
    quality_breakdown: Mapped["DataQualityScoreRecord | None"] = relationship("DataQualityScoreRecord", back_populates="observation", uselist=False)

    __table_args__ = (
        Index("ix_price_obs_comp_canonical_date", "competitor_id", "canonical_service_id", "collected_at"),
        {"comment": "Immutable time-series pricing observations"},
    )


class PricingResolutionRecord(Base):
    __tablename__ = "pricing_resolution_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_service_id: Mapped[int] = mapped_column(Integer, ForeignKey("canonical_services.id", ondelete="CASCADE"), nullable=False, index=True)
    conflicting_observations: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    resolved_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    promotional_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_type: Mapped[str] = mapped_column(String(50), nullable=False, default="standard")
    resolution_reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.9)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        {"comment": "Audit trail of conflicting pricing discrepancy resolutions"},
    )


class DataQualityScoreRecord(Base):
    __tablename__ = "data_quality_score_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observation_id: Mapped[int] = mapped_column(Integer, ForeignKey("price_observations.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    completeness: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    consistency: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    timeliness: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    validity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    uniqueness: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    comparability: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    observation: Mapped["PriceObservation"] = relationship("PriceObservation", back_populates="quality_breakdown")

    __table_args__ = (
        {"comment": "Detailed 7-dimension data quality scores"},
    )


class MLPredictionRecord(Base):
    __tablename__ = "ml_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("competitor_services.id", ondelete="SET NULL"), nullable=True, index=True)
    canonical_service_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("canonical_services.id", ondelete="SET NULL"), nullable=True, index=True)
    service_name: Mapped[str] = mapped_column(String(500), nullable=False)
    prediction_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    prediction_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    utservio_base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    current_competitor_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    predicted_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    lower_bound: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    upper_bound: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    predicted_service_available: Mapped[str] = mapped_column(String(50), nullable=False, default="Likely")
    service_probability: Mapped[float] = mapped_column(Float, nullable=False, default=0.85)
    price_gap_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="XGBoost & Ridge Ensemble")
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v2.0-db")
    training_data_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.85)
    comparability_status: Mapped[str] = mapped_column(String(50), nullable=False, default="comparable")  # "comparable", "insufficient_comparability", "insufficient_data"
    contributing_factors: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    feedbacks: Mapped[list["MLPredictionFeedbackRecord"]] = relationship("MLPredictionFeedbackRecord", back_populates="prediction", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_ml_predictions_comp_canon_date", "competitor_id", "canonical_service_id", "prediction_timestamp"),
        {"comment": "Database-persisted ML predictions for competitor service adoption & pricing"},
    )


class MLPredictionFeedbackRecord(Base):
    __tablename__ = "ml_prediction_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prediction_id: Mapped[int] = mapped_column(Integer, ForeignKey("ml_predictions.id", ondelete="CASCADE"), nullable=False, index=True)
    actual_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    prediction_error: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    absolute_error: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    percentage_error: Mapped[float] = mapped_column(Float, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    prediction: Mapped["MLPredictionRecord"] = relationship("MLPredictionRecord", back_populates="feedbacks")

    __table_args__ = (
        {"comment": "Continuous feedback loop tracking actual vs predicted pricing error"},
    )
