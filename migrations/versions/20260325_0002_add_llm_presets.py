"""add llm presets

Revision ID: 20260325_0002
Revises: 20260325_0001
Create Date: 2026-03-25 00:02:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260325_0002"
down_revision: Union[str, None] = "20260325_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    dialect_name = context.dialect.name
    is_offline = context.as_sql
    op.execute(
        "UPDATE articles_draft SET status = 'flagged' WHERE status NOT IN "
        "('new','flagged','approved','rejected','published')"
    )
    if dialect_name == "sqlite" and not is_offline:
        with op.batch_alter_table("articles_draft", recreate="always") as batch_op:
            batch_op.alter_column(
                "status",
                existing_type=sa.Text(),
                server_default=sa.text("'new'"),
                nullable=False,
            )
            batch_op.create_check_constraint(
                "articles_draft_status_valid",
                "status IN ('new','flagged','approved','rejected','published')",
            )
    elif dialect_name != "sqlite":
        op.alter_column(
            "articles_draft",
            "status",
            existing_type=sa.Text(),
            server_default=sa.text("'new'"),
            nullable=False,
        )
        op.create_check_constraint(
            "articles_draft_status_valid",
            "articles_draft",
            "status IN ('new','flagged','approved','rejected','published')",
        )
    op.create_table(
        "llm_presets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt_template", sa.Text(), nullable=False),
        sa.Column("default_model", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_presets")),
        sa.UniqueConstraint("name", name=op.f("uq_llm_presets_name")),
    )

    op.bulk_insert(
        sa.table(
            "llm_presets",
            sa.column("name", sa.Text),
            sa.column("task_type", sa.Text),
            sa.column("system_prompt", sa.Text),
            sa.column("user_prompt_template", sa.Text),
            sa.column("default_model", sa.Text),
            sa.column("enabled", sa.Boolean),
        ),
        [
            {
                "name": "summary",
                "task_type": "summary",
                "system_prompt": "Ты — редактор новостей. Сделай краткое резюме, выделив главное. Без оценочных суждений.",
                "user_prompt_template": "Сформируй резюме до {{max_len}} символов. Язык: {{target_lang}}.\n\nТекст:\n{{content}}",
                "default_model": "openai/gpt-4o-mini",
                "enabled": True,
            },
            {
                "name": "rewrite_style",
                "task_type": "rewrite",
                "system_prompt": "Ты — копирайтер редакции. Перепиши текст в фирменном стиле канала: лаконично, короткие абзацы, без кликбейта.",
                "user_prompt_template": "Перепиши на {{target_lang}}. Добавь 3–5 хэштегов по теме.\n\nТекст:\n{{content}}",
                "default_model": "openai/gpt-4o-mini",
                "enabled": True,
            },
            {
                "name": "title_hashtags",
                "task_type": "title_hashtags",
                "system_prompt": "Ты — заголовочник. Заголовок информативный, до 80 символов, без кликбейта. Хэштеги: 3–7, релевантные.",
                "user_prompt_template": "Сгенерируй заголовок и список хэштегов на {{target_lang}}.\n\nКонтент:\n{{content}}",
                "default_model": "openai/gpt-4o-mini",
                "enabled": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("llm_presets")
    context = op.get_context()
    dialect_name = context.dialect.name
    is_offline = context.as_sql
    if dialect_name == "sqlite" and not is_offline:
        with op.batch_alter_table("articles_draft", recreate="always") as batch_op:
            batch_op.drop_constraint("articles_draft_status_valid", type_="check")
    else:
        op.drop_constraint(
            "articles_draft_status_valid",
            "articles_draft",
            type_="check",
        )
