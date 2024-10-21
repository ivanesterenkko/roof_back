from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ARRAY, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

class Slopes(Base):
    __tablename__ = 'slope'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    lines_id: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('project.id'), nullable=False)

    project = relationship("Projects", back_populates="slopes")
    cutouts = relationship("Cutouts", back_populates="slope", cascade="all, delete-orphan")
    sheets = relationship("Sheets", back_populates="slope", cascade="all, delete-orphan")
