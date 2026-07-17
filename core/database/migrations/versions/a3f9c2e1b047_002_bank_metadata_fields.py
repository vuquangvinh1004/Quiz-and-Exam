"""002_bank_metadata_fields

Add optional metadata columns to question_banks table for exam export pre-fill.

Revision ID: a3f9c2e1b047
Revises: 10ab01a26fe9
Create Date: 2026-04-21 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f9c2e1b047"
down_revision: str | Sequence[str] | None = "10ab01a26fe9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("question_banks") as batch_op:
        batch_op.add_column(sa.Column("school", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("department", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("subject", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("course_code", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("exam_title", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("question_banks") as batch_op:
        batch_op.drop_column("exam_title")
        batch_op.drop_column("course_code")
        batch_op.drop_column("subject")
        batch_op.drop_column("department")
        batch_op.drop_column("school")
