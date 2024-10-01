from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Projects(Base):
    __tablename__ = 'project'

    id: Mapped[int] = mapped_column(primary_key=True)
    lines: Mapped[str] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)

    user = relationship("Users", back_populates="projects")
    slopes = relationship("Slopes", back_populates="project", cascade="all, delete-orphan")

class Slopes(Base):
    __tablename__ = 'slope'

    id: Mapped[int] = mapped_column(primary_key=True)
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

