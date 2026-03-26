"""async queue statuses and job ids

Revision ID: 20260325_0005
Revises: 20260325_0004
Create Date: 2026-03-25 00:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260325_0005"
down_revision: Union[str, None] = "20260325_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    dialect_name = context.dialect.name
    is_offline = context.as_sql

    # Normalize statuses before enforcing new constraints.
    op.execute(
        "UPDATE llm_tasks SET status = 'success' "
        "WHERE status NOT IN ('queued','running','success','error')"
    )
    op.execute(
        "UPDATE publications SET status = 'success' "
        "WHERE status NOT IN ('queued','running','scheduled','success','error')"
    )
    op.execute(
        "UPDATE publications SET status = 'success' "
        "WHERE status = 'published'"
    )

    if dialect_name == "sqlite" and not is_offline:
        with op.batch_alter_table("llm_tasks", recreate="always") as batch_op:
            batch_op.add_column(sa.Column("queue_job_id", sa.Text(), nullable=True))
            batch_op.alter_column(
                "status",
                existing_type=sa.Text(),
                server_default=sa.text("'queued'"),
                nullable=False,
            )
            batch_op.create_check_constraint(
                "llm_tasks_status_valid",
                "status IN ('queued','running','success','error')",
            )
            batch_op.create_unique_constraint(
                "uq_llm_tasks_queue_job_id",
                ["queue_job_id"],
            )

        with op.batch_alter_table("publications", recreate="always") as batch_op:
            batch_op.add_column(sa.Column("channel_alias", sa.Text(), nullable=True))
            batch_op.add_column(sa.Column("queue_job_id", sa.Text(), nullable=True))
            batch_op.alter_column(
                "status",
                existing_type=sa.Text(),
                server_default=sa.text("'queued'"),
                nullable=False,
            )
            batch_op.create_check_constraint(
                "publications_status_async_valid",
                "status IN ('queued','running','scheduled','success','error')",
            )
            batch_op.create_unique_constraint(
                "uq_publications_queue_job_id",
                ["queue_job_id"],
            )
    elif dialect_name != "sqlite":
        op.add_column("llm_tasks", sa.Column("queue_job_id", sa.Text(), nullable=True))
        op.alter_column(
            "llm_tasks",
            "status",
            existing_type=sa.Text(),
            server_default=sa.text("'queued'"),
            nullable=False,
        )
        op.create_check_constraint(
            "llm_tasks_status_valid",
            "llm_tasks",
            "status IN ('queued','running','success','error')",
        )
        op.create_unique_constraint("uq_llm_tasks_queue_job_id", "llm_tasks", ["queue_job_id"])

        op.add_column("publications", sa.Column("channel_alias", sa.Text(), nullable=True))
        op.add_column("publications", sa.Column("queue_job_id", sa.Text(), nullable=True))
        op.alter_column(
            "publications",
            "status",
            existing_type=sa.Text(),
            server_default=sa.text("'queued'"),
            nullable=False,
        )
        op.create_check_constraint(
            "publications_status_async_valid",
            "publications",
            "status IN ('queued','running','scheduled','success','error')",
        )
        op.create_unique_constraint("uq_publications_queue_job_id", "publications", ["queue_job_id"])


def downgrade() -> None:
    context = op.get_context()
    dialect_name = context.dialect.name
    is_offline = context.as_sql

    if dialect_name == "sqlite" and not is_offline:
        with op.batch_alter_table("llm_tasks", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_llm_tasks_queue_job_id", type_="unique")
            batch_op.drop_constraint("llm_tasks_status_valid", type_="check")
            batch_op.drop_column("queue_job_id")

        with op.batch_alter_table("publications", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_publications_queue_job_id", type_="unique")
            batch_op.drop_constraint("publications_status_async_valid", type_="check")
            batch_op.drop_column("queue_job_id")
            batch_op.drop_column("channel_alias")
    else:
        op.drop_constraint("uq_llm_tasks_queue_job_id", "llm_tasks", type_="unique")
        op.drop_constraint("llm_tasks_status_valid", "llm_tasks", type_="check")
        op.drop_column("llm_tasks", "queue_job_id")

        op.drop_constraint("uq_publications_queue_job_id", "publications", type_="unique")
        op.drop_constraint("publications_status_async_valid", "publications", type_="check")
        op.drop_column("publications", "queue_job_id")
        op.drop_column("publications", "channel_alias")

    # Restore legacy status labels for backward compatibility.
    op.execute("UPDATE publications SET status = 'published' WHERE status = 'success'")
