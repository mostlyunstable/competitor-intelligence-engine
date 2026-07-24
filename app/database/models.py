import enum
from datetime import date, datetime
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
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
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
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
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
    market_position: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

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

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="ai_insight")
