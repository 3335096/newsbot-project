"""init schema

Revision ID: 20260325_0001
Revises:
Create Date: 2026-03-25 00:01:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260325_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "moderation_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_moderation_rules")),
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("schedule_cron", sa.Text(), nullable=True),
        sa.Column("translate_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("default_target_language", sa.Text(), server_default=sa.text("'ru'"), nullable=False),
        sa.Column("extraction_rules", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("type IN ('rss','site')", name="source_type_valid"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('admin','editor')", name="user_role_valid"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("telegram_user_id", name=op.f("uq_users_telegram_user_id")),
    )

    op.create_table(
        "articles_raw",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title_raw", sa.Text(), nullable=True),
        sa.Column("content_raw", sa.Text(), nullable=True),
        sa.Column("media", sa.JSON(), nullable=True),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("language_detected", sa.Text(), nullable=True),
        sa.Column("hash_original", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], name=op.f("fk_articles_raw_source_id_sources")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_articles_raw")),
        sa.UniqueConstraint("hash_original", "source_id", name="uq_articles_raw_hash_source"),
        sa.UniqueConstraint("url", name=op.f("uq_articles_raw_url")),
    )

    op.create_table(
        "articles_draft",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_raw_id", sa.Integer(), nullable=True),
        sa.Column("target_language", sa.Text(), server_default=sa.text("'ru'"), nullable=False),
        sa.Column("title_translated", sa.Text(), nullable=True),
        sa.Column("content_translated", sa.Text(), nullable=True),
        sa.Column("translation_engine", sa.Text(), nullable=True),
        sa.Column("translation_preset", sa.Text(), nullable=True),
        sa.Column("translation_quality_score", sa.Numeric(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'new'"), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("flags", sa.JSON(), nullable=True),
        sa.Column("media", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["article_raw_id"],
            ["articles_raw.id"],
            name=op.f("fk_articles_draft_article_raw_id_articles_raw"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_articles_draft")),
    )

    op.create_table(
        "llm_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draft_id", sa.Integer(), nullable=True),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("preset", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["articles_draft.id"],
            name=op.f("fk_llm_tasks_draft_id_articles_draft"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_tasks")),
    )

    op.create_table(
        "publications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draft_id", sa.Integer(), nullable=True),
        sa.Column("channel_id", sa.BigInteger(), nullable=True),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("target_language", sa.Text(), server_default=sa.text("'ru'"), nullable=False),
        sa.Column("log", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["articles_draft.id"],
            name=op.f("fk_publications_draft_id_articles_draft"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_publications")),
    )


def downgrade() -> None:
    op.drop_table("publications")
    op.drop_table("llm_tasks")
    op.drop_table("articles_draft")
    op.drop_table("articles_raw")
    op.drop_table("users")
    op.drop_table("sources")
    op.drop_table("moderation_rules")
