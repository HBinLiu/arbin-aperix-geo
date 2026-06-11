"""Initial schema for Aperix AI MVP."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TS = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    subject_type = postgresql.ENUM("domain", "brand", name="subject_type", create_type=True)
    subject_type.create(op.get_bind(), checkfirst=True)
    job_status = postgresql.ENUM(
        "queued", "running", "succeed", "failed", "partial",
        name="sampling_job_status",
        create_type=True,
    )
    job_status.create(op.get_bind(), checkfirst=True)
    resp_status = postgresql.ENUM("pending", "success", "failed", name="llm_response_status", create_type=True)
    resp_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tb_tenants",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    )
    op.create_table(
        "tb_users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False, server_default=""),
        sa.Column("email", sa.String(320), nullable=False, server_default=""),
        sa.Column("password", sa.String(255), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    )
    op.create_index(
        "uq_users_phone",
        "tb_users",
        ["phone"],
        unique=True,
        postgresql_where=sa.text("phone <> ''"),
    )
    op.create_index(
        "uq_users_tenant_email_nn",
        "tb_users",
        ["tenant_id", "email"],
        unique=True,
        postgresql_where=sa.text("email <> ''"),
    )
    op.execute(
        sa.text(
            "ALTER TABLE tb_users ADD CONSTRAINT ck_tb_users_email_or_phone "
            "CHECK (email <> '' OR phone <> '')"
        )
    )
    op.create_table(
        "tb_brands",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False, server_default=""),
        sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("website_url", sa.String(255), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    )
    op.create_index("ix_brands_tenant_id", "tb_brands", ["tenant_id"])
    op.create_index("ix_brands_tenant_brand", "tb_brands", ["tenant_id", "brand"])
    op.create_index(
        "uq_brands_tenant_domain",
        "tb_brands",
        ["tenant_id", "domain"],
        unique=True,
        postgresql_where=sa.text("domain <> ''"),
    )
    op.create_index(
        "uq_brands_tenant_brand_no_domain",
        "tb_brands",
        ["tenant_id", "brand"],
        unique=True,
        postgresql_where=sa.text("domain = ''"),
    )
    op.create_table(
        "tb_subjects",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM("domain", "brand", name="subject_type", create_type=False),
            nullable=False,
            server_default=sa.text("'domain'::subject_type"),
        ),
        sa.Column("domain", sa.String(255), nullable=False, server_default=""),
        sa.Column("brand", sa.String(255), nullable=False, server_default=""),
        sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("website_url", sa.String(255), nullable=False, server_default=""),
        sa.Column("monitoring_scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("profile_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "sampling_platforms",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("sampling_interval", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("last_sampled_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    )
    op.execute(
        sa.text(
            "ALTER TABLE tb_subjects ADD CONSTRAINT ck_tb_subjects_sampling_interval "
            "CHECK (sampling_interval IN (0, 6, 12, 24, 72, 168))"
        )
    )
    op.create_index("ix_subjects_tenant_id", "tb_subjects", ["tenant_id"])
    op.create_table(
        "tb_competitors",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("subject_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False, server_default=""),
        sa.Column("brand", sa.String(255), nullable=False, server_default=""),
        sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("website_url", sa.String(255), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    )
    op.create_index("ix_competitors_subject_id", "tb_competitors", ["subject_id"])
    op.create_index(
        "uq_competitors_subject_domain",
        "tb_competitors",
        ["subject_id", "domain"],
        unique=True,
        postgresql_where=sa.text("domain <> ''"),
    )
    op.create_index(
        "uq_competitors_subject_brand_no_domain",
        "tb_competitors",
        ["subject_id", "brand"],
        unique=True,
        postgresql_where=sa.text("domain = ''"),
    )
    op.create_table(
        "tb_topics",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("subject_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    )
    op.create_index("ix_topics_subject_id", "tb_topics", ["subject_id"])
    op.create_table(
        "tb_prompts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("subject_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("text_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("funnel_stage", sa.String(8), nullable=False, server_default="mofu"),
        sa.Column("search_intent", sa.String(16), nullable=False, server_default="commercial"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
        sa.UniqueConstraint("subject_id", "text_hash", name="uq_subject_prompt_hash"),
    )
    op.create_index("ix_prompts_subject_id", "tb_prompts", ["subject_id"])
    op.create_index("ix_prompts_topic_id", "tb_prompts", ["topic_id"])
    op.create_table(
        "tb_sampling_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "queued",
                "running",
                "succeed",
                "failed",
                "partial",
                name="sampling_job_status",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'queued'::sampling_job_status"),
        ),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("finished_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    )
    op.create_index("ix_sampling_jobs_tenant_id", "tb_sampling_jobs", ["tenant_id"])
    op.create_index(
        "ix_sampling_jobs_subject_created",
        "tb_sampling_jobs",
        ["subject_id", "created_at"],
    )
    op.create_table(
        "tb_llm_responses",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("sampling_job_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_sampling_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_prompts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(128), nullable=False, server_default=""),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "success", "failed", name="llm_response_status", create_type=False),
            nullable=False,
            server_default=sa.text("'pending'::llm_response_status"),
        ),
        sa.Column("error_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("raw_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("parsed", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usage", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
        sa.UniqueConstraint("sampling_job_id", "prompt_id", "platform", name="uq_job_prompt_platform"),
    )
    op.create_index(
        "ix_llm_responses_job_created",
        "tb_llm_responses",
        ["sampling_job_id", "created_at"],
    )
    op.create_index("ix_llm_responses_created_at", "tb_llm_responses", ["created_at"])
    op.create_table(
        "tb_citation_domains",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "response_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_llm_responses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prompt_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_prompts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("domain", sa.String(255), nullable=False, server_default=""),
        sa.Column("cite_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("domain_type", sa.String(128), nullable=False, server_default=""),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
        sa.UniqueConstraint("response_id", "domain", name="uq_citation_domain"),
    )
    op.create_index("ix_citation_domains_prompt_id", "tb_citation_domains", ["prompt_id"])
    op.create_index("ix_citation_domains_domain", "tb_citation_domains", ["domain"])
    op.create_index("ix_citation_domains_response_id", "tb_citation_domains", ["response_id"])
    op.create_table(
        "tb_citation_urls",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "response_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_llm_responses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prompt_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_prompts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False, server_default=""),
        sa.Column("page_title", sa.String(500), nullable=False, server_default=""),
        sa.Column("domain_type", sa.String(128), nullable=False, server_default=""),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("headings", sa.Text(), nullable=False, server_default=""),
        sa.Column("has_table", sa.Boolean(), nullable=True),
        sa.Column("has_code_block", sa.Boolean(), nullable=True),
        sa.Column("text_snippet", sa.Text(), nullable=False, server_default=""),
        sa.Column("llm_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("fetch_ok", sa.Boolean(), nullable=True),
        sa.Column("from_api", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("url_type", sa.String(128), nullable=False, server_default=""),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
        sa.UniqueConstraint("response_id", "url", name="uq_citation_url"),
    )
    op.create_index("ix_citation_urls_prompt_id", "tb_citation_urls", ["prompt_id"])
    op.create_index("ix_citation_urls_response_id", "tb_citation_urls", ["response_id"])
    op.create_table(
        "tb_llm_response_signals",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "response_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_llm_responses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subject_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prompt_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_prompts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(128), nullable=False, server_default=""),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("entity_kind", sa.String(16), nullable=False),
        sa.Column(
            "brand_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_brands.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("entity_label", sa.String(255), nullable=False, server_default=""),
        sa.Column("primary_domain", sa.String(255), nullable=False, server_default=""),
        sa.Column("mentioned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mention_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mention_rank", sa.Integer(), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("sentiment_label", sa.String(16), nullable=False, server_default="neutral"),
        sa.Column("has_domain_link", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("cited_on_source", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
        sa.UniqueConstraint("response_id", "entity_id", name="uq_llm_response_signal"),
    )
    op.create_index(
        "ix_llm_response_signals_subject_entity_created",
        "tb_llm_response_signals",
        ["subject_id", "entity_id", "created_at"],
    )
    op.create_index(
        "ix_llm_response_signals_subject_prompt_entity",
        "tb_llm_response_signals",
        ["subject_id", "prompt_id", "entity_id"],
    )
    op.create_index("ix_llm_response_signals_response_id", "tb_llm_response_signals", ["response_id"])
    op.create_index("ix_llm_response_signals_brand_id", "tb_llm_response_signals", ["brand_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_response_signals_brand_id", table_name="tb_llm_response_signals")
    op.drop_index("ix_llm_response_signals_response_id", table_name="tb_llm_response_signals")
    op.drop_index("ix_llm_response_signals_subject_prompt_entity", table_name="tb_llm_response_signals")
    op.drop_index("ix_llm_response_signals_subject_entity_created", table_name="tb_llm_response_signals")
    op.drop_table("tb_llm_response_signals")
    op.drop_index("ix_citation_urls_response_id", table_name="tb_citation_urls")
    op.drop_index("ix_citation_urls_prompt_id", table_name="tb_citation_urls")
    op.drop_table("tb_citation_urls")
    op.drop_index("ix_citation_domains_response_id", table_name="tb_citation_domains")
    op.drop_index("ix_citation_domains_domain", table_name="tb_citation_domains")
    op.drop_index("ix_citation_domains_prompt_id", table_name="tb_citation_domains")
    op.drop_table("tb_citation_domains")
    op.drop_index("ix_llm_responses_created_at", table_name="tb_llm_responses")
    op.drop_index("ix_llm_responses_job_created", table_name="tb_llm_responses")
    op.drop_table("tb_llm_responses")
    op.drop_index("ix_sampling_jobs_subject_created", table_name="tb_sampling_jobs")
    op.drop_index("ix_sampling_jobs_tenant_id", table_name="tb_sampling_jobs")
    op.drop_table("tb_sampling_jobs")
    op.drop_index("ix_prompts_topic_id", table_name="tb_prompts")
    op.drop_index("ix_prompts_subject_id", table_name="tb_prompts")
    op.drop_table("tb_prompts")
    op.drop_index("ix_topics_subject_id", table_name="tb_topics")
    op.drop_table("tb_topics")
    op.drop_index("uq_competitors_subject_brand_no_domain", table_name="tb_competitors")
    op.drop_index("uq_competitors_subject_domain", table_name="tb_competitors")
    op.drop_index("ix_competitors_subject_id", table_name="tb_competitors")
    op.drop_table("tb_competitors")
    op.execute(sa.text("ALTER TABLE tb_subjects DROP CONSTRAINT IF EXISTS ck_tb_subjects_sampling_interval"))
    op.drop_index("ix_subjects_tenant_id", table_name="tb_subjects")
    op.drop_table("tb_subjects")
    op.drop_index("uq_brands_tenant_brand_no_domain", table_name="tb_brands")
    op.drop_index("uq_brands_tenant_domain", table_name="tb_brands")
    op.drop_index("ix_brands_tenant_brand", table_name="tb_brands")
    op.drop_index("ix_brands_tenant_id", table_name="tb_brands")
    op.drop_table("tb_brands")
    op.execute(sa.text("ALTER TABLE tb_users DROP CONSTRAINT IF EXISTS ck_tb_users_email_or_phone"))
    op.drop_index("uq_users_tenant_email_nn", table_name="tb_users")
    op.drop_index("uq_users_phone", table_name="tb_users")
    op.drop_table("tb_users")
    op.drop_table("tb_tenants")
    op.execute(sa.text("DROP TYPE IF EXISTS llm_response_status"))
    op.execute(sa.text("DROP TYPE IF EXISTS sampling_job_status"))
    op.execute(sa.text("DROP TYPE IF EXISTS subject_type"))
