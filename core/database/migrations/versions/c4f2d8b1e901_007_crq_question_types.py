"""007_crq_question_types

Revision ID: c4f2d8b1e901
Revises: 7d8f4a1e9c55
Create Date: 2026-07-15 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f2d8b1e901"
down_revision: str | Sequence[str] | None = "7d8f4a1e9c55"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("questions", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_questions_type", type_="check")
        batch_op.create_check_constraint(
            "ck_questions_type",
            "question_type IN ('MC', 'MA', 'BLANK', 'TF', 'SA', 'ES', 'PR')",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("questions", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_questions_type", type_="check")
        batch_op.create_check_constraint(
            "ck_questions_type",
            "question_type IN ('MC', 'MA', 'BLANK', 'TF', 'SA', 'ES')",
        )
