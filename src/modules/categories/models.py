from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.modules.todos_categories.models import todos_categories

if TYPE_CHECKING:
    from src.modules.todos.models import Todo


class Category(Base):
    """
    Modele SQLAlchemy pour la table 'categories'
    """

    __tablename__ = "categories"

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#FAFAFA")

    __table_args__ = (Index("uq_categories_name_lower", func.lower(name), unique=True),)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    todos: Mapped[list["Todo"]] = relationship(
        secondary=todos_categories,
        back_populates="categories",
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name} color={self.color}>"
