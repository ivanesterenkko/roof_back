from datetime import datetime
import uuid
import string
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ARRAY, event, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session

from app.db import Base


class Projects(Base):
    __tablename__ = 'project'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    full_name_customer: Mapped[str] = mapped_column(String, nullable=False)
    is_company: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    customer_contacts: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    datetime_created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey('users.id'), nullable=False)
    
    lines = relationship("Lines", back_populates="project")
    user = relationship("Users", back_populates="projects")
    slopes = relationship("Slopes", back_populates="project", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.is_company:
            self.company_name = None

class Lines(Base):
    __tablename__ = 'line'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    x_start_projection: Mapped[float] = mapped_column(Float, nullable=False)
    y_start_projection: Mapped[float] = mapped_column(Float, nullable=False)
    x_end_projection: Mapped[float] = mapped_column(Float, nullable=False)
    y_end_projection: Mapped[float] = mapped_column(Float, nullable=False)
    x_start: Mapped[float] = mapped_column(Float, nullable=True)
    y_start: Mapped[float] = mapped_column(Float, nullable=True)
    x_end: Mapped[float] = mapped_column(Float, nullable=True)
    y_end: Mapped[float] = mapped_column(Float, nullable=True)
    length: Mapped[float] = mapped_column(Float, nullable=False)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('project.id'), nullable=False)

    project = relationship("Projects", back_populates="lines")
    # slope = relationship("Slopes", back_populates="lines")

class Slopes(Base):
    __tablename__ = 'slope'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    lines_id: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('project.id'), nullable=False)

    project = relationship("Projects", back_populates="slopes")
    # lines = relationship("Lines", back_populates="slope")
    roofs = relationship("Roofs", back_populates="slope", cascade="all, delete-orphan")

class Roofs(Base):
    __tablename__ = 'roof'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    points: Mapped[str] = mapped_column(nullable=False)
    lenght: Mapped[float] = mapped_column(nullable=False)
    square: Mapped[float] = mapped_column(nullable=False)

    slope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('slope.id'), nullable=False)

    slope = relationship("Slopes", back_populates="roofs")


