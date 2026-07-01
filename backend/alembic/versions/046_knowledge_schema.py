"""Knowledge schema: subject_knowledge, knowledge_sources, knowledge_chunks (pgvector)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "046_knowledge_schema"
down_revision: Union[str, None] = "045_plan_team_seats"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TS = sa.DateTime(timezone=True)
_NOW = sa.text("now()")
_EPOCH = sa.text("'1970-01-01T00:00:00+00:00'::timestamptz")
_ZERO_UUID = sa.text("'00000000-0000-0000-0000-000000000000'::uuid")
_JSONB_EMPTY = sa.text("'{}'::jsonb")

_STD_COLS = (
    sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
    sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
)

_EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "tb_subject_knowledge",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subject_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("index_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("indexed_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("index_error", sa.Text(), nullable=False, server_default=""),
        sa.Column("identity_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=_JSONB_EMPTY),
        sa.Column("facts_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=_JSONB_EMPTY),
        sa.Column("relations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=_JSONB_EMPTY),
        sa.Column("narrative_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=_JSONB_EMPTY),
        sa.Column("voice_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=_JSONB_EMPTY),
        sa.Column("verified_at", _TS, nullable=False, server_default=_EPOCH),
        sa.Column("verified_by_user_id", sa.Uuid(as_uuid=True), nullable=False, server_default=_ZERO_UUID),
        *_STD_COLS,
    )
    op.create_index(
        "uq_subject_knowledge_subject",
        "tb_subject_knowledge",
        ["subject_id"],
        unique=True,
        postgresql_where=sa.text("deleted = false"),
    )
    op.create_index("ix_subject_knowledge_tenant", "tb_subject_knowledge", ["tenant_id"])
    op.create_index(
        "ix_subject_knowledge_status",
        "tb_subject_knowledge",
        ["subject_id", "status"],
        postgresql_where=sa.text("deleted = false"),
    )

    op.create_table(
        "tb_knowledge_sources",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subject_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False, server_default=""),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("uri", sa.String(2048), nullable=False, server_default=""),
        sa.Column("mime_type", sa.String(128), nullable=False, server_default=""),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_key", sa.String(512), nullable=False, server_default=""),
        sa.Column("raw_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parse_status", sa.String(16), nullable=False, server_default="ok"),
        sa.Column("parse_error", sa.Text(), nullable=False, server_default=""),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=_JSONB_EMPTY),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        *_STD_COLS,
    )
    op.create_index(
        "ix_knowledge_sources_subject",
        "tb_knowledge_sources",
        ["subject_id", "kind"],
        postgresql_where=sa.text("deleted = false"),
    )
    op.create_index("ix_knowledge_sources_tenant", "tb_knowledge_sources", ["tenant_id"])

    op.create_table(
        "tb_knowledge_chunks",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subject_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_knowledge_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("knowledge_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("content_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("char_start", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("char_end", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding", Vector(_EMBEDDING_DIM), nullable=False),
        sa.Column("embedding_model", sa.String(64), nullable=False, server_default=""),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=_JSONB_EMPTY),
        *_STD_COLS,
    )
    op.create_index(
        "uq_knowledge_chunks_source_idx_ver",
        "tb_knowledge_chunks",
        ["source_id", "knowledge_version", "chunk_index"],
        unique=True,
        postgresql_where=sa.text("deleted = false"),
    )
    op.create_index(
        "ix_knowledge_chunks_subject_ver",
        "tb_knowledge_chunks",
        ["subject_id", "knowledge_version"],
        postgresql_where=sa.text("deleted = false"),
    )
    op.create_index(
        "ix_knowledge_chunks_hash",
        "tb_knowledge_chunks",
        ["subject_id", "content_hash", "knowledge_version"],
        postgresql_where=sa.text("deleted = false"),
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX ix_knowledge_chunks_embedding_hnsw
            ON tb_knowledge_chunks
            USING hnsw (embedding vector_cosine_ops)
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw"))
    op.drop_index("ix_knowledge_chunks_hash", table_name="tb_knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_subject_ver", table_name="tb_knowledge_chunks")
    op.drop_index("uq_knowledge_chunks_source_idx_ver", table_name="tb_knowledge_chunks")
    op.drop_table("tb_knowledge_chunks")

    op.drop_index("ix_knowledge_sources_tenant", table_name="tb_knowledge_sources")
    op.drop_index("ix_knowledge_sources_subject", table_name="tb_knowledge_sources")
    op.drop_table("tb_knowledge_sources")

    op.drop_index("ix_subject_knowledge_status", table_name="tb_subject_knowledge")
    op.drop_index("ix_subject_knowledge_tenant", table_name="tb_subject_knowledge")
    op.drop_index("uq_subject_knowledge_subject", table_name="tb_subject_knowledge")
    op.drop_table("tb_subject_knowledge")
