"""ORM models."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, SmallInteger, String, Text
from sqlalchemy import text as sa_text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from pgvector.sqlalchemy import Vector

from aperix_geo.db.base import Base, utc_now


class SubjectType(str, enum.Enum):
    domain = "domain"
    brand = "brand"


class UserRole(str, enum.Enum):
    admin = "admin"
    member = "member"
    readonly = "readonly"


class SamplingJobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeed = "succeed"
    failed = "failed"
    partial = "partial"


class LLMResponseStatus(str, enum.Enum):
    pending = "pending"
    llm_ready = "llm_ready"
    crawl_ready = "crawl_ready"
    success = "success"
    failed = "failed"


class EntityKind(str, enum.Enum):
    own = "own"
    competitor = "competitor"
    other = "other"


_NOW = sa_text("now()")
ZERO_UUID = uuid.UUID("00000000-0000-0000-0000-000000000000")
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class Tenant(Base):
    __tablename__ = "tb_tenants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    usage_pack_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    users: Mapped[list["User"]] = relationship(back_populates="tenant")
    subjects: Mapped[list["Subject"]] = relationship(back_populates="tenant")
    subscription: Mapped["TenantSubscription | None"] = relationship(
        back_populates="tenant", uselist=False, cascade="all, delete-orphan"
    )
    usage_periods: Mapped[list["TenantUsagePeriod"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    plan_override: Mapped["TenantPlanOverride | None"] = relationship(
        back_populates="tenant", uselist=False, cascade="all, delete-orphan"
    )
    pay_orders: Mapped[list["TenantPayOrder"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    quota_ledger: Mapped[list["TenantQuotaLedger"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )

    __table_args__ = (CheckConstraint("usage_pack_balance >= 0", name="ck_tb_tenants_usage_pack_balance_nonneg"),)


class BrandSource:
    setup = "setup"
    sampling_open_set = "sampling_open_set"


class Brand(Base):
    """Subject-scoped brand registry (own / configured competitor / open-set other)."""

    __tablename__ = "tb_brands"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False
    )
    entity_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="other", server_default="other")
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    brand: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    domain: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    website_url: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    aliases: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=sa_text("'[]'::jsonb"))
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    subject: Mapped["Subject"] = relationship(back_populates="brands")
    llm_response_signals: Mapped[list["LLMResponseSignal"]] = relationship(back_populates="brand")

    __table_args__ = (
        Index("ix_brands_subject_id", "subject_id"),
        Index("ix_brands_subject_brand", "subject_id", "brand"),
        Index(
            "uq_brands_domain_nonempty",
            "subject_id",
            "domain",
            unique=True,
            postgresql_where=sa_text("domain <> '' AND deleted = false"),
        ),
        Index(
            "uq_brands_domain_empty_by_brand",
            "subject_id",
            "brand",
            unique=True,
            postgresql_where=sa_text("domain = '' AND deleted = false"),
        ),
        Index(
            "uq_brands_subject_entity_id",
            "subject_id",
            "entity_id",
            unique=True,
            postgresql_where=sa_text("entity_id <> '' AND deleted = false"),
        ),
    )


class User(Base):
    __tablename__ = "tb_users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False, default="", server_default="")
    email: Mapped[str] = mapped_column(String(320), nullable=False, default="", server_default="")
    password: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=UserRole.admin.value,
        server_default=sa_text("'admin'"),
    )
    nick_name: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    open_id: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    union_id: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    notify_in_app: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    notify_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    notify_wechat: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    tenant: Mapped[Tenant] = relationship(back_populates="users")
    notifications: Mapped[list["UserNotification"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("email <> '' OR phone <> ''", name="ck_tb_users_email_or_phone"),
        Index(
            "uq_users_phone",
            "phone",
            unique=True,
            postgresql_where=sa_text("phone <> '' AND deleted = false"),
        ),
        Index(
            "uq_users_tenant_email_nn",
            "tenant_id",
            "email",
            unique=True,
            postgresql_where=sa_text("email <> '' AND deleted = false"),
        ),
        Index(
            "uq_users_wechat_open_id",
            "open_id",
            unique=True,
            postgresql_where=sa_text("open_id <> '' AND deleted = false"),
        ),
        Index(
            "uq_users_wechat_union_id",
            "union_id",
            unique=True,
            postgresql_where=sa_text("union_id <> '' AND deleted = false"),
        ),
    )


class Subject(Base):
    __tablename__ = "tb_subjects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[SubjectType] = mapped_column(
        SAEnum(SubjectType, name="subject_type"),
        nullable=False,
        default=SubjectType.domain,
        server_default=sa_text("'domain'::subject_type"),
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    brand: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    aliases: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=sa_text("'[]'::jsonb"))
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    website_url: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    profile_summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    niche_profile: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa_text("'{}'::jsonb")
    )
    sampling_platforms: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa_text("'[]'::jsonb")
    )
    last_sampled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=_NOW
    )
    sampling_frequency: Mapped[str] = mapped_column(
        String(32), nullable=False, default="daily_1", server_default="daily_1"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    tenant: Mapped[Tenant] = relationship(back_populates="subjects")
    competitors: Mapped[list["Competitor"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )
    topics: Mapped[list["Topic"]] = relationship(back_populates="subject", cascade="all, delete-orphan")
    prompts: Mapped[list["Prompt"]] = relationship(back_populates="subject", cascade="all, delete-orphan")
    sampling_jobs: Mapped[list["SamplingJob"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )
    brand_report_exports: Mapped[list["BrandReportExport"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )
    brands: Mapped[list["Brand"]] = relationship(back_populates="subject", cascade="all, delete-orphan")
    knowledge: Mapped["SubjectKnowledge | None"] = relationship(
        back_populates="subject", uselist=False, cascade="all, delete-orphan"
    )
    knowledge_sources: Mapped[list["KnowledgeSource"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )
    knowledge_chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_subjects_tenant_id", "tenant_id"),
    )


class Competitor(Base):
    __tablename__ = "tb_competitors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    website_url: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    brand: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    aliases: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=sa_text("'[]'::jsonb"))
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    cross_validate_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    cross_validate_reason: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    cross_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    subject: Mapped[Subject] = relationship(back_populates="competitors")

    __table_args__ = (
        Index("ix_competitors_subject_id", "subject_id"),
        Index(
            "uq_competitors_domain_nonempty",
            "subject_id",
            "domain",
            unique=True,
            postgresql_where=sa_text("domain <> '' AND deleted = false"),
        ),
        Index(
            "uq_competitors_domain_empty_by_brand",
            "subject_id",
            "brand",
            unique=True,
            postgresql_where=sa_text("domain = '' AND deleted = false"),
        ),
    )


class Topic(Base):
    __tablename__ = "tb_subject_topics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    decision_dimension: Mapped[str] = mapped_column(
        String(32), nullable=False, default="", server_default=""
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    subject: Mapped[Subject] = relationship(back_populates="topics")
    prompts: Mapped[list["Prompt"]] = relationship(back_populates="topic", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_subject_topics_subject_id", "subject_id"),)


class Prompt(Base):
    __tablename__ = "tb_subject_prompts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subject_topics.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    funnel_stage: Mapped[str] = mapped_column(String(8), nullable=False, default="mofu", server_default="mofu")
    search_intent: Mapped[str] = mapped_column(
        String(16), nullable=False, default="commercial", server_default="commercial"
    )
    decision_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="", server_default=""
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    subject: Mapped[Subject] = relationship(back_populates="prompts")
    topic: Mapped[Topic] = relationship(back_populates="prompts")
    responses: Mapped[list["LLMResponse"]] = relationship(back_populates="prompt")
    citation_urls: Mapped[list["CitationUrl"]] = relationship(
        back_populates="prompt", cascade="all, delete-orphan"
    )
    citation_domains: Mapped[list["CitationDomain"]] = relationship(
        back_populates="prompt", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "uq_subject_prompts_hash",
            "subject_id",
            "text_hash",
            unique=True,
            postgresql_where=sa_text("deleted = false"),
        ),
        Index("ix_subject_prompts_subject_id", "subject_id"),
        Index("ix_subject_prompts_topic_id", "topic_id"),
    )


class SamplingJob(Base):
    __tablename__ = "tb_sampling_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[SamplingJobStatus] = mapped_column(
        SAEnum(SamplingJobStatus, name="sampling_job_status"),
        nullable=False,
        default=SamplingJobStatus.queued,
        server_default=sa_text("'queued'::sampling_job_status"),
    )
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=_NOW
    )
    finished_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=_NOW
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    subject: Mapped[Subject] = relationship(back_populates="sampling_jobs")
    llm_responses: Mapped[list["LLMResponse"]] = relationship(
        back_populates="sampling_job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_sampling_jobs_tenant_id", "tenant_id"),
        Index("ix_sampling_jobs_subject_created", "subject_id", "created_at"),
    )


class BrandReportExport(Base):
    """Audit log for on-demand brand report PDF exports."""

    __tablename__ = "tb_brand_report_exports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_users.id", ondelete="CASCADE"), nullable=False
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    platform: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=sa_text("'[]'::jsonb"))
    topic_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=sa_text("'[]'::jsonb"))
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="pdf", server_default="pdf")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    subject: Mapped[Subject] = relationship(back_populates="brand_report_exports")

    __table_args__ = (
        Index("ix_brand_report_exports_subject_created", "subject_id", "created_at"),
        Index("ix_brand_report_exports_tenant_user_created", "tenant_id", "user_id", "created_at"),
    )


class LLMResponse(Base):
    __tablename__ = "tb_llm_responses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sampling_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_sampling_jobs.id", ondelete="CASCADE"), nullable=False
    )
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subject_prompts.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    status: Mapped[LLMResponseStatus] = mapped_column(
        SAEnum(LLMResponseStatus, name="llm_response_status"),
        nullable=False,
        default=LLMResponseStatus.pending,
        server_default=sa_text("'pending'::llm_response_status"),
    )
    error_text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    parsed: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=sa_text("'{}'::jsonb")
    )
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    usage: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=sa_text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    sampling_job: Mapped[SamplingJob] = relationship(back_populates="llm_responses")
    prompt: Mapped[Prompt] = relationship(back_populates="responses")
    citation_urls: Mapped[list["CitationUrl"]] = relationship(
        back_populates="llm_response", cascade="all, delete-orphan"
    )
    citation_domains: Mapped[list["CitationDomain"]] = relationship(
        back_populates="llm_response", cascade="all, delete-orphan"
    )
    llm_response_signals: Mapped[list["LLMResponseSignal"]] = relationship(
        back_populates="llm_response", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "uq_job_prompt_platform",
            "sampling_job_id",
            "prompt_id",
            "platform",
            unique=True,
            postgresql_where=sa_text("deleted = false"),
        ),
        Index("ix_llm_responses_job_created", "sampling_job_id", "created_at"),
        Index("ix_llm_responses_job_status", "sampling_job_id", "status"),
        Index("ix_llm_responses_job_status_created", "sampling_job_id", "status", "created_at"),
        Index("ix_llm_responses_prompt_status_created", "prompt_id", "status", "created_at"),
        Index("ix_llm_responses_created_at", "created_at"),
    )


class LLMResponseSignal(Base):
    """Per-response, per-entity analytical signals (flat fact table for KPI aggregation)."""

    __tablename__ = "tb_llm_response_signals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    response_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_llm_responses.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False
    )
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subject_prompts.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    entity_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="", server_default="")
    brand_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_brands.id", ondelete="RESTRICT"), nullable=False
    )
    entity_label: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    primary_domain: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    mentioned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    mention_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    sentiment_reason: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    has_domain_link: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # Source page body mentions the entity (used by citation_coverage / opportunities, not citation_rate KPI).
    cited_on_source: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    llm_response: Mapped[LLMResponse] = relationship(back_populates="llm_response_signals")
    subject: Mapped["Subject"] = relationship()
    prompt: Mapped["Prompt"] = relationship()
    brand: Mapped["Brand"] = relationship(back_populates="llm_response_signals")

    __table_args__ = (
        Index(
            "uq_llm_response_signal",
            "response_id",
            "entity_id",
            unique=True,
            postgresql_where=sa_text("deleted = false"),
        ),
        Index("ix_llm_response_signals_subject_entity_created", "subject_id", "entity_id", "created_at"),
        Index("ix_llm_response_signals_subject_prompt_entity", "subject_id", "prompt_id", "entity_id"),
        Index("ix_llm_response_signals_subject_kind_created", "subject_id", "entity_kind", "created_at"),
        Index("ix_llm_response_signals_subject_kind_cited", "subject_id", "entity_kind", "cited_on_source"),
        Index("ix_llm_response_signals_response_id", "response_id"),
        Index("ix_llm_response_signals_brand_id", "brand_id"),
    )


class CitationDomain(Base):
    """单次采样回答中的引用域名及出现次数（用于域名维度统计）。"""

    __tablename__ = "tb_citation_domains"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    response_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_llm_responses.id", ondelete="CASCADE"), nullable=False
    )
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subject_prompts.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    cite_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    llm_response: Mapped[LLMResponse] = relationship(
        back_populates="citation_domains",
        foreign_keys="CitationDomain.response_id",
    )
    prompt: Mapped[Prompt] = relationship(back_populates="citation_domains")

    __table_args__ = (
        Index(
            "uq_citation_domain",
            "response_id",
            "domain",
            unique=True,
            postgresql_where=sa_text("deleted = false"),
        ),
        Index("ix_citation_domains_prompt_id", "prompt_id"),
        Index("ix_citation_domains_domain", "domain"),
        Index("ix_citation_domains_domain_response", "domain", "response_id"),
        Index("ix_citation_domains_domain_prompt", "domain", "prompt_id"),
        Index("ix_citation_domains_response_id", "response_id"),
    )


class CitationUrl(Base):
    """单次采样回答中的引用 URL 明细。"""

    __tablename__ = "tb_citation_urls"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    response_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_llm_responses.id", ondelete="CASCADE"), nullable=False
    )
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subject_prompts.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    page_title: Mapped[str] = mapped_column(String(500), nullable=False, default="", server_default="")
    http_status: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    headings: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    has_table: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    has_code_block: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    text_snippet: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    llm_analysis: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=sa_text("'{}'::jsonb")
    )
    fetch_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    from_api: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    llm_response: Mapped[LLMResponse] = relationship(
        back_populates="citation_urls",
        foreign_keys="CitationUrl.response_id",
    )
    prompt: Mapped[Prompt] = relationship(back_populates="citation_urls")

    __table_args__ = (
        Index(
            "uq_citation_url",
            "response_id",
            "url",
            unique=True,
            postgresql_where=sa_text("deleted = false"),
        ),
        Index("ix_citation_urls_prompt_id", "prompt_id"),
        Index("ix_citation_urls_response_id", "response_id"),
        Index("ix_citation_urls_url_response", "url", "response_id"),
    )


class Plan(Base):
    __tablename__ = "tb_plans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    max_subjects: Mapped[int] = mapped_column(Integer, nullable=False)
    max_per_platforms: Mapped[int] = mapped_column(Integer, nullable=False)
    max_per_competitors: Mapped[int] = mapped_column(Integer, nullable=False)
    max_prompts_total: Mapped[int] = mapped_column(Integer, nullable=False)
    per_month_usages: Mapped[int] = mapped_column(Integer, nullable=False)
    max_team_members: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    sampling_frequency: Mapped[str] = mapped_column(String(32), nullable=False, default="daily_1", server_default="daily_1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    prices: Mapped[list["PlanPrice"]] = relationship(back_populates="plan", cascade="all, delete-orphan")
    subscriptions: Mapped[list["TenantSubscription"]] = relationship(back_populates="plan")

    __table_args__ = (
        Index("uq_plans_code", "code", unique=True, postgresql_where=sa_text("deleted = false")),
    )


class PlanPrice(Base):
    __tablename__ = "tb_plan_prices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_plans.id", ondelete="CASCADE"), nullable=False
    )
    billing_cycle: Mapped[str] = mapped_column(String(16), nullable=False)
    monthly_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    period_total_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    discount_label: Mapped[str] = mapped_column(String(16), nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    plan: Mapped[Plan] = relationship(back_populates="prices")

    __table_args__ = (
        Index(
            "uq_plan_prices_plan_cycle",
            "plan_id",
            "billing_cycle",
            unique=True,
            postgresql_where=sa_text("deleted = false"),
        ),
    )


class PlanPack(Base):
    __tablename__ = "tb_plan_packs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    __table_args__ = (
        Index("uq_plan_packs_code", "code", unique=True, postgresql_where=sa_text("deleted = false")),
    )


class TenantSubscription(Base):
    __tablename__ = "tb_tenant_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tb_plans.id"), nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pending_plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, default=ZERO_UUID, server_default=sa_text("'00000000-0000-0000-0000-000000000000'::uuid")
    )
    canceled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=EPOCH, server_default=sa_text("'1970-01-01T00:00:00+00:00'::timestamptz")
    )
    pay_channel: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    tenant: Mapped[Tenant] = relationship(back_populates="subscription")
    plan: Mapped[Plan] = relationship(back_populates="subscriptions")
    usage_periods: Mapped[list["TenantUsagePeriod"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_tenant_subscriptions_tenant_id", "tenant_id"),
        Index(
            "uq_tenant_subscriptions_tenant",
            "tenant_id",
            unique=True,
            postgresql_where=sa_text("deleted = false"),
        ),
    )


class TenantUsagePeriod(Base):
    __tablename__ = "tb_tenant_usage_periods"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenant_subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    monthly_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    tenant: Mapped[Tenant] = relationship(back_populates="usage_periods")
    subscription: Mapped[TenantSubscription] = relationship(back_populates="usage_periods")

    __table_args__ = (
        Index(
            "uq_tenant_usage_periods_tenant_start",
            "tenant_id",
            "period_start",
            unique=True,
            postgresql_where=sa_text("deleted = false"),
        ),
        Index("ix_tenant_usage_periods_period_end", "period_end"),
    )


class TenantPlanOverride(Base):
    __tablename__ = "tb_tenant_plan_overrides"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    max_subjects: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_per_platforms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_per_competitors: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_prompts_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    per_month_usages: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_team_members: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    sampling_frequency: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default="")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    tenant: Mapped[Tenant] = relationship(back_populates="plan_override")

    __table_args__ = (
        Index(
            "uq_tenant_plan_overrides_tenant",
            "tenant_id",
            unique=True,
            postgresql_where=sa_text("deleted = false"),
        ),
    )


class TenantPayOrder(Base):
    __tablename__ = "tb_tenant_pay_orders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, default=ZERO_UUID, server_default=sa_text("'00000000-0000-0000-0000-000000000000'::uuid")
    )
    order_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=EPOCH, server_default=sa_text("'1970-01-01T00:00:00+00:00'::timestamptz")
    )
    payment_id: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, default=ZERO_UUID, server_default=sa_text("'00000000-0000-0000-0000-000000000000'::uuid")
    )
    billing_cycle: Mapped[str] = mapped_column(String(16), nullable=False, default="", server_default="")
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=EPOCH, server_default=sa_text("'1970-01-01T00:00:00+00:00'::timestamptz")
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=EPOCH, server_default=sa_text("'1970-01-01T00:00:00+00:00'::timestamptz")
    )
    product_code: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default="")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    tenant: Mapped[Tenant] = relationship(back_populates="pay_orders")

    __table_args__ = (
        Index("ix_tenant_pay_orders_tenant_created", "tenant_id", sa_text("created_at DESC")),
        Index("ix_tenant_pay_orders_status", "status"),
    )


class TenantQuotaLedger(Base):
    __tablename__ = "tb_tenant_quota_ledger"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, default=ZERO_UUID, server_default=sa_text("'00000000-0000-0000-0000-000000000000'::uuid")
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, default=ZERO_UUID, server_default=sa_text("'00000000-0000-0000-0000-000000000000'::uuid")
    )
    consumed_from: Mapped[str] = mapped_column(String(16), nullable=False, default="", server_default="")
    record_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    platform: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    tenant: Mapped[Tenant] = relationship(back_populates="quota_ledger")

    __table_args__ = (
        Index("ix_tenant_quota_ledger_tenant_created", "tenant_id", sa_text("created_at DESC")),
        Index(
            "uq_tenant_quota_ledger_dedup",
            "tenant_id",
            "record_type",
            "reference_id",
            "source",
            unique=True,
            postgresql_where=sa_text(
                "reference_id <> '00000000-0000-0000-0000-000000000000'::uuid AND deleted = false"
            ),
        ),
    )


class UserNotification(Base):
    __tablename__ = "tb_user_notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_users.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    action_url: Mapped[str] = mapped_column(String(512), nullable=False, default="", server_default="")
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=EPOCH, server_default=sa_text("'1970-01-01T00:00:00+00:00'::timestamptz")
    )
    dedupe_key: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    user: Mapped[User] = relationship(back_populates="notifications")

    __table_args__ = (
        Index("ix_user_notifications_user_created", "user_id", sa_text("created_at DESC")),
        Index(
            "ix_user_notifications_user_unread",
            "user_id",
            "read_at",
            postgresql_where=sa_text("read_at = '1970-01-01T00:00:00+00:00'::timestamptz AND deleted = false"),
        ),
        Index(
            "uq_user_notifications_dedupe",
            "user_id",
            "dedupe_key",
            unique=True,
            postgresql_where=sa_text("dedupe_key <> '' AND deleted = false"),
        ),
    )


class SubjectKnowledge(Base):
    """Structured brand knowledge (1:1 subject). See docs/08-品牌模式.md §2.6.2."""

    __tablename__ = "tb_subject_knowledge"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", server_default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    index_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", server_default="pending")
    indexed_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    index_error: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    identity_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa_text("'{}'::jsonb"))
    facts_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa_text("'{}'::jsonb"))
    relations_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa_text("'{}'::jsonb"))
    narrative_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa_text("'{}'::jsonb"))
    voice_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa_text("'{}'::jsonb"))
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=EPOCH, server_default=sa_text("'1970-01-01T00:00:00+00:00'::timestamptz")
    )
    verified_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, default=ZERO_UUID, server_default=sa_text("'00000000-0000-0000-0000-000000000000'::uuid")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    subject: Mapped[Subject] = relationship(back_populates="knowledge")

    __table_args__ = (
        Index(
            "uq_subject_knowledge_subject",
            "subject_id",
            unique=True,
            postgresql_where=sa_text("deleted = false"),
        ),
        Index("ix_subject_knowledge_tenant", "tenant_id"),
        Index(
            "ix_subject_knowledge_status",
            "subject_id",
            "status",
            postgresql_where=sa_text("deleted = false"),
        ),
    )


class KnowledgeSource(Base):
    """Evidence source for RAG indexing. See docs/08-品牌模式.md §2.6.3."""

    __tablename__ = "tb_knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default="")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    uri: Mapped[str] = mapped_column(String(2048), nullable=False, default="", server_default="")
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, default="", server_default="")
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    parse_status: Mapped[str] = mapped_column(String(16), nullable=False, default="ok", server_default="ok")
    parse_error: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa_text("'{}'::jsonb"))
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    subject: Mapped[Subject] = relationship(back_populates="knowledge_sources")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "ix_knowledge_sources_subject",
            "subject_id",
            "kind",
            postgresql_where=sa_text("deleted = false"),
        ),
        Index("ix_knowledge_sources_tenant", "tenant_id"),
    )


class KnowledgeChunk(Base):
    """Vector-indexed chunk; multiple knowledge_version rows retained for audit. See docs/08-品牌模式.md §2.6.4."""

    __tablename__ = "tb_knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_knowledge_sources.id", ondelete="CASCADE"), nullable=False
    )
    knowledge_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    content_text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    char_start: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    char_end: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    embedding: Mapped[Any] = mapped_column(Vector(1024), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa_text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    subject: Mapped[Subject] = relationship(back_populates="knowledge_chunks")
    source: Mapped[KnowledgeSource] = relationship(back_populates="chunks")

    __table_args__ = (
        Index(
            "uq_knowledge_chunks_source_idx_ver",
            "source_id",
            "knowledge_version",
            "chunk_index",
            unique=True,
            postgresql_where=sa_text("deleted = false"),
        ),
        Index(
            "ix_knowledge_chunks_subject_ver",
            "subject_id",
            "knowledge_version",
            postgresql_where=sa_text("deleted = false"),
        ),
        Index(
            "ix_knowledge_chunks_hash",
            "subject_id",
            "content_hash",
            "knowledge_version",
            postgresql_where=sa_text("deleted = false"),
        ),
    )
