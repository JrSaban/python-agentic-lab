"""backfill owner_id and created_by_id

Revision ID: 9e90d89d433e
Revises: 312759b2f0cc
Create Date: 2026-09-21 14:44:46.406106

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9e90d89d433e"
down_revision: str | Sequence[str] | None = "312759b2f0cc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    connection = op.get_bind()

    first_user = connection.execute(sa.text("SELECT min(id) as id FROM users")).scalar()
    total_todos = connection.execute(
        sa.text("SELECT count(*) FROM todos where owner_id is null")
    ).scalar_one()
    total_categories = connection.execute(
        sa.text("SELECT count(*) FROM categories where created_by_id is null")
    ).scalar_one()

    if first_user is None and (total_todos > 0 or total_categories > 0):
        raise RuntimeError(
            "Impossible de faire la migration: il y a des todos ou des categories sans utilisateur."
            " Veuillez créer un utilisateur et réessayer."
        )

    connection.execute(
        sa.text("UPDATE todos SET owner_id = :first_user WHERE owner_id IS NULL").bindparams(
            first_user=first_user
        )
    )
    connection.execute(
        sa.text(
            "UPDATE categories SET created_by_id = :first_user WHERE created_by_id IS NULL"
        ).bindparams(first_user=first_user)
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
