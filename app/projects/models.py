from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ARRAY, JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Projects(Base):
    __tablename__ = 'project'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    step: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    datetime_created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey('users.id'), nullable=False)
    roof_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey('roof.id'), nullable=True)
    
    lines = relationship("Lines", back_populates="project", cascade="all, delete-orphan")
    user = relationship("Users", back_populates="projects")
    roof = relationship("Roofs", back_populates="projects")
    slopes = relationship("Slopes", back_populates="project", cascade="all, delete-orphan")
    accessories = relationship("Accessories", back_populates="project", cascade="all, delete-orphan")
    materials = relationship("Materials", back_populates="project", cascade="all, delete-orphan")


class Lines(Base):
    __tablename__ = 'line'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=True)
    x_start: Mapped[float] = mapped_column(Float, nullable=True)
    y_start: Mapped[float] = mapped_column(Float, nullable=True)
    x_end: Mapped[float] = mapped_column(Float, nullable=True)
    y_end: Mapped[float] = mapped_column(Float, nullable=True)
    length: Mapped[float] = mapped_column(Float, nullable=False)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('project.id', ondelete='CASCADE'), nullable=False)

    project = relationship("Projects", back_populates="lines")
    lines_slope = relationship("LinesSlope", back_populates="line", cascade="all, delete-orphan")

class LinesSlope(Base):
    __tablename__ = 'line_slope'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    x_start: Mapped[float] = mapped_column(Float, nullable=True)
    y_start: Mapped[float] = mapped_column(Float, nullable=True)
    x_end: Mapped[float] = mapped_column(Float, nullable=True)
    y_end: Mapped[float] = mapped_column(Float, nullable=True)
    length: Mapped[float] = mapped_column(Float, nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)

    line_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('line.id', ondelete='CASCADE'), nullable=False)
    slope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('slope.id', ondelete='CASCADE'), nullable=False)

    line = relationship("Lines", back_populates="lines_slope")
    slope = relationship("Slopes", back_populates="lines_slope")

class Slopes(Base):
    __tablename__ = 'slope'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    area: Mapped[float] = mapped_column(Float, nullable=True)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('project.id', ondelete='CASCADE'), nullable=False)

    project = relationship("Projects", back_populates="slopes")
    lines_slope = relationship("LinesSlope", back_populates="slope", cascade="all, delete-orphan")
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
    x_start: Mapped[float] = mapped_column(Float, nullable=False)
    y_start: Mapped[float] = mapped_column(Float, nullable=False)
    length: Mapped[float] = mapped_column(Float, nullable=False)
    area_overall: Mapped[float] = mapped_column(Float, nullable=False)
    area_usefull: Mapped[float] = mapped_column(Float, nullable=False)

    slope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('slope.id', ondelete='CASCADE'), nullable=False)

    slope = relationship("Slopes", back_populates="sheets")

class Accessories(Base):
    __tablename__ = 'accessory'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parameters: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('project.id', ondelete='CASCADE'), nullable=False)
    lines_id: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)

    project = relationship("Projects", back_populates="accessories")

class Materials(Base):
    __tablename__ = 'material'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    material: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[str] = mapped_column(String, nullable=False)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('project.id', ondelete='CASCADE'), nullable=False)

    project = relationship("Projects", back_populates="materials")
