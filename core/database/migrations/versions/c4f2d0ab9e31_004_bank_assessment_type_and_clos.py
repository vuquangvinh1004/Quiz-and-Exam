"""004_bank_assessment_type_and_clos

Add assessment_type and course_learning_outcomes metadata to question_banks.

Revision ID: c4f2d0ab9e31
Revises: b6d4e2f8c1aa
Create Date: 2026-06-30 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f2d0ab9e31"
down_revision: str | Sequence[str] | None = "b6d4e2f8c1aa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("question_banks") as batch_op:
        batch_op.add_column(sa.Column("assessment_type", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("course_learning_outcomes", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("question_banks") as batch_op:
        batch_op.drop_column("course_learning_outcomes")
        batch_op.drop_column("assessment_type")
