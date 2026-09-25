"""new lower and unique index for category.name field

Revision ID: 9251abfc77b1
Revises: e073da9b8a87
Create Date: 2026-09-24 17:38:20.772415

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import func

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9251abfc77b1"
down_revision: str | Sequence[str] | None = "e073da9b8a87"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.create_index(
        op.f("uq_categories_name_lower"), "categories", [sa.literal_column("lower(name)")], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("uq_categories_name_lower"), table_name="categories")
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=True)
