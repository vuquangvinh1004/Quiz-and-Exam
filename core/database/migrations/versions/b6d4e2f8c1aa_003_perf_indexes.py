"""003_perf_indexes

Add performance indexes for dashboard/history hot queries.

Revision ID: b6d4e2f8c1aa
Revises: a3f9c2e1b047
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b6d4e2f8c1aa"
down_revision: Union[str, Sequence[str], None] = "a3f9c2e1b047"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("questions") as batch_op:
        batch_op.create_index("ix_questions_bank_id", ["bank_id"], unique=False)

    with op.batch_alter_table("quizzes") as batch_op:
        batch_op.create_index("ix_quizzes_bank_id", ["bank_id"], unique=False)

    with op.batch_alter_table("attempts") as batch_op:
        batch_op.create_index("ix_attempts_quiz_id", ["quiz_id"], unique=False)
        batch_op.create_index("ix_attempts_started_at", ["started_at"], unique=False)

    with op.batch_alter_table("quiz_questions") as batch_op:
        batch_op.create_index("ix_quiz_questions_question_id", ["question_id"], unique=False)

    with op.batch_alter_table("attempt_answers") as batch_op:
        batch_op.create_index("ix_attempt_answers_quiz_question_id", ["quiz_question_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("attempt_answers") as batch_op:
        batch_op.drop_index("ix_attempt_answers_quiz_question_id")

    with op.batch_alter_table("quiz_questions") as batch_op:
        batch_op.drop_index("ix_quiz_questions_question_id")

    with op.batch_alter_table("attempts") as batch_op:
        batch_op.drop_index("ix_attempts_started_at")
        batch_op.drop_index("ix_attempts_quiz_id")

    with op.batch_alter_table("quizzes") as batch_op:
        batch_op.drop_index("ix_quizzes_bank_id")

    with op.batch_alter_table("questions") as batch_op:
        batch_op.drop_index("ix_questions_bank_id")
