"""006_problem_rubric_templates

Revision ID: 7d8f4a1e9c55
Revises: f2b1c8d4e902
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7d8f4a1e9c55"
down_revision: Union[str, Sequence[str], None] = "f2b1c8d4e902"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "question_rubric_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("template_payload", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bank_id"], ["question_banks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bank_id", "name", name="uq_question_rubric_templates_bank_name"),
    )
    op.create_index(
        "ix_question_rubric_templates_bank_id",
        "question_rubric_templates",
        ["bank_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_question_rubric_templates_bank_id", table_name="question_rubric_templates")
    op.drop_table("question_rubric_templates")

