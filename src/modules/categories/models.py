from datetime import datetime
from sqlalchemy import DateTime, String, func
from src.core.database import Base
from sqlalchemy.orm import Mapped, mapped_column

class Category(Base):
    """
    Modele SQLAlchemy pour la table 'categories'
    """
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#FAFAFA")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name} color={self.color}>"