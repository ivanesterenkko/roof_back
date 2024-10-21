from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ARRAY, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Projects(Base):
    __tablename__ = 'project'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    datetime_created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey('users.id'), nullable=False)
    roof_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey('roof.id'), nullable=True)
    
    lines = relationship("Lines", back_populates="project", cascade="all, delete-orphan")
    user = relationship("Users", back_populates="projects")
    roof = relationship("Roofs", back_populates="projects")
    slopes = relationship("Slopes", back_populates="project", cascade="all, delete-orphan")


class Lines(Base):
    __tablename__ = 'line'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=True)
    x_start_projection: Mapped[float] = mapped_column(Float, nullable=False)
    y_start_projection: Mapped[float] = mapped_column(Float, nullable=False)
    x_end_projection: Mapped[float] = mapped_column(Float, nullable=False)
    y_end_projection: Mapped[float] = mapped_column(Float, nullable=False)
    x_start: Mapped[float] = mapped_column(Float, nullable=True)
    y_start: Mapped[float] = mapped_column(Float, nullable=True)
    x_end: Mapped[float] = mapped_column(Float, nullable=True)
    y_end: Mapped[float] = mapped_column(Float, nullable=True)
    length: Mapped[float] = mapped_column(Float, nullable=False)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('project.id', ondelete='CASCADE'), nullable=False)

    project = relationship("Projects", back_populates="lines")

class Slopes(Base):
    __tablename__ = 'slope'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    lines_id: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('project.id', ondelete='CASCADE'), nullable=False)

    project = relationship("Projects", back_populates="slopes")
    cutouts = relationship("Cutouts", back_populates="slope", cascade="all, delete-orphan")
    sheets = relationship("Sheets", back_populates="slope", cascade="all, delete-orphan")

class Cutouts(Base):
    __tablename__ = 'cutout'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    x_coords: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
    y_coords: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)

    slope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('slope.id', ondelete='CASCADE'), nullable=False)

    slope = relationship("Slopes", back_populates="cutouts")

class Sheets(Base):
    __tablename__ = 'sheet'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    x_start: Mapped[float] = mapped_column(Float, nullable=False)
    y_start: Mapped[float] = mapped_column(Float, nullable=False)
    length: Mapped[float] = mapped_column(Float, nullable=False)
    area: Mapped[float] = mapped_column(Float, nullable=False)

    slope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('slope.id', ondelete='CASCADE'), nullable=False)

    slope = relationship("Slopes", back_populates="sheets")

