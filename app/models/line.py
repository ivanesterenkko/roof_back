from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ARRAY, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

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

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('project.id'), nullable=False)

    project = relationship("Projects", back_populates="lines")