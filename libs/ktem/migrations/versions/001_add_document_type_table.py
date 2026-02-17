"""Add document_type table for custom document types.

Revision ID: 001_document_type
Revises:
Create Date: 2025-02-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_document_type"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_type",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, index=True, unique=True),
        sa.Column("display_name", sa.String(256), nullable=False),
        sa.Column("schema_def", sa.JSON(), server_default=sa.text("'[]'")),
        sa.Column(
            "extraction_prompt_template", sa.Text(), server_default=sa.text("''")
        ),
        sa.Column("classifier_keywords", sa.JSON(), server_default=sa.text("'{}'")),
        sa.Column("enable_pre_aggregation", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("user", sa.String(256), server_default=""),
    )


def downgrade() -> None:
    op.drop_table("document_type")
