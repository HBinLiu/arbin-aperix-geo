"""ORM models."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy import text as sa_text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from aperix_geo.db.base import Base


class SubjectType(str, enum.Enum):
    domain = "domain"
    brand = "brand"


class SamplingJobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeed = "succeed"
    failed = "failed"
    partial = "partial"


class LLMResponseStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class EntityKind(str, enum.Enum):
    own = "own"
    competitor = "competitor"
    other = "other"


def utc_now() -> datetime:
    return datetime.now(UTC)


_NOW = sa_text("now()")


class Tenant(Base):
    __tablename__ = "tb_tenants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    users: Mapped[list["User"]] = relationship(back_populates="tenant")
    subjects: Mapped[list["Subject"]] = relationship(back_populates="tenant")
    brands: Mapped[list["Brand"]] = relationship(back_populates="tenant")


class Brand(Base):
    """Tenant-scoped canonical brand registry (shared across subjects)."""

    __tablename__ = "tb_brands"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    brand: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    website_url: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    aliases: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=sa_text("'[]'::jsonb"))
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    tenant: Mapped[Tenant] = relationship(back_populates="brands")
    llm_response_signals: Mapped[list["LLMResponseSignal"]] = relationship(back_populates="brand")

    __table_args__ = (
        Index("ix_brands_tenant_id", "tenant_id"),
        Index("ix_brands_tenant_brand", "tenant_id", "brand"),
        Index(
            "uq_brands_tenant_domain",
            "tenant_id",
            "domain",
            unique=True,
            postgresql_where=sa_text("domain <> ''"),
        ),
        Index(
            "uq_brands_tenant_brand_no_domain",
            "tenant_id",
            "brand",
            unique=True,
            postgresql_where=sa_text("domain = ''"),
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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    tenant: Mapped[Tenant] = relationship(back_populates="users")

    __table_args__ = (
        CheckConstraint("email <> '' OR phone <> ''", name="ck_tb_users_email_or_phone"),
        Index(
            "uq_users_phone",
            "phone",
            unique=True,
            postgresql_where=sa_text("phone <> ''"),
        ),
        Index(
            "uq_users_tenant_email_nn",
            "tenant_id",
            "email",
            unique=True,
            postgresql_where=sa_text("email <> ''"),
        ),
    )


class Subject(Base):
    __tablename__ = "tb_subjects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[SubjectType] = mapped_column(SAEnum(SubjectType, name="subject_type"), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    brand: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    aliases: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=sa_text("'[]'::jsonb"))
    website_url: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    monitoring_scope: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=sa_text("'{}'::jsonb")
    )
    profile_summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    sampling_platforms: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa_text("'[]'::jsonb")
    )
    sampling_interval: Mapped[int] = mapped_column(Integer, nullable=False, server_default="24")
    last_sampled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=_NOW
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

    __table_args__ = (
        CheckConstraint(
            "sampling_interval IN (0, 6, 12, 24, 72, 168)",
            name="ck_tb_subjects_sampling_interval",
        ),
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    subject: Mapped[Subject] = relationship(back_populates="competitors")

    __table_args__ = (
        Index("ix_competitors_subject_id", "subject_id"),
        Index(
            "uq_competitors_subject_domain",
            "subject_id",
            "domain",
            unique=True,
            postgresql_where=sa_text("domain <> ''"),
        ),
        Index(
            "uq_competitors_subject_brand_no_domain",
            "subject_id",
            "brand",
            unique=True,
            postgresql_where=sa_text("domain = ''"),
        ),
    )


class Topic(Base):
    __tablename__ = "tb_topics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    subject: Mapped[Subject] = relationship(back_populates="topics")
    prompts: Mapped[list["Prompt"]] = relationship(back_populates="topic", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_topics_subject_id", "subject_id"),)


class Prompt(Base):
    __tablename__ = "tb_prompts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_topics.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
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
        UniqueConstraint("subject_id", "text_hash", name="uq_subject_prompt_hash"),
        Index("ix_prompts_subject_id", "subject_id"),
        Index("ix_prompts_topic_id", "topic_id"),
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


class LLMResponse(Base):
    __tablename__ = "tb_llm_responses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sampling_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_sampling_jobs.id", ondelete="CASCADE"), nullable=False
    )
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_prompts.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(128), nullable=False)
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
        UniqueConstraint("sampling_job_id", "prompt_id", "platform", name="uq_job_prompt_platform"),
        Index("ix_llm_responses_job_created", "sampling_job_id", "created_at"),
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
        Uuid(as_uuid=True), ForeignKey("tb_prompts.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_brands.id", ondelete="SET NULL"), nullable=True
    )
    entity_label: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    primary_domain: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    mentioned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    mention_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(nullable=True)
    sentiment_label: Mapped[str] = mapped_column(String(16), nullable=False, default="neutral", server_default="neutral")
    has_domain_link: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    cited_on_source: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)

    llm_response: Mapped[LLMResponse] = relationship(back_populates="llm_response_signals")
    subject: Mapped["Subject"] = relationship()
    prompt: Mapped["Prompt"] = relationship()
    brand: Mapped["Brand | None"] = relationship(back_populates="llm_response_signals")

    __table_args__ = (
        UniqueConstraint("response_id", "entity_id", name="uq_llm_response_signal"),
        Index("ix_llm_response_signals_subject_entity_created", "subject_id", "entity_id", "created_at"),
        Index("ix_llm_response_signals_subject_prompt_entity", "subject_id", "prompt_id", "entity_id"),
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
        Uuid(as_uuid=True), ForeignKey("tb_prompts.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    cite_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    domain_type: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
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
        UniqueConstraint("response_id", "domain", name="uq_citation_domain"),
        Index("ix_citation_domains_prompt_id", "prompt_id"),
        Index("ix_citation_domains_domain", "domain"),
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
        Uuid(as_uuid=True), ForeignKey("tb_prompts.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    page_title: Mapped[str] = mapped_column(String(500), nullable=False, default="", server_default="")
    domain_type: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    headings: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    has_table: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_code_block: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    text_snippet: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    llm_analysis: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=sa_text("'{}'::jsonb")
    )
    fetch_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    from_api: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    url_type: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
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
        UniqueConstraint("response_id", "url", name="uq_citation_url"),
        Index("ix_citation_urls_prompt_id", "prompt_id"),
        Index("ix_citation_urls_response_id", "response_id"),
    )
