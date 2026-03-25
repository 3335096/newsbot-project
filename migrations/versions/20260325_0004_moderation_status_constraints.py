"""moderation status constraints

Revision ID: 20260325_0004
Revises: 20260325_0003
Create Date: 2026-03-25 00:04:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260325_0004"
down_revision: Union[str, None] = "20260325_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    dialect_name = context.dialect.name
    is_offline = context.as_sql

    op.execute(
        "UPDATE moderation_rules SET kind = 'keyword_blacklist' "
        "WHERE kind NOT IN ('domain_blacklist','keyword_blacklist')"
    )
    op.execute(
        "UPDATE moderation_rules SET action = 'flag' "
        "WHERE action NOT IN ('block','flag')"
    )

    if dialect_name == "sqlite" and not is_offline:
        with op.batch_alter_table("moderation_rules", recreate="always") as batch_op:
            batch_op.create_check_constraint(
                "moderation_rules_kind_valid",
                "kind IN ('domain_blacklist','keyword_blacklist')",
            )
            batch_op.create_check_constraint(
                "moderation_rules_action_valid",
                "action IN ('block','flag')",
            )
    elif dialect_name != "sqlite":
        op.create_check_constraint(
            "moderation_rules_kind_valid",
            "moderation_rules",
            "kind IN ('domain_blacklist','keyword_blacklist')",
        )
        op.create_check_constraint(
            "moderation_rules_action_valid",
            "moderation_rules",
            "action IN ('block','flag')",
        )


def downgrade() -> None:
    context = op.get_context()
    dialect_name = context.dialect.name
    is_offline = context.as_sql

    if dialect_name == "sqlite" and not is_offline:
        with op.batch_alter_table("moderation_rules", recreate="always") as batch_op:
            batch_op.drop_constraint("moderation_rules_kind_valid", type_="check")
            batch_op.drop_constraint("moderation_rules_action_valid", type_="check")
    else:
        op.drop_constraint("moderation_rules_kind_valid", "moderation_rules", type_="check")
        op.drop_constraint("moderation_rules_action_valid", "moderation_rules", type_="check")
