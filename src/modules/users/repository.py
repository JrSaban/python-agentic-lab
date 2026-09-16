"""Repository Pattern pour l'accès aux données de User."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.users.models import User
from src.modules.users.schemas import UserCreate, UserUpdate


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        email: str | None = None,
        name: str | None = None,
        pseudo: str | None = None,
        is_active: bool | None = None,
        is_admin: bool | None = None,
    ) -> Sequence[User]:
        """Get all users"""
        query = select(User).offset(skip).limit(limit)
        query = self._apply_filters(
            query,
            email=email,
            name=name,
            pseudo=pseudo,
            is_active=is_active,
            is_admin=is_admin,
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_id(self, entity_id: int) -> User | None:
        """Get an user by its ID"""
        query = select(User).where(User.id == entity_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get an user by its email"""
        query = select(User).where(func.lower(User.email) == email.strip().lower())

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: UserCreate, hashed_password: str) -> User:
        """Create a new user."""
        user = User(
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
            pseudo=data.pseudo,
            hashed_password=hashed_password,
        )

        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def update(self, user: User, data: UserUpdate) -> User:
        """Update an existing user."""
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def update_password(self, user: User, hashed_password: str) -> User:
        """Update an existing user's password."""
        user.hashed_password = hashed_password

        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def set_active(self, user: User, is_active: bool) -> User:
        """Set an user's active status"""
        user.is_active = is_active

        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def set_admin(self, user: User, is_admin: bool) -> User:
        """Set an user's admin status"""
        user.is_admin = is_admin

        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def update_last_login_date(self, user: User) -> User:
        """Update an user's last login date"""
        user.last_login_at = datetime.now(UTC)

        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def count(
        self,
        email: str | None = None,
        name: str | None = None,
        pseudo: str | None = None,
        is_active: bool | None = None,
        is_admin: bool | None = None,
    ) -> int:
        """Count all users"""
        query = select(func.count(User.id))
        query = self._apply_filters(
            query,
            email=email,
            name=name,
            pseudo=pseudo,
            is_active=is_active,
            is_admin=is_admin,
        )
        result = await self.session.execute(query)
        return result.scalar_one()

    def _apply_filters(
        self,
        query: Select,
        email: str | None = None,
        name: str | None = None,
        pseudo: str | None = None,
        is_active: bool | None = None,
        is_admin: bool | None = None,
    ) -> Select:
        """Helper qui applique les filtres sur une requête."""
        if email is not None:
            query = query.where(User.email.ilike(f"%{email}%"))
        if name is not None:
            query = query.where(
                User.first_name.ilike(f"%{name}%") | User.last_name.ilike(f"%{name}%")
            )
        if pseudo is not None:
            query = query.where(User.pseudo.ilike(f"%{pseudo}%"))
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        if is_admin is not None:
            query = query.where(User.is_admin == is_admin)
        return query
