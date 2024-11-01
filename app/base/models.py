import uuid
from sqlalchemy import UUID, Float, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AccessoriesBD(Base):
    __tablename__ = 'accessory_bd'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    sale: Mapped[float] = mapped_column(nullable=False)
    
class Roofs(Base):
    __tablename__ = 'roof'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    overall_width: Mapped[float] = mapped_column(Float, nullable=False)
    useful_width: Mapped[float] = mapped_column(Float, nullable=False)
    overlap: Mapped[float] = mapped_column(Float, nullable=False)
    min_length: Mapped[float] = mapped_column(Float, nullable=False)
    max_length: Mapped[float] = mapped_column(Float, nullable=False)

    projects = relationship("Projects", back_populates="roof")

    
