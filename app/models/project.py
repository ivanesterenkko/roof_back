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