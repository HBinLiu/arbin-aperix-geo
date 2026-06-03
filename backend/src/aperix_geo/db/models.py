"""ORM models."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
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


def utc_now() -> datetime:
    return datetime.now(UTC)


_NOW = text("now()")


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
            postgresql_where=text("phone <> ''"),
        ),
        Index(
            "uq_users_tenant_email_nn",
            "tenant_id",
            "email",
            unique=True,
            postgresql_where=text("email <> ''"),
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
    aliases: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    website_url: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    monitoring_scope: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    profile_summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    sampling_platforms: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
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
    competitor_domains: Mapped[list["CompetitorDomain"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )
    competitor_brands: Mapped[list["CompetitorBrand"]] = relationship(
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


class CompetitorDomain(Base):
    __tablename__ = "tb_competitor_domains"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    website_url: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    site_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    subject: Mapped[Subject] = relationship(back_populates="competitor_domains")

    __table_args__ = (
        UniqueConstraint("subject_id", "domain", name="uq_competitor_domain"),
        Index("ix_competitor_domains_subject_id", "subject_id"),
    )


class CompetitorBrand(Base):
    __tablename__ = "tb_competitor_brands"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    subject: Mapped[Subject] = relationship(back_populates="competitor_brands")

    __table_args__ = (
        UniqueConstraint("subject_id", "name", name="uq_competitor_brand"),
        Index("ix_competitor_brands_subject_id", "subject_id"),
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
        server_default=text("'queued'::sampling_job_status"),
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
        server_default=text("'pending'::llm_response_status"),
    )
    error_text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    parsed: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    usage: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, server_default=_NOW)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=_NOW
    )

    sampling_job: Mapped[SamplingJob] = relationship(back_populates="llm_responses")
    prompt: Mapped[Prompt] = relationship(back_populates="responses")

    __table_args__ = (
        UniqueConstraint("sampling_job_id", "prompt_id", "platform", name="uq_job_prompt_platform"),
        Index("ix_llm_responses_job_created", "sampling_job_id", "created_at"),
        Index("ix_llm_responses_created_at", "created_at"),
    )
