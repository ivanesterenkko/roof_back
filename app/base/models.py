import uuid
from sqlalchemy import UUID, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AccessoriesBD(Base):
    __tablename__ = 'accessory_bd'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    parent_type: Mapped[str] = mapped_column(String, nullable=False)
    length: Mapped[float] = mapped_column(Float, nullable=False)
    overlap: Mapped[float] = mapped_column(Float, nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False)

    accessories = relationship("Accessories", back_populates="accessory_base", cascade="all, delete-orphan")


class Roofs(Base):
    __tablename__ = 'roof'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    overall_width: Mapped[float] = mapped_column(Float, nullable=False)
    useful_width: Mapped[float] = mapped_column(Float, nullable=False)
    overlap: Mapped[float] = mapped_column(Float, nullable=False)
    max_length: Mapped[float] = mapped_column(Float, nullable=False)
    min_length: Mapped[float] = mapped_column(Float, nullable=False)

    projects = relationship("Projects", back_populates="roof", cascade="all, delete-orphan")


class Tariffs(Base):
    __tablename__ = 'tariff'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    limit_users: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)

    subscriptions = relationship("Subscriptions", back_populates="tariff")
