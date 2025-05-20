from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Orders(Base):

    __tablename__ = 'order'

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False)

    subscription_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('subscription.id', ondelete='CASCADE'), nullable=True)

    subscription = relationship("Subscriptions", back_populates="order")


class Subscriptions(Base):

    __tablename__ = 'subscription'

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    expired_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    company_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('company.id', ondelete='CASCADE'), nullable=False)
    tariff_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('tariff.id'), nullable=True)

    company = relationship("Company", back_populates="subscription")
    tariff = relationship("Tariffs", back_populates="subscriptions")
    order = relationship("Orders", back_populates="subscription", cascade="all, delete-orphan")


class Company(Base):

    __tablename__ = 'company'

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    INN: Mapped[str] = mapped_column(nullable=False)
    OGRN: Mapped[str] = mapped_column(nullable=False)

    users = relationship("Users", back_populates="company", cascade="all, delete-orphan")
    subscription = relationship("Subscriptions", back_populates="company", cascade="all, delete-orphan")


class Users(Base):

    __tablename__ = 'users'

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    login: Mapped[str] = mapped_column(nullable=False, unique=True)
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
    device: Mapped[str] = mapped_column(nullable=False)
    name_device: Mapped[str] = mapped_column(nullable=False)
    city: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    user = relationship("Users", back_populates="session")
