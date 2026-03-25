"""publication status and uniqueness

Revision ID: 20260325_0003
Revises: 20260325_0002
Create Date: 2026-03-25 00:03:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260325_0003"
down_revision: Union[str, None] = "20260325_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    dialect_name = context.dialect.name
    is_offline = context.as_sql

    op.execute(
        "UPDATE publications SET status = 'published' WHERE status NOT IN "
        "('queued','scheduled','published','error')"
    )

    if dialect_name == "sqlite" and not is_offline:
        with op.batch_alter_table("publications", recreate="always") as batch_op:
            batch_op.alter_column(
                "status",
                existing_type=sa.Text(),
                server_default=sa.text("'queued'"),
                nullable=False,
            )
            batch_op.create_check_constraint(
                "publications_status_valid",
                "status IN ('queued','scheduled','published','error')",
            )
            batch_op.create_unique_constraint(
                "publications_draft_channel_unique",
                ["draft_id", "channel_id"],
            )
    elif dialect_name != "sqlite":
        op.alter_column(
            "publications",
            "status",
            existing_type=sa.Text(),
            server_default=sa.text("'queued'"),
            nullable=False,
        )
        op.create_check_constraint(
            "publications_status_valid",
            "publications",
            "status IN ('queued','scheduled','published','error')",
        )
        op.create_unique_constraint(
            "publications_draft_channel_unique",
            "publications",
            ["draft_id", "channel_id"],
        )


def downgrade() -> None:
    context = op.get_context()
    dialect_name = context.dialect.name
    is_offline = context.as_sql

    if dialect_name == "sqlite" and not is_offline:
        with op.batch_alter_table("publications", recreate="always") as batch_op:
            batch_op.drop_constraint("publications_draft_channel_unique", type_="unique")
            batch_op.drop_constraint("publications_status_valid", type_="check")
    else:
        op.drop_constraint("publications_draft_channel_unique", "publications", type_="unique")
        op.drop_constraint("publications_status_valid", "publications", type_="check")
