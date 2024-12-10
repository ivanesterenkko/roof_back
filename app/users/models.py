from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Company(Base):

    __tablename__ = 'company'

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    INN: Mapped[str] = mapped_column(nullable=False)

    users = relationship("Users", back_populates="company", cascade="all, delete-orphan")


class Users(Base):

    __tablename__ = 'users'

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    login: Mapped[str] = mapped_column(nullable=False)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False)

    company_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('company.id', ondelete='CASCADE'), nullable=False)

    company = relationship("Company", back_populates="users")
    projects = relationship("Projects", back_populates="user", cascade="all, delete-orphan")
    session = relationship("Sessions", back_populates="user", cascade="all, delete-orphan")

    def __str__(self):

        return f"Пользователь {self.login}"


class Sessions(Base):
    __tablename__ = 'sessions'

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jwt_token: Mapped[str] = mapped_column(nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    user = relationship("Users", back_populates="session")
