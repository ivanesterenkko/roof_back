from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ARRAY, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Projects(Base):
    __tablename__ = 'project'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    step: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    datetime_created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    roof_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('roof.id', ondelete='CASCADE'), nullable=True)

    lines = relationship("Lines", back_populates="project", cascade="all, delete-orphan")
    slopes = relationship("Slopes", back_populates="project", cascade="all, delete-orphan")
    accessories = relationship("Accessories", back_populates="project", cascade="all, delete-orphan")
    materials = relationship("Materials", back_populates="project", cascade="all, delete-orphan")
    user = relationship("Users", back_populates="projects")
    roof = relationship("Roofs", back_populates="projects")
    points = relationship("Point", back_populates="project", cascade="all, delete-orphan")


class Point(Base):
    __tablename__ = 'point'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('project.id', ondelete='CASCADE'), nullable=False)

    lines_as_start = relationship("Lines", back_populates="start", foreign_keys='Lines.start_id', cascade="all, delete-orphan", lazy='joined')
    lines_as_end = relationship("Lines", back_populates="end", foreign_keys='Lines.end_id', cascade="all, delete-orphan", lazy='joined')
    point_slope = relationship("PointSlope", back_populates="point", cascade="all, delete-orphan")
    project = relationship("Projects", back_populates="points")


class Lines(Base):
    __tablename__ = 'line'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=True)
    length: Mapped[float] = mapped_column(Float, nullable=True)
    is_perimeter: Mapped[bool] = mapped_column(Boolean, nullable=False)

    start_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('point.id', ondelete='CASCADE'), nullable=False)
    end_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('point.id', ondelete='CASCADE'), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('project.id', ondelete='CASCADE'), nullable=False)

    start: Mapped['Point'] = relationship("Point", foreign_keys=[start_id], back_populates='lines_as_start', lazy='joined')
    end: Mapped['Point'] = relationship("Point", foreign_keys=[end_id], back_populates='lines_as_end', lazy='joined')

    lines_slope = relationship("LinesSlope", back_populates="line", cascade="all, delete-orphan")
    project = relationship("Projects", back_populates="lines")


class PointSlope(Base):
    __tablename__ = 'point_slope'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)

    parent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('point.id', ondelete='CASCADE'), nullable=False)
    slope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('slope.id', ondelete='CASCADE'), nullable=False)

    lines_as_start = relationship("LinesSlope", back_populates="start", foreign_keys='LinesSlope.start_id', cascade="all, delete-orphan", lazy='joined')
    lines_as_end = relationship("LinesSlope", back_populates="end", foreign_keys='LinesSlope.end_id', cascade="all, delete-orphan", lazy='joined')
    point = relationship("Point", back_populates="point_slope")
    length_slope = relationship("LengthSlope", back_populates="point", foreign_keys='LengthSlope.point_id', cascade="all, delete-orphan", lazy='joined')
    slope = relationship("Slopes", back_populates="points_slope")


class LinesSlope(Base):
    __tablename__ = 'line_slope'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=True)
    number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    length: Mapped[float] = mapped_column(Float, nullable=True)

    start_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('point_slope.id', ondelete='CASCADE'), nullable=False)
    end_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('point_slope.id', ondelete='CASCADE'), nullable=False)
    parent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('line.id', ondelete='CASCADE'), nullable=False)
    slope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('slope.id', ondelete='CASCADE'), nullable=False)

    start: Mapped['Point'] = relationship("PointSlope", foreign_keys=[start_id], back_populates='lines_as_start', lazy='joined')
    end: Mapped['Point'] = relationship("PointSlope", foreign_keys=[end_id], back_populates='lines_as_end', lazy='joined')

    line = relationship("Lines", back_populates="lines_slope")
    length_slope = relationship("LengthSlope", back_populates="line_slope", foreign_keys='LengthSlope.line_slope_id', cascade="all, delete-orphan", lazy='joined')
    slope = relationship("Slopes", back_populates="lines_slope")


class LengthSlope(Base):
    __tablename__ = 'length_slope'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    length: Mapped[float] = mapped_column(Float, nullable=True)

    point_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('point_slope.id', ondelete='CASCADE'), nullable=False)
    line_slope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('line_slope.id', ondelete='CASCADE'), nullable=False)
    slope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('slope.id', ondelete='CASCADE'), nullable=False)

    point: Mapped['Point'] = relationship("PointSlope", foreign_keys=[point_id], back_populates='length_slope', lazy='joined')
    line_slope: Mapped['LinesSlope'] = relationship("LinesSlope", foreign_keys=[line_slope_id], back_populates='length_slope', lazy='joined')
    slope = relationship("Slopes", back_populates="length_slope")


class Slopes(Base):
    __tablename__ = 'slope'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    area: Mapped[float] = mapped_column(Float, nullable=True)
    length: Mapped[float] = mapped_column(Float, nullable=True)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('project.id', ondelete='CASCADE'), nullable=False)

    project = relationship("Projects", back_populates="slopes")
    lines_slope = relationship("LinesSlope", back_populates="slope", cascade="all, delete-orphan")
    length_slope = relationship("LengthSlope", back_populates="slope", cascade="all, delete-orphan")
    cutouts = relationship("Cutouts", back_populates="slope", cascade="all, delete-orphan")
    sheets = relationship("Sheets", back_populates="slope", cascade="all, delete-orphan")
    points_slope = relationship("PointSlope", back_populates="slope", cascade="all, delete-orphan")


class Cutouts(Base):
    __tablename__ = 'cutout'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    slope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('slope.id', ondelete='CASCADE'), nullable=False)

    points = relationship("PointsCutout", back_populates="cutout", cascade="all, delete-orphan")
    slope = relationship("Slopes", back_populates="cutouts")


class PointsCutout(Base):
    __tablename__ = 'cutout_points'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)

    cutout_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('cutout.id', ondelete='CASCADE'), nullable=False)

    cutout = relationship("Cutouts", back_populates="points")


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
    type: Mapped[str] = mapped_column(String, nullable=False)
    length: Mapped[float] = mapped_column(Float, nullable=False)
    lines_length: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=True)
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
