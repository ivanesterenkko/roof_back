from typing import List
import uuid
from sqlalchemy import JSON, UUID, Float, Integer, String, Tuple
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AccessoriesBD(Base):
    __tablename__ = 'accessory_bd'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    parent_type: Mapped[str] = mapped_column(String, nullable=False)
    overall_width: Mapped[float] = mapped_column(Float, nullable=False)
    useful_width: Mapped[float] = mapped_column(Float, nullable=False)
    overlap: Mapped[float] = mapped_column(Float, nullable=True)
    modulo: Mapped[float] = mapped_column(Float, nullable=True)
    material: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=True)

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
    len_wave: Mapped[float] = mapped_column(Float, nullable=False)
    min_length: Mapped[float] = mapped_column(Float, nullable=False)
    imp_sizes: Mapped[List[List[float]]] = mapped_column(JSON, nullable=True, default=list)

    projects = relationship("Projects", back_populates="roof", cascade="all, delete-orphan")


class Tariffs(Base):
    __tablename__ = 'tariff'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    limit_users: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)

    subscriptions = relationship("Subscriptions", back_populates="tariff")
