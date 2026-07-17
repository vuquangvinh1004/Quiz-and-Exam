"""005_question_learning_outcome_code

Add learning_outcome_code to questions so each question can reference a
course learning outcome (CLO) defined on its question bank.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f2b1c8d4e902"
down_revision = "c4f2d0ab9e31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("questions") as batch_op:
        batch_op.drop_constraint("ck_questions_type", type_="check")
        batch_op.create_check_constraint(
            "ck_questions_type",
            "question_type IN ('MC', 'MA', 'BLANK', 'TF', 'SA', 'ES')",
        )
        batch_op.add_column(sa.Column("learning_outcome_code", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("questions") as batch_op:
        batch_op.drop_column("learning_outcome_code")
        batch_op.drop_constraint("ck_questions_type", type_="check")
        batch_op.create_check_constraint(
            "ck_questions_type",
            "question_type IN ('MC', 'MA', 'BLANK', 'SA')",
        )
