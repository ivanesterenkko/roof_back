from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Projects(Base):
    __tablename__ = 'project'

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    full_name_customer: Mapped[str] = mapped_column(String, nullable=False)
    is_company: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    customer_contacts: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    datetime_created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)

    user = relationship("Users", back_populates="projects")
    slopes = relationship("Slopes", back_populates="project", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.is_company:
            self.company_name = None

class Lines(Base):
    __tablename__ = 'line'

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    x_start: Mapped[float] = mapped_column(Float, nullable=False)
    y_start: Mapped[float] = mapped_column(Float, nullable=False)
    x_end: Mapped[float] = mapped_column(Float, nullable=False)
    y_end: Mapped[float] = mapped_column(Float, nullable=False)
    length: Mapped[float] = mapped_column(Float, nullable=False)
    project = relationship("Projects", back_populates="slopes")

class Slopes(Base):
    __tablename__ = 'slope'

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    points: Mapped[str] = mapped_column(nullable=False)
    hole_points: Mapped[str] = mapped_column(nullable=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('project.id'), nullable=False)

    project = relationship("Projects", back_populates="slopes")
    roofs = relationship("Roofs", back_populates="slope", cascade="all, delete-orphan")

class Roofs(Base):
    __tablename__ = 'roof'

    id: Mapped[int] = mapped_column(primary_key=True)
    points: Mapped[str] = mapped_column(nullable=False)
    lenght: Mapped[float] = mapped_column(nullable=False)
    square: Mapped[float] = mapped_column(nullable=False)
    slope_id: Mapped[int] = mapped_column(ForeignKey('slope.id', ondelete='CASCADE'), nullable=False)

    slope = relationship("Slopes", back_populates="roofs")

