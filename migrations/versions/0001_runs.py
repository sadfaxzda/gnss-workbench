"""Persist run identity, configuration and lifecycle."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("epoch_count", sa.Integer(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("runs")
