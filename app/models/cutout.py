from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ARRAY, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

class Cutouts(Base):
    __tablename__ = 'cutout'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    x_coords: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
    y_coords: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)

    slope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('slope.id'), nullable=False)

    slope = relationship("Slopes", back_populates="cutouts")