from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ARRAY, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

class Roofs(Base):
    __tablename__ = 'roof'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    overall_width: Mapped[float] = mapped_column(Float, nullable=False)
    useful_width: Mapped[float] = mapped_column(Float, nullable=False)
    overlap: Mapped[float] = mapped_column(Float, nullable=False)
    material: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[str] = mapped_column(String, nullable=False)
    min_length: Mapped[float] = mapped_column(Float, nullable=False)
    max_length: Mapped[float] = mapped_column(Float, nullable=False)

    projects = relationship("Projects", back_populates="roof")